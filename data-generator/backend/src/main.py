import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from kafka_utils import KafkaWrapper
from generator import IndustrialSensorGenerator
from typing import Dict, Set
import asyncio
import os
import logging
from time import time
from pydantic import BaseModel

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka-service.kafka.svc.cluster.local:9092')

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
sensor_generator = IndustrialSensorGenerator()
kafka = KafkaWrapper(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

try:
    logging.info("Attempting test message to Kafka....")
    kafka.send_message(
        'raw-sensor-data',
        {
            "type": "startup",
            "message": "Sensor generator initialized",
            "timestamp": time()
        }
    )
    logging.info(f"Successfully connected to Kafka\n{kafka.__dict__}")
except Exception as e:
    logging.error(f"Failed to connect to Kafka on startup: {e}")

active_websockets: Set[int] = set()  # Store WebSocket IDs instead of objects
websocket_instances: Dict[int, WebSocket] = {}  # Map IDs to WebSocket instances
next_ws_id = 0

class ConfigureRequest(BaseModel):
    num_sensors: int
    frequency_hz: float

class AnomalyRequest(BaseModel):
    sensor_ids: list[str]
    anomaly_type: str

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global next_ws_id
    # Accept the connection
    await websocket.accept()
    
    # Assign an ID to this websocket
    ws_id = next_ws_id
    next_ws_id += 1
    
    # Store the websocket
    active_websockets.add(ws_id)
    websocket_instances[ws_id] = websocket
    
    try:
        while True:
            # Wait for messages but don't do anything with them
            await websocket.receive_text()
    except:
        # Clean up on disconnection
        active_websockets.discard(ws_id)
        websocket_instances.pop(ws_id, None)

@app.post("/configure")
async def configure_generator(config: ConfigureRequest):
    """Configure the sensor generator with number of sensors and frequency"""
    num_sensors = config.num_sensors
    frequency_hz = config.frequency_hz
    
    # Update the current frequency
    app.current_frequency = frequency_hz
    
    # Update sensors
    current_sensors = set(sensor_generator.sensor_configs.keys())
    desired_sensors = {f"sensor_{i}" for i in range(num_sensors)}
    
    # Remove extra sensors
    for sensor_id in current_sensors - desired_sensors:
        sensor_generator.remove_sensor(sensor_id)
    
    # Add new sensors
    for sensor_id in desired_sensors - current_sensors:
        sensor_generator.add_sensor(sensor_id)
    
    # Start data generation if not already running
    if not hasattr(app, "generation_task"):
        app.generation_task = asyncio.create_task(generate_data())
    
    return {"status": "configured", "sensor_count": num_sensors, "frequency": frequency_hz}

@app.post("/inject-anomaly")
async def inject_anomaly(config: AnomalyRequest):
    """Inject anomalies into specified sensors"""
    for sensor_id in config.sensor_ids:
        sensor_generator.inject_anomaly(sensor_id, config.anomaly_type)
    
    return {"status": "anomaly_injected"}

async def generate_data():
    """Generate and broadcast sensor data"""
    while True:
        current_frequency = getattr(app, "current_frequency", 1.0)  # Default to 1 Hz if not set
        
        for sensor_id in sensor_generator.sensor_configs.keys():
            reading = sensor_generator.generate_reading(sensor_id)
            
            # Send to Kafka
            kafka.send_message(
                'raw-sensor-data',
                reading,
                partition=hash(sensor_id) % 3  # Assuming 3 partitions
            )
            
            # Send to WebSocket clients
            for ws_id in list(active_websockets):  # Create a copy of the set for iteration
                try:
                    websocket = websocket_instances.get(ws_id)
                    if websocket:
                        await websocket.send_json({
                            "type": "sensor_reading",
                            "data": reading
                        })
                except Exception as e:
                    logging.error(f"Error sending to websocket {ws_id}: {e}")
                    active_websockets.discard(ws_id)
                    websocket_instances.pop(ws_id, None)
        
        # Send sensor states
        states = sensor_generator.get_sensor_states()
        for ws_id in list(active_websockets):
            try:
                websocket = websocket_instances.get(ws_id)
                if websocket:
                    await websocket.send_json({
                        "type": "sensor_states",
                        "data": states
                    })
            except Exception as e:
                logging.error(f"Error sending states to websocket {ws_id}: {e}")
                active_websockets.discard(ws_id)
                websocket_instances.pop(ws_id, None)
        
        await asyncio.sleep(1 / current_frequency)


_startup_complete = False

async def startup_event():
    """Send test messages on startup"""
    global _startup_complete
    
    if _startup_complete:
        return
        
    try:
        logging.info("Sending test messages to verify Kafka connectivity...")
        test_sensor_id = "test_sensor_0"
        sensor_generator.add_sensor(test_sensor_id, is_test=True)
        reading = sensor_generator.generate_reading(test_sensor_id, is_test=True)
        
        success = kafka.send_message(
            'raw-sensor-data',
            reading,
            partition=0
        )
        
        if success:
            logging.info("Test message sent successfully")
            _startup_complete = True
        else:
            logging.error("Failed to send test message")
                
    except Exception as e:
        logging.error(f"Error during startup test messages: {e}")
        raise

app.add_event_handler("startup", startup_event)
