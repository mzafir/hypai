# Load Testing Guide

Complete guide for testing GKE autoscaling with different load levels.

## Load Generator Levels

### 1. Moderate Load (`load-generators.yaml`)
**Purpose**: Basic autoscaling demonstration
**Resources**: 10 total replicas, moderate CPU usage
**Expected**: 3-5 nodes, pod scaling to 6-8 replicas

```bash
kubectl apply -f load-generators.yaml
```

### 2. Intensive Load (`intensive-load.yaml`) 
**Purpose**: Force node autoscaling
**Resources**: Higher CPU/memory requests
**Expected**: 5-7 nodes, pod scaling to max (10 replicas)

```bash
kubectl apply -f intensive-load.yaml
```

### 3. Extreme Load (`extreme-load-generators.yaml`)
**Purpose**: Maximum cluster scaling (10+ nodes)
**Resources**: 400+ replicas with high resource requests
**Expected**: Scale to node pool maximum (5 nodes per pool)

```bash
# ⚠️  WARNING: This will create 400+ pods and max out your cluster
kubectl apply -f extreme-load-generators.yaml
```

## Load Testing Scenarios

### Scenario 1: Basic Autoscaling Demo
```bash
# 1. Deploy moderate load
kubectl apply -f load-generators.yaml

# 2. Monitor scaling
kubectl get hpa -w &
kubectl get pods -w &

# 3. Wait for scaling (2-3 minutes)
# Expected: 3 → 6-8 pods

# 4. Clean up
kubectl delete -f load-generators.yaml
```

### Scenario 2: Node Autoscaling Demo  
```bash
# 1. Deploy intensive load
kubectl apply -f intensive-load.yaml

# 2. Monitor nodes and pods
kubectl get nodes -w &
kubectl get hpa -w &

# 3. Wait for node scaling (3-5 minutes)
# Expected: 2 → 5+ nodes, pods at maximum

# 4. Clean up
kubectl delete -f intensive-load.yaml
```

### Scenario 3: Maximum Scaling Test
```bash
# ⚠️  Use only for testing maximum cluster capacity

# 1. Deploy extreme load
kubectl apply -f extreme-load-generators.yaml

# 2. Monitor cluster scaling
kubectl get nodes -w &
kubectl top nodes &

# 3. Wait for maximum scaling (5-10 minutes)
# Expected: All available nodes provisioned

# 4. IMPORTANT: Clean up immediately
kubectl delete -f extreme-load-generators.yaml
```

## Monitoring Commands

### Real-time Monitoring
```bash
# Watch everything (multiple terminals)
kubectl get hpa -w                    # Pod autoscaling
kubectl get nodes -w                  # Node autoscaling  
kubectl get pods -o wide -w           # Pod distribution
kubectl top nodes                     # Resource usage
```

### Load Testing Metrics
```bash
# Check current load
kubectl get deployments | grep load

# Resource usage
kubectl top pods | grep load

# Scaling status
kubectl describe hpa hello-world

# Node capacity
kubectl describe nodes | grep -A5 "Allocated resources"
```

## Clean Up Commands

### Remove Specific Load
```bash
# Remove moderate load
kubectl delete -f load-generators.yaml

# Remove intensive load  
kubectl delete -f intensive-load.yaml

# Remove extreme load
kubectl delete -f extreme-load-generators.yaml
```

### Emergency Clean Up
```bash
# Remove ALL load generators
kubectl delete deployment --selector=app=load-generator
kubectl delete deployment --selector=app=intensive-load
kubectl delete deployment --selector=app=cpu-stress
kubectl delete deployment --selector=app=massive-load
kubectl delete deployment --selector=app=extreme-load-1
kubectl delete deployment --selector=app=extreme-load-2

# Or delete by name pattern
kubectl delete deployment -l 'app in (load-generator,intensive-load,cpu-stress,massive-load,extreme-load-1,extreme-load-2)'
```

### Scale Down Applications
```bash
# Scale hello-world back to minimum
kubectl scale deployment hello-world --replicas=3

# Wait for node scale-down (10-20 minutes)
kubectl get nodes -w
```

## Expected Timelines

| Load Level | Pod Scaling | Node Scaling Up | Node Scaling Down |
|------------|-------------|-----------------|-------------------|
| Moderate   | 1-2 min     | 3-5 min         | 10-15 min         |
| Intensive  | 1-2 min     | 3-5 min         | 15-20 min         |
| Extreme    | 2-3 min     | 5-10 min        | 20-30 min         |

## Troubleshooting

### Pods Stuck Pending
```bash
# Check node resources
kubectl describe nodes | grep -A10 "Allocated resources"

# Check pending pods
kubectl get pods --field-selector=status.phase=Pending

# Check events
kubectl get events --sort-by='.lastTimestamp' | tail -20
```

### Autoscaling Not Working
```bash
# Check HPA status
kubectl describe hpa hello-world

# Check metrics server
kubectl top pods

# Check resource requests
kubectl describe deployment hello-world
```

### Too Many Resources Used
```bash
# Emergency scale down
kubectl scale deployment hello-world --replicas=1
kubectl delete deployment --all --selector='app in (load-generator,intensive-load,cpu-stress,massive-load,extreme-load-1,extreme-load-2)'

# Check costs (if applicable)
gcloud billing budgets list
```