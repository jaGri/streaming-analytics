import React, { useEffect, useState, useCallback } from 'react';
import { AlertTriangle, Activity } from 'lucide-react';

interface SensorReading {
  sensor_id: string;
  temperature: number;
  vibration: number;
  pressure: number;
  operational_state: string;
  maintenance_needed: boolean;
  timestamp: number;
}

interface WebSocketMessage {
  type: 'sensor_reading' | 'sensor_states';
  data: SensorReading;
}

const App: React.FC = () => {
  const [numSensors, setNumSensors] = useState(3);
  const [frequency, setFrequency] = useState(1);
  const [readings, setReadings] = useState<Record<string, SensorReading>>({});
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const wsUrl = `ws://${window.location.hostname}:30080/ws`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('Connected to WebSocket');
      setConnected(true);
    };

    websocket.onclose = () => {
      console.log('Disconnected from WebSocket');
      setConnected(false);
    };

    websocket.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      if (message.type === 'sensor_reading') {
        setReadings(prev => ({
          ...prev,
          [message.data.sensor_id]: message.data
        }));
      }
    };

    return () => {
      websocket.close();
    };
  }, []);

  const updateConfiguration = useCallback(async () => {
    try {
      const response = await fetch('/api/configure', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          num_sensors: numSensors,
          frequency_hz: frequency,
        }),
      });
      if (!response.ok) throw new Error('Configuration failed');
    } catch (error) {
      console.error('Error configuring sensors:', error);
    }
  }, [numSensors, frequency]);

  const injectAnomaly = useCallback(async (sensorId: string, anomalyType: string) => {
    try {
      const response = await fetch('/api/inject-anomaly', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sensor_ids: [sensorId],
          anomaly_type: anomalyType,
        }),
      });
      if (!response.ok) throw new Error('Failed to inject anomaly');
    } catch (error) {
      console.error('Error injecting anomaly:', error);
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Sensor Data Generator</h1>
            <div className="flex items-center space-x-2">
              <span className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span className="text-sm text-gray-600">{connected ? 'Connected' : 'Disconnected'}</span>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">Number of Sensors</label>
              <input
                type="range"
                min="1"
                max="20"
                value={numSensors}
                onChange={(e) => setNumSensors(parseInt(e.target.value))}
                className="w-full"
              />
              <span className="text-sm text-gray-600">{numSensors} sensors</span>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Update Frequency</label>
              <input
                type="range"
                min="0.1"
                max="10"
                step="0.1"
                value={frequency}
                onChange={(e) => setFrequency(parseFloat(e.target.value))}
                className="w-full"
              />
              <span className="text-sm text-gray-600">{frequency} Hz</span>
            </div>
          </div>
          <button
            onClick={updateConfiguration}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Apply Configuration
          </button>
        </div>

        {/* Sensor Readings */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(readings).map(([sensorId, reading]) => (
            <div key={sensorId} className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold">{sensorId}</h2>
                <div className="flex space-x-2">
                  {reading.maintenance_needed && (
                    <AlertTriangle className="w-5 h-5 text-yellow-500" />
                  )}
                  {reading.operational_state === 'anomaly' && (
                    <Activity className="w-5 h-5 text-red-500" />
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Temperature</span>
                  <span>{reading.temperature.toFixed(1)}°C</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Vibration</span>
                  <span>{reading.vibration.toFixed(3)} m/s²</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Pressure</span>
                  <span>{reading.pressure.toFixed(1)} kPa</span>
                </div>
              </div>
              <div className="mt-4 flex space-x-2">
                <button
                  onClick={() => injectAnomaly(sensorId, 'temperature_spike')}
                  className="px-3 py-1 bg-red-100 text-red-800 rounded text-sm hover:bg-red-200"
                >
                  Temp Spike
                </button>
                <button
                  onClick={() => injectAnomaly(sensorId, 'vibration_fault')}
                  className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded text-sm hover:bg-yellow-200"
                >
                  Vibration Fault
                </button>
                <button
                  onClick={() => injectAnomaly(sensorId, 'pressure_drop')}
                  className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm hover:bg-blue-200"
                >
                  Pressure Drop
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default App;