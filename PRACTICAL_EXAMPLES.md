# 📋 Practical Examples - Ready to Use

## **1. Blog Dashboard API**

```python
from drf_progressive_delivery import RegistryProgressiveView, ProgressivePartsRegistry
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Sum, Avg

class BlogDashboard(RegistryProgressiveView, APIView):
    permission_classes = [IsAuthenticated]
    progressive_chunk_size = 2
    
    def get_parts_registry(self):
        registry = ProgressivePartsRegistry()
        
        # Quick metadata (immediate)
        registry.add_static("meta", {
            "blog_name": "My Blog",
            "user": self.request.user.username,
            "timestamp": timezone.now().isoformat(),
            "total_posts": Post.objects.count()
        })
        
        # Recent posts (fast query)
        registry.add_model(
            "recent_posts",
            Post.objects.select_related('author', 'category')
                       .order_by('-created_at')[:20],
            PostSerializer,
            lazy=True
        )
        
        # Popular posts (moderate query)
        registry.add_model(
            "popular_posts",
            Post.objects.annotate(view_count=Count('views'))
                       .order_by('-view_count')[:10],
            PostSerializer,
            lazy=True
        )
        
        # Analytics (expensive computation)
        registry.add_function("analytics", self._compute_analytics, lazy=True)
        
        return registry
    
    def _compute_analytics(self, request, **kwargs):
        """Expensive analytics computation."""
        from datetime import timedelta
        
        last_30_days = timezone.now() - timedelta(days=30)
        recent_posts = Post.objects.filter(created_at__gte=last_30_days)
        
        return {
            "total_views": View.objects.filter(
                post__created_at__gte=last_30_days
            ).count(),
            "avg_views_per_post": View.objects.filter(
                post__created_at__gte=last_30_days
            ).aggregate(Avg('count'))['count__avg'] or 0,
            "top_categories": Category.objects.annotate(
                post_count=Count('posts')
            ).order_by('-post_count')[:5].values('name', 'post_count'),
            "engagement_rate": self._calculate_engagement_rate(recent_posts)
        }
    
    def _calculate_engagement_rate(self, posts):
        """Calculate average engagement rate."""
        if not posts.exists():
            return 0
        
        total_engagement = 0
        for post in posts:
            views = post.views.count()
            comments = post.comments.count()
            if views > 0:
                total_engagement += (comments / views) * 100
        
        return total_engagement / posts.count()
```

## **2. E-commerce Admin Dashboard**

```python
class EcommerceAdmin(RegistryProgressiveView, APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    progressive_chunk_size = 3
    
    def get_parts_registry(self):
        registry = ProgressivePartsRegistry()
        
        # Store overview (immediate)
        registry.add_static("overview", {
            "store_name": settings.STORE_NAME,
            "currency": settings.DEFAULT_CURRENCY,
            "admin_user": self.request.user.username,
            "timestamp": timezone.now().isoformat()
        })
        
        # Today's summary (fast)
        registry.add_function("today_summary", self._today_summary, lazy=True)
        
        # Recent orders (moderate)
        registry.add_model(
            "recent_orders",
            Order.objects.select_related('customer', 'shipping_address')
                         .prefetch_related('items__product')
                         .order_by('-created_at')[:50],
            OrderSerializer,
            lazy=True
        )
        
        # Inventory alerts (fast)
        registry.add_model(
            "low_stock_alerts",
            Product.objects.filter(stock__lt=10, is_active=True),
            ProductSerializer,
            lazy=True
        )
        
        # Sales analytics (expensive)
        registry.add_function("sales_analytics", self._sales_analytics, lazy=True)
        
        # Customer insights (very expensive)
        registry.add_function("customer_insights", self._customer_insights, lazy=True)
        
        return registry
    
    def _today_summary(self, request, **kwargs):
        """Today's key metrics."""
        today = timezone.now().date()
        today_orders = Order.objects.filter(created_at__date=today)
        
        return {
            "orders_today": today_orders.count(),
            "revenue_today": float(today_orders.aggregate(
                Sum('total_amount')
            )['total_amount__sum'] or 0),
            "new_customers_today": Customer.objects.filter(
                created_at__date=today
            ).count(),
            "pending_orders": Order.objects.filter(
                status='pending'
            ).count()
        }
    
    def _sales_analytics(self, request, **kwargs):
        """Complex sales analytics."""
        from datetime import timedelta
        
        last_30_days = timezone.now() - timedelta(days=30)
        orders = Order.objects.filter(created_at__gte=last_30_days)
        
        return {
            "total_revenue": float(orders.aggregate(
                Sum('total_amount')
            )['total_amount__sum'] or 0),
            "avg_order_value": float(orders.aggregate(
                Avg('total_amount')
            )['total_amount__avg'] or 0),
            "conversion_rate": self._calculate_conversion_rate(),
            "top_products": self._get_top_products(orders),
            "revenue_by_day": self._revenue_by_day(orders),
            "payment_methods": self._payment_method_breakdown(orders)
        }
    
    def _customer_insights(self, request, **kwargs):
        """Advanced customer analytics."""
        return {
            "total_customers": Customer.objects.count(),
            "active_customers": Customer.objects.filter(
                orders__created_at__gte=timezone.now() - timedelta(days=30)
            ).distinct().count(),
            "customer_lifetime_value": self._calculate_clv(),
            "churn_rate": self._calculate_churn_rate(),
            "customer_segments": self._segment_customers(),
            "geographic_distribution": self._geographic_analysis()
        }
    
    def _get_top_products(self, orders):
        """Get top selling products."""
        return OrderItem.objects.filter(
            order__in=orders
        ).values(
            'product__name'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('price')
        ).order_by('-total_sold')[:10]
    
    def _revenue_by_day(self, orders):
        """Calculate daily revenue."""
        from django.db.models import F, DateField
        from django.db.models.functions import Cast
        
        return orders.extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            revenue=Sum('total_amount')
        ).order_by('day')
```

## **3. Analytics Platform API**

```python
from drf_progressive_delivery import MethodProgressiveView

class AnalyticsPlatform(MethodProgressiveView, APIView):
    progressive_chunk_size = 2
    
    def add_meta_data(self, request, **kwargs):
        return {
            "platform": "Analytics Dashboard",
            "version": "2.0.0",
            "user": request.user.username,
            "timezone": str(timezone.get_current_timezone()),
            "features": ["real-time", "historical", "predictive"]
        }
    
    def add_model_data(self, request, **kwargs):
        return [
            {
                "recent_events": EventSerializer(
                    Event.objects.filter(
                        user=request.user
                    ).order_by('-timestamp')[:100],
                    many=True
                ).data
            },
            {
                "user_sessions": SessionSerializer(
                    Session.objects.filter(
                        user=request.user,
                        ended_at__isnull=True
                    ).order_by('-started_at')[:50],
                    many=True
                ).data
            }
        ]
    
    def add_computed_data(self, request, **kwargs):
        return [
            {
                "real_time_metrics": self._get_realtime_metrics(request.user),
                "performance_stats": self._get_performance_stats(request.user)
            },
            {
                "historical_analysis": self._get_historical_analysis(request.user),
                "predictive_insights": self._get_predictive_insights(request.user)
            }
        ]
    
    def _get_realtime_metrics(self, user):
        """Real-time metrics calculation."""
        from datetime import timedelta
        
        last_hour = timezone.now() - timedelta(hours=1)
        
        return {
            "active_users": Session.objects.filter(
                ended_at__isnull=True,
                started_at__gte=last_hour
            ).count(),
            "events_per_minute": Event.objects.filter(
                timestamp__gte=last_hour
            ).count() / 60,
            "error_rate": self._calculate_error_rate(last_hour),
            "response_time": self._calculate_avg_response_time(last_hour)
        }
    
    def _get_historical_analysis(self, user):
        """Historical data analysis."""
        from datetime import timedelta
        
        last_30_days = timezone.now() - timedelta(days=30)
        
        return {
            "total_events": Event.objects.filter(
                timestamp__gte=last_30_days
            ).count(),
            "unique_visitors": Session.objects.filter(
                started_at__gte=last_30_days
            ).values('user').distinct().count(),
            "avg_session_duration": self._calculate_avg_session_duration(last_30_days),
            "bounce_rate": self._calculate_bounce_rate(last_30_days),
            "conversion_funnel": self._calculate_conversion_funnel(last_30_days)
        }
```

## **4. Social Media Dashboard**

```python
from drf_progressive_delivery import DecoratorProgressiveView, progressive_meta, progressive_data

class SocialMediaDashboard(DecoratorProgressiveView, APIView):
    progressive_chunk_size = 2
    
    @progressive_meta
    def platform_meta(self, request, **kwargs):
        return {
            "platform": "Social Media Analytics",
            "user": request.user.username,
            "profile": {
                "followers": request.user.profile.followers.count(),
                "following": request.user.profile.following.count(),
                "posts": request.user.posts.count()
            },
            "timestamp": timezone.now().isoformat()
        }
    
    @progressive_data("recent_posts")
    def get_recent_posts(self, request, **kwargs):
        posts = Post.objects.filter(
            author=request.user
        ).select_related('author').prefetch_related(
            'likes', 'comments'
        ).order_by('-created_at')[:20]
        
        return PostSerializer(posts, many=True).data
    
    @progressive_data("engagement_stats")
    def get_engagement_stats(self, request, **kwargs):
        user_posts = Post.objects.filter(author=request.user)
        
        return {
            "total_likes": Like.objects.filter(
                post__author=request.user
            ).count(),
            "total_comments": Comment.objects.filter(
                post__author=request.user
            ).count(),
            "avg_engagement_rate": self._calculate_engagement_rate(user_posts),
            "best_performing_post": self._get_best_post(user_posts),
            "engagement_by_time": self._engagement_by_time(user_posts)
        }
    
    @progressive_data("followers_analysis")
    def get_followers_analysis(self, request, **kwargs):
        return {
            "follower_growth": self._calculate_follower_growth(request.user),
            "follower_demographics": self._analyze_follower_demographics(request.user),
            "top_followers": self._get_top_followers(request.user),
            "follower_engagement": self._analyze_follower_engagement(request.user)
        }
    
    @progressive_data("content_recommendations")
    def get_content_recommendations(self, request, **kwargs):
        return {
            "trending_topics": self._get_trending_topics(),
            "optimal_posting_times": self._calculate_optimal_times(request.user),
            "hashtag_suggestions": self._suggest_hashtags(request.user),
            "content_ideas": self._generate_content_ideas(request.user)
        }
    
    def _calculate_engagement_rate(self, posts):
        """Calculate average engagement rate."""
        if not posts.exists():
            return 0
        
        total_engagement = 0
        for post in posts:
            likes = post.likes.count()
            comments = post.comments.count()
            views = getattr(post, 'view_count', 1)
            
            if views > 0:
                engagement_rate = ((likes + comments) / views) * 100
                total_engagement += engagement_rate
        
        return total_engagement / posts.count()
```

## **5. Financial Dashboard**

```python
class FinancialDashboard(RegistryProgressiveView, APIView):
    permission_classes = [IsAuthenticated]
    progressive_chunk_size = 2
    
    def get_parts_registry(self):
        registry = ProgressivePartsRegistry()
        
        # Account overview (immediate)
        registry.add_static("account_overview", {
            "account_holder": self.request.user.get_full_name(),
            "account_type": self.request.user.profile.account_type,
            "currency": self.request.user.profile.preferred_currency,
            "last_login": self.request.user.last_login.isoformat() if self.request.user.last_login else None
        })
        
        # Account balances (fast)
        registry.add_function("balances", self._get_balances, lazy=True)
        
        # Recent transactions (moderate)
        registry.add_model(
            "recent_transactions",
            Transaction.objects.filter(
                user=self.request.user
            ).select_related('category').order_by('-timestamp')[:100],
            TransactionSerializer,
            lazy=True
        )
        
        # Spending analytics (expensive)
        registry.add_function("spending_analysis", self._spending_analysis, lazy=True)
        
        # Investment portfolio (very expensive)
        registry.add_function("portfolio_analysis", self._portfolio_analysis, lazy=True)
        
        return registry
    
    def _get_balances(self, request, **kwargs):
        """Get all account balances."""
        accounts = Account.objects.filter(user=request.user)
        
        return {
            "total_balance": float(accounts.aggregate(
                Sum('balance')
            )['balance__sum'] or 0),
            "accounts": [
                {
                    "name": account.name,
                    "type": account.account_type,
                    "balance": float(account.balance),
                    "currency": account.currency
                }
                for account in accounts
            ]
        }
    
    def _spending_analysis(self, request, **kwargs):
        """Analyze spending patterns."""
        from datetime import timedelta
        
        last_30_days = timezone.now() - timedelta(days=30)
        transactions = Transaction.objects.filter(
            user=request.user,
            timestamp__gte=last_30_days,
            amount__lt=0  # Expenses
        )
        
        return {
            "total_spending": float(abs(transactions.aggregate(
                Sum('amount')
            )['amount__sum'] or 0)),
            "spending_by_category": self._spending_by_category(transactions),
            "daily_spending": self._daily_spending(transactions),
            "budget_comparison": self._compare_with_budget(transactions),
            "spending_trends": self._analyze_spending_trends(transactions)
        }
    
    def _portfolio_analysis(self, request, **kwargs):
        """Analyze investment portfolio."""
        investments = Investment.objects.filter(user=request.user)
        
        return {
            "total_portfolio_value": self._calculate_portfolio_value(investments),
            "portfolio_allocation": self._calculate_allocation(investments),
            "performance_metrics": self._calculate_performance(investments),
            "risk_analysis": self._analyze_risk(investments),
            "recommendations": self._generate_investment_recommendations(investments)
        }
```

## **6. Simple Method-Based API**

```python
from drf_progressive_delivery import MethodProgressiveView

class SimpleUserDashboard(MethodProgressiveView, APIView):
    progressive_chunk_size = 1
    
    def add_meta_data(self, request, **kwargs):
        return {
            "user": request.user.username,
            "timestamp": timezone.now().isoformat()
        }
    
    def add_model_data(self, request, **kwargs):
        return [
            {
                "profile": UserProfileSerializer(request.user.profile).data
            },
            {
                "recent_activity": ActivitySerializer(
                    Activity.objects.filter(user=request.user)[:10],
                    many=True
                ).data
            }
        ]
    
    def add_computed_data(self, request, **kwargs):
        return [
            {
                "statistics": {
                    "login_count": request.user.login_logs.count(),
                    "last_active": request.user.last_login.isoformat() if request.user.last_login else None
                }
            }
        ]
```

## **Frontend Integration Examples**

### **React Hook for Progressive Loading**
```javascript
import { useState, useEffect } from 'react';

function useProgressiveData(apiUrl) {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    useEffect(() => {
        let mounted = true;
        
        async function loadData() {
            setLoading(true);
            setError(null);
            
            try {
                let cursor = null;
                const allData = [];
                
                do {
                    const url = cursor ? `${apiUrl}?cursor=${cursor}` : apiUrl;
                    const response = await fetch(url);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    
                    const result = await response.json();
                    
                    if (mounted) {
                        allData.push(...result.results);
                        setData([...allData]);
                    }
                    
                    cursor = result.cursor;
                    
                    // Small delay to show progressive loading
                    if (cursor && mounted) {
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                } while (cursor && mounted);
                
            } catch (err) {
                if (mounted) {
                    setError(err.message);
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }
        
        loadData();
        
        return () => { mounted = false; };
    }, [apiUrl]);
    
    return { data, loading, error };
}

// Usage in component
function Dashboard() {
    const { data, loading, error } = useProgressiveData('/api/dashboard/');
    
    if (error) {
        return <div>Error: {error}</div>;
    }
    
    return (
        <div>
            {data.map((item, index) => {
                const [partName, partData] = Object.entries(item)[0];
                return (
                    <DashboardCard 
                        key={index}
                        title={partName}
                        data={partData}
                    />
                );
            })}
            {loading && <LoadingSpinner />}
        </div>
    );
}
```

### **Vue.js Progressive Loading**
```javascript
export default {
    data() {
        return {
            dashboardData: [],
            loading: false,
            error: null
        };
    },
    
    async mounted() {
        await this.loadDashboard();
    },
    
    methods: {
        async loadDashboard() {
            this.loading = true;
            this.error = null;
            
            try {
                let cursor = null;
                
                do {
                    const url = cursor ? 
                        `/api/dashboard/?cursor=${cursor}` : 
                        '/api/dashboard/';
                    
                    const response = await this.$http.get(url);
                    
                    // Add new data progressively
                    this.dashboardData.push(...response.data.results);
                    
                    cursor = response.data.cursor;
                    
                    // Allow UI to update
                    await this.$nextTick();
                    
                } while (cursor);
                
            } catch (error) {
                this.error = error.message;
            } finally {
                this.loading = false;
            }
        }
    }
};
```

## **Testing Examples**

```python
# test_progressive_apis.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

class ProgressiveAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_progressive_dashboard_loading(self):
        """Test that dashboard loads progressively."""
        # First request
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertIn('cursor', data)
        
        # Should have some results
        self.assertGreater(len(data['results']), 0)
        
        # If there's a cursor, load next chunk
        if data['cursor']:
            response2 = self.client.get(f'/api/dashboard/?cursor={data["cursor"]}')
            self.assertEqual(response2.status_code, 200)
            
            data2 = response2.json()
            self.assertIn('results', data2)
            
            # Should have different results
            self.assertNotEqual(data['results'], data2['results'])
    
    def test_progressive_parts_content(self):
        """Test that expected parts are returned."""
        all_parts = []
        cursor = None
        
        # Load all parts
        while True:
            url = f'/api/dashboard/?cursor={cursor}' if cursor else '/api/dashboard/'
            response = self.client.get(url)
            data = response.json()
            
            all_parts.extend(data['results'])
            cursor = data.get('cursor')
            
            if not cursor:
                break
        
        # Check that we got expected parts
        part_names = []
        for part in all_parts:
            part_names.extend(part.keys())
        
        expected_parts = ['meta', 'recent_orders', 'analytics']
        for expected_part in expected_parts:
            self.assertIn(expected_part, part_names)
```

These examples show real-world usage patterns that Django developers can immediately copy and adapt for their own projects. Each example demonstrates different aspects of the progressive delivery pattern while remaining practical and focused on common use cases. 