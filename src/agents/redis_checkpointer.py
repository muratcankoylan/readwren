"""Custom Redis checkpointer for LangGraph state persistence."""

import pickle
from typing import Optional, Any, Dict, Sequence, Tuple
import redis
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


class RedisCheckpointSaver(BaseCheckpointSaver):
    """Redis-based checkpoint saver for LangGraph.
    
    Stores conversation state in Redis with automatic serialization/deserialization.
    Supports TTL for automatic session cleanup.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        namespace: str = "langgraph:checkpoint",
        ttl: int = 86400  # 24 hours default
    ):
        """Initialize Redis checkpointer.
        
        Args:
            redis_client: Redis client instance
            namespace: Key prefix for all checkpoints
            ttl: Time-to-live for checkpoints in seconds (default 24h)
        """
        super().__init__(serde=JsonPlusSerializer())
        self.redis = redis_client
        self.namespace = namespace
        self.ttl = ttl

    def _make_key(self, thread_id: str, checkpoint_ns: str = "", checkpoint_id: Optional[str] = None) -> str:
        """Generate Redis key for a checkpoint.
        
        Args:
            thread_id: Session/thread identifier
            checkpoint_ns: Checkpoint namespace
            checkpoint_id: Optional specific checkpoint ID
            
        Returns:
            Redis key string
        """
        parts = [self.namespace, thread_id]
        if checkpoint_ns:
            parts.append(checkpoint_ns)
        if checkpoint_id:
            parts.append(checkpoint_id)
        else:
            parts.append("latest")
        return ":".join(parts)

    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Dict[str, Any],
        new_versions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save a checkpoint to Redis.
        
        Args:
            config: Configuration with thread_id
            checkpoint: Checkpoint data to save
            metadata: Checkpoint metadata
            new_versions: Version information
            
        Returns:
            Updated configuration
        """
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        
        # Only store serializable config data
        safe_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint.get("id")
            }
        }
        
        # Serialize checkpoint tuple
        data = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "config": safe_config
        }
        serialized = pickle.dumps(data)
        
        # Store in Redis with TTL
        key = self._make_key(thread_id, checkpoint_ns, checkpoint.get("id"))
        self.redis.setex(key, self.ttl, serialized)
        
        # Also store as latest
        latest_key = self._make_key(thread_id, checkpoint_ns)
        self.redis.setex(latest_key, self.ttl, serialized)
        
        return config

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Retrieve checkpoint tuple from Redis.
        
        Args:
            config: Configuration with thread_id
            
        Returns:
            CheckpointTuple or None if not found
        """
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        # Retrieve from Redis
        key = self._make_key(thread_id, checkpoint_ns, checkpoint_id)
        serialized = self.redis.get(key)
        
        if serialized is None:
            return None
        
        # Deserialize
        data = pickle.loads(serialized)
        
        return CheckpointTuple(
            config=data.get("config", config),
            checkpoint=data["checkpoint"],
            metadata=data.get("metadata", {}),
            parent_config=data.get("config", {}).get("configurable")
        )

    def list(self, config: Dict[str, Any], *, filter: Optional[Dict[str, Any]] = None, before: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> Sequence[CheckpointTuple]:
        """List checkpoints for a thread.
        
        Args:
            config: Configuration with thread_id
            filter: Optional filter criteria
            before: Optional cursor for pagination
            limit: Maximum number of results
            
        Returns:
            Sequence of CheckpointTuples
        """
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        
        # Find all keys for this thread
        pattern = f"{self.namespace}:{thread_id}:{checkpoint_ns}:*" if checkpoint_ns else f"{self.namespace}:{thread_id}:*"
        keys = self.redis.keys(pattern)
        
        tuples = []
        for key in keys:
            # Skip 'latest' keys
            if key.decode().endswith(":latest"):
                continue
                
            serialized = self.redis.get(key)
            if serialized:
                data = pickle.loads(serialized)
                tuples.append(CheckpointTuple(
                    config=data.get("config", config),
                    checkpoint=data["checkpoint"],
                    metadata=data.get("metadata", {}),
                    parent_config=data.get("config", {}).get("configurable")
                ))
        
        # Apply limit if specified
        if limit:
            tuples = tuples[:limit]
        
        return tuples

    def put_writes(self, config: Dict[str, Any], writes: Sequence[Tuple[str, Any]], task_id: str) -> None:
        """Store pending writes (not implemented for simple use case).
        
        Args:
            config: Configuration
            writes: Pending writes
            task_id: Task identifier
        """
        # For simple use case, we don't need to implement this
        pass

