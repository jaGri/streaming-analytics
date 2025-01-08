from dataclasses import dataclass
import numpy as np
from typing import Dict, List, Optional
import random
import time
import logging

@dataclass
class SensorConfig:
    base_temperature: float
    base_vibration: float
    base_pressure: float
    noise_level: float
    drift_rate: float
    maintenance_cycle: int  # Hours until maintenance needed
    last_maintenance: float  # Timestamp of last maintenance
    
class IndustrialSensorGenerator:
    def __init__(self):
        self.sensor_configs: Dict[str, SensorConfig] = {}
        self.anomaly_states: Dict[str, dict] = {}
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)
        
    def add_sensor(self, sensor_id: str, is_test: bool = False):
        """Initialize a new sensor with realistic baseline parameters"""
        if is_test:
            # Test sensors have fixed parameters for verification
            self.sensor_configs[sensor_id] = SensorConfig(
                base_temperature=70.0,
                base_vibration=0.2,
                base_pressure=100.0,
                noise_level=0.01,
                drift_rate=0.001,
                maintenance_cycle=168,  # 1 week
                last_maintenance=time.time()
            )
        else:
            self.sensor_configs[sensor_id] = SensorConfig(
                base_temperature=random.uniform(60, 80),
                base_vibration=random.uniform(0.1, 0.3),
                base_pressure=random.uniform(90, 110),
                noise_level=random.uniform(0.02, 0.05),
                drift_rate=random.uniform(0.001, 0.003),
                maintenance_cycle=random.randint(120, 240),  # 5-10 days
                last_maintenance=time.time()
            )
            
        self.anomaly_states[sensor_id] = {
            "active": False,
            "type": None,
            "severity": 0.0,
            "duration": 0
        }
        
    def generate_reading(self, sensor_id: str, is_test: bool = False) -> dict:
        """Generate a single sensor reading with realistic patterns"""
        if sensor_id not in self.sensor_configs:
            raise ValueError(f"Unknown sensor: {sensor_id}")
            
        config = self.sensor_configs[sensor_id]
        anomaly = self.anomaly_states[sensor_id]
        
        # Calculate time-based effects
        elapsed_time = time.time() - self.start_time
        hours_since_maintenance = (time.time() - config.last_maintenance) / 3600
        maintenance_factor = min(1.0, hours_since_maintenance / config.maintenance_cycle)
        
        # Base readings with noise and maintenance degradation
        temp = config.base_temperature + np.random.normal(0, config.noise_level)
        temp += config.drift_rate * elapsed_time * maintenance_factor
        
        vibration = config.base_vibration + np.random.normal(0, config.noise_level)
        vibration += config.drift_rate * elapsed_time * maintenance_factor * 2
        
        pressure = config.base_pressure + np.random.normal(0, config.noise_level)
        pressure -= config.drift_rate * elapsed_time * maintenance_factor
        
        # Apply daily patterns if not a test reading
        if not is_test:
            hour_of_day = time.localtime().tm_hour
            # Simulate increased load during working hours
            if 8 <= hour_of_day <= 18:
                temp += random.uniform(2, 5)
                vibration += random.uniform(0.05, 0.1)
                pressure += random.uniform(5, 10)
        
        # Apply anomaly if active
        if anomaly["active"]:
            anomaly_elapsed = time.time() - anomaly["start_time"]
            if anomaly_elapsed > anomaly["duration"]:
                anomaly["active"] = False
            else:
                severity = anomaly["severity"]
                if anomaly["type"] == "temperature_spike":
                    temp += 20 * severity
                elif anomaly["type"] == "vibration_fault":
                    vibration += 1.5 * severity
                elif anomaly["type"] == "pressure_drop":
                    pressure -= 30 * severity
        
        return {
            "sensor_id": sensor_id,
            "timestamp": time.time(),
            "temperature": round(temp, 2),
            "vibration": round(vibration, 3),
            "pressure": round(pressure, 1),
            "operational_state": "anomaly" if anomaly["active"] else "normal",
            "maintenance_needed": maintenance_factor > 0.8,
            "is_test": is_test
        }
    
    def remove_sensor(self, sensor_id: str):
        """Remove a sensor from the generator"""
        if sensor_id in self.sensor_configs:
            del self.sensor_configs[sensor_id]
            del self.anomaly_states[sensor_id]

    def inject_anomaly(self, sensor_id: str, anomaly_type: str):
        """Inject an anomaly into a sensor"""
        if sensor_id not in self.sensor_configs:
            raise ValueError(f"Unknown sensor: {sensor_id}")
            
        self.anomaly_states[sensor_id] = {
            "active": True,
            "type": anomaly_type,
            "severity": random.uniform(0.5, 1.0),
            "duration": random.randint(10, 30),
            "start_time": time.time()
        }
        
    def get_sensor_states(self) -> dict:
        """Get current states of all sensors"""
        return {
            sensor_id: {
                "anomaly_active": self.anomaly_states[sensor_id]["active"],
                "anomaly_type": self.anomaly_states[sensor_id]["type"]
            }
            for sensor_id in self.sensor_configs
        }