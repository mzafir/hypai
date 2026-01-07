# GitHub Actions → GCP Deployment Workflow

## Complete Flow Schematic

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SETUP PHASE (One-time)                      │
└─────────────────────────────────────────────────────────────────────┘

1. GCP Setup (run setup-gcp-oidc.sh)
   ├── Enable APIs (IAM, Container, Compute)
   ├── Create Service Account (github-actions-deployer)
   ├── Grant Roles (container.admin, compute.admin)
   ├── Create Workload Identity Pool (github-pool)
   ├── Create OIDC Provider (github-provider)
   │   └── Issuer: https://token.actions.githubusercontent.com
   └── Bind Service Account to GitHub Repo

2. GitHub Secrets Configuration
   ├── GCP_PROJECT_ID
   ├── WIF_PROVIDER (projects/123/locations/global/workloadIdentityPools/...)
   └── WIF_SERVICE_ACCOUNT (github-actions-deployer@project.iam.gserviceaccount.com)


┌─────────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT PHASE (Runtime)                     │
└─────────────────────────────────────────────────────────────────────┘

Step 1: Trigger Workflow
   └── GitHub Actions UI → Run workflow → Select environment

Step 2: GitHub Actions Runner Starts
   ├── permissions: id-token: write
   └── GitHub generates OIDC token with claims:
       ├── sub: repo:owner/repo:ref:refs/heads/main
       ├── repository: owner/repo
       └── actor: username

Step 3: Authenticate to GCP
   ├── google-github-actions/auth@v2
   ├── Sends OIDC token to GCP
   ├── GCP Workload Identity validates token
   │   ├── Checks issuer: token.actions.githubusercontent.com
   │   ├── Validates repository claim
   │   └── Matches attribute mapping
   ├── GCP issues temporary credentials (1 hour)
   └── Credentials stored in runner environment

Step 4: Setup Cloud SDK
   └── gcloud configured with temporary credentials

Step 5: Terraform Infrastructure
   ├── terraform init
   ├── terraform plan
   └── terraform apply
       ├── Creates GKE cluster
       ├── Creates node pools (system + worker)
       └── Enables autoscaling

Step 6: Get GKE Credentials
   └── gcloud container clusters get-credentials

Step 7: Deploy Application
   ├── kubectl apply -f webapp-deployment.yaml
   └── kubectl apply -f hpa.yaml

Step 8: Verify Deployment
   ├── kubectl get pods
   ├── kubectl get hpa
   └── kubectl get nodes


┌─────────────────────────────────────────────────────────────────────┐
│                         SECURITY MODEL                              │
└─────────────────────────────────────────────────────────────────────┘

GitHub OIDC Token (JWT)
    ↓
    ├── Signed by GitHub
    ├── Contains repository identity
    ├── Valid for 1 hour
    └── Cannot be reused outside GitHub Actions
    
GCP Workload Identity Federation
    ↓
    ├── Trusts GitHub as OIDC provider
    ├── Validates token signature
    ├── Checks attribute conditions (repository match)
    └── Issues GCP access token
    
GCP Service Account
    ↓
    ├── Impersonated by GitHub Actions
    ├── Has specific IAM roles
    └── Scoped to project resources

No Long-lived Credentials Stored ✓
No Service Account Keys ✓
Automatic Token Rotation ✓


┌─────────────────────────────────────────────────────────────────────┐
│                         FILE STRUCTURE                              │
└─────────────────────────────────────────────────────────────────────┘

deployer/hypai/
├── .github/workflows/
│   ├── deploy-gcp.yml          # Main deployment workflow
│   └── destroy-gcp.yml         # Cleanup workflow
├── takehome-signify/
│   └── gke-autoscaling-demo-step-1/
│       ├── main.tf             # Terraform GKE config
│       ├── variables.tf
│       ├── webapp-deployment.yaml
│       └── hpa.yaml
├── setup-gcp-oidc.sh          # One-time GCP setup script
└── DEPLOYMENT.md              # Setup instructions


┌─────────────────────────────────────────────────────────────────────┐
│                         QUICK START                                 │
└─────────────────────────────────────────────────────────────────────┘

1. Run GCP setup:
   ./setup-gcp-oidc.sh

2. Add secrets to GitHub:
   Settings → Secrets → Actions → New repository secret

3. Deploy:
   Actions → Deploy to GCP → Run workflow

4. Destroy (when done):
   Actions → Destroy GCP Infrastructure → Run workflow
```
