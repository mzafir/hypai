
STEP1

# GKE Cluster Deployment & Autoscaling Demo

Complete demonstration of Kubernetes autoscaling with GKE cluster elasticity.

## Features
- **Horizontal Pod Autoscaler (HPA)**: Scales pods based on CPU usage
- **Cluster Autoscaler**: Scales nodes based on resource demand
- **Load Testing**: Generate traffic to trigger autoscaling
-

## Prerequisites
- Google Cloud SDK installed
- Terraform installed
- kubectl installed
- GCP project with billing enabled

## Quick Start

### 1. Deploy GKE Cluster - go to the deployer folder 
```bash
./fast-deploy.sh <gcp_project> <region> <type>
```
```./fast-deploy.sh grabbion-324509 us-west1 zonal
```

### 2. Deploy Applications - go to the deployment folder 
```bash
# Deploy hello-world app
```kubectl apply -f hello-world-app.yaml```


# Enable autoscaling (3-10 replicas, 50% CPU threshold)
kubectl autoscale deployment hello-world --cpu-percent=50 --min=3 --max=10
```

### 3. Generate Load & Test Autoscaling - go thj load-generator folder
```bash
# Apply load generators
kubectl apply -f load-generators.yaml

# Monitor autoscaling
kubectl get hpa -w
kubectl get nodes -w
```

### 4. Clean Up Load
```bash
# Remove all load generators
kubectl delete deployment massive-load cpu-stress extreme-load-1 extreme-load-2 --ignore-not-found=true

# Scale back to minimum
kubectl scale deployment hello-world --replicas=3
```

## Monitoring Commands

```bash
# Check cluster status
kubectl get nodes
kubectl top nodes

# Monitor autoscaling
kubectl get hpa
kubectl get pods -o wide



# Check logs
kubectl logs -f deployment/hello-world
```

## Cleanup

```bash
# Destroy infrastructure
terraform destroy -auto-approve

# Or via gcloud
gcloud container clusters delete CLUSTER_NAME --zone=ZONE
```

## Troubleshooting

**Pods Pending**: Check node resources
```bash
kubectl describe nodes
kubectl get pods --field-selector=status.phase=Pending
```

**Autoscaling Not Working**: Verify metrics server
```bash
kubectl top pods
kubectl get hpa
```

**Load Balancer Pending**: Check GCP quotas and firewall rules
```bash
kubectl describe service hello-world
```


**gcloud force cluster delete**: 
``` gcloud container clusters delete <cluster_name> --zone=us-west1-a --quiet
```

**us-west1-a deployment timings are fast compared to other regions** 


**how to check autoscaler enabled/disabled**: 
``` gcloud container clusters describe <cluster_name> --zone=us-west1-a --format="table(nodePools[].name,nodePools[].autoscaling.enabled,nodePools[].autoscaling.minNodeCount,nodePools[].autoscaling.maxNodeCount)"
```

**autoscaler takes 10 minutes on GKE to drain the under utilized node** 