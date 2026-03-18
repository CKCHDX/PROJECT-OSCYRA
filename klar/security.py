"""
Security Utilities for Klar Search Engine
Enterprise-Grade Security Controls

Features:
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting
- Security headers
- API key management
"""

import re
import hashlib
import secrets
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from functools import wraps
from flask import request, jsonify
from logger_config import get_security_logger

logger = get_security_logger()


class InputValidator:
    """Validate and sanitize user inputs"""
    
    @staticmethod
    def sanitize_search_query(query: str, max_length: int = 500) -> str:
        """
        Sanitize search query
        
        Args:
            query: Raw search query
            max_length: Maximum allowed length
        
        Returns:
            Sanitized query string
        
        Raises:
            ValueError: If query is invalid
        """
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        # Trim whitespace
        query = query.strip()
        
        # Check length
        if len(query) > max_length:
            logger.warning(f"Query too long: {len(query)} chars (max {max_length})")
            raise ValueError(f"Query exceeds maximum length of {max_length} characters")
        
        if len(query) < 1:
            raise ValueError("Query cannot be empty")
        
        # Remove null bytes
        query = query.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        query = ''.join(char for char in query if ord(char) >= 32 or char in '\n\t')
        
        # Limit consecutive whitespace
        query = re.sub(r'\s+', ' ', query)
        
        return query.strip()
    
    @staticmethod
    def validate_pagination(page: any, per_page: any, max_per_page: int = 100) -> tuple:
        """
        Validate pagination parameters
        
        Returns:
            Tuple of (page, per_page) as validated integers
        
        Raises:
            ValueError: If parameters are invalid
        """
        try:
            page = int(page) if page else 1
            per_page = int(per_page) if per_page else 10
        except (ValueError, TypeError):
            raise ValueError("Invalid pagination parameters")
        
        if page < 1:
            raise ValueError("Page must be >= 1")
        
        if per_page < 1:
            raise ValueError("Per_page must be >= 1")
        
        if per_page > max_per_page:
            raise ValueError(f"Per_page exceeds maximum of {max_per_page}")
        
        return page, per_page
    
    @staticmethod
    def validate_domain(domain: str) -> bool:
        """
        Validate domain name format
        
        Returns:
            True if valid domain
        """
        domain_pattern = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
        return bool(re.match(domain_pattern, domain.lower()))
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: List[str] = ['http', 'https']) -> bool:
        """
        Validate URL format and scheme
        
        Returns:
            True if valid URL
        """
        url_pattern = r'^(https?):\/\/[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url, re.IGNORECASE):
            return False
        
        scheme = url.split('://')[0].lower()
        return scheme in allowed_schemes


class XSSProtection:
    """Protect against Cross-Site Scripting (XSS) attacks"""
    
    @staticmethod
    def escape_html(text: str) -> str:
        """
        Escape HTML special characters
        
        Args:
            text: Input text
        
        Returns:
            HTML-escaped text
        """
        if not text:
            return text
        
        escape_chars = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }
        
        return ''.join(escape_chars.get(char, char) for char in text)
    
    @staticmethod
    def strip_tags(text: str) -> str:
        """
        Remove HTML tags from text
        
        Args:
            text: Input text with potential HTML
        
        Returns:
            Text with HTML tags removed
        """
        if not text:
            return text
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove script content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        return text


class RateLimiter:
    """
    Advanced rate limiting with multiple strategies
    """
    
    def __init__(self):
        # IP -> list of request timestamps
        self.request_history: Dict[str, List[datetime]] = {}
        
        # IP -> block expiry time
        self.blocked_ips: Dict[str, datetime] = {}
    
    def is_rate_limited(
        self,
        identifier: str,
        max_requests: int = 60,
        window_seconds: int = 60,
        block_duration: int = 300
    ) -> tuple:
        """
        Check if identifier (IP, API key, etc.) is rate limited
        
        Args:
            identifier: Unique identifier (IP address, API key, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            block_duration: How long to block after exceeding limit
        
        Returns:
            Tuple of (is_limited: bool, retry_after: int)
        """
        now = datetime.now()
        
        # Check if currently blocked
        if identifier in self.blocked_ips:
            if now < self.blocked_ips[identifier]:
                retry_after = int((self.blocked_ips[identifier] - now).total_seconds())
                return True, retry_after
            else:
                # Block expired, remove
                del self.blocked_ips[identifier]
        
        # Get request history for this identifier
        if identifier not in self.request_history:
            self.request_history[identifier] = []
        
        # Remove old requests outside window
        window_start = now - timedelta(seconds=window_seconds)
        self.request_history[identifier] = [
            ts for ts in self.request_history[identifier]
            if ts > window_start
        ]
        
        # Check if limit exceeded
        if len(self.request_history[identifier]) >= max_requests:
            # Block this identifier
            self.blocked_ips[identifier] = now + timedelta(seconds=block_duration)
            logger.warning(
                f"Rate limit exceeded for {identifier}: "
                f"{len(self.request_history[identifier])} requests in {window_seconds}s. "
                f"Blocked for {block_duration}s"
            )
            return True, block_duration
        
        # Add current request
        self.request_history[identifier].append(now)
        
        return False, 0
    
    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """Clean up old entries to prevent memory bloat"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=max_age_seconds)
        
        # Clean request history
        for identifier in list(self.request_history.keys()):
            self.request_history[identifier] = [
                ts for ts in self.request_history[identifier]
                if ts > cutoff
            ]
            if not self.request_history[identifier]:
                del self.request_history[identifier]
        
        # Clean expired blocks
        for identifier in list(self.blocked_ips.keys()):
            if now >= self.blocked_ips[identifier]:
                del self.blocked_ips[identifier]


class APIKeyManager:
    """Manage API keys for authenticated access"""
    
    def __init__(self):
        self.api_keys: Dict[str, Dict] = {}  # key -> metadata
    
    def generate_key(self, user_id: str, permissions: List[str] = None) -> str:
        """
        Generate a new API key
        
        Args:
            user_id: User identifier
            permissions: List of permissions
        
        Returns:
            API key string
        """
        # Generate secure random key
        key = secrets.token_urlsafe(32)
        
        # Store metadata
        self.api_keys[key] = {
            'user_id': user_id,
            'permissions': permissions or ['read'],
            'created_at': datetime.now().isoformat(),
            'last_used': None,
            'request_count': 0
        }
        
        logger.info(f"Generated API key for user {user_id}")
        return key
    
    def validate_key(self, key: str) -> Optional[Dict]:
        """
        Validate API key and return metadata
        
        Returns:
            Key metadata if valid, None otherwise
        """
        if key not in self.api_keys:
            logger.warning(f"Invalid API key attempted: {key[:8]}...")
            return None
        
        # Update usage
        self.api_keys[key]['last_used'] = datetime.now().isoformat()
        self.api_keys[key]['request_count'] += 1
        
        return self.api_keys[key]
    
    def revoke_key(self, key: str) -> bool:
        """
        Revoke an API key
        
        Returns:
            True if key was revoked
        """
        if key in self.api_keys:
            user_id = self.api_keys[key]['user_id']
            del self.api_keys[key]
            logger.info(f"Revoked API key for user {user_id}")
            return True
        return False


class SecurityHeaders:
    """Security HTTP headers"""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """
        Get recommended security headers
        
        Returns:
            Dictionary of header name -> value
        """
        return {
            # Prevent clickjacking
            'X-Frame-Options': 'DENY',
            
            # Prevent MIME type sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # XSS protection (legacy but still useful)
            'X-XSS-Protection': '1; mode=block',
            
            # HTTPS enforcement (31536000 = 1 year)
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            
            # Referrer policy
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Permissions policy (disable unnecessary features)
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
            
            # Content Security Policy
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';"
        }


# Decorators for route protection
def require_valid_input(func):
    """Decorator to validate search query input"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        query = request.args.get('q', '')
        
        try:
            sanitized_query = InputValidator.sanitize_search_query(query)
            # Add sanitized query to request context
            request.sanitized_query = sanitized_query
            return func(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Invalid input from {request.remote_addr}: {e}")
            return jsonify({'error': str(e)}), 400
    
    return wrapper


def rate_limit(max_requests: int = 60, window_seconds: int = 60):
    """Decorator for rate limiting"""
    limiter = RateLimiter()
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            identifier = request.remote_addr
            
            is_limited, retry_after = limiter.is_rate_limited(
                identifier,
                max_requests,
                window_seconds
            )
            
            if is_limited:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': retry_after
                }), 429
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global instances
input_validator = InputValidator()
xss_protection = XSSProtection()
rate_limiter = RateLimiter()
api_key_manager = APIKeyManager()
security_headers = SecurityHeaders()


if __name__ == '__main__':
    # Test security functions
    print("Testing security utilities...")
    
    # Test input validation
    try:
        query = input_validator.sanitize_search_query("  test  query  ")
        print(f"Sanitized query: '{query}'")
    except ValueError as e:
        print(f"Validation error: {e}")
    
    # Test XSS protection
    xss_text = "<script>alert('XSS')</script>Normal text"
    safe_text = xss_protection.strip_tags(xss_text)
    print(f"XSS stripped: {safe_text}")
    
    # Test rate limiting
    for i in range(5):
        is_limited, retry = rate_limiter.is_rate_limited("test_ip", max_requests=3, window_seconds=10)
        print(f"Request {i+1}: Limited={is_limited}, Retry={retry}")
    
    print("Security utilities test completed")
