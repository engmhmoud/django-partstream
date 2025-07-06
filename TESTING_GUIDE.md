# Testing Guide for DRF Progressive Delivery

This guide walks you through testing the progressive delivery package in different ways.

## 🚀 Quick Start Testing

### Option 1: All-in-One Test Runner
```bash
# Run all tests (standalone + Django)
python run_tests.py

# Run specific test types
python run_tests.py standalone  # Test without Django
python run_tests.py django      # Test with Django
python run_tests.py server      # Start Django server
```

### Option 2: Manual Step-by-Step Testing

#### Step 1: Install Dependencies
```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

#### Step 2: Test Without Django (Standalone)
```bash
# Test core functionality without Django
python test_progressive_delivery.py
```

#### Step 3: Test With Django
```bash
# Go to example project
cd example_project

# Setup database
python manage.py migrate

# Create test data
python manage.py test_progressive --create-data

# Test progressive API
python manage.py test_progressive --test-api

# Start server
python manage.py runserver
```

#### Step 4: Test HTTP API (in another terminal)
```bash
# Test all endpoints
python test_client.py

# Interactive testing
python test_client.py interactive

# Test specific endpoint
python test_client.py /api/order-analytics/
```

## 🧪 Test Scenarios

### 1. Standalone Tests
Tests the core progressive delivery logic without Django:

- ✅ **Cursor Management**: Encryption/decryption, validation
- ✅ **Progressive Logic**: Chunking, pagination, cursor generation
- ✅ **Client Simulation**: How a client would consume the API

**Expected Output:**
```
🚀 Testing DRF Progressive Delivery Package
==================================================
Testing Cursor Management
==================================================
Created cursor: gAAAAABh7x8y...
Decoded data: {'start_index': 2, 'user_id': 123, 'filters': {'status': 'active'}}
✅ Cursor management test passed!
✅ Invalid cursor properly rejected: InvalidCursorError

Testing Progressive Delivery Logic
==================================================
First request (no cursor):
Response: {
  "results": [
    {"meta": {"total": 100, "generated_at": "2024-01-01"}},
    {"orders": [{"id": 1, "amount": 100}, {"id": 2, "amount": 200}]}
  ],
  "cursor": "gAAAAABh7x8y..."
}
...
```

### 2. Django Integration Tests
Tests the full Django integration:

- ✅ **Database Setup**: Migrations, sample data creation
- ✅ **View Integration**: Progressive views work with Django models
- ✅ **Serializer Integration**: DRF serializers work with progressive delivery
- ✅ **Multiple View Types**: APIView and ViewSet patterns

**Expected Output:**
```
Creating sample data...
Created product: Laptop
Created product: Mouse
...
Sample data created successfully!

Testing progressive API...
Testing first request (no cursor)...
Response status: 200
Results count: 2
Cursor present: True
...
```

### 3. HTTP API Tests
Tests the actual HTTP endpoints:

- ✅ **Real HTTP Requests**: Using requests library
- ✅ **Multiple Endpoints**: Different progressive delivery endpoints
- ✅ **Cursor Flow**: Following cursors through multiple requests
- ✅ **Error Handling**: Invalid cursors, network errors

**Expected Output:**
```
🎯 Testing Progressive Delivery API Endpoints
============================================================

🔍 Testing endpoint: /api/order-analytics/
🔄 Fetching data from: /api/order-analytics/
--------------------------------------------------
📡 Request 1:
   URL: http://127.0.0.1:8000/api/order-analytics/
   Status: 200
   Parts received: 2
     Part 1: ['meta']
     Part 2: ['orders_batch']
   Next cursor: Yes
...
```

## 📊 Available Test Endpoints

### 1. `/api/order-analytics/`
**Complex Dashboard Example**
- Meta information
- Order batches (from database)
- Analytics data (computed)
- Product inventory
- Summary statistics

### 2. `/api/simple-progressive/`
**Simple Example**
- User data
- System stats
- External API simulation
- Database metrics

### 3. `/api/reports/`
**ViewSet Example**
- Report metadata
- Sales data
- Customer insights
- Product performance

### 4. `/api/reports/comprehensive_report/`
**Custom Action Example**
- Same as above but accessed via custom action

## 🔧 Configuration Testing

### Test Different Chunk Sizes
Modify `progressive_chunk_size` in the views:

```python
# In example_project/example_app/views.py
class OrderAnalyticsView(ProgressiveDeliveryMixin, APIView):
    progressive_chunk_size = 1  # Try 1, 2, 3, or 5
```

### Test Cursor Expiration
Enable cursor TTL:

```python
class OrderAnalyticsView(ProgressiveDeliveryMixin, APIView):
    progressive_cursor_ttl = 60  # 1 minute expiration
```

### Test Error Scenarios
- Invalid cursors
- Expired cursors
- Network errors
- Empty responses

## 🐛 Troubleshooting

### Common Issues

1. **"No module named 'drf_progressive_delivery'"**
   ```bash
   # Install the package in development mode
   pip install -e .
   ```

2. **"WSGI application could not be loaded"**
   - Fixed! The `wsgi.py` file has been created.

3. **"No such table: example_app_order"**
   ```bash
   cd example_project
   python manage.py migrate
   ```

4. **"Connection refused"**
   ```bash
   # Make sure Django server is running
   python manage.py runserver
   ```

5. **Empty API responses**
   ```bash
   # Create sample data
   python manage.py test_progressive --create-data
   ```

### Debug Mode
Add this to your view for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

class MyView(ProgressiveDeliveryMixin, APIView):
    def build_parts(self, request):
        logging.debug("Building parts...")
        # Your code here
```

## 🎯 Manual Testing with curl

### Basic Request
```bash
curl -X GET "http://127.0.0.1:8000/api/order-analytics/" \
     -H "Accept: application/json"
```

### Request with Cursor
```bash
curl -X GET "http://127.0.0.1:8000/api/order-analytics/?cursor=YOUR_CURSOR_HERE" \
     -H "Accept: application/json"
```

### Pretty Print Response
```bash
curl -X GET "http://127.0.0.1:8000/api/order-analytics/" \
     -H "Accept: application/json" | python -m json.tool
```

## 📈 Performance Testing

### Test with Large Data Sets
Modify the management command to create more data:

```python
# In test_progressive management command
for i in range(1000):  # Create 1000 orders
    Order.objects.create(...)
```

### Monitor Memory Usage
```bash
# Install memory profiler
pip install memory-profiler

# Profile the view
python -m memory_profiler example_project/example_app/views.py
```

## ✅ Test Checklist

- [ ] Standalone tests pass
- [ ] Django migrations work
- [ ] Sample data created
- [ ] Django management command works
- [ ] Server starts without errors
- [ ] HTTP endpoints return 200 status
- [ ] Cursors are generated correctly
- [ ] Multiple requests follow cursor chain
- [ ] Final request has no cursor
- [ ] Error handling works (invalid cursors)
- [ ] Different chunk sizes work
- [ ] All view types work (APIView, ViewSet)

## 🎉 Success Criteria

Your progressive delivery package is working correctly if:

1. **All tests pass** without errors
2. **API endpoints respond** with proper JSON structure
3. **Cursors work** for pagination between requests
4. **Data is chunked** according to configuration
5. **Final request** has `cursor: null`
6. **Error handling** works for invalid cursors

Happy testing! 🚀 

## 🎯 **Ready-to-Use Test Suite**

### **Option 1: Quick All-in-One Test**
```bash
<code_block_to_apply_changes_from>
# Run all tests automatically
python run_tests.py
```

### **Option 2: Step-by-Step Testing**

#### **1. Test Core Functionality (No Django needed)**
```bash
python test_progressive_delivery.py
```

#### **2. Test Django Integration**
```bash
python run_tests.py django
```

#### **3. Start Django Server**
```bash
python run_tests.py server
```

#### **4. Test HTTP API (in another terminal)**
```bash
python test_client.py
```

## 🔧 **What Gets Tested**

### **✅ Core Functionality**
- Cursor encryption/decryption
- Progressive chunking logic
- Error handling
- Client simulation

### **✅ Django Integration**
- Database models and migrations
- DRF serializers
- Multiple view patterns (APIView, ViewSet)
- Sample data creation

### **✅ HTTP API**
- Real HTTP requests
- Multiple endpoints
- Cursor flow between requests
- Error scenarios

## 📋 **Test Endpoints Available**

Once the server is running, you can test:

- **`/api/order-analytics/`** - Complex dashboard with 5 parts
- **`/api/simple-progressive/`** - Simple example with 4 parts  
- **`/api/reports/`** - ViewSet example
- **`/api/reports/comprehensive_report/`** - Custom action

## 🎮 **Interactive Testing**

```bash
# Interactive mode lets you test specific endpoints
python test_client.py interactive
```

## 🚀 **Expected Results**

Each test will show:
- ✅ **Cursor management** working correctly
- ✅ **Progressive chunking** returning parts in batches
- ✅ **Secure tokens** preventing tampering
- ✅ **Stateless operation** with no server-side storage
- ✅ **Error handling** for invalid cursors

## 📊 **Success Example**

When working correctly, you'll see API responses like:
```json
{
  "results": [
    {"meta": {"total": 100, "generated_at": "2024-01-01"}},
    {"orders_batch": [{"id": 1, "amount": 100}]}
  ],
  "cursor": "gAAAAABh7x8y_encrypted_token_here"
}
```

## 🔥 **What to Try**

1. **Run the standalone test** to verify core functionality
2. **Start the Django server** to test real HTTP endpoints
3. **Use the HTTP client** to see progressive delivery in action
4. **Try different chunk sizes** by modifying `progressive_chunk_size`
5. **Test error scenarios** with invalid cursors

Everything is set up and ready to go! The package includes comprehensive testing, documentation, and real working examples. You can now see your progressive delivery package in action! 🎉 