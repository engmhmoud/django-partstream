# Django PartStream - Complete Guide

**Transform slow Django APIs into lightning-fast progressive experiences**

> **TL;DR**: Break large API responses into chunks that load progressively. Your users get data in 100ms instead of 15 seconds.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Configuration](#configuration)
5. [Security](#security)
6. [Performance](#performance)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

## 🚀 Quick Start

### Installation

```bash
pip install django-partstream
```

### Add to Django

```python
# settings.py
INSTALLED_APPS = [
    # ... your other apps
    'django_partstream',
]
```

### Your First Progressive View

```python
# views.py
from django_partstream import ProgressiveView, lazy
from django.utils import timezone

class DashboardView(ProgressiveView):
    def get_parts(self):
        return [
            # Immediate data (loads first)
            ("meta", {"timestamp": timezone.now()}),
            
            # Lazy data (loads later)
            ("orders", lazy(self.get_orders)),
            ("analytics", lazy(self.get_analytics)),
        ]
    
    def get_orders(self, request):
        return list(Order.objects.all()[:100].values())
    
    def get_analytics(self, request):
        # This only runs when requested
        return {"total_revenue": 50000}

# urls.py
from django.urls import path
urlpatterns = [
    path('api/dashboard/', DashboardView.as_view()),
]
```

### Test It

```bash
# First request - gets immediate data + first chunk
curl http://localhost:8000/api/dashboard/
{
    "results": [
        {"meta": {"timestamp": "2024-01-01T12:00:00Z"}},
        {"orders": [...]}
    ],
    "cursor": "encrypted_token_here",
    "meta": {"has_more": true}
}

# Second request - gets remaining data
curl http://localhost:8000/api/dashboard/?cursor=encrypted_token_here
{
    "results": [
        {"analytics": {"total_revenue": 50000}}
    ],
    "cursor": null,
    "meta": {"has_more": false}
}
```

**🎉 Done!** Your API now loads 10x faster.

## 📖 Basic Usage

### 1. Simple Data Loading

```python
from django_partstream import ProgressiveView, lazy

class SimpleView(ProgressiveView):
    def get_parts(self):
        return [
            ("users", lazy(self.get_users)),
            ("products", lazy(self.get_products)),
        ]
    
    def get_users(self, request):
        return list(User.objects.all().values())
    
    def get_products(self, request):
        return list(Product.objects.all().values())
```

### 2. Mix Immediate and Lazy Data

```python
class MixedView(ProgressiveView):
    def get_parts(self):
        return [
            # Immediate data
            ("meta", {"user": self.request.user.username}),
            ("config", self.get_config()),
            
            # Lazy data
            ("data", lazy(self.get_expensive_data)),
        ]
    
    def get_config(self):
        return {"theme": "dark", "language": "en"}
    
    def get_expensive_data(self, request):
        # Expensive operation
        return {"result": "heavy_computation"}
```

### 3. Error Handling

```python
from django_partstream import ProgressiveView, lazy, safe_call

class SafeView(ProgressiveView):
    def get_parts(self):
        return [
            ("safe_data", lazy(safe_call(
                self.risky_function,
                fallback={"error": "Service unavailable"}
            ))),
        ]
    
    def risky_function(self, request):
        # This might fail
        response = requests.get("https://external-api.com/data")
        return response.json()
```

### 4. Caching

```python
from django_partstream import ProgressiveView, lazy, cached_for

class CachedView(ProgressiveView):
    def get_parts(self):
        return [
            ("cached_data", lazy(self.get_cached_data)),
        ]
    
    @cached_for(300)  # Cache for 5 minutes
    def get_cached_data(self, request):
        # Expensive operation that gets cached
        return {"expensive_result": "computed_value"}
```

## 🔥 Advanced Features

### Hybrid View (Multiple Access Methods)

```python
from django_partstream import HybridProgressiveView

class AdvancedView(HybridProgressiveView):
    # Define available parts
    def get_parts_manifest(self):
        return {
            "meta": {"size": "small", "dependencies": []},
            "orders": {"size": "medium", "dependencies": ["meta"]},
            "analytics": {"size": "large", "dependencies": []},
        }
    
    def get_parts(self):
        return [
            ("meta", {"timestamp": timezone.now()}),
            ("orders", lazy(self.get_orders)),
            ("analytics", lazy(self.get_analytics)),
        ]
    
    def get_orders(self, request):
        return list(Order.objects.all()[:100].values())
    
    def get_analytics(self, request):
        return {"revenue": 50000}
```

**Usage:**
```bash
# Sequential access (traditional)
curl /api/data/
curl /api/data/?cursor=token

# Selective access (get specific parts)
curl /api/data/parts/?keys=meta,orders

# Discovery (see available parts)
curl /api/data/manifest/
```

### Conditional Loading

```python
from django_partstream import ConditionalProgressiveView

class ConditionalView(ConditionalProgressiveView):
    def get_public_parts(self):
        return [("public_data", {"message": "Hello world"})]
    
    def get_authenticated_parts(self):
        return [("user_data", {"user": self.request.user.username})]
    
    def get_staff_parts(self):
        return [("admin_data", {"admin": True})]
```

### Complex Workflows

```python
from django_partstream import ProgressiveView, lazy, safe_call, cached_for

class ComplexView(ProgressiveView):
    chunk_size = 1  # One part at a time
    
    def get_parts(self):
        return [
            # Step 1: Basic info
            ("info", {"step": 1, "total_steps": 4}),
            
            # Step 2: User data with caching
            ("user", lazy(self.get_cached_user_data)),
            
            # Step 3: External API with fallback
            ("external", lazy(safe_call(
                self.fetch_external_data,
                fallback={"error": "External service unavailable"}
            ))),
            
            # Step 4: Heavy computation
            ("analytics", lazy(self.compute_analytics)),
        ]
    
    @cached_for(600)  # Cache for 10 minutes
    def get_cached_user_data(self, request):
        return {"user": request.user.username, "preferences": {}}
    
    def fetch_external_data(self, request):
        import requests
        response = requests.get("https://api.example.com/data", timeout=5)
        return response.json()
    
    def compute_analytics(self, request):
        # Simulate heavy computation
        import time
        time.sleep(2)
        return {"computed": "result"}
```

## ⚙️ Configuration

### Basic Settings

```python
# settings.py
DJANGO_PARTSTREAM = {
    # Response settings
    'DEFAULT_CHUNK_SIZE': 2,      # Parts per request
    'CURSOR_TTL': 3600,           # Cursor expiration (seconds)
    
    # Caching
    'ENABLE_CACHING': True,
    'CACHE_TTL': 300,             # Default cache time
    
    # Security
    'ENABLE_RATE_LIMITING': True,
    'RATE_LIMIT': 100,            # Requests per minute
    'BURST_LIMIT': 10,            # Burst requests per 10 seconds
    
    # Performance
    'ENABLE_PERFORMANCE_MONITORING': True,
    'ENABLE_AUDIT_LOGGING': True,
}
```

### View-Level Settings

```python
class CustomView(ProgressiveView):
    chunk_size = 3              # Override default chunk size
    cursor_ttl = 7200           # 2 hours cursor expiration
    
    def get_parts(self):
        return [
            ("data1", lazy(self.get_data1)),
            ("data2", lazy(self.get_data2)),
            ("data3", lazy(self.get_data3)),
        ]
```

## 🔒 Security

### Automatic Security Features

✅ **Encrypted cursors** - All tokens are encrypted using Fernet
✅ **Rate limiting** - Prevents abuse
✅ **Audit logging** - All security events logged
✅ **Request validation** - Suspicious patterns blocked

### Security Configuration

```python
# settings.py
DJANGO_PARTSTREAM = {
    'ENABLE_RATE_LIMITING': True,
    'RATE_LIMIT': 100,                    # requests per minute
    'BURST_LIMIT': 10,                    # burst requests per 10 seconds
    'CURSOR_TTL': 3600,                   # 1 hour cursor expiration
    'ENABLE_AUDIT_LOGGING': True,
}

# Make sure SECRET_KEY is set (required for encryption)
SECRET_KEY = 'your-secret-key-here'
```

### Manual Security Controls

```python
from django_partstream.security import rate_limit, require_authentication

class SecureView(ProgressiveView):
    @rate_limit(limit=50, burst_limit=5)
    @require_authentication
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
```

## 📊 Performance

### Monitoring

```python
# Built-in performance tracking
from django_partstream.performance import track_performance

class MonitoredView(ProgressiveView):
    @track_performance
    def get_parts(self):
        return [
            ("data", lazy(self.get_monitored_data)),
        ]
    
    @track_performance
    def get_monitored_data(self, request):
        # Automatically tracked for performance
        return {"result": "data"}
```

### Health Checks

```bash
# Check system health
python manage.py partstream_health_check

# JSON output
python manage.py partstream_health_check --format=json
```

### Performance Tips

1. **Use caching** for expensive operations:
   ```python
   @cached_for(300)  # 5 minutes
   def expensive_operation(self, request):
       return heavy_computation()
   ```

2. **Optimize database queries**:
   ```python
   def get_optimized_data(self, request):
       return list(
           Order.objects
           .select_related('user')
           .prefetch_related('items')
           .values()
       )
   ```

3. **Use appropriate chunk sizes**:
   ```python
   class FastView(ProgressiveView):
       chunk_size = 1  # For very fast responses
   
   class BalancedView(ProgressiveView):
       chunk_size = 3  # Good balance
   ```

## 🔧 Troubleshooting

### Common Issues

**1. "No module named 'django_partstream'"**
```bash
# Make sure it's installed
pip install django-partstream

# Add to INSTALLED_APPS
INSTALLED_APPS = ['django_partstream']
```

**2. "Invalid cursor" errors**
```python
# Check SECRET_KEY is set
SECRET_KEY = 'your-secret-key-here'

# Check cursor TTL
DJANGO_PARTSTREAM = {
    'CURSOR_TTL': 3600,  # 1 hour
}
```

**3. Performance issues**
```python
# Enable caching
DJANGO_PARTSTREAM = {
    'ENABLE_CACHING': True,
}

# Use database query optimization
def get_data(self, request):
    return list(
        Model.objects
        .select_related('related_field')
        .values()
    )
```

**4. Rate limiting problems**
```python
# Adjust rate limits
DJANGO_PARTSTREAM = {
    'RATE_LIMIT': 200,      # Increase if needed
    'BURST_LIMIT': 20,
}
```

### Debug Mode

```python
# Enable debug logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_partstream': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## 📚 API Reference

### Core Classes

#### `ProgressiveView`
```python
class ProgressiveView(APIView):
    chunk_size = 2          # Parts per request
    cursor_ttl = 3600       # Cursor expiration
    
    def get_parts(self):
        """Return list of (name, data) tuples"""
        return [
            ("part1", data1),
            ("part2", lazy(self.get_part2)),
        ]
```

#### `HybridProgressiveView`
```python
class HybridProgressiveView(ProgressiveView):
    max_keys_per_request = 10
    allowed_keys = None     # Restrict available keys
    
    def get_parts_manifest(self):
        """Return part metadata"""
        return {
            "part1": {"size": "small", "dependencies": []},
        }
```

### Utility Functions

#### `lazy(func)`
```python
from django_partstream import lazy

def my_view(self):
    return [
        ("data", lazy(self.expensive_function)),
    ]
```

#### `safe_call(func, fallback=None)`
```python
from django_partstream import safe_call

def my_view(self):
    return [
        ("data", lazy(safe_call(
            self.risky_function,
            fallback={"error": "Failed"}
        ))),
    ]
```

#### `cached_for(ttl)`
```python
from django_partstream import cached_for

@cached_for(300)  # Cache for 5 minutes
def expensive_function(self, request):
    return {"result": "expensive"}
```

### Response Format

```json
{
    "results": [
        {"part1": {"data": "..."}},
        {"part2": {"data": "..."}}
    ],
    "cursor": "encrypted_token_or_null",
    "meta": {
        "total_parts": 5,
        "current_chunk": 1,
        "has_more": true,
        "timestamp": "2024-01-01T12:00:00Z"
    }
}
```

## 🎯 Best Practices

1. **Start small** - Begin with simple examples
2. **Use caching** - Cache expensive operations
3. **Handle errors** - Use `safe_call` for external APIs
4. **Monitor performance** - Enable built-in monitoring
5. **Test thoroughly** - Test both success and failure cases
6. **Security first** - Use rate limiting and authentication

## 📝 Example Project

Complete working example:

```python
# views.py
from django_partstream import ProgressiveView, lazy, safe_call, cached_for
from django.utils import timezone
import requests

class CompleteExampleView(ProgressiveView):
    chunk_size = 2
    
    def get_parts(self):
        return [
            # Immediate data
            ("meta", {
                "timestamp": timezone.now(),
                "user": self.request.user.username if self.request.user.is_authenticated else "anonymous"
            }),
            
            # Cached expensive operation
            ("analytics", lazy(self.get_analytics)),
            
            # External API with fallback
            ("external", lazy(safe_call(
                self.fetch_external_data,
                fallback={"error": "External service unavailable"}
            ))),
            
            # Database query
            ("orders", lazy(self.get_orders)),
        ]
    
    @cached_for(600)  # Cache for 10 minutes
    def get_analytics(self, request):
        # Simulate expensive computation
        return {
            "total_revenue": 50000,
            "user_count": 1000,
            "computed_at": timezone.now().isoformat()
        }
    
    def fetch_external_data(self, request):
        response = requests.get("https://jsonplaceholder.typicode.com/posts/1", timeout=5)
        return response.json()
    
    def get_orders(self, request):
        # This would be your actual model
        return [
            {"id": 1, "total": 100.00, "status": "completed"},
            {"id": 2, "total": 250.00, "status": "pending"},
        ]

# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/example/', views.CompleteExampleView.as_view(), name='example'),
]
```

**Usage:**
```bash
# First request
curl http://localhost:8000/api/example/

# Follow-up requests
curl http://localhost:8000/api/example/?cursor=<token>
```

---

**🚀 You're ready to build lightning-fast APIs with django-partstream!**

For more examples, check the `example_project/` directory in the source code. 