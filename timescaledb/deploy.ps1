$ErrorActionPreference = "Stop"

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
    # Apply all YAML files in order
    Write-Host "Creating namespace..."
    kubectl apply -f 01-timescaledb-namespace.yaml
    
    Write-Host "Applying ConfigMap and Secret..."
    kubectl apply -f 02-timescaledb-configmap.yaml
    kubectl apply -f 03-timescaledb-secret.yaml
    
    Write-Host "Creating PVC..."
    kubectl apply -f 04-timescaledb-pvc.yaml
    
    Write-Host "Deploying TimescaleDB..."
    kubectl apply -f 05-timescaledb-deployment.yaml
    kubectl apply -f 06-timescaledb-service.yaml
    
    # Wait for TimescaleDB to be ready
    if (-not (Wait-ForPod -namespace "timeseriesdb" -label "app=timescaledb")) {
        throw "TimescaleDB deployment failed"
    }
    
    # Give the database a few more seconds to initialize
    Write-Host "Waiting for database to initialize..."
    Start-Sleep -Seconds 10
    
    Write-Host "Running database initialization..."
    kubectl apply -f 07-timescaledb-init.yaml
    
    # Wait for init job to complete
    Write-Host "Waiting for initialization job to complete..."
    kubectl wait --for=condition=complete job/timescaledb-init -n timeseriesdb --timeout=60s
    
    Write-Host "Deployment complete!"
    Write-Host "`nTo verify deployment:"
    Write-Host "kubectl get pods -n timeseriesdb"
    Write-Host "kubectl logs -n timeseriesdb job/timescaledb-init"
}
catch {
    Write-Error "Deployment failed: $_"
    exit 1
}