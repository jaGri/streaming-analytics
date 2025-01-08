$ErrorActionPreference = "Stop"

# If monitoring namespace exists, delete it
kubectl delete namespace monitoring

# Create monitoring namespace
kubectl apply -f 01-namespace.yaml

# Install Prometheus Operator
# Download and modify bundle yaml
$bundle = Invoke-WebRequest https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
$bundle.Content | ForEach-Object { $_ -replace 'namespace: default', 'namespace: monitoring' } | Set-Content ./modified-bundle.yaml
# Apply modified bundle
kubectl apply --server-side -f ./modified-bundle.yaml -n monitoring

# Wait for operator to be ready
kubectl wait deployment/prometheus-operator --for=condition=Available=True -n monitoring --timeout=300s

# Apply monitoring configurations
kubectl apply -f 02-prometheus-alerts.yaml -n monitoring
kubectl apply -f 03-prometheus.yaml -n monitoring
kubectl apply -f 04-kafka-servicemonitor.yaml -n monitoring
kubectl apply -f 05-prometheus-pod.yaml -n monitoring
kubectl apply -f 06-grafana-dashboards.yaml -n monitoring
kubectl apply -f 07-grafana.yaml -n monitoring

# Wait for deployments
kubectl wait deployment/grafana --for=condition=Available=True -n monitoring --timeout=300s

# Get Grafana NodePort
$GRAFANA_PORT = kubectl get svc grafana -n monitoring -o jsonpath="{.spec.ports[0].nodePort}"
Write-Host "Grafana is available at http://localhost:$GRAFANA_PORT"
Write-Host "Default credentials: admin/admin"