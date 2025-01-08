kubectl delete namespace sensor-frontend

docker build -t localhost:5000/sensor-frontend:latest .
docker push localhost:5000/sensor-frontend:latest

kubectl apply -f k8s/01-frontend-namespace.yaml
kubectl apply -f k8s/02-frontend-deployment.yaml
kubectl apply -f k8s/03-frontend-service.yaml

kubectl get all -n sensor-frontend

