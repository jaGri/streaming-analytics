kubectl delete namespace system-dashboard

docker build -t localhost:5000/system-dashboard:latest .
docker push localhost:5000/system-dashboard:latest

kubectl apply -f k8s/01-dashboard-namespace.yaml
kubectl apply -f k8s/02-dashboard-deployment.yaml
kubectl apply -f k8s/03-dashboard-service.yaml

kubectl get all -n system-dashboard