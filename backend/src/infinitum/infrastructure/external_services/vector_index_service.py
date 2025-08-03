"""
Vertex AI Vector Index Management Service
Handles creation, deployment, and management of vector indexes for semantic search
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
from google.api_core import exceptions as gcp_exceptions
import vertexai

from infinitum.settings import settings
from infinitum.infrastructure.logging_config import get_agent_logger
from infinitum.infrastructure.persistence.firestore_client import db

logger = get_agent_logger("vector_index_service")

class VectorIndexService:
    """Comprehensive service for managing Vertex AI Vector Search indexes"""
    
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = "us-central1"
        self.index_collection = db.collection('vector_indexes')
        self.deployment_collection = db.collection('vector_deployments')
        
        # Initialize Vertex AI
        try:
            vertexai.init(project=self.project_id, location=self.location)
            aiplatform.init(project=self.project_id, location=self.location)
            logger.info(f"Initialized Vertex AI for project {self.project_id} in {self.location}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise
    
    async def create_vector_index(
        self,
        index_name: str,
        dimensions: int = 768,
        distance_measure: str = "COSINE_DISTANCE",
        algorithm_config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new vector index with specified configuration
        
        Args:
            index_name: Unique name for the index
            dimensions: Vector dimensions (768 for text-embedding-004, 1536 for ada-002)
            distance_measure: Distance metric (COSINE_DISTANCE, DOT_PRODUCT_DISTANCE, etc.)
            algorithm_config: Algorithm-specific configuration
            metadata: Additional metadata for the index
            
        Returns:
            Dict containing index information and status
        """
        try:
            logger.info(f"Creating vector index: {index_name}")
            
            # Default algorithm configuration
            if algorithm_config is None:
                algorithm_config = {
                    "treeAhConfig": {
                        "leafNodeEmbeddingCount": 500,
                        "leafNodesToSearchPercent": 7
                    }
                }
            
            # Create index configuration
            index_config = {
                "dimensions": dimensions,
                "approximateNeighborsCount": 150,
                "distanceMeasureType": distance_measure,
                "algorithmConfig": algorithm_config
            }
            
            # Create the index
            index = MatchingEngineIndex.create_tree_ah_index(
                display_name=index_name,
                contents_delta_uri=None,  # Will be populated during data upload
                dimensions=dimensions,
                approximate_neighbors_count=150,
                distance_measure_type=distance_measure,
                leaf_node_embedding_count=algorithm_config.get("treeAhConfig", {}).get("leafNodeEmbeddingCount", 500),
                leaf_nodes_to_search_percent=algorithm_config.get("treeAhConfig", {}).get("leafNodesToSearchPercent", 7),
                description=f"Vector index for {index_name}",
                labels=metadata or {"created_by": "infinitum_ai_agent"}
            )
            
            # Store index information in Firestore
            index_info = {
                "index_id": index.resource_name,
                "index_name": index_name,
                "display_name": index.display_name,
                "dimensions": dimensions,
                "distance_measure": distance_measure,
                "algorithm_config": algorithm_config,
                "status": "CREATING",
                "created_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            await self._store_index_info(index_name, index_info)
            
            logger.info(f"Vector index creation initiated: {index.resource_name}")
            
            return {
                "success": True,
                "index_id": index.resource_name,
                "index_name": index_name,
                "status": "CREATING",
                "message": "Index creation initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create vector index {index_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create index {index_name}"
            }
    
    async def create_index_endpoint(
        self,
        endpoint_name: str,
        description: Optional[str] = None,
        network: Optional[str] = None,
        enable_private_service_connect: bool = False
    ) -> Dict[str, Any]:
        """
        Create an index endpoint for serving vector search queries
        
        Args:
            endpoint_name: Name for the endpoint
            description: Optional description
            network: VPC network for private access
            enable_private_service_connect: Enable private service connect
            
        Returns:
            Dict containing endpoint information
        """
        try:
            logger.info(f"Creating index endpoint: {endpoint_name}")
            
            # Create endpoint configuration
            endpoint_config = {
                "display_name": endpoint_name,
                "description": description or f"Endpoint for {endpoint_name}",
                "network": network,
                "enable_private_service_connect": enable_private_service_connect
            }
            
            # Create the endpoint
            endpoint = MatchingEngineIndexEndpoint.create(
                display_name=endpoint_name,
                description=description or f"Endpoint for {endpoint_name}",
                network=network,
                enable_private_service_connect=enable_private_service_connect
            )
            
            # Store endpoint information
            endpoint_info = {
                "endpoint_id": endpoint.resource_name,
                "endpoint_name": endpoint_name,
                "display_name": endpoint.display_name,
                "network": network,
                "private_service_connect": enable_private_service_connect,
                "status": "CREATING",
                "created_at": datetime.now().isoformat()
            }
            
            await self._store_endpoint_info(endpoint_name, endpoint_info)
            
            logger.info(f"Index endpoint creation initiated: {endpoint.resource_name}")
            
            return {
                "success": True,
                "endpoint_id": endpoint.resource_name,
                "endpoint_name": endpoint_name,
                "status": "CREATING",
                "message": "Endpoint creation initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create index endpoint {endpoint_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create endpoint {endpoint_name}"
            }
    
    async def deploy_index_to_endpoint(
        self,
        index_name: str,
        endpoint_name: str,
        deployed_index_id: str,
        machine_type: str = "n1-standard-2",
        min_replica_count: int = 1,
        max_replica_count: int = 3
    ) -> Dict[str, Any]:
        """
        Deploy a vector index to an endpoint for serving
        
        Args:
            index_name: Name of the index to deploy
            endpoint_name: Name of the target endpoint
            deployed_index_id: Unique ID for this deployment
            machine_type: Machine type for serving
            min_replica_count: Minimum number of replicas
            max_replica_count: Maximum number of replicas
            
        Returns:
            Dict containing deployment information
        """
        try:
            logger.info(f"Deploying index {index_name} to endpoint {endpoint_name}")
            
            # Get index and endpoint information
            index_info = await self._get_index_info(index_name)
            endpoint_info = await self._get_endpoint_info(endpoint_name)
            
            if not index_info or not endpoint_info:
                raise ValueError("Index or endpoint not found")
            
            # Get the actual index and endpoint objects
            index = MatchingEngineIndex(index_info["index_id"])
            endpoint = MatchingEngineIndexEndpoint(endpoint_info["endpoint_id"])
            
            # Wait for index to be ready
            await self._wait_for_index_ready(index)
            
            # Deploy the index
            deployed_index = endpoint.deploy_index(
                index=index,
                deployed_index_id=deployed_index_id,
                display_name=f"{index_name} deployment",
                machine_type=machine_type,
                min_replica_count=min_replica_count,
                max_replica_count=max_replica_count
            )
            
            # Store deployment information
            deployment_info = {
                "deployment_id": deployed_index_id,
                "index_name": index_name,
                "endpoint_name": endpoint_name,
                "index_id": index_info["index_id"],
                "endpoint_id": endpoint_info["endpoint_id"],
                "machine_type": machine_type,
                "min_replica_count": min_replica_count,
                "max_replica_count": max_replica_count,
                "status": "DEPLOYING",
                "deployed_at": datetime.now().isoformat()
            }
            
            await self._store_deployment_info(deployed_index_id, deployment_info)
            
            logger.info(f"Index deployment initiated: {deployed_index_id}")
            
            return {
                "success": True,
                "deployment_id": deployed_index_id,
                "status": "DEPLOYING",
                "message": "Index deployment initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy index {index_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to deploy index {index_name}"
            }
    
    async def update_index_data(
        self,
        index_name: str,
        embeddings_data_uri: str,
        update_method: str = "BATCH_UPDATE"
    ) -> Dict[str, Any]:
        """
        Update vector index with new embeddings data
        
        Args:
            index_name: Name of the index to update
            embeddings_data_uri: GCS URI containing embeddings data
            update_method: Update method (BATCH_UPDATE or STREAM_UPDATE)
            
        Returns:
            Dict containing update status
        """
        try:
            logger.info(f"Updating index {index_name} with data from {embeddings_data_uri}")
            
            # Get index information
            index_info = await self._get_index_info(index_name)
            if not index_info:
                raise ValueError(f"Index {index_name} not found")
            
            # Get the index object
            index = MatchingEngineIndex(index_info["index_id"])
            
            # Update the index
            if update_method == "BATCH_UPDATE":
                operation = index.update_embeddings(
                    contents_delta_uri=embeddings_data_uri
                )
            else:
                # For stream updates, we would use a different approach
                raise NotImplementedError("Stream updates not yet implemented")
            
            # Update status in Firestore
            index_info["last_updated"] = datetime.now().isoformat()
            index_info["status"] = "UPDATING"
            index_info["data_uri"] = embeddings_data_uri
            await self._store_index_info(index_name, index_info)
            
            logger.info(f"Index update initiated for {index_name}")
            
            return {
                "success": True,
                "index_name": index_name,
                "status": "UPDATING",
                "operation_id": operation.operation.name if hasattr(operation, 'operation') else None,
                "message": "Index update initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update index {index_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update index {index_name}"
            }
    
    async def get_index_status(self, index_name: str) -> Dict[str, Any]:
        """Get the current status of a vector index"""
        try:
            index_info = await self._get_index_info(index_name)
            if not index_info:
                return {"success": False, "error": "Index not found"}
            
            # Get live status from Vertex AI
            try:
                index = MatchingEngineIndex(index_info["index_id"])
                live_status = index.gca_resource.state.name
                
                # Update stored status if different
                if live_status != index_info.get("status"):
                    index_info["status"] = live_status
                    index_info["last_status_check"] = datetime.now().isoformat()
                    await self._store_index_info(index_name, index_info)
                
            except Exception as e:
                logger.warning(f"Could not get live status for {index_name}: {e}")
                live_status = index_info.get("status", "UNKNOWN")
            
            return {
                "success": True,
                "index_name": index_name,
                "status": live_status,
                "index_info": index_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get status for index {index_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_indexes(self) -> Dict[str, Any]:
        """List all vector indexes"""
        try:
            # Get from Firestore
            indexes_ref = self.index_collection.stream()
            indexes = []
            
            async for doc in indexes_ref:
                index_data = doc.to_dict()
                index_data["firestore_id"] = doc.id
                indexes.append(index_data)
            
            return {
                "success": True,
                "indexes": indexes,
                "count": len(indexes)
            }
            
        except Exception as e:
            logger.error(f"Failed to list indexes: {e}")
            return {
                "success": False,
                "error": str(e),
                "indexes": []
            }
    
    async def delete_index(self, index_name: str, force: bool = False) -> Dict[str, Any]:
        """Delete a vector index and clean up resources"""
        try:
            logger.info(f"Deleting index {index_name}")
            
            index_info = await self._get_index_info(index_name)
            if not index_info:
                return {"success": False, "error": "Index not found"}
            
            # Check for active deployments
            if not force:
                deployments = await self._get_index_deployments(index_name)
                if deployments:
                    return {
                        "success": False,
                        "error": "Index has active deployments. Use force=True to delete anyway.",
                        "active_deployments": len(deployments)
                    }
            
            # Delete the index
            index = MatchingEngineIndex(index_info["index_id"])
            index.delete()
            
            # Clean up Firestore records
            await self._delete_index_info(index_name)
            
            logger.info(f"Index {index_name} deleted successfully")
            
            return {
                "success": True,
                "message": f"Index {index_name} deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # Private helper methods
    
    async def _store_index_info(self, index_name: str, info: Dict[str, Any]):
        """Store index information in Firestore"""
        try:
            self.index_collection.document(index_name).set(info)
        except Exception as e:
            logger.error(f"Failed to store index info for {index_name}: {e}")
    
    async def _get_index_info(self, index_name: str) -> Optional[Dict[str, Any]]:
        """Get index information from Firestore"""
        try:
            doc = self.index_collection.document(index_name).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Failed to get index info for {index_name}: {e}")
            return None
    
    async def _delete_index_info(self, index_name: str):
        """Delete index information from Firestore"""
        try:
            self.index_collection.document(index_name).delete()
        except Exception as e:
            logger.error(f"Failed to delete index info for {index_name}: {e}")
    
    async def _store_endpoint_info(self, endpoint_name: str, info: Dict[str, Any]):
        """Store endpoint information in Firestore"""
        try:
            db.collection('vector_endpoints').document(endpoint_name).set(info)
        except Exception as e:
            logger.error(f"Failed to store endpoint info for {endpoint_name}: {e}")
    
    async def _get_endpoint_info(self, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """Get endpoint information from Firestore"""
        try:
            doc = db.collection('vector_endpoints').document(endpoint_name).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Failed to get endpoint info for {endpoint_name}: {e}")
            return None
    
    async def _store_deployment_info(self, deployment_id: str, info: Dict[str, Any]):
        """Store deployment information in Firestore"""
        try:
            self.deployment_collection.document(deployment_id).set(info)
        except Exception as e:
            logger.error(f"Failed to store deployment info for {deployment_id}: {e}")
    
    async def _get_index_deployments(self, index_name: str) -> List[Dict[str, Any]]:
        """Get all deployments for an index"""
        try:
            deployments_ref = self.deployment_collection.where("index_name", "==", index_name).stream()
            return [doc.to_dict() for doc in deployments_ref]
        except Exception as e:
            logger.error(f"Failed to get deployments for {index_name}: {e}")
            return []
    
    async def _wait_for_index_ready(self, index: MatchingEngineIndex, timeout: int = 1800):
        """Wait for index to be ready for deployment"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                state = index.gca_resource.state.name
                if state == "INDEX_STATE_READY":
                    logger.info(f"Index {index.display_name} is ready")
                    return
                elif state in ["INDEX_STATE_FAILED", "INDEX_STATE_ERROR"]:
                    raise Exception(f"Index failed with state: {state}")
                
                logger.info(f"Index {index.display_name} state: {state}, waiting...")
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error checking index status: {e}")
                await asyncio.sleep(30)
        
        raise TimeoutError(f"Index {index.display_name} did not become ready within {timeout} seconds")

# Global instance
vector_index_service = VectorIndexService()