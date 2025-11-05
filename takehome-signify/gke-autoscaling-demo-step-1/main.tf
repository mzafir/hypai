provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_container_cluster" "primary" {
  name     = "signify-test"
  location = "${var.region}-a"  # Zonal cluster is faster

  remove_default_node_pool = true
  initial_node_count       = 1
  deletion_protection      = false

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

# System node pool for system pods
resource "google_container_node_pool" "system_pool" {
  name       = "system-pool"
  location   = "${var.region}-a"
  cluster    = google_container_cluster.primary.name
  node_count = 1

  node_config {
    preemptible  = true
    machine_type = "e2-small"
    disk_size_gb = 20
    disk_type    = "pd-standard"
    
    # Taint for system pods only
    taint {
      key    = "CriticalAddonsOnly"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}

# Worker node pool for application pods
resource "google_container_node_pool" "worker_pool" {
  name       = "worker-pool"
  location   = "${var.region}-a"
  cluster    = google_container_cluster.primary.name
  
  # Enable autoscaling
  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }
  
  initial_node_count = 2

  node_config {
    preemptible  = true
    machine_type = "e2-small"
    disk_size_gb = 20
    disk_type    = "pd-standard"
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}