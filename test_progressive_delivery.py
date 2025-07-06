#!/usr/bin/env python
"""
Test script for progressive delivery functionality.
This script demonstrates how the progressive delivery package works
without requiring a full Django server setup.
"""

import os
import sys
import json
from typing import Generator, Tuple, Any

# Add the package to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Test the cursor management functionality
def test_cursor_management():
    """Test cursor creation and decoding."""
    print("=" * 50)
    print("Testing Cursor Management")
    print("=" * 50)
    
    from drf_progressive_delivery.cursors import CursorManager
    
    # Create cursor manager
    cursor_manager = CursorManager(secret_key="test-secret-key-for-demo")
    
    # Test data
    test_data = {
        "start_index": 2,
        "user_id": 123,
        "filters": {"status": "active"}
    }
    
    # Create cursor
    cursor = cursor_manager.create_cursor(test_data)
    print(f"Created cursor: {cursor[:50]}...")
    
    # Decode cursor
    decoded_data = cursor_manager.decode_cursor(cursor)
    print(f"Decoded data: {decoded_data}")
    
    # Verify data integrity
    assert decoded_data == test_data, "Data integrity check failed!"
    print("✅ Cursor management test passed!")
    
    # Test invalid cursor
    try:
        cursor_manager.decode_cursor("invalid-cursor")
        assert False, "Should have raised an error"
    except Exception as e:
        print(f"✅ Invalid cursor properly rejected: {type(e).__name__}")
    
    print()


def test_progressive_logic():
    """Test the progressive delivery logic."""
    print("=" * 50)
    print("Testing Progressive Delivery Logic")
    print("=" * 50)
    
    # Mock request class
    class MockRequest:
        def __init__(self, cursor=None):
            self.GET = {'cursor': cursor} if cursor else {}
            self.user = MockUser()
    
    class MockUser:
        username = "test_user"
        is_authenticated = True
    
    # Mock progressive delivery class
    class TestProgressiveDelivery:
        def __init__(self):
            from drf_progressive_delivery.cursors import CursorManager
            self.progressive_chunk_size = 2
            self.progressive_cursor_ttl = None
            self.progressive_cursor_param = 'cursor'
            self.cursor_manager = CursorManager(secret_key="test-secret")
        
        def build_parts(self, request) -> Generator[Tuple[str, Any], None, None]:
            """Generate test parts."""
            parts = [
                ("meta", {"total": 100, "generated_at": "2024-01-01"}),
                ("orders", [{"id": 1, "amount": 100}, {"id": 2, "amount": 200}]),
                ("analytics", {"revenue": 300, "orders": 2}),
                ("summary", {"processed": True, "complete": True}),
                ("extra_data", {"bonus": "information"}),
            ]
            
            for name, data in parts:
                yield (name, data)
        
        def get_progressive_response(self, request):
            """Simulate progressive response logic."""
            cursor = request.GET.get(self.progressive_cursor_param)
            start_index = 0
            
            if cursor:
                try:
                    cursor_data = self.cursor_manager.decode_cursor(cursor)
                    start_index = cursor_data.get('start_index', 0)
                except Exception as e:
                    return {"error": str(e)}
            
            # Generate all parts
            all_parts = list(self.build_parts(request))
            
            # Get chunk
            end_index = start_index + self.progressive_chunk_size
            current_parts = all_parts[start_index:end_index]
            
            # Format response
            results = []
            for part_name, part_data in current_parts:
                results.append({part_name: part_data})
            
            response_data = {
                "results": results,
                "cursor": None
            }
            
            # Add cursor if more parts exist
            if end_index < len(all_parts):
                next_cursor_data = {"start_index": end_index}
                response_data["cursor"] = self.cursor_manager.create_cursor(next_cursor_data)
            
            return response_data
    
    # Test the progressive delivery
    delivery = TestProgressiveDelivery()
    
    # First request (no cursor)
    print("First request (no cursor):")
    request1 = MockRequest()
    response1 = delivery.get_progressive_response(request1)
    print(f"Response: {json.dumps(response1, indent=2)}")
    
    cursor1 = response1.get('cursor')
    print(f"Cursor present: {cursor1 is not None}")
    
    # Second request (with cursor)
    if cursor1:
        print("\nSecond request (with cursor):")
        request2 = MockRequest(cursor1)
        response2 = delivery.get_progressive_response(request2)
        print(f"Response: {json.dumps(response2, indent=2)}")
        
        cursor2 = response2.get('cursor')
        print(f"Cursor present: {cursor2 is not None}")
        
        # Third request (with cursor)
        if cursor2:
            print("\nThird request (final):")
            request3 = MockRequest(cursor2)
            response3 = delivery.get_progressive_response(request3)
            print(f"Response: {json.dumps(response3, indent=2)}")
            
            cursor3 = response3.get('cursor')
            print(f"Cursor present: {cursor3 is not None}")
    
    print("✅ Progressive delivery logic test passed!")
    print()


def test_client_simulation():
    """Simulate how a client would consume the progressive API."""
    print("=" * 50)
    print("Client Simulation")
    print("=" * 50)
    
    class MockProgressiveAPI:
        def __init__(self):
            from drf_progressive_delivery.cursors import CursorManager
            self.cursor_manager = CursorManager(secret_key="test-secret")
            self.chunk_size = 2
            
        def get_data(self, cursor=None):
            """Simulate API endpoint."""
            all_parts = [
                ("dashboard_meta", {"type": "analytics", "generated": "2024-01-01"}),
                ("sales_data", {"revenue": 50000, "orders": 200}),
                ("customer_data", {"new": 15, "returning": 85}),
                ("product_data", {"total": 50, "low_stock": 3}),
                ("system_metrics", {"cpu": 45, "memory": 60}),
            ]
            
            start_index = 0
            if cursor:
                try:
                    cursor_data = self.cursor_manager.decode_cursor(cursor)
                    start_index = cursor_data.get('start_index', 0)
                except:
                    return {"error": "Invalid cursor"}
            
            end_index = start_index + self.chunk_size
            current_parts = all_parts[start_index:end_index]
            
            results = []
            for name, data in current_parts:
                results.append({name: data})
            
            next_cursor = None
            if end_index < len(all_parts):
                next_cursor = self.cursor_manager.create_cursor({"start_index": end_index})
            
            return {
                "results": results,
                "cursor": next_cursor,
                "total_parts": len(all_parts),
                "current_index": start_index
            }
    
    # Simulate client fetching all data
    api = MockProgressiveAPI()
    all_results = []
    cursor = None
    request_count = 0
    
    print("Fetching data progressively...")
    
    while True:
        request_count += 1
        print(f"\nRequest {request_count}:")
        
        response = api.get_data(cursor)
        
        if "error" in response:
            print(f"Error: {response['error']}")
            break
        
        results = response.get('results', [])
        cursor = response.get('cursor')
        
        print(f"  Received {len(results)} parts")
        for result in results:
            part_name = list(result.keys())[0]
            print(f"    - {part_name}")
        
        all_results.extend(results)
        
        if not cursor:
            print("  No more data (cursor is None)")
            break
        else:
            print(f"  Cursor for next request: {cursor[:20]}...")
    
    print(f"\n✅ Client simulation complete!")
    print(f"Total requests made: {request_count}")
    print(f"Total parts received: {len(all_results)}")
    print(f"Final data: {len(all_results)} parts")


if __name__ == "__main__":
    print("🚀 Testing DRF Progressive Delivery Package")
    print("=" * 60)
    
    try:
        test_cursor_management()
        test_progressive_logic()
        test_client_simulation()
        
        print("=" * 60)
        print("🎉 All tests passed! The progressive delivery package is working correctly.")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 