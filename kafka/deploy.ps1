$ErrorActionPreference = "Stop"

# Delete existing namespace
kubectl delete namespace kafka

# Create namespace
kubectl create namespace kafka

# Install Strimzi operator
kubectl apply -f https://strimzi.io/install/latest?namespace=kafka -n kafka

# Wait for operator to be ready
kubectl wait deployment/strimzi-cluster-operator --for=condition=Available=True -n kafka --timeout=300s

# Apply configurations in order
kubectl apply -f 01-kafka-namespace.yaml -n kafka
kubectl apply -f 02-kafka-metrics-configmap.yaml -n kafka
kubectl apply -f 03-kafka-cluster.yaml -n kafka

# Wait for Kafka to be ready
kubectl wait kafka/iot --for=condition=Ready --timeout=300s -n kafka

# Apply topics and users
kubectl apply -f topics/ -n kafka
kubectl apply -f users/ -n kafka


# Wait for topics to be ready
$topics = @("raw-sensor-data", "sql-features", "advanced-features", "predictions", "analysis")
foreach ($topic in $topics) {
    kubectl wait kafkatopic/$topic --for=condition=Ready --timeout=300s -n kafka
}

# Apply Kafka metrics service
kubectl apply -f 04-kafka-metrics-service.yaml -n kafka
