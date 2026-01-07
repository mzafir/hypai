# One-Click GCP Deployment Setup

## Prerequisites

1. **GCP Project** with billing enabled
2. **GitHub Repository** with the code
3. **Workload Identity Federation** configured

## Setup Steps

### 1. Enable Required GCP APIs

```bash
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable iamcredentials.googleapis.com
```

### 2. Create Service Account

```bash
export PROJECT_ID="your-project-id"
export SA_NAME="github-actions-deployer"

gcloud iam service-accounts create $SA_NAME \
  --project=$PROJECT_ID \
  --display-name="GitHub Actions Deployer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/compute.admin"
```

### 3. Configure Workload Identity Federation

```bash
export REPO="owner/repo-name"
export POOL_NAME="github-pool"
export PROVIDER_NAME="github-provider"

# Create Workload Identity Pool
gcloud iam workload-identity-pools create $POOL_NAME \
  --project=$PROJECT_ID \
  --location=global \
  --display-name="GitHub Actions Pool"

# Create Provider
gcloud iam workload-identity-pools providers create-oidc $PROVIDER_NAME \
  --project=$PROJECT_ID \
  --location=global \
  --workload-identity-pool=$POOL_NAME \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Bind Service Account
gcloud iam service-accounts add-iam-policy-binding \
  $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
  --project=$PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/$POOL_NAME/attribute.repository/$REPO"
```

### 4. Get Workload Identity Provider

```bash
gcloud iam workload-identity-pools providers describe $PROVIDER_NAME \
  --project=$PROJECT_ID \
  --location=global \
  --workload-identity-pool=$POOL_NAME \
  --format="value(name)"
```

### 5. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `GCP_PROJECT_ID`: Your GCP project ID
- `WIF_PROVIDER`: Full provider name from step 4
- `WIF_SERVICE_ACCOUNT`: `github-actions-deployer@PROJECT_ID.iam.gserviceaccount.com`

## Deploy

1. Go to **Actions** tab in GitHub
2. Select **Deploy to GCP** workflow
3. Click **Run workflow**
4. Select environment (dev/staging/prod)
5. Click **Run workflow**

## Destroy

1. Go to **Actions** tab
2. Select **Destroy GCP Infrastructure** workflow
3. Click **Run workflow**
4. Type `destroy` to confirm
5. Click **Run workflow**
