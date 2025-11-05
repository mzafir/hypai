STEP 2


# Pod Migrator Operator

Kubernetes Operator that safely migrates pods to new nodes based on user-defined time thresholds with zero downtime.

## Features
- **User-Defined Thresholds**: 5min, 1hr, 1day, 2day, 3day
- **Migration Formula**: Migration Time = Node Deployment Time (t1) + New Depth Threshold (ndt)
- **Zero Downtime**: Provisions new nodes before draining old ones
- **Safety Checks**: Respects health thresholds and pod disruption budgets
- **Comprehensive Logging**: Full operational visibility
- **pod-migration threshold**: newDepthThreshold is defined in "example-nodefresh.yaml" - by default it is set to 5min for demo purpose. Once the nodes are 5 min old and pod_migrator is deployed the pod_migration will start taking place as follows: 
1. Node that crosses /meet the threshold will be picked 
2. A New node will get deployed
3. Migration of the pod will start taking place from the old node, you could see the old node will start loosing the pod and the new node will start spinning the node. use `kubectl get pods -owide` to check the pod uptime status on respective node 
4. Once the old node has flushed all the pods, the node will be put into cordoned state for the GKE lifecycle management to decomission and remove the node 
## Architecture

**Custom Resource Definition (CRD):**
- `NodeRefresh`: Defines migration policies

**Controller Logic:**
1. Monitor node ages against thresholds
2. Provision new nodes when threshold exceeded
3. Migrate pods using eviction API
4. Drain and decommission old nodes
5. Update status and logs

## Quick Start

### 1. Deploy Operator
```bash
./deploy.sh
```

### 2. Create Migration Policy
```bash
kubectl apply -f example-noderefresh.yaml
```

### 3. Monitor Operations
```bash
# Watch operator logs
kubectl logs -f deployment/pod-migrator

# Check migration status
kubectl get noderefresh -o wide
```

## Migration Thresholds

| Threshold | Description | Use Case |
|-----------|-------------|----------|
| `5min` | 5 minutes | Testing/Demo |
| `1hr` | 1 hour | Development |
| `1day` | 1 day | Staging |
| `2day` | 2 days | Production (frequent) |
| `3day` | 3 days | Production (standard) |

## Configuration

**NodeRefresh Spec:**
```yaml
spec:
  targetNodeLabels:
    cloud.google.com/gke-nodepool: "primary-pool"
  maxPodsPerBatch: 5
  minHealthThreshold: 80
  newDepthThreshold: "1day"  # Migration threshold
  refreshSchedule: "0 2 * * *"
```

**Parameters:**
- `targetNodeLabels`: Node selector for migration targets
- `maxPodsPerBatch`: Maximum pods to migrate simultaneously
- `minHealthThreshold`: Minimum cluster health percentage
- `newDepthThreshold`: Time threshold for migration
- `refreshSchedule`: Cron schedule for checks

## Safety Features

**Health Checks:**
- Cluster health monitoring
- Pod readiness verification
- Resource availability validation

**Graceful Migration:**
- Eviction API usage
- Pod disruption budget respect
- Rolling migration strategy

**Error Handling:**
- Retry mechanisms
- Status reporting
- Comprehensive logging

## Monitoring

**Status Fields:**
- `phase`: Current operation phase
- `message`: Detailed status message
- `nodesProcessed`: Number of nodes migrated
- `lastMigration`: Timestamp of last operation

**Log Levels:**
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Critical failures

## Troubleshooting

**Common Issues:**

1. **Operator Not Starting**
   ```bash
   kubectl describe pod -l app=pod-migrator
   kubectl logs deployment/pod-migrator
   ```

2. **Migration Stuck**
   ```bash
   kubectl get noderefresh -o yaml
   kubectl describe nodes
   ```


## Cleanup

```bash
# Delete migration policies
kubectl delete noderefresh --all

# Delete operator
kubectl delete -f deployment.yaml
kubectl delete -f crd.yaml
```