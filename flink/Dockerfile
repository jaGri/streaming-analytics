FROM apache/flink:1.17.0

USER root
RUN apt-get update && \
    apt-get install -y python3 python3.11-dev python3-pip && \
    pip3 install apache-flink==1.17.0 kafka-python numpy && \
    mkdir -p /opt/flink/jobs && \
    chmod -R 777 /opt/flink/jobs && \
    wget -P /opt/flink/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-connector-kafka/1.17.0/flink-connector-kafka-1.17.0.jar && \
    wget -P /opt/flink/lib/ https://repo.maven.apache.org/maven2/org/apache/kafka/kafka-clients/3.2.3/kafka-clients-3.2.3.jar

COPY jobs/sensor-processing.py /opt/flink/jobs/
RUN chmod 777 /opt/flink/jobs/sensor-processing.py

USER flink