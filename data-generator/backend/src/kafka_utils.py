# data-sources/sensor-generator/kafka_utils.py
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import logging
import time
from typing import Optional, Dict, Any

class KafkaWrapper:
    def __init__(self, bootstrap_servers: str, retries: int = 3):
        self.bootstrap_servers = bootstrap_servers
        self.retries = retries
        self.producer: Optional[KafkaProducer] = None
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing KafkaWrapper with bootstrap_servers: {bootstrap_servers}")
        
    def connect(self) -> bool:
        """Establish connection to Kafka with retries"""
        for attempt in range(self.retries):
            try:
                self.logger.info(f"Attempting to connect to Kafka (attempt {attempt + 1}/{self.retries})")
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers.split(','),
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',  # Wait for all replicas
                    retries=3,   # Retry sending messages
                    retry_backoff_ms=1000,  # Backoff between retries
                    max_in_flight_requests_per_connection=1,  # Preserve ordering
                    compression_type='gzip'  # Compress messages
                )
                self.logger.info("Successfully connected to Kafka")
                return True
            except KafkaError as e:
                self.logger.error(f"Kafka connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        return False
    
    def send_message(self, topic: str, message: Dict[str, Any], 
                    partition: Optional[int] = None) -> bool:
        """Send message to Kafka with retries"""
        if not self.producer:
            self.logger.info("No producer found, attempting to connect...")
            if not self.connect():
                return False
                
        try:
            self.logger.info(f"Sending message to topic {topic}")
            future = self.producer.send(
                topic,
                value=message,
                partition=partition
            )
            # Wait for the message to be sent
            future.get(timeout=10)
            self.logger.info(f"Successfully sent message to topic {topic}")
            return True
        except KafkaError as e:
            self.logger.error(f"Failed to send message to topic {topic}: {str(e)}")
            # Try to reconnect
            self.connect()
            return False