# Django-Friendly Progressive Delivery Guide

This guide shows the **new and improved** Django-friendly approaches for progressive delivery that **don't require generators (yield)** and support **lazy loading**.

## 🚀 **Why the New Approach?**

### ❌ **Old Generator Approach (Still Supported)**
```python
def build_parts(self, request):
    yield ("meta", {"timestamp": "2024-01-01"})  # Requires yield knowledge
    yield ("orders", expensive_query())          # Always executes
    yield ("analytics", heavy_computation())     # Always executes
```

**Problems:**
- Requires understanding Python generators (`yield`)
- No lazy loading - all parts execute immediately
- Not familiar to Django developers
- Hard to reuse parts across views

### ✅ **New Django-Friendly Approaches**

1. **Registry-based** (Recommended)
2. **Method-based** (Simple)
3. **Decorator-based** (Flexible)

All support:
- ✅ **Lazy loading** - Parts load only when needed
- ✅ **Familiar Django patterns**
- ✅ **No generators required**
- ✅ **Easy to understand and use**
- ✅ **Reusable components**

---

## 📋 **Approach 1: Registry-Based** (Recommended)

The most flexible and powerful approach. Great for complex dashboards.

```python
from rest_framework.views import APIView
from drf_progressive_delivery import RegistryProgressiveView, ProgressivePartsRegistry
from .models import Order, Product
from .serializers import OrderSerializer, ProductSerializer

class DashboardView(RegistryProgressiveView, APIView):
    progressive_chunk_size = 2
    
    def get_parts_registry(self):
        registry = ProgressivePartsRegistry()
        
        # Static metadata (loads immediately)
        registry.add_static("meta", {
            "dashboard_type": "analytics",
            "generated_at": timezone.now().isoformat()
        })
        
        # Model data with serializer (lazy loaded)
        registry.add_model(
            name="recent_orders",
            queryset=Order.objects.order_by('-created_at')[:10],
            serializer_class=OrderSerializer,
            lazy=True  # Only loads when needed
        )
        
        # Computed data (lazy loaded)
        registry.add_function("analytics", self.compute_analytics, lazy=True)
        
        return registry
    
    def compute_analytics(self, request, **kwargs):
        """This only runs if analytics part is requested."""
        return {
            "revenue": Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'],
            "orders_count": Order.objects.count()
        }
```

**Benefits:**
- 🎯 **Most flexible** - Mix static, model, and computed data
- ⚡ **Lazy loading** - Expensive operations only run when needed
- 🔄 **Reusable** - Registry can be shared across views
- 📊 **Clear structure** - Easy to see all response parts

---

## 📋 **Approach 2: Method-Based** (Simple)

Override simple methods to provide data. Great for beginners.

```python
from drf_progressive_delivery import MethodProgressiveView

class DashboardView(MethodProgressiveView, APIView):
    progressive_chunk_size = 2
    
    def add_meta_data(self, request, **kwargs):
        """Provide metadata."""
        return {
            "dashboard_type": "simple",
            "user": request.user.username,
            "timestamp": timezone.now().isoformat()
        }
    
    def add_model_data(self, request, **kwargs):
        """Provide model data."""
        return [
            {"orders": OrderSerializer(Order.objects.all()[:10], many=True).data},
            {"products": ProductSerializer(Product.objects.all()[:20], many=True).data}
        ]
    
    def add_computed_data(self, request, **kwargs):
        """Provide analytics/computed data."""
        return [
            {"analytics": self.calculate_analytics()},
            {"summary": self.calculate_summary()}
        ]
```

**Benefits:**
- 📝 **Simple** - Just override methods
- 🎓 **Beginner-friendly** - Easy to understand
- 🏗️ **Django-like** - Similar to Django's method overrides

---

## 📋 **Approach 3: Decorator-Based** (Flexible)

Use decorators to mark methods as progressive parts.

```python
from drf_progressive_delivery import DecoratorProgressiveView, progressive_meta, progressive_data

class DashboardView(DecoratorProgressiveView, APIView):
    progressive_chunk_size = 2
    
    @progressive_meta  # Loads immediately
    def get_meta_info(self, request, **kwargs):
        return {
            "dashboard_type": "decorator_based",
            "timestamp": timezone.now().isoformat()
        }
    
    @progressive_data("orders")  # Lazy loaded
    def get_orders_data(self, request, **kwargs):
        orders = Order.objects.order_by('-created_at')[:10]
        return OrderSerializer(orders, many=True).data
    
    @progressive_data("analytics")  # Lazy loaded
    def get_analytics_data(self, request, **kwargs):
        return {
            "revenue": Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'],
            "orders_count": Order.objects.count()
        }
```

**Benefits:**
- 🏷️ **Decorator-based** - Familiar Django pattern
- 🔧 **Flexible** - Fine control over each part
- 👁️ **Explicit** - Clear which methods are progressive parts

---

## ⚡ **Lazy Loading in Action**

### **Without Lazy Loading** (Old approach)
```python
# ALL parts execute immediately, even if not needed
def build_parts(self, request):
    yield ("meta", {...})                    # ✅ Fast
    yield ("orders", expensive_db_query())   # ❌ Always runs (slow)
    yield ("analytics", heavy_computation()) # ❌ Always runs (very slow)
    yield ("summary", external_api_call())   # ❌ Always runs (network delay)
```

### **With Lazy Loading** (New approach)
```python
# Parts only execute when their chunk is requested
registry.add_static("meta", {...})                           # ✅ Immediate
registry.add_model("orders", expensive_queryset, lazy=True)  # ⚡ Only when needed
registry.add_function("analytics", heavy_computation, lazy=True) # ⚡ Only when needed
registry.add_function("summary", external_api_call, lazy=True)   # ⚡ Only when needed
```

### **Request Flow Example:**
```
Request 1: GET /api/dashboard/
  → Returns: meta + orders (analytics not executed yet!)
  → Fast response ⚡

Request 2: GET /api/dashboard/?cursor=abc123
  → NOW executes: analytics computation
  → Returns: analytics + summary
```

---

## 🎯 **Choosing the Right Approach**

| Use Case | Recommended Approach | Why |
|----------|---------------------|-----|
| **Complex dashboard** | Registry-based | Most flexible, best lazy loading |
| **Simple API** | Method-based | Easy to understand and implement |
| **Multiple small parts** | Decorator-based | Clear separation, good for teams |
| **Legacy migration** | Keep generator | No changes needed |

---

## 🔄 **Migration from Generator Approach**

### **Before (Generator):**
```python
class MyView(ProgressiveDeliveryMixin, APIView):
    def build_parts(self, request):
        yield ("meta", self.get_meta())
        yield ("orders", self.get_orders())
        yield ("analytics", self.get_analytics())
```

### **After (Registry):**
```python
class MyView(RegistryProgressiveView, APIView):
    def get_parts_registry(self):
        registry = ProgressivePartsRegistry()
        registry.add_function("meta", self.get_meta, lazy=False)
        registry.add_function("orders", self.get_orders, lazy=True)
        registry.add_function("analytics", self.get_analytics, lazy=True)
        return registry
```

**Benefits of migration:**
- ✅ **Lazy loading** - Better performance
- ✅ **No generators** - More familiar to Django developers
- ✅ **Better error handling** - Individual part errors don't break everything
- ✅ **Caching support** - Parts can cache their results

---

## 🧪 **Testing the New Approaches**

### **Test Registry Approach:**
```bash
# Test the new registry-based view
curl "http://localhost:8000/api/dashboard-registry/"
```

### **Test Method Approach:**
```bash
# Test the new method-based view
curl "http://localhost:8000/api/dashboard-method/"
```

### **Test Decorator Approach:**
```bash
# Test the new decorator-based view
curl "http://localhost:8000/api/dashboard-decorator/"
```

---

## 📊 **Performance Comparison**

| Approach | First Request | Subsequent Requests | Memory Usage | Complexity |
|----------|---------------|-------------------|--------------|------------|
| **Generator** | Slow (all parts) | Fast | High | Medium |
| **Registry + Lazy** | Fast (only needed) | Fast | Low | Low |
| **Method + Lazy** | Fast (only needed) | Fast | Low | Very Low |
| **Decorator + Lazy** | Fast (only needed) | Fast | Low | Low |

---

## 🎉 **Real-World Example**

Here's a complete example of a dashboard API that loads different sections progressively:

```python
class AnalyticsDashboard(RegistryProgressiveView, APIView):
    progressive_chunk_size = 2
    
    def get_parts_registry(self):
        registry = ProgressivePartsRegistry()
        
        # 1. Quick metadata (immediate)
        registry.add_static("meta", {
            "dashboard": "analytics",
            "user": self.request.user.username,
            "timestamp": timezone.now().isoformat()
        })
        
        # 2. Recent orders (fast query, lazy)
        registry.add_model(
            "recent_orders",
            queryset=lambda req, **kw: Order.objects.select_related('user').order_by('-created_at')[:10],
            serializer_class=OrderSerializer,
            lazy=True
        )
        
        # 3. Heavy analytics (expensive, lazy)
        registry.add_function("revenue_analytics", self._compute_revenue, lazy=True)
        
        # 4. External data (slow API call, lazy)
        registry.add_function("external_metrics", self._fetch_external_data, lazy=True)
        
        # 5. Summary (depends on previous data, lazy)
        registry.add_function("summary", self._compute_summary, lazy=True)
        
        return registry
    
    def _compute_revenue(self, request, **kwargs):
        """Heavy computation - only runs when needed."""
        # This might take 2-3 seconds
        return {
            "total_revenue": Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'],
            "revenue_by_month": self._monthly_revenue_calculation(),
            "growth_rate": self._calculate_growth_rate()
        }
    
    def _fetch_external_data(self, request, **kwargs):
        """External API call - only runs when needed."""
        # This might take 1-2 seconds due to network
        return external_analytics_api.get_metrics()
    
    def _compute_summary(self, request, **kwargs):
        """Final summary - only runs when needed."""
        return {
            "alerts": self._check_business_alerts(),
            "recommendations": self._generate_recommendations(),
            "next_actions": self._suggest_actions()
        }
```

**Response Flow:**
1. **Request 1**: Returns `meta` + `recent_orders` (fast - <100ms)
2. **Request 2**: Returns `revenue_analytics` + `external_metrics` (slower - computes when needed)
3. **Request 3**: Returns `summary` (final computation)

Each request only does the work it needs to do! 🚀

---

## 🔗 **Backward Compatibility**

The old generator approach still works:

```python
# This still works exactly as before
class OldView(ProgressiveDeliveryMixin, APIView):
    def build_parts(self, request):
        yield ("meta", {"version": "old"})
        yield ("data", some_data)
```

You can migrate gradually or keep using generators if your team prefers them. 