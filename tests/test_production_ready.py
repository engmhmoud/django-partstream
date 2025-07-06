"""
Production-ready test suite for django-partstream
Tests all critical functionality including edge cases, security, and performance
"""
import pytest
import time
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.response import Response

from django_partstream import ProgressiveView, lazy, safe_call, cached_for
from django_partstream.cursors import CursorManager
from django_partstream.exceptions import ProgressiveDeliveryError


class TestProgressiveView(APITestCase):
    """Test the main ProgressiveView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_basic_progressive_view(self):
        """Test basic progressive view functionality"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return [
                    ("meta", {"timestamp": timezone.now().isoformat()}),
                    ("data", {"test": "data"})
                ]
        
        view = TestView()
        request = Mock()
        request.user = self.user
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_lazy_loading(self):
        """Test lazy loading functionality"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return [
                    ("immediate", {"fast": "data"}),
                    ("lazy", lazy(self.slow_operation))
                ]
            
            def slow_operation(self, request):
                return {"slow": "data"}
        
        view = TestView()
        request = Mock()
        request.user = self.user
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['immediate']['fast'], 'data')
        self.assertEqual(response.data['results'][1]['lazy']['slow'], 'data')
    
    def test_chunked_loading(self):
        """Test chunked loading with cursors"""
        class TestView(ProgressiveView):
            chunk_size = 1
            
            def get_parts(self):
                return [
                    ("part1", {"data": 1}),
                    ("part2", {"data": 2}),
                    ("part3", {"data": 3})
                ]
        
        view = TestView()
        request = Mock()
        request.user = self.user
        request.GET = {}
        view.request = request
        
        # First chunk
        response1 = view.get(request)
        self.assertEqual(len(response1.data['results']), 1)
        self.assertIsNotNone(response1.data['cursor'])
        
        # Second chunk
        request.GET = {'cursor': response1.data['cursor']}
        response2 = view.get(request)
        self.assertEqual(len(response2.data['results']), 1)
        self.assertIsNotNone(response2.data['cursor'])
        
        # Third chunk
        request.GET = {'cursor': response2.data['cursor']}
        response3 = view.get(request)
        self.assertEqual(len(response3.data['results']), 1)
        self.assertIsNone(response3.data['cursor'])
    
    def test_error_handling(self):
        """Test error handling doesn't crash the view"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return [
                    ("good", {"data": "ok"}),
                    ("bad", lazy(self.failing_operation))
                ]
            
            def failing_operation(self, request):
                raise Exception("Test error")
        
        view = TestView()
        request = Mock()
        request.user = self.user
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        # Should not crash, should return partial results
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        # The error should be logged but not break the response
    
    def test_safe_call_with_fallback(self):
        """Test safe_call with fallback values"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return [
                    ("safe", lazy(safe_call(self.risky_operation, fallback={"error": "fallback"})))
                ]
            
            def risky_operation(self, request):
                raise Exception("Test error")
        
        view = TestView()
        request = Mock()
        request.user = self.user
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['safe']['error'], 'fallback')
    
    def test_cached_for_decorator(self):
        """Test cached_for decorator"""
        class TestView(ProgressiveView):
            call_count = 0
            
            def get_parts(self):
                return [
                    ("cached", lazy(self.get_cached_data))
                ]
            
            @cached_for(60)
            def get_cached_data(self, request):
                self.call_count += 1
                return {"count": self.call_count}
        
        view = TestView()
        request = Mock()
        request.user = self.user
        request.GET = {}
        view.request = request
        
        # First call
        response1 = view.get(request)
        count1 = response1.data['results'][0]['cached']['count']
        
        # Second call should use cache
        response2 = view.get(request)
        count2 = response2.data['results'][0]['cached']['count']
        
        self.assertEqual(count1, count2)  # Should be cached
    
    def test_empty_parts(self):
        """Test handling of empty parts list"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return []
        
        view = TestView()
        request = Mock()
        request.user = self.user
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        self.assertIsNone(response.data['cursor'])
    
    def test_none_parts(self):
        """Test handling of None parts"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return None
        
        view = TestView()
        request = Mock()
        request.user = self.user
        request.GET = {}
        view.request = request
        
        with self.assertRaises(ProgressiveDeliveryError):
            view.get(request)


class TestCursorManager(TestCase):
    """Test cursor management and security"""
    
    def setUp(self):
        self.cursor_manager = CursorManager()
    
    def test_cursor_generation(self):
        """Test cursor generation and validation"""
        data = {"index": 5, "user_id": 1}
        cursor = self.cursor_manager.generate_cursor(data)
        
        self.assertIsInstance(cursor, str)
        self.assertGreater(len(cursor), 0)
        
        # Should be able to decode the cursor
        decoded = self.cursor_manager.decode_cursor(cursor)
        self.assertEqual(decoded['index'], 5)
        self.assertEqual(decoded['user_id'], 1)
    
    def test_cursor_expiration(self):
        """Test cursor expiration"""
        data = {"index": 5}
        cursor = self.cursor_manager.generate_cursor(data, ttl=1)
        
        # Should work immediately
        decoded = self.cursor_manager.decode_cursor(cursor)
        self.assertEqual(decoded['index'], 5)
        
        # Should expire after TTL
        time.sleep(2)
        with self.assertRaises(ProgressiveDeliveryError):
            self.cursor_manager.decode_cursor(cursor)
    
    def test_invalid_cursor(self):
        """Test invalid cursor handling"""
        with self.assertRaises(ProgressiveDeliveryError):
            self.cursor_manager.decode_cursor("invalid-cursor")
        
        with self.assertRaises(ProgressiveDeliveryError):
            self.cursor_manager.decode_cursor("")
        
        with self.assertRaises(ProgressiveDeliveryError):
            self.cursor_manager.decode_cursor(None)
    
    def test_cursor_tampering(self):
        """Test cursor tampering detection"""
        data = {"index": 5}
        cursor = self.cursor_manager.generate_cursor(data)
        
        # Tamper with cursor
        tampered_cursor = cursor[:-5] + "tampr"
        
        with self.assertRaises(ProgressiveDeliveryError):
            self.cursor_manager.decode_cursor(tampered_cursor)


class TestSecurityFeatures(TestCase):
    """Test security features"""
    
    def test_cursor_encryption(self):
        """Test that cursors are properly encrypted"""
        cursor_manager = CursorManager()
        data = {"sensitive": "data", "user_id": 123}
        cursor = cursor_manager.generate_cursor(data)
        
        # Cursor should not contain plaintext data
        self.assertNotIn("sensitive", cursor)
        self.assertNotIn("123", cursor)
        
        # Should be URL-safe
        self.assertNotIn("+", cursor)
        self.assertNotIn("/", cursor)
        self.assertNotIn("=", cursor)
    
    def test_different_cursors_for_same_data(self):
        """Test that cursors are different even for same data (due to timestamp)"""
        cursor_manager = CursorManager()
        data = {"index": 5}
        
        cursor1 = cursor_manager.generate_cursor(data)
        time.sleep(0.01)  # Small delay
        cursor2 = cursor_manager.generate_cursor(data)
        
        self.assertNotEqual(cursor1, cursor2)


class TestPerformanceOptimizations(TestCase):
    """Test performance optimizations"""
    
    def test_lazy_loading_performance(self):
        """Test that lazy loading actually improves performance"""
        class TestView(ProgressiveView):
            chunk_size = 1
            
            def get_parts(self):
                return [
                    ("fast", {"data": "immediate"}),
                    ("slow", lazy(self.slow_operation))
                ]
            
            def slow_operation(self, request):
                time.sleep(0.1)  # Simulate slow operation
                return {"data": "slow"}
        
        view = TestView()
        request = Mock()
        request.user = User.objects.create_user(username='test')
        request.GET = {}
        view.request = request
        
        # First chunk should be fast (no lazy loading)
        start_time = time.time()
        response = view.get(request)
        elapsed = time.time() - start_time
        
        # Should be fast since slow operation is lazy
        self.assertLess(elapsed, 0.05)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNotNone(response.data['cursor'])
    
    def test_caching_performance(self):
        """Test that caching improves performance"""
        class TestView(ProgressiveView):
            call_count = 0
            
            def get_parts(self):
                return [
                    ("cached", lazy(self.get_cached_data))
                ]
            
            @cached_for(60)
            def get_cached_data(self, request):
                time.sleep(0.1)  # Simulate expensive operation
                self.call_count += 1
                return {"count": self.call_count}
        
        view = TestView()
        request = Mock()
        request.user = User.objects.create_user(username='test')
        request.GET = {}
        view.request = request
        
        # First call should be slow
        start_time = time.time()
        response1 = view.get(request)
        elapsed1 = time.time() - start_time
        
        # Second call should be fast (cached)
        start_time = time.time()
        response2 = view.get(request)
        elapsed2 = time.time() - start_time
        
        self.assertGreater(elapsed1, 0.05)  # First call was slow
        self.assertLess(elapsed2, 0.05)    # Second call was fast
        
        # Data should be the same
        self.assertEqual(
            response1.data['results'][0]['cached']['count'],
            response2.data['results'][0]['cached']['count']
        )


class TestRealWorldScenarios(TestCase):
    """Test real-world scenarios"""
    
    def test_large_dataset_chunking(self):
        """Test chunking with large datasets"""
        class TestView(ProgressiveView):
            chunk_size = 2
            
            def get_parts(self):
                # Simulate 10 parts
                return [(f"part{i}", {"data": i}) for i in range(10)]
        
        view = TestView()
        request = Mock()
        request.user = User.objects.create_user(username='test')
        request.GET = {}
        view.request = request
        
        all_results = []
        cursor = None
        
        # Load all chunks
        while True:
            if cursor:
                request.GET = {'cursor': cursor}
            else:
                request.GET = {}
            
            response = view.get(request)
            all_results.extend(response.data['results'])
            
            if not response.data['cursor']:
                break
            
            cursor = response.data['cursor']
        
        # Should have loaded all 10 parts
        self.assertEqual(len(all_results), 10)
        
        # Verify data integrity
        for i, result in enumerate(all_results):
            expected_key = f"part{i}"
            self.assertIn(expected_key, result)
            self.assertEqual(result[expected_key]['data'], i)
    
    def test_mixed_sync_async_operations(self):
        """Test mixing synchronous and asynchronous operations"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return [
                    ("sync", {"data": "immediate"}),
                    ("async", lazy(self.async_operation)),
                    ("sync2", {"data": "immediate2"}),
                    ("async2", lazy(self.async_operation2))
                ]
            
            def async_operation(self, request):
                time.sleep(0.01)  # Simulate async operation
                return {"data": "async1"}
            
            def async_operation2(self, request):
                time.sleep(0.01)  # Simulate async operation
                return {"data": "async2"}
        
        view = TestView()
        request = Mock()
        request.user = User.objects.create_user(username='test')
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 4)
        
        # Verify all data is correct
        results = response.data['results']
        self.assertEqual(results[0]['sync']['data'], 'immediate')
        self.assertEqual(results[1]['async']['data'], 'async1')
        self.assertEqual(results[2]['sync2']['data'], 'immediate2')
        self.assertEqual(results[3]['async2']['data'], 'async2')
    
    def test_conditional_parts_based_on_permissions(self):
        """Test conditional parts based on user permissions"""
        class TestView(ProgressiveView):
            def get_parts(self):
                parts = [
                    ("public", {"data": "public"})
                ]
                
                if self.request.user.is_authenticated:
                    parts.append(("user", {"data": "user"}))
                
                if self.request.user.is_staff:
                    parts.append(("staff", {"data": "staff"}))
                
                return parts
        
        view = TestView()
        
        # Test with anonymous user
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        request.user.is_staff = False
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('public', response.data['results'][0])
        
        # Test with authenticated user
        request.user.is_authenticated = True
        response = view.get(request)
        self.assertEqual(len(response.data['results']), 2)
        
        # Test with staff user
        request.user.is_staff = True
        response = view.get(request)
        self.assertEqual(len(response.data['results']), 3)


class TestEdgeCases(TestCase):
    """Test edge cases and error conditions"""
    
    def test_malformed_cursor(self):
        """Test handling of malformed cursors"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return [("test", {"data": "test"})]
        
        view = TestView()
        request = Mock()
        request.user = User.objects.create_user(username='test')
        request.GET = {'cursor': 'malformed-cursor'}
        view.request = request
        
        with self.assertRaises(ProgressiveDeliveryError):
            view.get(request)
    
    def test_empty_lazy_function(self):
        """Test lazy function that returns None"""
        class TestView(ProgressiveView):
            def get_parts(self):
                return [
                    ("empty", lazy(self.empty_function))
                ]
            
            def empty_function(self, request):
                return None
        
        view = TestView()
        request = Mock()
        request.user = User.objects.create_user(username='test')
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['empty'], None)
    
    def test_very_large_chunk_size(self):
        """Test with very large chunk size"""
        class TestView(ProgressiveView):
            chunk_size = 1000
            
            def get_parts(self):
                return [(f"part{i}", {"data": i}) for i in range(5)]
        
        view = TestView()
        request = Mock()
        request.user = User.objects.create_user(username='test')
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        # Should return all parts in one chunk
        self.assertEqual(len(response.data['results']), 5)
        self.assertIsNone(response.data['cursor'])
    
    def test_zero_chunk_size(self):
        """Test with zero chunk size (should use default)"""
        class TestView(ProgressiveView):
            chunk_size = 0
            
            def get_parts(self):
                return [(f"part{i}", {"data": i}) for i in range(5)]
        
        view = TestView()
        request = Mock()
        request.user = User.objects.create_user(username='test')
        request.GET = {}
        view.request = request
        
        response = view.get(request)
        
        # Should use default chunk size (2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertIsNotNone(response.data['cursor'])


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 