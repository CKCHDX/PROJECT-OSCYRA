"""
Environment Configuration Manager
Handles environment-specific settings for development, staging, and production
"""

import os
from pathlib import Path
from typing import Dict, Any

class EnvironmentConfig:
    """Environment-specific configuration"""
    
    def __init__(self, env: str = None):
        self.env = env or os.getenv('KSE_ENV', 'development')
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration based on environment"""
        
        # Base configuration
        base = {
            'APP_NAME': 'Klar Search Engine',
            'VERSION': '1.0.0',
            'DEBUG': False,
            'TESTING': False,
        }
        
        # Environment-specific overrides
        if self.env == 'development':
            return {
                **base,
                'DEBUG': True,
                'LOG_LEVEL': 'DEBUG',
                'API_HOST': '127.0.0.1',
                'API_PORT': 5000,
                'CORS_ORIGINS': '*',
                'PRODUCTION': False,
                'ENABLE_PROFILING': True,
            }
        
        elif self.env == 'staging':
            return {
                **base,
                'DEBUG': False,
                'LOG_LEVEL': 'INFO',
                'API_HOST': '0.0.0.0',
                'API_PORT': 5000,
                'CORS_ORIGINS': 'https://staging.oscyra.solutions',
                'PRODUCTION': True,
                'ENABLE_PROFILING': False,
            }
        
        elif self.env == 'production':
            return {
                **base,
                'DEBUG': False,
                'LOG_LEVEL': 'WARNING',
                'API_HOST': '0.0.0.0',
                'API_PORT': 5000,
                'CORS_ORIGINS': 'https://klar.oscyra.solutions',
                'PRODUCTION': True,
                'ENABLE_PROFILING': False,
                'SECURITY_HEADERS': True,
            }
        
        else:
            raise ValueError(f"Unknown environment: {self.env}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        # Check environment variable first
        env_value = os.getenv(f'KSE_{key}')
        if env_value is not None:
            return env_value
        
        # Fall back to config
        return self.config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        return self.get(key)
    
    def __repr__(self) -> str:
        return f"EnvironmentConfig(env='{self.env}')"


# Global instance
env_config = EnvironmentConfig()


# Environment variables reference
ENV_VARS_REFERENCE = """
KSE Environment Variables:

Core:
  KSE_ENV                 - Environment name (development/staging/production)
  KSE_PRODUCTION          - Production mode (0/1)
  KSE_DEBUG               - Debug mode (0/1)
  KSE_LOG_LEVEL           - Logging level (DEBUG/INFO/WARNING/ERROR)

API:
  KSE_API_HOST            - API server host (default: 0.0.0.0)
  KSE_API_PORT            - API server port (default: 5000)
  KSE_CORS_ORIGINS        - CORS allowed origins

Crawler:
  KSE_MAX_CONCURRENT_CRAWLS  - Max parallel crawls (default: 10)
  KSE_CRAWL_TIMEOUT          - Request timeout in seconds (default: 30)

Database (optional):
  KSE_DATABASE_URL        - PostgreSQL connection string
  KSE_DATABASE_POOL_SIZE  - Connection pool size (default: 10)

Security:
  KSE_SECRET_KEY          - Secret key for session management
  KSE_RATE_LIMIT          - API rate limit (requests per minute)

Monitoring:
  KSE_SENTRY_DSN          - Sentry error tracking DSN
  KSE_PROMETHEUS_PORT     - Prometheus metrics port
"""

if __name__ == '__main__':
    print(ENV_VARS_REFERENCE)
    print(f"\nCurrent environment: {env_config.env}")
    print(f"Config: {env_config.config}")
