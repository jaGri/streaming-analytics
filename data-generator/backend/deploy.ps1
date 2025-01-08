# Build the Docker image
docker build -t localhost:5000/sensor-backend .

# Push the Docker image to the local registry
docker push localhost:5000/sensor-backend

# Apply the Kubernetes deployment using the YAML files in the k8s directory
kubectl apply -f k8s/01-sensor-backend-namespace.yaml -n sensor-backend
kubectl apply -f k8s/02-sensor-backend-configmap.yaml -n sensor-backend
kubectl apply -f k8s/03-sensor-backend-deployment.yaml -n sensor-backend
kubectl apply -f k8s/04-sensor-backend-service.yaml -n sensor-backend

# Verify the deployment
kubectl get all -n sensor-backend
kubectl logs --namespace sensor-backend -l app=sensor-backend
