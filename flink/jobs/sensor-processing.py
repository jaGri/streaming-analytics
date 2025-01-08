from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.common.time import Time
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_kafka_source(t_env):
    """Create Kafka source table with sensor data"""
    return t_env.execute_sql("""
        CREATE TABLE sensor_data (
            sensor_id STRING,
            temperature DOUBLE,
            vibration DOUBLE,
            pressure DOUBLE,
            operational_state STRING,
            maintenance_needed BOOLEAN,
            is_test BOOLEAN,
            `timestamp` TIMESTAMP(3),
            WATERMARK FOR `timestamp` AS `timestamp` - INTERVAL '5' SECONDS
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'raw-sensor-data',
            'properties.bootstrap.servers' = 'iot-kafka-brokers.kafka.svc.cluster.local:9092',
            'properties.group.id' = 'flink-sensor-processor',
            'properties.auto.offset.reset' = 'latest',
            'scan.startup.mode' = 'group-offsets',
            'format' = 'json'
        )
    """)

def create_kafka_sinks(t_env):
    """Create Kafka sink tables for processed data"""
    # Sink for basic statistics
    t_env.execute_sql("""
        CREATE TABLE stats_sink (
            window_start TIMESTAMP(3),
            window_end TIMESTAMP(3),
            sensor_id STRING,
            avg_temp DOUBLE,
            avg_vibration DOUBLE,
            avg_pressure DOUBLE,
            alerts_count BIGINT
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'sensor-stats',
            'properties.bootstrap.servers' = 'iot-kafka-brokers.kafka.svc.cluster.local:9092',
            'format' = 'json'
        )
    """)
    
    # Sink for anomaly detection
    t_env.execute_sql("""
        CREATE TABLE anomaly_sink (
            sensor_id STRING,
            anomaly_type STRING,
            severity DOUBLE,
            detection_time TIMESTAMP(3)
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'sensor-anomalies',
            'properties.bootstrap.servers' = 'iot-kafka-brokers.kafka.svc.cluster.local:9092',
            'format' = 'json'
        )
    """)
    
    # Sink for TimescaleDB
    t_env.execute_sql("""
        CREATE TABLE timescale_sink (
            window_start TIMESTAMP(3),
            window_end TIMESTAMP(3),
            sensor_id STRING,
            avg_temp DOUBLE,
            avg_vibration DOUBLE,
            avg_pressure DOUBLE,
            alerts_count BIGINT,
            PRIMARY KEY (window_start, window_end, sensor_id) NOT ENFORCED
        ) WITH (
            'connector' = 'jdbc',
            'url' = 'jdbc:postgresql://timescaledb.timeseriesdb:5432/sensordata',
            'table-name' = 'sensor_aggregates',
            'username' = 'tsdbadmin',
            'password' = 'P@ssw0rd'
        )
    """)

def main():
    # Set up the streaming environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(4)
    env.enable_checkpointing(60000)  # 60 seconds
    
    settings = EnvironmentSettings.new_instance() \
        .in_streaming_mode() \
        .build()
    
    t_env = StreamTableEnvironment.create(env, settings)
    
    # Create tables
    create_kafka_source(t_env)
    create_kafka_sinks(t_env)
    
    # Process data - 1-minute window aggregation
    t_env.execute_sql("""
        INSERT INTO stats_sink
        SELECT 
            window_start,
            window_end,
            sensor_id,
            AVG(temperature) as avg_temp,
            AVG(vibration) as avg_vibration,
            AVG(pressure) as avg_pressure,
            COUNT(*) FILTER (WHERE operational_state = 'anomaly' OR maintenance_needed = true) as alerts_count
        FROM TABLE(
            TUMBLE(TABLE sensor_data, DESCRIPTOR(`timestamp`), INTERVAL '1' MINUTE))
        GROUP BY window_start, window_end, sensor_id
    """)
    
    # Detect anomalies using simple thresholds
    t_env.execute_sql("""
        INSERT INTO anomaly_sink
        SELECT
            sensor_id,
            CASE 
                WHEN temperature > 85 THEN 'temperature_high'
                WHEN vibration > 0.5 THEN 'vibration_high'
                WHEN pressure < 80 THEN 'pressure_low'
                ELSE 'unknown'
            END as anomaly_type,
            CASE
                WHEN temperature > 85 THEN (temperature - 85) / 15
                WHEN vibration > 0.5 THEN (vibration - 0.5) / 0.5
                WHEN pressure < 80 THEN (80 - pressure) / 20
                ELSE 0
            END as severity,
            `timestamp` as detection_time
        FROM sensor_data
        WHERE operational_state = 'anomaly'
    """)
    
    # Store aggregations in TimescaleDB
    t_env.execute_sql("""
        INSERT INTO timescale_sink
        SELECT 
            window_start,
            window_end,
            sensor_id,
            avg_temp,
            avg_vibration,
            avg_pressure,
            alerts_count
        FROM stats_sink
    """)

if __name__ == '__main__':
    main()