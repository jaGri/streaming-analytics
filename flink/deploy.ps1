kubectl delete namespace flink

# Install Flink K8s Operator
#kubectl create -f https://github.com/apache/flink-kubernetes-operator/releases/download/v1.6.0/flink-kubernetes-operator.yaml

# Wait for operator to be ready
#kubectl wait deployment/flink-operator --for=condition=Available=True -n flink-operator-system --timeout=300s

kubectl apply -f 01-flink-operator-namespace.yaml

helm repo add flink-operator-repo https://downloads.apache.org/flink/flink-kubernetes-operator-1.10.0

helm install flink-kubernetes-operator flink-operator-repo/flink-kubernetes-operator -n flink

kubectl wait deployment/flink-kubernetes-operator --for=condition=Available=True --timeout=300s

# Build and push custom Flink image
docker build --no-cache -t localhost:5000/flink-python:latest .
docker push localhost:5000/flink-python:latest

# Apply Flink configurations
kubectl apply -f 02-flink-operator-rbac.yaml
kubectl apply -f 03-flink-session-cluster.yaml

# Wait for cluster to be ready
kubectl wait flinkdeployment/sensor-processing-cluster --for=condition=Available=True -n flink --timeout=300s

# Deploy job
kubectl apply -f 04-flink-sensor-job.yaml

# Apply metrics service
kubectl apply -f 05-flink-metrics-service.yaml

Write-Host "Deployment complete! Monitor job status with:"
Write-Host "kubectl get flinksessionjob sensor-processing-job -n flink"
Write-Host "kubectl logs -n flink -l component=jobmanager"