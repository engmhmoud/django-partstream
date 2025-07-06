"""
Performance optimization utilities for django-partstream
Production-ready performance monitoring and optimization
"""
import time
import threading
from typing import Dict, Any, Callable, Optional, List
from functools import wraps
from contextlib import contextmanager

from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.db import connection


class PerformanceConfig:
    """Performance configuration for django-partstream"""
    
    # Caching
    DEFAULT_CACHE_TTL = 300  # 5 minutes
    CACHE_KEY_PREFIX = 'partstream'
    
    # Monitoring
    ENABLE_MONITORING = True
    TRACK_QUERY_COUNT = True
    TRACK_RESPONSE_TIME = True
    
    # Optimization
    LAZY_LOADING_THRESHOLD = 0.1  # 100ms
    PARALLEL_EXECUTION = False
    MAX_CONCURRENT_PARTS = 5
    
    # Timeouts
    DEFAULT_TIMEOUT = 30  # seconds
    SLOW_QUERY_THRESHOLD = 1.0  # 1 second


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = {}
        self.lock = threading.Lock()
    
    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""
        timer_id = f"{operation}_{int(time.time() * 1000)}"
        with self.lock:
            self.metrics[timer_id] = {
                'operation': operation,
                'start_time': time.time(),
                'query_count_start': len(connection.queries) if PerformanceConfig.TRACK_QUERY_COUNT else 0
            }
        return timer_id
    
    def stop_timer(self, timer_id: str) -> Dict[str, Any]:
        """Stop timing an operation and return metrics"""
        end_time = time.time()
        
        with self.lock:
            if timer_id not in self.metrics:
                return {}
            
            metric = self.metrics[timer_id]
            duration = end_time - metric['start_time']
            
            query_count = 0
            if PerformanceConfig.TRACK_QUERY_COUNT:
                query_count = len(connection.queries) - metric['query_count_start']
            
            result = {
                'operation': metric['operation'],
                'duration': duration,
                'query_count': query_count,
                'timestamp': timezone.now().isoformat()
            }
            
            # Clean up
            del self.metrics[timer_id]
            
            return result
    
    def record_metric(self, metric_name: str, value: Any, tags: Dict[str, str] = None):
        """Record a custom metric"""
        if not PerformanceConfig.ENABLE_MONITORING:
            return
        
        metric_data = {
            'name': metric_name,
            'value': value,
            'tags': tags or {},
            'timestamp': timezone.now().isoformat()
        }
        
        # Store in cache for collection
        cache_key = f"{PerformanceConfig.CACHE_KEY_PREFIX}:metrics:{metric_name}"
        metrics_list = cache.get(cache_key, [])
        metrics_list.append(metric_data)
        
        # Keep only last 100 metrics
        if len(metrics_list) > 100:
            metrics_list = metrics_list[-100:]
        
        cache.set(cache_key, metrics_list, 3600)  # 1 hour
    
    def get_metrics(self, metric_name: str = None) -> Dict[str, Any]:
        """Get collected metrics"""
        if metric_name:
            cache_key = f"{PerformanceConfig.CACHE_KEY_PREFIX}:metrics:{metric_name}"
            return cache.get(cache_key, [])
        
        # Get all metrics
        all_metrics = {}
        cache_keys = cache.keys(f"{PerformanceConfig.CACHE_KEY_PREFIX}:metrics:*")
        
        for key in cache_keys:
            metric_name = key.split(':')[-1]
            all_metrics[metric_name] = cache.get(key, [])
        
        return all_metrics


# Global performance monitor
performance_monitor = PerformanceMonitor()


@contextmanager
def performance_timer(operation: str):
    """Context manager for timing operations"""
    timer_id = performance_monitor.start_timer(operation)
    try:
        yield
    finally:
        metrics = performance_monitor.stop_timer(timer_id)
        if metrics:
            performance_monitor.record_metric('operation_time', metrics['duration'], {
                'operation': operation,
                'query_count': str(metrics['query_count'])
            })


class CacheManager:
    """Advanced caching for progressive delivery"""
    
    @staticmethod
    def get_cache_key(prefix: str, user_id: int = None, **kwargs) -> str:
        """Generate cache key"""
        key_parts = [PerformanceConfig.CACHE_KEY_PREFIX, prefix]
        
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        for k, v in kwargs.items():
            key_parts.append(f"{k}:{v}")
        
        return ':'.join(key_parts)
    
    @staticmethod
    def cached_function(ttl: int = None, key_prefix: str = None, per_user: bool = True):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key_parts = {
                    'func': func.__name__,
                    'args': str(hash(str(args))),
                    'kwargs': str(hash(str(sorted(kwargs.items()))))
                }
                
                if per_user and args and hasattr(args[0], 'request'):
                    user_id = getattr(args[0].request.user, 'id', None)
                    if user_id:
                        cache_key_parts['user'] = user_id
                
                cache_key = CacheManager.get_cache_key(
                    key_prefix or func.__name__,
                    **cache_key_parts
                )
                
                # Try to get from cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    performance_monitor.record_metric('cache_hit', 1, {'function': func.__name__})
                    return cached_result
                
                # Execute function
                with performance_timer(f"cached_function_{func.__name__}"):
                    result = func(*args, **kwargs)
                
                # Cache result
                cache.set(cache_key, result, ttl or PerformanceConfig.DEFAULT_CACHE_TTL)
                performance_monitor.record_metric('cache_miss', 1, {'function': func.__name__})
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def invalidate_cache_pattern(pattern: str):
        """Invalidate cache keys matching pattern"""
        cache_keys = cache.keys(f"{PerformanceConfig.CACHE_KEY_PREFIX}:{pattern}*")
        for key in cache_keys:
            cache.delete(key)


class LazyLoader:
    """Optimized lazy loading for progressive delivery"""
    
    def __init__(self, func: Callable, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.cached_result = None
        self.is_loaded = False
        self.load_time = None
    
    def __call__(self, request):
        """Execute lazy function with performance monitoring"""
        if self.is_loaded:
            return self.cached_result
        
        start_time = time.time()
        
        try:
            with performance_timer(f"lazy_load_{self.func.__name__}"):
                self.cached_result = self.func(request, *self.args, **self.kwargs)
                self.is_loaded = True
                self.load_time = time.time() - start_time
                
                # Record metrics
                performance_monitor.record_metric('lazy_load_time', self.load_time, {
                    'function': self.func.__name__
                })
                
                return self.cached_result
                
        except Exception as e:
            performance_monitor.record_metric('lazy_load_error', 1, {
                'function': self.func.__name__,
                'error': str(e)
            })
            raise
    
    @property
    def performance_info(self) -> Dict[str, Any]:
        """Get performance information"""
        return {
            'function': self.func.__name__,
            'is_loaded': self.is_loaded,
            'load_time': self.load_time,
            'estimated_benefit': self.load_time > PerformanceConfig.LAZY_LOADING_THRESHOLD if self.load_time else None
        }


class QueryOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    def optimize_queryset(queryset, select_related: List[str] = None, prefetch_related: List[str] = None):
        """Optimize Django queryset with select_related and prefetch_related"""
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        return queryset
    
    @staticmethod
    def track_queries(func):
        """Decorator to track database queries"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            initial_queries = len(connection.queries)
            
            with performance_timer(f"query_tracking_{func.__name__}"):
                result = func(*args, **kwargs)
            
            final_queries = len(connection.queries)
            query_count = final_queries - initial_queries
            
            performance_monitor.record_metric('query_count', query_count, {
                'function': func.__name__
            })
            
            # Log slow queries
            if query_count > 10:  # Threshold for many queries
                performance_monitor.record_metric('slow_query_warning', 1, {
                    'function': func.__name__,
                    'query_count': str(query_count)
                })
            
            return result
        return wrapper


class ParallelExecutor:
    """Parallel execution for progressive delivery parts"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or PerformanceConfig.MAX_CONCURRENT_PARTS
    
    def execute_parts(self, parts: List[tuple], request) -> List[tuple]:
        """Execute parts in parallel where possible"""
        if not PerformanceConfig.PARALLEL_EXECUTION:
            return self._execute_sequential(parts, request)
        
        # Separate immediate and lazy parts
        immediate_parts = []
        lazy_parts = []
        
        for name, part_func in parts:
            if hasattr(part_func, '__call__') and hasattr(part_func, 'func'):
                lazy_parts.append((name, part_func))
            else:
                immediate_parts.append((name, part_func))
        
        # Execute immediate parts first
        results = []
        for name, data in immediate_parts:
            results.append((name, data))
        
        # Execute lazy parts in parallel
        if lazy_parts:
            results.extend(self._execute_parallel(lazy_parts, request))
        
        return results
    
    def _execute_sequential(self, parts: List[tuple], request) -> List[tuple]:
        """Execute parts sequentially"""
        results = []
        
        for name, part_func in parts:
            with performance_timer(f"part_execution_{name}"):
                if hasattr(part_func, '__call__'):
                    result = part_func(request)
                else:
                    result = part_func
                results.append((name, result))
        
        return results
    
    def _execute_parallel(self, lazy_parts: List[tuple], request) -> List[tuple]:
        """Execute lazy parts in parallel using threading"""
        import concurrent.futures
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all lazy parts
            future_to_name = {}
            for name, part_func in lazy_parts:
                future = executor.submit(part_func, request)
                future_to_name[future] = name
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    result = future.result()
                    results.append((name, result))
                except Exception as e:
                    performance_monitor.record_metric('parallel_execution_error', 1, {
                        'part_name': name,
                        'error': str(e)
                    })
                    results.append((name, {'error': str(e)}))
        
        return results


class MemoryOptimizer:
    """Memory optimization utilities"""
    
    @staticmethod
    def optimize_response_size(data: Any, max_size: int = 1024 * 1024) -> Any:
        """Optimize response size by truncating large data"""
        import json
        
        # Serialize to check size
        serialized = json.dumps(data, default=str)
        
        if len(serialized) <= max_size:
            return data
        
        # Data is too large, need to optimize
        if isinstance(data, dict):
            return MemoryOptimizer._optimize_dict(data, max_size)
        elif isinstance(data, list):
            return MemoryOptimizer._optimize_list(data, max_size)
        
        return data
    
    @staticmethod
    def _optimize_dict(data: dict, max_size: int) -> dict:
        """Optimize dictionary by removing large values"""
        optimized = {}
        
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                optimized[key] = MemoryOptimizer.optimize_response_size(value, max_size // 2)
            else:
                optimized[key] = value
        
        return optimized
    
    @staticmethod
    def _optimize_list(data: list, max_size: int) -> list:
        """Optimize list by truncating if necessary"""
        if len(data) <= 100:  # Small lists are OK
            return data
        
        # For large lists, take first 50 and last 50
        return data[:50] + [{'truncated': f'{len(data) - 100} items'}] + data[-50:]


class PerformanceAnalyzer:
    """Analyze and report performance metrics"""
    
    @staticmethod
    def get_performance_report() -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        metrics = performance_monitor.get_metrics()
        
        report = {
            'timestamp': timezone.now().isoformat(),
            'cache_metrics': PerformanceAnalyzer._analyze_cache_metrics(metrics),
            'query_metrics': PerformanceAnalyzer._analyze_query_metrics(metrics),
            'timing_metrics': PerformanceAnalyzer._analyze_timing_metrics(metrics),
            'error_metrics': PerformanceAnalyzer._analyze_error_metrics(metrics),
            'recommendations': PerformanceAnalyzer._generate_recommendations(metrics)
        }
        
        return report
    
    @staticmethod
    def _analyze_cache_metrics(metrics: Dict[str, List]) -> Dict[str, Any]:
        """Analyze cache performance"""
        hits = metrics.get('cache_hit', [])
        misses = metrics.get('cache_miss', [])
        
        total_requests = len(hits) + len(misses)
        hit_rate = (len(hits) / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests,
            'hits': len(hits),
            'misses': len(misses)
        }
    
    @staticmethod
    def _analyze_query_metrics(metrics: Dict[str, List]) -> Dict[str, Any]:
        """Analyze database query performance"""
        query_counts = [m['value'] for m in metrics.get('query_count', [])]
        
        if not query_counts:
            return {'status': 'No query data'}
        
        return {
            'avg_queries_per_request': round(sum(query_counts) / len(query_counts), 2),
            'max_queries': max(query_counts),
            'min_queries': min(query_counts),
            'total_queries': sum(query_counts),
            'slow_query_warnings': len(metrics.get('slow_query_warning', []))
        }
    
    @staticmethod
    def _analyze_timing_metrics(metrics: Dict[str, List]) -> Dict[str, Any]:
        """Analyze timing performance"""
        timings = [m['value'] for m in metrics.get('operation_time', [])]
        
        if not timings:
            return {'status': 'No timing data'}
        
        return {
            'avg_response_time': round(sum(timings) / len(timings) * 1000, 2),  # ms
            'max_response_time': round(max(timings) * 1000, 2),
            'min_response_time': round(min(timings) * 1000, 2),
            'total_operations': len(timings),
            'slow_operations': len([t for t in timings if t > PerformanceConfig.SLOW_QUERY_THRESHOLD])
        }
    
    @staticmethod
    def _analyze_error_metrics(metrics: Dict[str, List]) -> Dict[str, Any]:
        """Analyze error metrics"""
        errors = metrics.get('lazy_load_error', [])
        parallel_errors = metrics.get('parallel_execution_error', [])
        
        return {
            'lazy_load_errors': len(errors),
            'parallel_execution_errors': len(parallel_errors),
            'total_errors': len(errors) + len(parallel_errors)
        }
    
    @staticmethod
    def _generate_recommendations(metrics: Dict[str, List]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Cache recommendations
        cache_data = PerformanceAnalyzer._analyze_cache_metrics(metrics)
        if cache_data.get('hit_rate', 0) < 80:
            recommendations.append("Consider increasing cache TTL or optimizing cache keys")
        
        # Query recommendations
        query_data = PerformanceAnalyzer._analyze_query_metrics(metrics)
        if query_data.get('avg_queries_per_request', 0) > 10:
            recommendations.append("High query count detected - consider using select_related/prefetch_related")
        
        # Timing recommendations
        timing_data = PerformanceAnalyzer._analyze_timing_metrics(metrics)
        if timing_data.get('avg_response_time', 0) > 1000:  # 1 second
            recommendations.append("Response times are high - consider optimizing slow operations")
        
        # Error recommendations
        error_data = PerformanceAnalyzer._analyze_error_metrics(metrics)
        if error_data.get('total_errors', 0) > 0:
            recommendations.append("Errors detected - check error handling and external service reliability")
        
        return recommendations


# Performance optimization decorators
def optimize_queries(select_related: List[str] = None, prefetch_related: List[str] = None):
    """Decorator to optimize database queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This would be implemented based on your ORM usage
            return func(*args, **kwargs)
        return wrapper
    return decorator


def memory_efficient(max_size: int = 1024 * 1024):
    """Decorator to ensure memory efficient responses"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return MemoryOptimizer.optimize_response_size(result, max_size)
        return wrapper
    return decorator


def performance_tracked(func):
    """Decorator to track function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with performance_timer(func.__name__):
            return func(*args, **kwargs)
    return wrapper 