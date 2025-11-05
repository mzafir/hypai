#!/bin/bash

echo "=== Deploying Pod Migrator Operator ==="

# Apply CRD
echo "Creating NodeRefresh CRD..."
kubectl apply -f crd.yaml

# Create ConfigMap with operator code
echo "Creating operator code ConfigMap..."
kubectl create configmap pod-migrator-code --from-file=pod_migrator.py --dry-run=client -o yaml | kubectl apply -f -

# Deploy operator
echo "Deploying operator..."
kubectl apply -f deployment.yaml

# Wait for operator to be ready
echo "Waiting for operator to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/pod-migrator

echo "=== Operator deployed successfully ==="
echo
echo "Usage examples:"
echo "1. Deploy test migration (1hr threshold):"
echo "   kubectl apply -f example-noderefresh.yaml"
echo
echo "2. Check operator logs:"
echo "   kubectl logs -f deployment/pod-migrator"
echo
echo "3. Check NodeRefresh status:"
echo "   kubectl get noderefresh -o wide"
echo
echo "Migration Thresholds Available:"
echo "- 5min: Migrate nodes older than 5 minutes"
echo "- 1hr:  Migrate nodes older than 1 hour"  
echo "- 1day: Migrate nodes older than 1 day"
echo "- 2day: Migrate nodes older than 2 days"
echo "- 3day: Migrate nodes older than 3 days"