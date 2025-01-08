# health-api/src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from kafka import KafkaAdminClient
from kubernetes import client, config
import requests
import logging
import os
from typing import Dict, Any
from datetime import datetime, timedelta

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load k8s config when running in cluster
config.load_incluster_config()
v1 = client.CoreV1Api()

def parse_message_rate(metrics_text: str) -> float:
    """Extract message rate from Kafka metrics"""
    try:
        # Look for messagesin metrics for raw-sensor-data topic
        for line in metrics_text.split('\n'):
            if 'kafka_server_brokertopicmetrics_messagesin_total{topic="raw-sensor-data"}' in line:
                return float(line.split()[1])
    except Exception as e:
        logger.error(f"Failed to parse message rate: {e}")
    return 0

@app.get("/health/kafka")
async def kafka_health() -> Dict[str, Any]:
    try:
        admin = KafkaAdminClient(
            bootstrap_servers='iot-kafka-brokers.kafka.svc.cluster.local:9092',
            client_id='health-checker'
        )
        topics = admin.list_topics()
        
        # Get message rates
        metrics_response = requests.get(
            "http://kafka-metrics.kafka:9404/metrics",
            timeout=3
        )
        message_rate = parse_message_rate(metrics_response.text)
        
        return {
            "status": "healthy",
            "topics": len(topics),
            "message_rate": message_rate,
            "details": {
                "topics": topics
            }
        }
    except Exception as e:
        logger.error(f"Kafka health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/health/timescaledb")
async def timescaledb_health() -> Dict[str, Any]:
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        with conn.cursor() as cur:
            # Get active sensors in last minute
            cur.execute("""
                SELECT COUNT(DISTINCT sensor_id) 
                FROM sensor_data 
                WHERE time > NOW() - INTERVAL '1 minute'
            """)
            active_count = cur.fetchone()[0]
            
            # Get total record count
            cur.execute("SELECT count(*) FROM sensor_data")
            total_count = cur.fetchone()[0]
            
        conn.close()
        return {
            "status": "healthy", 
            "active_sensors": active_count,
            "total_records": total_count
        }
    except Exception as e:
        logger.error(f"TimescaleDB health check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/health/flink")
async def flink_health() -> Dict[str, Any]:
    try:
        # Get job status
        response = requests.get(
            "http://flink-jobmanager.flink:8081/jobs/overview", 
            timeout=3
        )
        jobs = response.json()
        
        # Get metrics
        metrics_response = requests.get(
            "http://flink-jobmanager.flink:8081/metrics",
            timeout=3
        )
        metrics = metrics_response.json()
        
        # Calculate average processing latency
        processing_delay = next(
            (m for m in metrics if m["id"] == "processing-delay-ms"),
            {"value": 0}
        )["value"]
        
        return {
            "status": "healthy",
            "running_jobs": len([j for j in jobs["jobs"] if j["state"] == "RUNNING"]),
            "processing_latency": processing_delay,
            "details": jobs
        }
    except Exception as e:
        logger.error(f"Flink health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/health/sensors")
async def sensors_health() -> Dict[str, Any]:
    try:
        response = requests.get(
            "http://sensor-backend.sensor-backend:8000/status",
            timeout=3
        )
        sensor_data = response.json()
        
        return {
            "status": "healthy",
            "active_sensors": len(sensor_data.get("active_sensors", [])),
            "details": sensor_data
        }
    except Exception as e:
        logger.error(f"Sensor health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    try:
        # Get Kafka metrics
        kafka_response = await kafka_health()
        message_rate = kafka_response.get("message_rate", 0)
        
        # Get active sensors (prioritize real-time backend count)
        sensor_response = await sensors_health()
        active_sensors = sensor_response.get("active_sensors", 0)
        
        # If sensor backend is down, fallback to database count
        if active_sensors == 0:
            db_response = await timescaledb_health()
            active_sensors = db_response.get("active_sensors", 0)
        
        # Get Flink metrics
        flink_response = await flink_health()
        
        # Count alerts from anomaly detection
        alerts = sum(
            1 for j in flink_response["details"].get("jobs", [])
            if j.get("alerts", 0) > 0
        )
        
        return {
            "sensorCount": active_sensors,
            "messageRate": round(message_rate, 2),
            "processingLatency": flink_response.get("processing_latency", 0),
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))