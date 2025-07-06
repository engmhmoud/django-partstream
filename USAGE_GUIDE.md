# Quick Usage Guide

## Step 1: Install the Package

```bash
# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Step 2: Choose Your Approach

### 🚀 **NEW: Registry Approach** (Recommended - No generators!)

```python
from rest_framework.views import APIView
from drf_progressive_delivery import RegistryProgressiveView, ProgressivePartsRegistry

class MyDataView(RegistryProgressiveView, APIView):
    progressive_chunk_size = 2
    
    def get_parts_registry(self):
        registry = ProgressivePartsRegistry()
        
        # Add static data
        registry.add_static("meta", {"total": 100, "timestamp": "2024-01-01"})
        
        # Add model data with lazy loading
        registry.add_model("orders", 
            queryset=Order.objects.all()[:10], 
            serializer_class=OrderSerializer,
            lazy=True  # Only loads when needed!
        )
        
        # Add computed data
        registry.add_function("analytics", self.compute_analytics, lazy=True)
        
        return registry
    
    def compute_analytics(self, request, **kwargs):
        return {"revenue": 300, "orders": 50}
```

### 📝 **NEW: Method Approach** (Simple)

```python
from drf_progressive_delivery import MethodProgressiveView

class MyDataView(MethodProgressiveView, APIView):
    progressive_chunk_size = 2
    
    def add_meta_data(self, request, **kwargs):
        return {"total": 100, "timestamp": "2024-01-01"}
    
    def add_model_data(self, request, **kwargs):
        return [
            {"orders": OrderSerializer(Order.objects.all()[:10], many=True).data}
        ]
    
    def add_computed_data(self, request, **kwargs):
        return [
            {"analytics": {"revenue": 300}},
            {"summary": {"complete": True}}
        ]
```

### 🏷️ **NEW: Decorator Approach** (Flexible)

```python
from drf_progressive_delivery import DecoratorProgressiveView, progressive_meta, progressive_data

class MyDataView(DecoratorProgressiveView, APIView):
    progressive_chunk_size = 2
    
    @progressive_meta
    def get_meta(self, request, **kwargs):
        return {"total": 100, "timestamp": "2024-01-01"}
    
    @progressive_data("orders")
    def get_orders(self, request, **kwargs):
        return OrderSerializer(Order.objects.all()[:10], many=True).data
    
    @progressive_data("analytics")
    def get_analytics(self, request, **kwargs):
        return {"revenue": 300}
```

### ⚙️ **Legacy: Generator Approach** (Still supported)

```python
from drf_progressive_delivery.mixins import ProgressiveDeliveryMixin

class MyDataView(ProgressiveDeliveryMixin, APIView):
    progressive_chunk_size = 2
    
    def build_parts(self, request):
        yield ("meta", {"total": 100, "timestamp": "2024-01-01"})
        yield ("orders", [{"id": 1, "amount": 100}])
        yield ("analytics", {"revenue": 300})
        yield ("summary", {"complete": True})
```

## Step 3: Add to URLs

```python
from django.urls import path
from . import views

urlpatterns = [
    path('my-data/', views.MyDataView.as_view(), name='my-data'),
]
```

## Step 4: Make Requests

**First request:**
```http
GET /api/my-data/
```

**Response:**
```json
{
  "results": [
    {"meta": {"total": 100, "timestamp": "2024-01-01"}},
    {"orders": [{"id": 1, "amount": 100}]}
  ],
  "cursor": "encrypted_cursor_token"
}
```

**Next request:**
```http
GET /api/my-data/?cursor=encrypted_cursor_token
```

**Response:**
```json
{
  "results": [
    {"analytics": {"revenue": 300}},
    {"summary": {"complete": true}}
  ],
  "cursor": null
}
```

## Step 5: Handle in Client

```javascript
async function fetchAllData(url) {
    const allResults = [];
    let cursor = null;
    
    do {
        const response = await fetch(
            cursor ? `${url}?cursor=${cursor}` : url
        );
        const data = await response.json();
        
        allResults.push(...data.results);
        cursor = data.cursor;
    } while (cursor);
    
    return allResults;
}
```

That's it! You now have progressive delivery working in your Django REST Framework API. 