"""
Klar Search Engine - Centralized Logging Configuration
Enterprise-Grade Logging Infrastructure

Features:
- Rotating file handlers (prevents log files from growing too large)
- Separate log files for different components
- Structured logging with JSON support
- Different log levels for development and production
- Performance tracking
- Error tracking with stack traces
- Security event logging
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from config import LOGS_DIR, PRODUCTION, LOG_LEVEL

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output (development)"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m'  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(name: str, log_file: str = None, level: int = None) -> logging.Logger:
    """
    Setup a logger with rotating file handlers and console output
    
    Args:
        name: Logger name (usually module name)
        log_file: Optional specific log file (default: <name>.log)
        level: Log level (default: from config)
    
    Returns:
        Configured logger instance
    """
    if level is None:
        level = getattr(logging, LOG_LEVEL)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler with rotation (10 MB per file, keep 10 files)
    if log_file is None:
        log_file = f"{name.replace('.', '_')}.log"
    
    file_path = LOGS_DIR / log_file
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
        encoding='utf-8'
    )
    
    if PRODUCTION:
        # JSON format for production (easier to parse)
        file_handler.setFormatter(JSONFormatter())
    else:
        # Human-readable format for development
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
    
    logger.addHandler(file_handler)
    
    # Console handler (always human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if PRODUCTION:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


# Specialized loggers for different components
def get_crawler_logger():
    """Logger for web crawler operations"""
    return setup_logger('kse.crawler', 'crawler.log')


def get_indexer_logger():
    """Logger for index building operations"""
    return setup_logger('kse.indexer', 'indexer.log')


def get_nlp_logger():
    """Logger for NLP processing"""
    return setup_logger('kse.nlp', 'nlp.log')


def get_ranker_logger():
    """Logger for ranking operations"""
    return setup_logger('kse.ranker', 'ranker.log')


def get_api_logger():
    """Logger for API server operations"""
    return setup_logger('kse.api', 'api.log')


def get_security_logger():
    """Logger for security events (unauthorized access, rate limiting, etc.)"""
    logger = setup_logger('kse.security', 'security.log')
    logger.setLevel(logging.WARNING)  # Only log warnings and above
    return logger


def get_performance_logger():
    """Logger for performance tracking"""
    return setup_logger('kse.performance', 'performance.log')


# Error tracking utilities
class ErrorTracker:
    """Track and aggregate errors for monitoring"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.logger = setup_logger('kse.errors', 'errors.log')
    
    def log_error(self, error_type: str, message: str, extra_data: Dict[str, Any] = None):
        """Log an error with tracking"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        self.logger.error(
            f"{error_type}: {message}",
            extra={'extra_data': extra_data} if extra_data else None
        )
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of error counts"""
        return self.error_counts.copy()
    
    def reset_counts(self):
        """Reset error counts (useful for periodic reporting)"""
        self.error_counts.clear()


# Performance tracking utilities
class PerformanceTracker:
    """Track performance metrics"""
    
    def __init__(self):
        self.logger = get_performance_logger()
        self.metrics: Dict[str, list] = {}
    
    def log_operation(self, operation: str, duration_ms: float, success: bool = True, 
                     extra_data: Dict[str, Any] = None):
        """Log an operation's performance"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append({
            'duration_ms': duration_ms,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            f"Operation '{operation}' completed in {duration_ms:.2f}ms (success={success})",
            extra={'extra_data': extra_data} if extra_data else None
        )
    
    def get_metrics(self, operation: str = None) -> Dict:
        """Get performance metrics"""
        if operation:
            return {
                'operation': operation,
                'data': self.metrics.get(operation, [])
            }
        return self.metrics.copy()


# Global instances
error_tracker = ErrorTracker()
performance_tracker = PerformanceTracker()


# Setup main application logger
def setup_application_logging():
    """Initialize logging for the entire application"""
    # Create main application logger
    app_logger = setup_logger('kse', 'kse.log')
    
    app_logger.info("=" * 80)
    app_logger.info("Klar Search Engine - Logging System Initialized")
    app_logger.info(f"Mode: {'PRODUCTION' if PRODUCTION else 'DEVELOPMENT'}")
    app_logger.info(f"Log Level: {LOG_LEVEL}")
    app_logger.info(f"Logs Directory: {LOGS_DIR}")
    app_logger.info("=" * 80)
    
    return app_logger


# Initialize on import
main_logger = setup_application_logging()
