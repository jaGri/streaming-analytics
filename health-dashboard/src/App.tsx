import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Activity, Server, Database, MessageSquare } from 'lucide-react';

interface HealthData {
  status: string;
  details?: any;
}

interface Metrics {
  sensorCount: number;
  messageRate: number;
  processingLatency: number;
  alerts: number;
}

const MetricCard: React.FC<{
  title: string;
  value: number;
  unit?: string;
  className?: string;
}> = ({ title, value, unit = "", className = "" }) => (
  <div className={`rounded-lg p-4 ${className}`}>
    <div className="text-sm font-medium mb-1">{title}</div>
    <div className="text-2xl font-bold">
      {value.toLocaleString()}
      {unit && <span className="text-lg ml-1">{unit}</span>}
    </div>
  </div>
);

const App = () => {
  const [healthData, setHealthData] = useState<Record<string, HealthData>>({
    kafka: { status: 'unhealthy' },
    timescaledb: { status: 'unhealthy' },
    flink: { status: 'unhealthy' },
    sensors: { status: 'unhealthy' }
  });

  const [metrics, setMetrics] = useState<Metrics>({
    sensorCount: 0,
    messageRate: 0,
    processingLatency: 0,
    alerts: 0
  });

  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        // Fetch health status for each service
        const services = ['kafka', 'timescaledb', 'flink', 'sensors'];
        const results = await Promise.all(
          services.map(service =>
            fetch(`/api/health/${service}`)
              .then(res => res.json())
              .catch(() => ({ status: 'unhealthy' }))
          )
        );
        
        setHealthData(
          services.reduce((acc, service, idx) => ({
            ...acc,
            [service]: results[idx]
          }), {})
        );

        // Fetch metrics
        const metricsResponse = await fetch('/api/metrics');
        if (metricsResponse.ok) {
          const metricsData = await metricsResponse.json();
          setMetrics(metricsData);
        }
        
        setLastUpdated(new Date());
      } catch (error) {
        console.error('Failed to fetch health data:', error);
      }
    };

    // Initial fetch
    fetchHealth();
    
    // Poll every 5 seconds
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const getServiceIcon = (service: string) => {
    switch (service) {
      case 'kafka':
        return <MessageSquare className="w-5 h-5" />;
      case 'timescaledb':
        return <Database className="w-5 h-5" />;
      case 'flink':
        return <Activity className="w-5 h-5" />;
      case 'sensors':
        return <Server className="w-5 h-5" />;
      default:
        return null;
    }
  };

  const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
    if (status === 'healthy') {
      return <CheckCircle2 className="w-6 h-6 text-green-500" />;
    }
    if (status === 'degraded') {
      return <AlertTriangle className="w-6 h-6 text-yellow-500" />;
    }
    return <XCircle className="w-6 h-6 text-red-500" />;
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900">System Health Dashboard</h1>
            <div className="text-sm text-gray-500">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            {Object.entries(healthData).map(([service, data]) => (
              <div key={service} 
                   className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center space-x-3">
                  <div className="text-gray-600">
                    {getServiceIcon(service)}
                  </div>
                  <span className="capitalize font-medium">{service}</span>
                </div>
                <StatusIcon status={data?.status || 'unhealthy'} />
              </div>
            ))}
          </div>

          <h2 className="text-xl font-semibold mb-4">System Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Active Sensors"
              value={metrics.sensorCount}
              className="bg-blue-50 text-blue-900"
            />
            
            <MetricCard
              title="Messages/sec"
              value={metrics.messageRate}
              unit="msg/s"
              className="bg-green-50 text-green-900"
            />
            
            <MetricCard
              title="Processing Latency"
              value={metrics.processingLatency}
              unit="ms"
              className="bg-purple-50 text-purple-900"
            />
            
            <MetricCard
              title="Active Alerts"
              value={metrics.alerts}
              className="bg-red-50 text-red-900"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;