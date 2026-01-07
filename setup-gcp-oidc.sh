#!/bin/bash
set -e

# Configuration
read -p "Enter GCP Project ID: " PROJECT_ID
read -p "Enter GitHub Repository (format: owner/repo): " GITHUB_REPO

export PROJECT_ID
export GITHUB_REPO
export SA_NAME="github-actions-deployer"
export POOL_NAME="github-pool"
export PROVIDER_NAME="github-provider"

echo "==> Setting up GCP for GitHub Actions OIDC"

# Enable required APIs
echo "==> Enabling GCP APIs"
gcloud services enable iamcredentials.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  sts.googleapis.com \
  container.googleapis.com \
  compute.googleapis.com \
  --project=$PROJECT_ID

# Create Service Account
echo "==> Creating Service Account"
gcloud iam service-accounts create $SA_NAME \
  --project=$PROJECT_ID \
  --display-name="GitHub Actions Deployer" || echo "Service account already exists"

# Grant permissions
echo "==> Granting IAM roles"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create Workload Identity Pool
echo "==> Creating Workload Identity Pool"
gcloud iam workload-identity-pools create $POOL_NAME \
  --project=$PROJECT_ID \
  --location=global \
  --display-name="GitHub Actions Pool" || echo "Pool already exists"

# Create OIDC Provider
echo "==> Creating OIDC Provider"
gcloud iam workload-identity-pools providers create-oidc $PROVIDER_NAME \
  --project=$PROJECT_ID \
  --location=global \
  --workload-identity-pool=$POOL_NAME \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com" || echo "Provider already exists"

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

# Bind Service Account to GitHub repo
echo "==> Binding Service Account to GitHub repository"
gcloud iam service-accounts add-iam-policy-binding \
  $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
  --project=$PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME/attribute.repository/$GITHUB_REPO"

# Get Workload Identity Provider name
WIF_PROVIDER=$(gcloud iam workload-identity-pools providers describe $PROVIDER_NAME \
  --project=$PROJECT_ID \
  --location=global \
  --workload-identity-pool=$POOL_NAME \
  --format="value(name)")

echo ""
echo "==> Setup Complete!"
echo ""
echo "Add these secrets to your GitHub repository:"
echo "-------------------------------------------"
echo "GCP_PROJECT_ID: $PROJECT_ID"
echo "WIF_PROVIDER: $WIF_PROVIDER"
echo "WIF_SERVICE_ACCOUNT: $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo "Go to: https://github.com/$GITHUB_REPO/settings/secrets/actions"
