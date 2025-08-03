"""
Embeddings Pipeline Service
Handles text-to-vector conversion with batch processing, rate limiting, and multiple provider support
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import tempfile
import gzip

import numpy as np
from google.cloud import aiplatform
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

from infinitum.settings import settings
from infinitum.infrastructure.logging_config import get_agent_logger
from infinitum.infrastructure.persistence.firestore_client import db

logger = get_agent_logger("embeddings_service")

@dataclass
class EmbeddingRequest:
    """Single embedding request"""
    id: str
    text: str
    metadata: Optional[Dict[str, Any]] = None
    task_type: str = "SEMANTIC_SIMILARITY"  # SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING

@dataclass
class EmbeddingResult:
    """Single embedding result"""
    id: str
    embedding: List[float]
    metadata: Optional[Dict[str, Any]] = None
    model_used: str = ""
    processing_time: float = 0.0
    error: Optional[str] = None

@dataclass
class BatchEmbeddingResult:
    """Batch embedding processing result"""
    success_count: int
    error_count: int
    results: List[EmbeddingResult]
    total_processing_time: float
    model_used: str
    batch_id: str

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_requests_per_minute: int = 1000, max_tokens_per_minute: int = 100000):
        self.max_requests_per_minute = max_requests_per_minute
        self.max_tokens_per_minute = max_tokens_per_minute
        self.request_times = []
        self.token_counts = []
        self.lock = asyncio.Lock()
    
    async def acquire(self, token_count: int = 1):
        """Acquire rate limit permission"""
        async with self.lock:
            now = time.time()
            minute_ago = now - 60
            
            # Clean old entries
            self.request_times = [t for t in self.request_times if t > minute_ago]
            self.token_counts = [(t, c) for t, c in self.token_counts if t > minute_ago]
            
            # Check limits
            current_requests = len(self.request_times)
            current_tokens = sum(c for _, c in self.token_counts)
            
            if (current_requests >= self.max_requests_per_minute or 
                current_tokens + token_count > self.max_tokens_per_minute):
                
                # Calculate wait time
                if current_requests >= self.max_requests_per_minute:
                    wait_time = 61 - (now - min(self.request_times))
                else:
                    wait_time = 61 - (now - min(t for t, _ in self.token_counts))
                
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(max(0, wait_time))
                return await self.acquire(token_count)
            
            # Record this request
            self.request_times.append(now)
            self.token_counts.append((now, token_count))

class EmbeddingsService:
    """Comprehensive embeddings service with multiple providers and advanced features"""
    
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = "us-central1"
        self.embeddings_collection = db.collection('embeddings_cache')
        self.batch_collection = db.collection('embedding_batches')
        
        # Rate limiters for different providers
        self.vertex_rate_limiter = RateLimiter(max_requests_per_minute=1000, max_tokens_per_minute=100000)
        self.openai_rate_limiter = RateLimiter(max_requests_per_minute=3000, max_tokens_per_minute=1000000)
        
        # Initialize providers
        self._initialize_providers()
        
        # Cache settings
        self.cache_enabled = True
        self.cache_ttl_hours = 24 * 7  # 1 week
        
        # Batch processing settings
        self.max_batch_size = 100
        self.max_concurrent_batches = 5
        
    def _initialize_providers(self):
        """Initialize embedding providers"""
        try:
            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            aiplatform.init(project=self.project_id, location=self.location)
            
            # Initialize models
            self.vertex_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
            self.vertex_multilingual_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
            
            logger.info("Initialized Vertex AI embedding models")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI embeddings: {e}")
            self.vertex_model = None
            self.vertex_multilingual_model = None
        
        # Initialize OpenAI if available
        try:
            if settings.OPENAI_API_KEY:
                import openai
                self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("Initialized OpenAI embeddings client")
            else:
                self.openai_client = None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            self.openai_client = None
    
    async def generate_embedding(
        self,
        text: str,
        model: str = "vertex-text-embedding-004",
        task_type: str = "SEMANTIC_SIMILARITY",
        use_cache: bool = True
    ) -> EmbeddingResult:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            model: Model to use (vertex-text-embedding-004, openai-text-embedding-ada-002, etc.)
            task_type: Task type for optimization
            use_cache: Whether to use caching
            
        Returns:
            EmbeddingResult with the generated embedding
        """
        start_time = time.time()
        text_id = self._generate_text_id(text, model)
        
        try:
            # Check cache first
            if use_cache:
                cached_result = await self._get_cached_embedding(text_id)
                if cached_result:
                    logger.debug(f"Using cached embedding for text ID: {text_id[:8]}...")
                    return cached_result
            
            # Generate new embedding
            if model.startswith("vertex-"):
                result = await self._generate_vertex_embedding(text, model, task_type)
            elif model.startswith("openai-"):
                result = await self._generate_openai_embedding(text, model)
            else:
                raise ValueError(f"Unsupported model: {model}")
            
            # Set metadata
            result.id = text_id
            result.processing_time = time.time() - start_time
            result.model_used = model
            
            # Cache the result
            if use_cache and result.error is None:
                await self._cache_embedding(text_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return EmbeddingResult(
                id=text_id,
                embedding=[],
                error=str(e),
                model_used=model,
                processing_time=time.time() - start_time
            )
    
    async def generate_batch_embeddings(
        self,
        requests: List[EmbeddingRequest],
        model: str = "vertex-text-embedding-004",
        batch_size: Optional[int] = None,
        max_concurrent: Optional[int] = None
    ) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts with batch processing
        
        Args:
            requests: List of embedding requests
            model: Model to use for all requests
            batch_size: Size of each batch (default: self.max_batch_size)
            max_concurrent: Maximum concurrent batches (default: self.max_concurrent_batches)
            
        Returns:
            BatchEmbeddingResult with all results
        """
        start_time = time.time()
        batch_id = f"batch_{int(time.time())}_{len(requests)}"
        
        logger.info(f"Starting batch embedding generation: {batch_id} ({len(requests)} requests)")
        
        # Set defaults
        batch_size = batch_size or self.max_batch_size
        max_concurrent = max_concurrent or self.max_concurrent_batches
        
        # Split into batches
        batches = [requests[i:i + batch_size] for i in range(0, len(requests), batch_size)]
        
        # Process batches concurrently
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [self._process_batch(batch, model, semaphore, f"{batch_id}_{i}") 
                for i, batch in enumerate(batches)]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_results = []
        success_count = 0
        error_count = 0
        
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Batch processing failed: {batch_result}")
                error_count += 1
                continue
            
            all_results.extend(batch_result)
            success_count += sum(1 for r in batch_result if r.error is None)
            error_count += sum(1 for r in batch_result if r.error is not None)
        
        total_time = time.time() - start_time
        
        # Store batch information
        batch_info = {
            "batch_id": batch_id,
            "total_requests": len(requests),
            "success_count": success_count,
            "error_count": error_count,
            "model_used": model,
            "processing_time": total_time,
            "created_at": datetime.now().isoformat()
        }
        
        await self._store_batch_info(batch_id, batch_info)
        
        logger.info(f"Batch embedding completed: {batch_id} "
                   f"({success_count} success, {error_count} errors, {total_time:.2f}s)")
        
        return BatchEmbeddingResult(
            success_count=success_count,
            error_count=error_count,
            results=all_results,
            total_processing_time=total_time,
            model_used=model,
            batch_id=batch_id
        )
    
    async def prepare_vector_index_data(
        self,
        embeddings_results: List[EmbeddingResult],
        output_gcs_path: str,
        metadata_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Prepare embeddings data for vector index upload
        
        Args:
            embeddings_results: List of embedding results
            output_gcs_path: GCS path for output files
            metadata_fields: Fields to include in metadata
            
        Returns:
            Dict with preparation results and file paths
        """
        try:
            logger.info(f"Preparing vector index data for {len(embeddings_results)} embeddings")
            
            # Filter successful results
            valid_results = [r for r in embeddings_results if r.error is None and r.embedding]
            
            if not valid_results:
                raise ValueError("No valid embeddings to prepare")
            
            # Prepare data in the format expected by Vertex AI Vector Search
            # Format: {"id": "item_id", "embedding": [0.1, 0.2, ...], "restricts": [{"namespace": "category", "allow": ["electronics"]}]}
            
            vector_data = []
            for result in valid_results:
                item = {
                    "id": result.id,
                    "embedding": result.embedding
                }
                
                # Add metadata as restricts if specified
                if result.metadata and metadata_fields:
                    restricts = []
                    for field in metadata_fields:
                        if field in result.metadata:
                            restricts.append({
                                "namespace": field,
                                "allow": [str(result.metadata[field])]
                            })
                    if restricts:
                        item["restricts"] = restricts
                
                vector_data.append(item)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
                for item in vector_data:
                    f.write(json.dumps(item) + '\n')
                temp_file_path = f.name
            
            # Compress the file
            compressed_path = temp_file_path + '.gz'
            with open(temp_file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Upload to GCS
            gcs_uri = await self._upload_to_gcs(compressed_path, output_gcs_path)
            
            # Clean up temporary files
            Path(temp_file_path).unlink()
            Path(compressed_path).unlink()
            
            logger.info(f"Vector index data prepared and uploaded to {gcs_uri}")
            
            return {
                "success": True,
                "gcs_uri": gcs_uri,
                "total_vectors": len(vector_data),
                "dimensions": len(valid_results[0].embedding) if valid_results else 0,
                "metadata_fields": metadata_fields or []
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare vector index data: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _process_batch(
        self,
        batch: List[EmbeddingRequest],
        model: str,
        semaphore: asyncio.Semaphore,
        batch_id: str
    ) -> List[EmbeddingResult]:
        """Process a single batch of embedding requests"""
        async with semaphore:
            logger.debug(f"Processing batch {batch_id} with {len(batch)} requests")
            
            tasks = [self.generate_embedding(req.text, model, req.task_type) for req in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to error results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(EmbeddingResult(
                        id=batch[i].id,
                        embedding=[],
                        error=str(result),
                        model_used=model
                    ))
                else:
                    processed_results.append(result)
            
            return processed_results
    
    async def _generate_vertex_embedding(
        self,
        text: str,
        model: str,
        task_type: str
    ) -> EmbeddingResult:
        """Generate embedding using Vertex AI"""
        if not self.vertex_model:
            raise ValueError("Vertex AI embedding model not available")
        
        # Rate limiting
        token_count = len(text.split())
        await self.vertex_rate_limiter.acquire(token_count)
        
        try:
            # Choose model based on requirements
            if "multilingual" in model:
                embedding_model = self.vertex_multilingual_model
            else:
                embedding_model = self.vertex_model
            
            # Create embedding input
            embedding_input = TextEmbeddingInput(
                text=text,
                task_type=task_type
            )
            
            # Generate embedding
            embeddings = embedding_model.get_embeddings([embedding_input])
            
            if not embeddings or not embeddings[0].values:
                raise ValueError("Empty embedding returned")
            
            return EmbeddingResult(
                id="",  # Will be set by caller
                embedding=embeddings[0].values,
                model_used=model
            )
            
        except Exception as e:
            logger.error(f"Vertex AI embedding generation failed: {e}")
            raise
    
    async def _generate_openai_embedding(self, text: str, model: str) -> EmbeddingResult:
        """Generate embedding using OpenAI"""
        if not self.openai_client:
            raise ValueError("OpenAI client not available")
        
        # Rate limiting
        token_count = len(text.split()) * 1.3  # Rough estimate
        await self.openai_rate_limiter.acquire(int(token_count))
        
        try:
            # Map model names
            openai_model = "text-embedding-ada-002"
            if "3-large" in model:
                openai_model = "text-embedding-3-large"
            elif "3-small" in model:
                openai_model = "text-embedding-3-small"
            
            response = await self.openai_client.embeddings.create(
                input=text,
                model=openai_model
            )
            
            if not response.data or not response.data[0].embedding:
                raise ValueError("Empty embedding returned")
            
            return EmbeddingResult(
                id="",  # Will be set by caller
                embedding=response.data[0].embedding,
                model_used=model
            )
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    def _generate_text_id(self, text: str, model: str) -> str:
        """Generate unique ID for text and model combination"""
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _get_cached_embedding(self, text_id: str) -> Optional[EmbeddingResult]:
        """Get cached embedding if available and valid"""
        try:
            doc = self.embeddings_collection.document(text_id).get()
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            # Check if cache is still valid
            cached_time = datetime.fromisoformat(data.get("cached_at", ""))
            if datetime.now() - cached_time > timedelta(hours=self.cache_ttl_hours):
                # Cache expired, delete it
                self.embeddings_collection.document(text_id).delete()
                return None
            
            return EmbeddingResult(
                id=text_id,
                embedding=data["embedding"],
                metadata=data.get("metadata"),
                model_used=data["model_used"],
                processing_time=0.0  # Cached, no processing time
            )
            
        except Exception as e:
            logger.error(f"Failed to get cached embedding: {e}")
            return None
    
    async def _cache_embedding(self, text_id: str, result: EmbeddingResult):
        """Cache embedding result"""
        try:
            cache_data = {
                "embedding": result.embedding,
                "metadata": result.metadata,
                "model_used": result.model_used,
                "cached_at": datetime.now().isoformat(),
                "processing_time": result.processing_time
            }
            
            self.embeddings_collection.document(text_id).set(cache_data)
            
        except Exception as e:
            logger.error(f"Failed to cache embedding: {e}")
    
    async def _store_batch_info(self, batch_id: str, info: Dict[str, Any]):
        """Store batch processing information"""
        try:
            self.batch_collection.document(batch_id).set(info)
        except Exception as e:
            logger.error(f"Failed to store batch info: {e}")
    
    async def _upload_to_gcs(self, local_path: str, gcs_path: str) -> str:
        """Upload file to Google Cloud Storage"""
        try:
            # Parse GCS path
            if not gcs_path.startswith("gs://"):
                raise ValueError("GCS path must start with gs://")
            
            path_parts = gcs_path[5:].split("/", 1)
            bucket_name = path_parts[0]
            blob_name = path_parts[1] if len(path_parts) > 1 else "embeddings.jsonl.gz"
            
            # Upload file
            client = storage.Client(project=self.project_id)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            blob.upload_from_filename(local_path)
            
            return f"gs://{bucket_name}/{blob_name}"
            
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            raise
    
    async def get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding service statistics"""
        try:
            # Get cache stats
            cache_docs = list(self.embeddings_collection.limit(1000).stream())
            cache_count = len(cache_docs)
            
            # Get batch stats
            batch_docs = list(self.batch_collection.limit(100).stream())
            recent_batches = [doc.to_dict() for doc in batch_docs]
            
            # Calculate stats
            total_embeddings = sum(batch.get("success_count", 0) for batch in recent_batches)
            total_errors = sum(batch.get("error_count", 0) for batch in recent_batches)
            
            return {
                "cache_entries": cache_count,
                "recent_batches": len(recent_batches),
                "total_embeddings_generated": total_embeddings,
                "total_errors": total_errors,
                "cache_hit_rate": "N/A",  # Would need more detailed tracking
                "available_models": [
                    "vertex-text-embedding-004",
                    "vertex-text-multilingual-embedding-002",
                    "openai-text-embedding-ada-002",
                    "openai-text-embedding-3-small",
                    "openai-text-embedding-3-large"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {"error": str(e)}
    
    async def clear_cache(self, older_than_hours: Optional[int] = None) -> Dict[str, Any]:
        """Clear embedding cache"""
        try:
            if older_than_hours:
                # Clear only old entries
                cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
                docs = self.embeddings_collection.where("cached_at", "<", cutoff_time.isoformat()).stream()
            else:
                # Clear all entries
                docs = self.embeddings_collection.stream()
            
            deleted_count = 0
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1
            
            logger.info(f"Cleared {deleted_count} cached embeddings")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"Cleared {deleted_count} cached embeddings"
            }
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Global instance
embeddings_service = EmbeddingsService()