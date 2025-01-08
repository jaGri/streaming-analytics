# Build custom Flink image with Python jobs included
docker build --no-cache -t localhost:5000/flink-python:latest .
docker push localhost:5000/flink-python:latest

function Wait-ForPod {
    param (
        [string]$namespace,
        [string]$label,
        [int]$timeoutSeconds = 300
    )
    Write-Host "Waiting for pod with label $label in namespace $namespace to be ready..."
    $startTime = Get-Date
    $timeoutTime = $startTime.AddSeconds($timeoutSeconds)
    while ($true) {
        try {
            $status = kubectl wait --for=condition=ready pod -l $label -n $namespace --timeout="${timeoutSeconds}s"
            if ($?) {
                Write-Host "Pod is ready"
                return $true
            }
        }
        catch {
            if ((Get-Date) -gt $timeoutTime) {
                Write-Error "Timeout waiting for pod to be ready"
                return $false
            }
            Start-Sleep -Seconds 5
        }
    }
}

try {
    Write-Host "Setting up Flink namespace..."
    kubectl create namespace flink 2>$null
    if ($?) {
        Write-Host "Created new namespace 'flink'"
    } else {
        Write-Host "Using existing namespace 'flink'"
        kubectl delete deployment -n flink --all
        kubectl delete service -n flink --all
        kubectl delete configmap -n flink --all
        kubectl delete pvc -n flink --all
        Start-Sleep -Seconds 10
    }

    Write-Host "Setting up RBAC..."
    kubectl apply -f 00-flink-rbac.yaml -n flink
    
    Write-Host "Deploying Flink components..."
    kubectl apply -f 01-flink-configmap.yaml -n flink
    kubectl apply -f 02-flink-pvc.yaml -n flink
    kubectl apply -f 03-flink-jobmanager.yaml -n flink
    kubectl apply -f 04-flink-taskmanager.yaml -n flink
    kubectl apply -f 05-flink-service.yaml -n flink

    Write-Host "Waiting for JobManager to be ready..."
    if (-not (Wait-ForPod -namespace "flink" -label "app=flink,component=jobmanager")) {
        throw "JobManager deployment failed"
    }

    Write-Host "Waiting for TaskManager to be ready..."
    if (-not (Wait-ForPod -namespace "flink" -label "app=flink,component=taskmanager")) {
        throw "TaskManager deployment failed"
    }

    Start-Sleep -Seconds 10

    Write-Host "Submitting sensor processing job..."
    $jobmanagerPod = $(kubectl get pod -l "app=flink,component=jobmanager" -n flink -o jsonpath='{.items[0].metadata.name}')
    Write-Host "JobManager pod name: $jobmanagerPod"
    
    kubectl exec -n flink $jobmanagerPod -- /opt/flink/bin/flink run -py /opt/flink/jobs/sensor-processing.py

    Write-Host "`nDeployment complete!"
    Write-Host "Flink UI is available at: http://localhost:30081"
    Write-Host "`nTo check job status:"
    Write-Host "kubectl get pods -n flink"
    Write-Host "kubectl logs -n flink -l 'app=flink,component=jobmanager' --tail=100"
}
catch {
    Write-Error "Deployment failed: $_"
    exit 1
}