"""
Security utilities for django-partstream
Production-ready security features for progressive delivery
"""
import hashlib
import hmac
import time
from typing import Dict, Any, Optional
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.http import HttpRequest
from rest_framework.throttling import BaseThrottle

from .exceptions import ProgressiveDeliveryError


class SecurityConfig:
    """Security configuration for django-partstream"""
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = 100  # requests per minute
    BURST_RATE_LIMIT = 10     # requests per 10 seconds
    
    # Cursor security
    CURSOR_MAX_AGE = 3600     # 1 hour
    CURSOR_SIGNATURE_KEY = None  # Will use SECRET_KEY if None
    
    # Request validation
    MAX_PARTS_PER_REQUEST = 50
    MAX_CURSOR_SIZE = 1024
    
    # IP-based restrictions
    ENABLE_IP_FILTERING = False
    ALLOWED_IPS = []
    BLOCKED_IPS = []
    
    @classmethod
    def get_signature_key(cls) -> str:
        """Get the key for cursor signatures"""
        if cls.CURSOR_SIGNATURE_KEY:
            return cls.CURSOR_SIGNATURE_KEY
        return settings.SECRET_KEY


class RateLimiter:
    """Advanced rate limiter for progressive delivery endpoints"""
    
    def __init__(self, rate_limit: int = None, burst_limit: int = None):
        self.rate_limit = rate_limit or SecurityConfig.DEFAULT_RATE_LIMIT
        self.burst_limit = burst_limit or SecurityConfig.BURST_RATE_LIMIT
    
    def is_allowed(self, request: HttpRequest) -> bool:
        """Check if request is within rate limits"""
        user_id = getattr(request.user, 'id', None) or request.META.get('REMOTE_ADDR', 'unknown')
        
        # Check burst rate (short-term)
        burst_key = f"progressive_burst:{user_id}"
        burst_count = cache.get(burst_key, 0)
        
        if burst_count >= self.burst_limit:
            return False
        
        # Check sustained rate (long-term)
        rate_key = f"progressive_rate:{user_id}"
        rate_count = cache.get(rate_key, 0)
        
        if rate_count >= self.rate_limit:
            return False
        
        # Update counters
        cache.set(burst_key, burst_count + 1, 10)  # 10 second window
        cache.set(rate_key, rate_count + 1, 60)    # 60 second window
        
        return True
    
    def get_reset_time(self, request: HttpRequest) -> Optional[int]:
        """Get when rate limit resets"""
        user_id = getattr(request.user, 'id', None) or request.META.get('REMOTE_ADDR', 'unknown')
        rate_key = f"progressive_rate:{user_id}"
        
        # Get TTL from cache
        ttl = cache.ttl(rate_key)
        if ttl is None:
            return None
        
        return int(time.time()) + ttl


class CursorSigner:
    """Secure cursor signing and verification"""
    
    @staticmethod
    def sign_cursor(cursor_data: str) -> str:
        """Sign a cursor with HMAC"""
        key = SecurityConfig.get_signature_key().encode('utf-8')
        signature = hmac.new(key, cursor_data.encode('utf-8'), hashlib.sha256).hexdigest()
        return f"{cursor_data}.{signature}"
    
    @staticmethod
    def verify_cursor(signed_cursor: str) -> str:
        """Verify and extract cursor data"""
        try:
            cursor_data, signature = signed_cursor.rsplit('.', 1)
        except ValueError:
            raise ProgressiveDeliveryError("Invalid cursor format")
        
        # Verify signature
        key = SecurityConfig.get_signature_key().encode('utf-8')
        expected_signature = hmac.new(key, cursor_data.encode('utf-8'), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise ProgressiveDeliveryError("Cursor signature verification failed")
        
        return cursor_data


class RequestValidator:
    """Validate progressive delivery requests"""
    
    @staticmethod
    def validate_cursor(cursor: str) -> None:
        """Validate cursor format and size"""
        if not cursor:
            return
        
        if len(cursor) > SecurityConfig.MAX_CURSOR_SIZE:
            raise ProgressiveDeliveryError("Cursor too large")
        
        # Check for suspicious patterns
        if any(char in cursor for char in ['<', '>', '"', "'", '&']):
            raise ProgressiveDeliveryError("Invalid cursor format")
    
    @staticmethod
    def validate_request_params(request: HttpRequest) -> None:
        """Validate request parameters"""
        # Check for suspicious parameters
        suspicious_params = ['__', 'eval', 'exec', 'import', 'system']
        
        for param in request.GET.keys():
            if any(sus in param.lower() for sus in suspicious_params):
                raise ProgressiveDeliveryError("Suspicious request parameter")
        
        # Validate cursor if present
        cursor = request.GET.get('cursor')
        if cursor:
            RequestValidator.validate_cursor(cursor)


class IPFilter:
    """IP-based access control"""
    
    @staticmethod
    def is_allowed_ip(request: HttpRequest) -> bool:
        """Check if IP is allowed"""
        if not SecurityConfig.ENABLE_IP_FILTERING:
            return True
        
        client_ip = RequestValidator.get_client_ip(request)
        
        # Check blocked IPs first
        if client_ip in SecurityConfig.BLOCKED_IPS:
            return False
        
        # Check allowed IPs
        if SecurityConfig.ALLOWED_IPS:
            return client_ip in SecurityConfig.ALLOWED_IPS
        
        return True
    
    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        forwarded_headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'HTTP_X_CLUSTER_CLIENT_IP',
            'REMOTE_ADDR'
        ]
        
        for header in forwarded_headers:
            ip = request.META.get(header)
            if ip:
                # Handle comma-separated IPs
                ip = ip.split(',')[0].strip()
                if ip:
                    return ip
        
        return request.META.get('REMOTE_ADDR', 'unknown')


class AuditLogger:
    """Security audit logging"""
    
    @staticmethod
    def log_access(request: HttpRequest, parts_count: int, cursor_used: bool = False) -> None:
        """Log access to progressive delivery endpoints"""
        import logging
        
        logger = logging.getLogger('django_partstream.security')
        
        log_data = {
            'user_id': getattr(request.user, 'id', None),
            'username': getattr(request.user, 'username', 'anonymous'),
            'ip': IPFilter.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
            'path': request.path,
            'method': request.method,
            'parts_count': parts_count,
            'cursor_used': cursor_used,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Progressive delivery access: {log_data}")
    
    @staticmethod
    def log_security_event(event_type: str, request: HttpRequest, details: Dict[str, Any]) -> None:
        """Log security events"""
        import logging
        
        logger = logging.getLogger('django_partstream.security')
        
        log_data = {
            'event_type': event_type,
            'user_id': getattr(request.user, 'id', None),
            'ip': IPFilter.get_client_ip(request),
            'timestamp': timezone.now().isoformat(),
            'details': details
        }
        
        logger.warning(f"Security event: {log_data}")


class SecurityMiddleware:
    """Security middleware for progressive delivery"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limiter = RateLimiter()
    
    def __call__(self, request):
        # Check IP filtering
        if not IPFilter.is_allowed_ip(request):
            AuditLogger.log_security_event('ip_blocked', request, {'ip': IPFilter.get_client_ip(request)})
            raise ProgressiveDeliveryError("Access denied")
        
        # Check rate limiting
        if not self.rate_limiter.is_allowed(request):
            AuditLogger.log_security_event('rate_limit_exceeded', request, {'ip': IPFilter.get_client_ip(request)})
            raise ProgressiveDeliveryError("Rate limit exceeded")
        
        # Validate request
        try:
            RequestValidator.validate_request_params(request)
        except ProgressiveDeliveryError as e:
            AuditLogger.log_security_event('invalid_request', request, {'error': str(e)})
            raise
        
        response = self.get_response(request)
        return response


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if not request.user.has_perm(permission):
                AuditLogger.log_security_event('permission_denied', request, {'permission': permission})
                raise ProgressiveDeliveryError("Insufficient permissions")
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_authentication(func):
    """Decorator to require authentication"""
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            AuditLogger.log_security_event('authentication_required', request, {})
            raise ProgressiveDeliveryError("Authentication required")
        return func(self, request, *args, **kwargs)
    return wrapper


def rate_limit(limit: int = None, burst_limit: int = None):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            limiter = RateLimiter(limit, burst_limit)
            if not limiter.is_allowed(request):
                AuditLogger.log_security_event('rate_limit_exceeded', request, {'limit': limit})
                raise ProgressiveDeliveryError("Rate limit exceeded")
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def secure_cursor_handling(func):
    """Decorator for secure cursor handling"""
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        cursor = request.GET.get('cursor')
        if cursor:
            try:
                # Verify cursor signature
                CursorSigner.verify_cursor(cursor)
                
                # Additional cursor validation
                RequestValidator.validate_cursor(cursor)
                
            except ProgressiveDeliveryError as e:
                AuditLogger.log_security_event('invalid_cursor', request, {'error': str(e)})
                raise
        
        return func(self, request, *args, **kwargs)
    return wrapper


class ProgressiveDeliveryThrottle(BaseThrottle):
    """DRF throttle for progressive delivery endpoints"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
    
    def allow_request(self, request, view):
        """Check if request should be allowed"""
        return self.rate_limiter.is_allowed(request)
    
    def wait(self):
        """Return number of seconds to wait before next request"""
        return 60  # Default wait time


# Security configuration validation
def validate_security_config():
    """Validate security configuration"""
    errors = []
    
    # Check if SECRET_KEY is set
    if not hasattr(settings, 'SECRET_KEY') or not settings.SECRET_KEY:
        errors.append("SECRET_KEY must be set for secure cursor handling")
    
    # Check cursor settings
    if SecurityConfig.CURSOR_MAX_AGE <= 0:
        errors.append("CURSOR_MAX_AGE must be positive")
    
    # Check rate limiting settings
    if SecurityConfig.DEFAULT_RATE_LIMIT <= 0:
        errors.append("DEFAULT_RATE_LIMIT must be positive")
    
    if SecurityConfig.BURST_RATE_LIMIT <= 0:
        errors.append("BURST_RATE_LIMIT must be positive")
    
    # Check IP filtering
    if SecurityConfig.ENABLE_IP_FILTERING and not SecurityConfig.ALLOWED_IPS:
        errors.append("ALLOWED_IPS must be set when IP filtering is enabled")
    
    if errors:
        raise ProgressiveDeliveryError(f"Security configuration errors: {', '.join(errors)}")


# Initialize security configuration
try:
    validate_security_config()
except Exception as e:
    import logging
    logging.getLogger('django_partstream.security').error(f"Security configuration error: {e}") 