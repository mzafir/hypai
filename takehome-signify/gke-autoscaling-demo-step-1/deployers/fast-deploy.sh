#!/bin/bash

echo "=== Fast GKE Deployment ==="

# Skip interactive prompts with defaults
PROJECT_ID=${1:-"grabbion-324509"}
REGION=${2:-"us-central1"}
CLUSTER_TYPE=${3:-"zonal"}  # zonal or autopilot

echo "Using: Project=$PROJECT_ID, Region=$REGION, Type=$CLUSTER_TYPE"

# Set project
gcloud config set project $PROJECT_ID

# Parallel API enabling
echo "Enabling APIs..."
gcloud services enable container.googleapis.com compute.googleapis.com --async

# Create appropriate config based on type
if [ "$CLUSTER_TYPE" = "autopilot" ]; then
    cat > main.tf << 'EOF'
provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_container_cluster" "primary" {
  name     = "fast-cluster"
  location = "${var.region}-a"
  
  enable_autopilot = true
  deletion_protection = false
}
EOF
else
    # Use existing zonal config - main.tf should already be optimized
    echo "Using existing zonal configuration"
fi

# Create tfvars
cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
region     = "$REGION"
EOF

# Skip auth if already authenticated
if ! gcloud auth application-default print-access-token > /dev/null 2>&1; then
    gcloud auth application-default login --no-browser
fi

# Clean up any existing state
rm -rf .terraform terraform.tfstate*

# Deploy with parallelism
echo "Deploying cluster..."
terraform init
terraform apply -auto-approve -parallelism=10

if [ $? -eq 0 ]; then
    # Get cluster name from terraform
    CLUSTER_NAME=$(terraform show -json | jq -r '.values.root_module.resources[] | select(.type=="google_container_cluster") | .values.name')
    
    # Enable autoscaling on worker-pool (if not autopilot)
    if [ "$CLUSTER_TYPE" != "autopilot" ]; then
        echo "Enabling autoscaling..."
        gcloud container clusters update $CLUSTER_NAME \
          --zone=${REGION}-a \
          --enable-autoscaling \
          --node-pool=worker-pool \
          --min-nodes=1 \
          --max-nodes=10
    fi
    
    # Get credentials
    echo "Getting cluster credentials..."
    gcloud container clusters get-credentials $CLUSTER_NAME --zone ${REGION}-a
    
    # Verify autoscaling
    echo "Verifying autoscaling..."
    gcloud container clusters describe $CLUSTER_NAME --zone=${REGION}-a --format="table(nodePools[].name,nodePools[].autoscaling.enabled,nodePools[].autoscaling.minNodeCount,nodePools[].autoscaling.maxNodeCount)"
    
    echo "Deployment complete!"
    kubectl get nodes
else
    echo "Deployment failed!"
    exit 1
fi