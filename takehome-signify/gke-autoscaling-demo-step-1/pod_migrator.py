#!/usr/bin/env python3  # Shebang for direct script execution
import asyncio  # For async/await functionality
import logging  # For operator logging
from datetime import datetime, timedelta  # For pod age calculations
from kubernetes import client, config, watch  # Kubernetes Python client
from kubernetes.client.rest import ApiException  # For K8s API error handling

logging.basicConfig(level=logging.INFO)  # Configure logging to INFO level
logger = logging.getLogger(__name__)  # Create logger instance

class PodMigrator:  # Main operator class
    def __init__(self):  # Initialize the operator
        try:
            config.load_incluster_config()  # Load config when running inside cluster
        except:
            config.load_kube_config()  # Load local kubeconfig for development
        
        self.v1 = client.CoreV1Api()  # Core API client for pods
        self.apps_v1 = client.AppsV1Api()  # Apps API client for deployments
        self.migration_interval = timedelta(days=3)  # Set 3-day migration interval
        
    async def safe_migrate_pod(self, pod):  # Main migration logic
        """Safely migrate a pod with zero downtime"""
        try:
            # Check if pod belongs to a deployment/replicaset
            owner_refs = pod.metadata.owner_references or []  # Get pod's owner references
            deployment_name = None  # Initialize deployment name tracker
            
            for ref in owner_refs:  # Loop through owner references
                if ref.kind == "ReplicaSet":  # If owned by ReplicaSet
                    rs = self.apps_v1.read_namespaced_replica_set(  # Get ReplicaSet details
                        ref.name, pod.metadata.namespace
                    )
                    if rs.metadata.owner_references:  # Check if RS has owners
                        for rs_ref in rs.metadata.owner_references:  # Loop through RS owners
                            if rs_ref.kind == "Deployment":  # If owned by Deployment
                                deployment_name = rs_ref.name  # Store deployment name
                                break  # Exit inner loop
                    break  # Exit outer loop
            
            if deployment_name:  # If pod belongs to deployment
                await self._rolling_restart_deployment(deployment_name, pod.metadata.namespace)  # Use rolling restart
            else:  # If standalone pod
                await self._evict_standalone_pod(pod)  # Use eviction
                
        except Exception as e:  # Handle any errors
            logger.error(f"Failed to migrate pod {pod.metadata.name}: {e}")  # Log error
    
    async def _rolling_restart_deployment(self, deployment_name, namespace):  # Rolling restart method
        """Perform rolling restart of deployment"""
        try:
            # Patch deployment to trigger rolling update
            patch = {  # Create patch object
                "spec": {  # Deployment spec
                    "template": {  # Pod template
                        "metadata": {  # Template metadata
                            "annotations": {  # Add restart annotation
                                "kubectl.kubernetes.io/restartedAt": datetime.utcnow().isoformat()  # Current timestamp
                            }
                        }
                    }
                }
            }
            
            self.apps_v1.patch_namespaced_deployment(  # Apply patch to deployment
                name=deployment_name,  # Deployment name
                namespace=namespace,  # Target namespace
                body=patch  # Patch body
            )
            logger.info(f"Triggered rolling restart for deployment {deployment_name}")  # Log success
            
        except ApiException as e:  # Handle K8s API errors
            logger.error(f"Failed to restart deployment {deployment_name}: {e}")  # Log error
    
    async def _evict_standalone_pod(self, pod):  # Eviction method for standalone pods
        """Evict standalone pod safely"""
        try:
            eviction = client.V1Eviction(  # Create eviction object
                metadata=client.V1ObjectMeta(  # Eviction metadata
                    name=pod.metadata.name,  # Pod name to evict
                    namespace=pod.metadata.namespace  # Pod namespace
                )
            )
            
            self.v1.create_namespaced_pod_eviction(  # Execute eviction
                name=pod.metadata.name,  # Target pod name
                namespace=pod.metadata.namespace,  # Target namespace
                body=eviction  # Eviction request body
            )
            logger.info(f"Evicted pod {pod.metadata.name}")  # Log successful eviction
            
        except ApiException as e:  # Handle eviction errors
            logger.error(f"Failed to evict pod {pod.metadata.name}: {e}")  # Log error
    
    def should_migrate_pod(self, pod):  # Age-based migration check
        """Check if pod should be migrated based on age"""
        if not pod.status.start_time:  # Skip pods without start time
            return False  # Don't migrate
            
        pod_age = datetime.now(pod.status.start_time.tzinfo) - pod.status.start_time  # Calculate pod age
        return pod_age >= self.migration_interval  # Return true if older than 3 days
    
    async def run(self):  # Main operator control loop
        """Main operator loop"""
        logger.info("Starting Pod Migrator Operator")  # Log startup
        
        while True:  # Infinite loop for continuous operation
            try:
                # Get all pods across all namespaces
                pods = self.v1.list_pod_for_all_namespaces()  # Fetch all pods cluster-wide
                
                for pod in pods.items:  # Iterate through each pod
                    # Skip system pods and completed pods
                    if (pod.metadata.namespace.startswith('kube-') or   # Skip kube-system pods
                        pod.status.phase in ['Succeeded', 'Failed']):  # Skip completed pods
                        continue  # Move to next pod
                    
                    if self.should_migrate_pod(pod):  # Check if pod needs migration
                        logger.info(f"Migrating pod {pod.metadata.name} in {pod.metadata.namespace}")  # Log migration
                        await self.safe_migrate_pod(pod)  # Execute migration
                
                # Check every hour
                await asyncio.sleep(3600)  # Wait 1 hour before next check
                
            except Exception as e:  # Handle unexpected errors
                logger.error(f"Error in main loop: {e}")  # Log error
                await asyncio.sleep(60)  # Wait 1 minute before retry

if __name__ == "__main__":  # Script entry point
    migrator = PodMigrator()  # Create operator instance
    asyncio.run(migrator.run())  # Start the operator