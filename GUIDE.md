# 📚 Django PartStream - Complete Guide

## **Table of Contents**
1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Real-World Examples](#real-world-examples)
5. [Frontend Integration](#frontend-integration)
6. [Performance Tips](#performance-tips)
7. [Troubleshooting](#troubleshooting)

---

## **Quick Start**

### **Installation**
```bash
pip install django-partstream
```

### **Basic Setup**
```python
from django_partstream import ProgressiveView, lazy
from rest_framework.views import APIView

class MyAPI(ProgressiveView):
    def get_parts(self):
        return [
            ("meta", {"timestamp": timezone.now()}),
            ("data", lazy(self.get_data))
        ]
    
    def get_data(self, request):
        return {"users": User.objects.count()}
```

### **Response Format**
```json
{
    "results": [
        {"meta": {"timestamp": "2024-01-01T10:00:00Z"}},
        {"data": {"users": 1000}}
    ],
    "cursor": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "meta": {
        "total_parts": 2,
        "current_chunk_size": 2,
        "has_more": false
    }
}
```

---

## **Basic Usage**

### **1. Define Your Progressive API**
```python
from django_partstream import ProgressiveView, lazy

class DashboardAPI(ProgressiveView):
    chunk_size = 2  # Load 2 parts per request
    
    def get_parts(self):
        return [
            ("overview", self.get_overview()),      # Immediate
            ("orders", lazy(self.get_orders)),      # Lazy
            ("analytics", lazy(self.get_analytics)) # Lazy
        ]
    
    def get_overview(self):
        return {
            "total_users": User.objects.count(),
            "timestamp": timezone.now().isoformat()
        }
    
    def get_orders(self, request):
        orders = Order.objects.all()[:100]
        return OrderSerializer(orders, many=True).data
    
    def get_analytics(self, request):
        return {
            "revenue": Order.objects.aggregate(Sum('total'))['total__sum'],
            "conversion_rate": self.calculate_conversion()
        }
```

### **2. Configuration Options**
```python
class MyAPI(ProgressiveView):
    chunk_size = 3          # Parts per request (default: 2)
    cursor_ttl = 1800       # Cursor expiration in seconds (default: 3600)
    
    def get_parts(self):
        # Your parts here
        pass
```

### **3. Lazy Loading**
```python
def get_parts(self):
    return [
        ("immediate", {"fast": "data"}),           # Loads immediately
        ("lazy", lazy(self.expensive_operation)),  # Loads when requested
        ("cached", lazy(self.cached_operation))    # Cached lazy loading
    ]
```

---

## **Advanced Features**

### **1. Error Handling**
```python
from django_partstream import ProgressiveView, lazy, safe_call

class RobustAPI(ProgressiveView):
    def get_parts(self):
        return [
            ("meta", {"timestamp": timezone.now()}),
            ("safe_data", lazy(safe_call(self.risky_operation))),
            ("fallback", lazy(safe_call(self.external_api, fallback={"error": "Service unavailable"})))
        ]
    
    def risky_operation(self, request):
        # This might fail
        return external_service.get_data()
    
    def external_api(self, request):
        # This might timeout
        return requests.get("https://api.example.com/data").json()
```

### **2. Caching**
```python
from django_partstream import ProgressiveView, lazy, cached_for

class CachedAPI(ProgressiveView):
    def get_parts(self):
        return [
            ("analytics", lazy(self.get_cached_analytics))
        ]
    
    @cached_for(300)  # Cache for 5 minutes
    def get_cached_analytics(self, request):
        # Expensive computation
        return complex_analytics_calculation()
```

### **3. Timeouts**
```python
from django_partstream import ProgressiveView, lazy, with_timeout

class TimeoutAPI(ProgressiveView):
    def get_parts(self):
        return [
            ("slow_data", lazy(with_timeout(self.slow_operation, 30)))
        ]
    
    def slow_operation(self, request):
        # This might take a long time
        return very_slow_computation()
```

### **4. Conditional Parts**
```python
class ConditionalAPI(ProgressiveView):
    def get_parts(self):
        parts = [
            ("meta", {"timestamp": timezone.now()}),
            ("public_data", lazy(self.get_public_data))
        ]
        
        if self.request.user.is_authenticated:
            parts.append(("user_data", lazy(self.get_user_data)))
        
        if self.request.user.is_staff:
            parts.append(("admin_data", lazy(self.get_admin_data)))
        
        return parts
```

### **5. Dynamic Parts**
```python
class DynamicAPI(ProgressiveView):
    def get_parts(self):
        parts = [("meta", {"timestamp": timezone.now()})]
        
        # Add parts based on request parameters
        if self.request.GET.get('include_analytics'):
            parts.append(("analytics", lazy(self.get_analytics)))
        
        if self.request.GET.get('include_reports'):
            parts.append(("reports", lazy(self.get_reports)))
        
        return parts
```

---

## **Real-World Examples**

### **1. E-commerce Admin Dashboard**
```python
class EcommerceDashboard(ProgressiveView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    chunk_size = 3
    
    def get_parts(self):
        return [
            ("overview", {
                "store_name": "My Store",
                "timestamp": timezone.now().isoformat(),
                "admin": self.request.user.username
            }),
            ("today_stats", lazy(self.get_today_stats)),
            ("recent_orders", lazy(self.get_recent_orders)),
            ("inventory_alerts", lazy(self.get_inventory_alerts)),
            ("sales_analytics", lazy(safe_call(self.get_sales_analytics))),
            ("customer_insights", lazy(safe_call(self.get_customer_insights)))
        ]
    
    def get_today_stats(self, request):
        today = timezone.now().date()
        return {
            "orders_today": Order.objects.filter(created_at__date=today).count(),
            "revenue_today": Order.objects.filter(created_at__date=today)
                                        .aggregate(Sum('total'))['total__sum'] or 0,
            "new_customers": Customer.objects.filter(created_at__date=today).count()
        }
    
    def get_recent_orders(self, request):
        orders = Order.objects.select_related('customer').order_by('-created_at')[:100]
        return OrderSerializer(orders, many=True).data
    
    def get_inventory_alerts(self, request):
        products = Product.objects.filter(stock__lt=10)
        return ProductSerializer(products, many=True).data
    
    def get_sales_analytics(self, request):
        # Complex analytics - might fail
        return {
            "total_revenue": Order.objects.aggregate(Sum('total'))['total__sum'],
            "avg_order_value": Order.objects.aggregate(Avg('total'))['total__avg'],
            "conversion_rate": self.calculate_conversion_rate()
        }
    
    def get_customer_insights(self, request):
        # Very expensive computation
        return {
            "total_customers": Customer.objects.count(),
            "churn_rate": self.calculate_churn_rate(),
            "lifetime_value": self.calculate_customer_lifetime_value()
        }
```

### **2. Social Media Dashboard**
```python
class SocialDashboard(ProgressiveView):
    def get_parts(self):
        return [
            ("profile", {
                "username": self.request.user.username,
                "followers": self.request.user.profile.followers.count(),
                "following": self.request.user.profile.following.count()
            }),
            ("recent_posts", lazy(self.get_recent_posts)),
            ("engagement", lazy(self.get_engagement_stats)),
            ("analytics", lazy(self.get_analytics))
        ]
    
    def get_recent_posts(self, request):
        posts = Post.objects.filter(author=request.user).order_by('-created_at')[:20]
        return PostSerializer(posts, many=True).data
    
    def get_engagement_stats(self, request):
        return {
            "total_likes": Like.objects.filter(post__author=request.user).count(),
            "total_comments": Comment.objects.filter(post__author=request.user).count(),
            "engagement_rate": self.calculate_engagement_rate()
        }
    
    def get_analytics(self, request):
        return {
            "reach": self.calculate_reach(),
            "impressions": self.calculate_impressions(),
            "best_time_to_post": self.calculate_optimal_posting_time()
        }
```

### **3. Analytics Platform**
```python
class AnalyticsPlatform(ProgressiveView):
    chunk_size = 2
    
    def get_parts(self):
        return [
            ("meta", {
                "platform": "Analytics Dashboard",
                "user": self.request.user.username,
                "timestamp": timezone.now().isoformat()
            }),
            ("realtime", lazy(self.get_realtime_metrics)),
            ("historical", lazy(self.get_historical_data)),
            ("predictions", lazy(self.get_predictions))
        ]
    
    @cached_for(30)  # Cache for 30 seconds
    def get_realtime_metrics(self, request):
        return {
            "active_users": self.count_active_users(),
            "requests_per_minute": self.calculate_rpm(),
            "error_rate": self.calculate_error_rate()
        }
    
    def get_historical_data(self, request):
        return {
            "traffic_trends": self.calculate_traffic_trends(),
            "user_behavior": self.analyze_user_behavior(),
            "conversion_funnel": self.calculate_conversion_funnel()
        }
    
    def get_predictions(self, request):
        return {
            "traffic_forecast": self.predict_traffic(),
            "user_growth": self.predict_user_growth(),
            "revenue_projection": self.predict_revenue()
        }
```

---

## **Frontend Integration**

### **1. JavaScript/React**
```javascript
// Progressive loader utility
class ProgressiveLoader {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
        this.allData = [];
    }
    
    async loadAll(onProgress = null) {
        let cursor = null;
        
        do {
            const url = cursor ? `${this.apiUrl}?cursor=${cursor}` : this.apiUrl;
            const response = await fetch(url);
            const data = await response.json();
            
            this.allData.push(...data.results);
            
            if (onProgress) {
                onProgress({
                    results: data.results,
                    totalLoaded: this.allData.length,
                    hasMore: !!data.cursor
                });
            }
            
            cursor = data.cursor;
        } while (cursor);
        
        return this.allData;
    }
}

// React component
function Dashboard() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    
    useEffect(() => {
        const loader = new ProgressiveLoader('/api/dashboard/');
        setLoading(true);
        
        loader.loadAll((progress) => {
            setData(prev => [...prev, ...progress.results]);
        }).finally(() => {
            setLoading(false);
        });
    }, []);
    
    return (
        <div>
            {data.map((item, index) => (
                <DashboardSection key={index} data={item} />
            ))}
            {loading && <LoadingSpinner />}
        </div>
    );
}
```

### **2. Vue.js**
```javascript
export default {
    data() {
        return {
            dashboardData: [],
            loading: false
        };
    },
    
    async mounted() {
        this.loading = true;
        let cursor = null;
        
        do {
            const url = cursor ? 
                `/api/dashboard/?cursor=${cursor}` : 
                '/api/dashboard/';
            
            const response = await this.$http.get(url);
            this.dashboardData.push(...response.data.results);
            cursor = response.data.cursor;
        } while (cursor);
        
        this.loading = false;
    }
};
```

### **3. Simple JavaScript**
```javascript
async function loadDashboard() {
    const container = document.getElementById('dashboard');
    let cursor = null;
    
    do {
        const url = cursor ? `/api/dashboard/?cursor=${cursor}` : '/api/dashboard/';
        const response = await fetch(url);
        const data = await response.json();
        
        data.results.forEach(part => {
            const [partName, partData] = Object.entries(part)[0];
            const element = document.createElement('div');
            element.className = 'dashboard-part';
            element.innerHTML = `
                <h3>${partName}</h3>
                <pre>${JSON.stringify(partData, null, 2)}</pre>
            `;
            container.appendChild(element);
        });
        
        cursor = data.cursor;
    } while (cursor);
}
```

---

## **Performance Tips**

### **1. Database Optimization**
```python
def get_orders(self, request):
    # ❌ Bad: N+1 queries
    orders = Order.objects.all()
    
    # ✅ Good: Optimized queryset
    orders = Order.objects.select_related('customer', 'payment') \
                          .prefetch_related('items__product') \
                          .order_by('-created_at')[:100]
    
    return OrderSerializer(orders, many=True).data
```

### **2. Appropriate Chunk Sizes**
```python
# For mobile APIs
chunk_size = 1

# For desktop dashboards
chunk_size = 3

# For admin interfaces
chunk_size = 5
```

### **3. Caching Strategy**
```python
from django.core.cache import cache

@cached_for(300)  # 5 minutes
def get_analytics(self, request):
    return expensive_computation()

# Manual caching
def get_custom_analytics(self, request):
    cache_key = f"analytics_{request.user.id}"
    result = cache.get(cache_key)
    
    if result is None:
        result = compute_analytics()
        cache.set(cache_key, result, 300)
    
    return result
```

### **4. Lazy Loading Best Practices**
```python
def get_parts(self):
    return [
        # Immediate for critical data
        ("meta", {"timestamp": timezone.now()}),
        
        # Lazy for expensive operations
        ("analytics", lazy(self.expensive_computation)),
        
        # Lazy for external APIs
        ("external", lazy(self.external_api_call))
    ]
```

---

## **Troubleshooting**

### **Common Issues**

#### **1. "get_parts() returned None"**
```python
# ❌ Wrong
def get_parts(self):
    pass  # Returns None

# ✅ Correct
def get_parts(self):
    return []  # Returns empty list
```

#### **2. "Lazy function not callable"**
```python
# ❌ Wrong
("data", lazy(self.get_data()))  # Called immediately

# ✅ Correct
("data", lazy(self.get_data))    # Function reference
```

#### **3. "Cursor expired"**
```python
# Increase cursor TTL
class MyAPI(ProgressiveView):
    cursor_ttl = 7200  # 2 hours instead of 1 hour
```

#### **4. "Memory issues with large datasets"**
```python
# Use smaller chunk sizes and better queries
class MyAPI(ProgressiveView):
    chunk_size = 1  # Smaller chunks
    
    def get_orders(self, request):
        # Limit queryset size
        return Order.objects.all()[:100]  # Don't load everything
```

### **Debug Mode**
```python
class DebugAPI(ProgressiveView):
    def get_parts(self):
        import time
        
        parts = [
            ("meta", {"timestamp": timezone.now()}),
            ("orders", lazy(self.get_orders))
        ]
        
        # Log timing in development
        if settings.DEBUG:
            start_time = time.time()
            result = self.get_orders(None)
            end_time = time.time()
            print(f"get_orders took {end_time - start_time:.2f} seconds")
        
        return parts
```

### **Testing**
```python
from django.test import TestCase
from rest_framework.test import APIClient

class ProgressiveAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
    
    def test_progressive_loading(self):
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertIn('cursor', data)
        
        # Test second chunk if cursor exists
        if data['cursor']:
            response2 = self.client.get(f'/api/dashboard/?cursor={data["cursor"]}')
            self.assertEqual(response2.status_code, 200)
```

---

## **Migration from Other Approaches**

### **From Standard DRF Views**
```python
# Old approach
class OldDashboard(APIView):
    def get(self, request):
        return Response({
            "orders": Order.objects.all(),
            "analytics": expensive_computation()
        })

# New approach
class NewDashboard(ProgressiveView):
    def get_parts(self):
        return [
            ("orders", lazy(lambda r: Order.objects.all())),
            ("analytics", lazy(lambda r: expensive_computation()))
        ]
```

### **From Complex Progressive API**
```python
# Old complex approach
class OldComplex(RegistryProgressiveView, APIView):
    def get_parts_registry(self):
        registry = ProgressivePartsRegistry()
        registry.add_function("analytics", self.get_analytics, lazy=True)
        return registry

# New simple approach
class NewSimple(ProgressiveView):
    def get_parts(self):
        return [
            ("analytics", lazy(self.get_analytics))
        ]
```

---

This guide covers everything you need to build fast, scalable Django APIs with progressive delivery. Start with the basic examples and gradually add advanced features as needed.

**Happy coding! 🚀** 