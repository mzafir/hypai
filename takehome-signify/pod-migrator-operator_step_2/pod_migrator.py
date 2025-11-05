#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime, timedelta
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import yaml
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodMigrator:
    def __init__(self):
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()
        
        # Time thresholds mapping
        self.time_thresholds = {
            "5min": timedelta(minutes=5),
            "1hr": timedelta(hours=1),
            "1day": timedelta(days=1),
            "2day": timedelta(days=2),
            "3day": timedelta(days=3)
        }

    def parse_node_age(self, node):
        """Calculate node age from creation time"""
        creation_time = node.metadata.creation_timestamp
        return datetime.now(creation_time.tzinfo) - creation_time

    def should_migrate_node(self, node, threshold):
        """Check if node exceeds migration threshold (t1 + ndt)"""
        node_age = self.parse_node_age(node)
        migration_threshold = self.time_thresholds[threshold]
        
        logger.info(f"Node {node.metadata.name}: age={node_age}, threshold={migration_threshold}")
        return node_age >= migration_threshold

    async def get_target_nodes(self, label_selector):
        """Get nodes matching target labels"""
        try:
            nodes = self.v1.list_node(label_selector=label_selector)
            return [node for node in nodes.items if node.spec.unschedulable != True]
        except ApiException as e:
            logger.error(f"Failed to get nodes: {e}")
            return []

    async def provision_new_node(self, node_template):
        """Simulate new node provisioning"""
        logger.info("Provisioning new node...")
        # In real implementation, this would call GKE/EKS APIs
        await asyncio.sleep(2)  # Simulate provisioning time
        logger.info("New node provisioned successfully")
        return True

    async def migrate_pods_from_node(self, node_name, max_pods):
        """Migrate pods from old node to new nodes"""
        try:
            pods = self.v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )
            
            migrated = 0
            for pod in pods.items[:max_pods]:
                if self.is_system_pod(pod):
                    continue
                    
                logger.info(f"Migrating pod {pod.metadata.name}")
                
                # Use eviction API for graceful migration
                eviction = client.V1Eviction(
                    metadata=client.V1ObjectMeta(
                        name=pod.metadata.name,
                        namespace=pod.metadata.namespace
                    )
                )
                
                try:
                    self.v1.create_namespaced_pod_eviction(
                        name=pod.metadata.name,
                        namespace=pod.metadata.namespace,
                        body=eviction
                    )
                    migrated += 1
                    await asyncio.sleep(1)  # Rate limiting
                except ApiException as e:
                    logger.warning(f"Failed to evict pod {pod.metadata.name}: {e}")
            
            return migrated
        except ApiException as e:
            logger.error(f"Migration failed: {e}")
            return 0

    def is_system_pod(self, pod):
        """Check if pod is system pod (skip migration)"""
        system_namespaces = ['kube-system', 'gke-managed-system', 'gmp-system']
        return pod.metadata.namespace in system_namespaces

    async def drain_and_decommission_node(self, node_name):
        """Force drain and decommission old node"""
        try:
            # Cordon node first
            body = {"spec": {"unschedulable": True}}
            self.v1.patch_node(node_name, body)
            logger.info(f"Cordoned node {node_name}")
            
            # Force evict remaining pods
            pods = self.v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )
            
            for pod in pods.items:
                if not self.is_system_pod(pod):
                    try:
                        self.v1.delete_namespaced_pod(
                            name=pod.metadata.name,
                            namespace=pod.metadata.namespace,
                            grace_period_seconds=0
                        )
                    except ApiException:
                        pass
            
            logger.info(f"Node {node_name} drained and ready for decommission")
            return True
            
        except ApiException as e:
            logger.error(f"Failed to drain node {node_name}: {e}")
            return False

    async def check_health_threshold(self, threshold_percent):
        """Check if cluster health meets minimum threshold"""
        try:
            nodes = self.v1.list_node()
            ready_nodes = sum(1 for node in nodes.items 
                            if any(condition.type == "Ready" and condition.status == "True" 
                                  for condition in node.status.conditions))
            
            health_percent = (ready_nodes / len(nodes.items)) * 100
            logger.info(f"Cluster health: {health_percent:.1f}%")
            return health_percent >= threshold_percent
            
        except ApiException as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def update_status(self, name, namespace, status):
        """Update NodeRefresh status"""
        try:
            self.custom_api.patch_namespaced_custom_object(
                group="migration.io",
                version="v1",
                namespace=namespace,
                plural="noderefreshes",
                name=name,
                body={"status": status}
            )
        except ApiException as e:
            logger.error(f"Failed to update status: {e}")

    async def reconcile_node_refresh(self, obj):
        """Main reconciliation loop"""
        name = obj["metadata"]["name"]
        namespace = obj["metadata"]["namespace"]
        spec = obj["spec"]
        
        logger.info(f"Reconciling NodeRefresh {name}")
        
        # Parse configuration
        target_labels = spec["targetNodeLabels"]
        max_pods = spec.get("maxPodsPerBatch", 5)
        min_health = spec.get("minHealthThreshold", 80)
        depth_threshold = spec["newDepthThreshold"]
        
        # Build label selector
        label_selector = ",".join([f"{k}={v}" for k, v in target_labels.items()])
        
        try:
            # Check cluster health
            if not await self.check_health_threshold(min_health):
                await self.update_status(name, namespace, {
                    "phase": "Waiting",
                    "message": f"Cluster health below {min_health}%"
                })
                return
            
            # Get target nodes
            nodes = await self.get_target_nodes(label_selector)
            if not nodes:
                await self.update_status(name, namespace, {
                    "phase": "Complete",
                    "message": "No target nodes found"
                })
                return
            
            # Check which nodes need migration
            nodes_to_migrate = [
                node for node in nodes 
                if self.should_migrate_node(node, depth_threshold)
            ]
            
            if not nodes_to_migrate:
                await self.update_status(name, namespace, {
                    "phase": "Monitoring",
                    "message": f"No nodes exceed {depth_threshold} threshold"
                })
                return
            
            # Process each node
            processed = 0
            for node in nodes_to_migrate:
                node_name = node.metadata.name
                logger.info(f"Processing node {node_name}")
                
                await self.update_status(name, namespace, {
                    "phase": "Migrating",
                    "message": f"Processing node {node_name}"
                })
                
                # Provision new node
                if await self.provision_new_node(node):
                    # Migrate pods
                    migrated = await self.migrate_pods_from_node(node_name, max_pods)
                    logger.info(f"Migrated {migrated} pods from {node_name}")
                    
                    # Wait for pods to stabilize
                    await asyncio.sleep(30)
                    
                    # Drain and decommission
                    if await self.drain_and_decommission_node(node_name):
                        processed += 1
                        logger.info(f"Successfully processed node {node_name}")
            
            # Update final status
            await self.update_status(name, namespace, {
                "phase": "Complete",
                "message": f"Processed {processed} nodes",
                "nodesProcessed": processed,
                "lastMigration": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            await self.update_status(name, namespace, {
                "phase": "Failed",
                "message": str(e)
            })

    async def watch_node_refreshes(self):
        """Watch for NodeRefresh resources"""
        logger.info("Starting NodeRefresh controller...")
        
        while True:
            try:
                # List all NodeRefresh resources
                resources = self.custom_api.list_cluster_custom_object(
                    group="migration.io",
                    version="v1",
                    plural="noderefreshes"
                )
                
                for obj in resources["items"]:
                    await self.reconcile_node_refresh(obj)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Watch error: {e}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    migrator = PodMigrator()
    asyncio.run(migrator.watch_node_refreshes())