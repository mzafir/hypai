# Step-by-Step GKE Autoscaling Demo

## Phase 1: Infrastructure Setup

### 1. Deploy GKE Cluster
```bash
# Run deployment script
./deploy.sh

# Inputs required:
# - Project ID: your-gcp-project
# - Region: us-central1 (or preferred)
# - Cluster name: gke-cluster
# - Machine type: e2-small
# - Nodes per pool: 2
```

### 2. Verify Cluster
```bash
# Check nodes
kubectl get nodes

# Expected: 2 nodes ready
```

## Phase 2: Application Deployment

### 3. Deploy Hello-World App
```bash
# Create deployment
kubectl create deployment hello-world --image=nginx:alpine

# Set resource limits
kubectl set resources deployment hello-world \
  --requests=cpu=50m,memory=64Mi \
  --limits=cpu=100m,memory=128Mi

# Scale to 3 replicas
kubectl scale deployment hello-world --replicas=3
```

### 4. Expose Service
```bash
# Create LoadBalancer service
kubectl expose deployment hello-world --type=LoadBalancer --port=80

# Wait for external IP (2-3 minutes)
kubectl get service hello-world -w
```

### 5. Enable Autoscaling
```bash
# Configure HPA
kubectl autoscale deployment hello-world --cpu-percent=50 --min=3 --max=10

# Verify HPA
kubectl get hpa
```

## Phase 3: Load Testing

### 6. Generate Moderate Load
```bash
# Apply moderate load
kubectl apply -f load-generators.yaml

# Monitor scaling (new terminal)
kubectl get hpa -w
```

### 7. Increase Load for Node Scaling
```bash
# Scale up load generators
kubectl scale deployment load-generator --replicas=6
kubectl scale deployment intensive-load --replicas=8
kubectl scale deployment cpu-stress --replicas=4

# Monitor nodes (new terminal)
kubectl get nodes -w
```

### 8. Observe Autoscaling
```bash
# Check pod distribution
kubectl get pods -o wide

# Check resource usage
kubectl top nodes
kubectl top pods

# Check HPA status
kubectl describe hpa hello-world
```

## Phase 4: Monitoring & Verification

### 9. Access Application
```bash
# Get external IP
EXTERNAL_IP=$(kubectl get service hello-world -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test application
curl http://$EXTERNAL_IP

# Load test from local machine
for i in {1..100}; do curl -s http://$EXTERNAL_IP > /dev/null & done
```

### 10. Monitor Scaling Events
```bash
# View HPA events
kubectl describe hpa hello-world

# View deployment events
kubectl describe deployment hello-world

# View cluster events
kubectl get events --sort-by='.lastTimestamp'
```

## Phase 5: Cleanup

### 11. Remove Load
```bash
# Delete load generators
kubectl delete deployment load-generator intensive-load cpu-stress

# Scale back hello-world
kubectl scale deployment hello-world --replicas=3

# Monitor scale-down (takes 10-20 minutes)
kubectl get nodes -w
```

### 12. Complete Cleanup
```bash
# Delete applications
kubectl delete deployment hello-world
kubectl delete service hello-world
kubectl delete hpa hello-world

# Destroy infrastructure
terraform destroy -auto-approve
```

## Expected Results

**Successful Demo Shows:**
1. ✅ Pods scale from 3 → 10 based on CPU load
2. ✅ Nodes scale from 2 → 5+ based on resource demand
3. ✅ Application remains accessible during scaling
4. ✅ Automatic scale-down when load decreases
5. ✅ Zero downtime throughout the process

**Timeline:**
- Pod scaling: 1-2 minutes
- Node scaling up: 2-5 minutes
- Node scaling down: 10-20 minutes
- Total demo: ~30 minutes