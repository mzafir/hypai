# Step-by-Step Pod Migrator Operator Deployment

## Phase 1: Prerequisites

### 1. Verify Kubernetes Cluster
```bash
# Check cluster access
kubectl cluster-info

# Verify nodes
kubectl get nodes

# Check permissions
kubectl auth can-i create customresourcedefinitions
```

### 2. Navigate to Operator Directory
```bash
cd pod-migrator-operator
ls -la
# Expected files: crd.yaml, deployment.yaml, pod_migrator.py, etc.
```

## Phase 2: Operator Deployment

### 3. Deploy Custom Resource Definition
```bash
# Create NodeRefresh CRD
kubectl apply -f crd.yaml

# Verify CRD creation
kubectl get crd noderefreshes.migration.io
```

### 4. Create Operator Code ConfigMap
```bash
# Create ConfigMap with Python code
kubectl create configmap pod-migrator-code --from-file=pod_migrator.py

# Verify ConfigMap
kubectl get configmap pod-migrator-code
```

### 5. Deploy Operator
```bash
# Apply RBAC and deployment
kubectl apply -f deployment.yaml

# Wait for operator to be ready
kubectl wait --for=condition=available --timeout=300s deployment/pod-migrator

# Verify deployment
kubectl get deployment pod-migrator
kubectl get pods -l app=pod-migrator
```

### 6. Check Operator Logs
```bash
# View startup logs
kubectl logs deployment/pod-migrator

# Expected output:
# INFO:__main__:Starting NodeRefresh controller...
# INFO:__main__:Reconciling NodeRefresh...
```

## Phase 3: Testing Migration Policies

### 7. Deploy Test Application (if needed)
```bash
# Create test workload
kubectl create deployment test-app --image=nginx:alpine
kubectl set resources deployment test-app --requests=cpu=50m,memory=64Mi
kubectl scale deployment test-app --replicas=3

# Verify pods are running
kubectl get pods -l app=test-app -o wide
```

### 8. Create Migration Policy - Testing (5min threshold)
```bash
# Apply test migration policy
cat << EOF | kubectl apply -f -
apiVersion: migration.io/v1
kind: NodeRefresh
metadata:
  name: test-migration
  namespace: default
spec:
  targetNodeLabels:
    kubernetes.io/os: "linux"
  maxPodsPerBatch: 3
  minHealthThreshold: 75
  newDepthThreshold: "5min"
  refreshSchedule: "*/5 * * * *"
EOF

# Verify NodeRefresh creation
kubectl get noderefresh test-migration
```

### 9. Monitor Migration Process
```bash
# Watch operator logs (new terminal)
kubectl logs -f deployment/pod-migrator

# Monitor NodeRefresh status (new terminal)
kubectl get noderefresh test-migration -o yaml -w

# Watch nodes (new terminal)
kubectl get nodes -w
```

### 10. Observe Migration Behavior
```bash
# Check node ages (nodes older than 5min will be flagged)
kubectl get nodes -o custom-columns=NAME:.metadata.name,AGE:.metadata.creationTimestamp

# Monitor pod distribution
kubectl get pods -o wide

# Check migration status
kubectl describe noderefresh test-migration
```

## Phase 4: Production Migration Policy

### 11. Create Production Policy (1day threshold)
```bash
# Apply production migration policy
cat << EOF | kubectl apply -f -
apiVersion: migration.io/v1
kind: NodeRefresh
metadata:
  name: production-migration
  namespace: default
spec:
  targetNodeLabels:
    cloud.google.com/gke-nodepool: "primary-pool"
  maxPodsPerBatch: 5
  minHealthThreshold: 80
  newDepthThreshold: "1day"
  refreshSchedule: "0 2 * * *"
EOF

# Verify creation
kubectl get noderefresh production-migration -o yaml
```

### 12. Monitor Long-term Operations
```bash
# Check all migration policies
kubectl get noderefresh

# View detailed status
kubectl describe noderefresh production-migration

# Monitor operator health
kubectl get deployment pod-migrator
```

## Phase 5: Validation & Testing

### 13. Validate Migration Logic
```bash
# Check operator decision making
kubectl logs deployment/pod-migrator | grep "age="

# Expected log format:
# INFO:__main__:Node gke-node-xyz: age=1 day, 2:30:45, threshold=1 day, 0:00:00
# INFO:__main__:Node gke-node-abc: age=0:45:30, threshold=1 day, 0:00:00
```

### 14. Test Different Thresholds
```bash
# Create multiple policies for testing
for threshold in "1hr" "1day" "2day"; do
cat << EOF | kubectl apply -f -
apiVersion: migration.io/v1
kind: NodeRefresh
metadata:
  name: test-${threshold}
  namespace: default
spec:
  targetNodeLabels:
    kubernetes.io/os: "linux"
  maxPodsPerBatch: 2
  minHealthThreshold: 70
  newDepthThreshold: "${threshold}"
EOF
done

# Monitor all policies
kubectl get noderefresh
```

### 15. Verify Safety Features
```bash
# Check health threshold enforcement
kubectl logs deployment/pod-migrator | grep "health"

# Verify eviction API usage
kubectl get events | grep -i evict

# Check pod disruption handling
kubectl get poddisruptionbudgets
```

## Phase 6: Cleanup & Maintenance

### 16. Clean Up Test Resources
```bash
# Delete test migration policies
kubectl delete noderefresh test-migration test-1hr test-1day test-2day

# Delete test applications
kubectl delete deployment test-app

# Keep production policy running
kubectl get noderefresh production-migration
```

### 17. Operator Maintenance
```bash
# Update operator (if needed)
kubectl set image deployment/pod-migrator controller=python:3.9-slim

# Restart operator
kubectl rollout restart deployment/pod-migrator

# Check operator health
kubectl get deployment pod-migrator -o wide
```

### 18. Complete Cleanup (if needed)
```bash
# Delete all migration policies
kubectl delete noderefresh --all

# Delete operator
kubectl delete deployment pod-migrator
kubectl delete serviceaccount pod-migrator
kubectl delete clusterrole pod-migrator
kubectl delete clusterrolebinding pod-migrator
kubectl delete configmap pod-migrator-code

# Delete CRD (removes all NodeRefresh resources)
kubectl delete crd noderefreshes.migration.io
```

## Expected Results

**Successful Deployment Shows:**
1. ✅ Operator pod running and healthy
2. ✅ NodeRefresh CRD registered
3. ✅ Migration policies created successfully
4. ✅ Operator logs show node age monitoring
5. ✅ Status updates in NodeRefresh resources
6. ✅ Safe migration behavior (no downtime)

**Timeline:**
- Operator deployment: 2-3 minutes
- Policy creation: Immediate
- First migration check: 1-5 minutes
- Migration execution: 5-10 minutes per node
- Status updates: Real-time

**Key Logs to Watch:**
```
INFO:__main__:Starting NodeRefresh controller...
INFO:__main__:Reconciling NodeRefresh production-migration
INFO:__main__:Node gke-node-xyz: age=1 day, 2:30:45, threshold=1 day, 0:00:00
INFO:__main__:Processing node gke-node-xyz
INFO:__main__:Provisioning new node...
INFO:__main__:Migrated 3 pods from gke-node-xyz
INFO:__main__:Successfully processed node gke-node-xyz
```