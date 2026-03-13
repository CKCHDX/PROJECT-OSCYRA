"""
Error Recovery Utilities
Enterprise-Grade Recovery Mechanisms for KSE

Features:
- Checkpoint/resume for long-running operations
- Automatic retry with exponential backoff
- Index corruption detection and recovery
- Transaction-like operations with rollback
- Circuit breaker pattern for external services
"""

import time
import json
import pickle
import hashlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, List
from functools import wraps
from datetime import datetime, timedelta

from config import DATA_DIR, INDEX_DIR, CRAWL_DIR
from logger_config import setup_logger

logger = setup_logger('kse.recovery', 'recovery.log')


class Checkpoint:
    """Checkpoint manager for resumable operations"""
    
    def __init__(self, operation_name: str, checkpoint_dir: Path = None):
        self.operation_name = operation_name
        self.checkpoint_dir = checkpoint_dir or (DATA_DIR / "checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / f"{operation_name}.checkpoint.json"
        self.state: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load checkpoint from disk"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    self.state = json.load(f)
                logger.info(f"Loaded checkpoint for {self.operation_name}: {len(self.state)} items")
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")
                self.state = {}
        else:
            self.state = {}
    
    def save(self):
        """Save checkpoint to disk"""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"Saved checkpoint for {self.operation_name}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def set(self, key: str, value: Any):
        """Set checkpoint value"""
        self.state[key] = value
        self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get checkpoint value"""
        return self.state.get(key, default)
    
    def mark_completed(self, item_id: str):
        """Mark an item as completed"""
        if 'completed' not in self.state:
            self.state['completed'] = []
        self.state['completed'].append(item_id)
        self.save()
    
    def is_completed(self, item_id: str) -> bool:
        """Check if item is completed"""
        return item_id in self.state.get('completed', [])
    
    def clear(self):
        """Clear checkpoint"""
        self.state = {}
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        logger.info(f"Cleared checkpoint for {self.operation_name}")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (retries - 1)), max_delay)
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} after {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)
            
            return None
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for external service calls
    Prevents cascading failures by stopping requests to failing services
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        States:
        - CLOSED: Normal operation, allow all requests
        - OPEN: Too many failures, block all requests
        - HALF_OPEN: Testing if service recovered
        """
        if self.state == 'OPEN':
            # Check if recovery timeout has passed
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            self.failure_count = 0
            logger.info("Circuit breaker closed - service recovered")
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


class IndexRecovery:
    """Index corruption detection and recovery"""
    
    @staticmethod
    def verify_index(index_path: Path) -> bool:
        """
        Verify index file integrity
        
        Returns:
            True if index is valid, False otherwise
        """
        try:
            with open(index_path, 'rb') as f:
                index = pickle.load(f)
            
            # Basic sanity checks
            if not hasattr(index, 'index'):
                logger.error("Index missing 'index' attribute")
                return False
            
            if not hasattr(index, 'documents'):
                logger.error("Index missing 'documents' attribute")
                return False
            
            if not hasattr(index, 'num_documents'):
                logger.error("Index missing 'num_documents' attribute")
                return False
            
            # Check consistency
            if len(index.documents) != index.num_documents:
                logger.error(f"Document count mismatch: {len(index.documents)} != {index.num_documents}")
                return False
            
            logger.info(f"Index verification passed: {index.num_documents} documents")
            return True
            
        except Exception as e:
            logger.error(f"Index verification failed: {e}")
            return False
    
    @staticmethod
    def backup_index(index_path: Path, backup_dir: Path = None) -> Optional[Path]:
        """
        Create backup of index file
        
        Returns:
            Path to backup file or None if failed
        """
        if not index_path.exists():
            logger.error(f"Index file not found: {index_path}")
            return None
        
        if backup_dir is None:
            backup_dir = DATA_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"index_backup_{timestamp}.pkl"
        
        try:
            import shutil
            shutil.copy2(index_path, backup_path)
            logger.info(f"Index backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup index: {e}")
            return None
    
    @staticmethod
    def restore_index(backup_path: Path, index_path: Path) -> bool:
        """
        Restore index from backup
        
        Returns:
            True if restored successfully, False otherwise
        """
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            import shutil
            shutil.copy2(backup_path, index_path)
            logger.info(f"Index restored from: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore index: {e}")
            return False
    
    @staticmethod
    def find_latest_backup(backup_dir: Path = None) -> Optional[Path]:
        """Find most recent backup file"""
        if backup_dir is None:
            backup_dir = DATA_DIR / "backups"
        
        if not backup_dir.exists():
            return None
        
        backups = list(backup_dir.glob("index_backup_*.pkl"))
        if not backups:
            return None
        
        # Sort by modification time, newest first
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backups[0]


class TransactionManager:
    """
    Simple transaction manager for atomic operations
    Allows rollback if operation fails
    """
    
    def __init__(self, name: str):
        self.name = name
        self.rollback_actions: List[Callable] = []
        self.committed = False
        self.logger = setup_logger(f'kse.transaction.{name}')
    
    def add_rollback_action(self, action: Callable, *args, **kwargs):
        """Add action to execute on rollback"""
        self.rollback_actions.append(lambda: action(*args, **kwargs))
    
    def commit(self):
        """Commit transaction (clear rollback actions)"""
        self.rollback_actions.clear()
        self.committed = True
        self.logger.info(f"Transaction '{self.name}' committed")
    
    def rollback(self):
        """Execute rollback actions in reverse order"""
        if self.committed:
            self.logger.warning(f"Cannot rollback committed transaction '{self.name}'")
            return
        
        self.logger.warning(f"Rolling back transaction '{self.name}'")
        for action in reversed(self.rollback_actions):
            try:
                action()
            except Exception as e:
                self.logger.error(f"Rollback action failed: {e}")
        
        self.rollback_actions.clear()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - rollback on exception"""
        if exc_type is not None:
            self.rollback()
        return False  # Don't suppress exceptions


# Example usage functions
def resumable_crawl_with_checkpoint(domains: List[str], checkpoint_name: str = "crawl"):
    """
    Example of resumable crawling with checkpoint
    
    Usage:
        resumable_crawl_with_checkpoint(ALL_DOMAINS, "national_crawl")
    """
    checkpoint = Checkpoint(checkpoint_name)
    
    for domain in domains:
        if checkpoint.is_completed(domain):
            logger.info(f"Skipping already crawled domain: {domain}")
            continue
        
        try:
            # Perform crawl (placeholder)
            logger.info(f"Crawling: {domain}")
            # actual_crawl_function(domain)
            
            # Mark as completed
            checkpoint.mark_completed(domain)
            
        except Exception as e:
            logger.error(f"Failed to crawl {domain}: {e}")
            # Checkpoint allows resume from this point
            continue
    
    checkpoint.clear()
    logger.info("Crawl completed successfully")


if __name__ == '__main__':
    # Test recovery mechanisms
    logger.info("Testing error recovery mechanisms...")
    
    # Test checkpoint
    cp = Checkpoint("test_operation")
    cp.set("progress", 50)
    cp.mark_completed("item1")
    print(f"Checkpoint state: {cp.state}")
    
    # Test retry
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    def failing_function():
        print("Attempting operation...")
        raise Exception("Simulated failure")
    
    try:
        failing_function()
    except:
        print("Function failed after retries")
    
    print("Recovery mechanisms test completed")
