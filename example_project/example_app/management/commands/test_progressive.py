"""
Django management command to test progressive delivery functionality.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from example_app.models import Order, Product
from decimal import Decimal
import json


class Command(BaseCommand):
    help = 'Test progressive delivery functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-data',
            action='store_true',
            help='Create sample data for testing',
        )
        parser.add_argument(
            '--test-api',
            action='store_true',
            help='Test the progressive API endpoints',
        )

    def handle(self, *args, **options):
        if options['create_data']:
            self.create_sample_data()
        
        if options['test_api']:
            self.test_progressive_api()

    def create_sample_data(self):
        """Create sample data for testing."""
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))
        
        # Create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Create sample products
        products_data = [
            ('Laptop', 999.99, 10),
            ('Mouse', 29.99, 50),
            ('Keyboard', 79.99, 25),
            ('Monitor', 299.99, 8),
            ('Webcam', 89.99, 15),
        ]
        
        for name, price, stock in products_data:
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'price': Decimal(str(price)),
                    'stock': stock
                }
            )
            if created:
                self.stdout.write(f'Created product: {name}')
        
        # Create sample orders
        orders_data = [
            (Decimal('99.99'), 'completed'),
            (Decimal('199.99'), 'pending'),
            (Decimal('299.99'), 'completed'),
            (Decimal('49.99'), 'cancelled'),
            (Decimal('399.99'), 'completed'),
        ]
        
        for amount, status in orders_data:
            order, created = Order.objects.get_or_create(
                user=user,
                total_amount=amount,
                status=status
            )
            if created:
                self.stdout.write(f'Created order: {amount} ({status})')
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))

    def test_progressive_api(self):
        """Test the progressive API functionality."""
        self.stdout.write(self.style.SUCCESS('Testing progressive API...'))
        
        # Mock request class
        class MockRequest:
            def __init__(self, cursor=None):
                self.GET = {'cursor': cursor} if cursor else {}
                self.user = User.objects.first()
        
        # Import and test the view
        from example_app.views import OrderAnalyticsView
        
        view = OrderAnalyticsView()
        
        # Test first request
        self.stdout.write('Testing first request (no cursor)...')
        request1 = MockRequest()
        response1 = view.get_progressive_response(request1)
        
        self.stdout.write(f'Response status: {response1.status_code}')
        data1 = response1.data
        
        self.stdout.write(f'Results count: {len(data1.get("results", []))}')
        self.stdout.write(f'Cursor present: {data1.get("cursor") is not None}')
        
        # Test second request with cursor
        if data1.get('cursor'):
            self.stdout.write('\nTesting second request (with cursor)...')
            request2 = MockRequest(data1['cursor'])
            response2 = view.get_progressive_response(request2)
            
            data2 = response2.data
            self.stdout.write(f'Results count: {len(data2.get("results", []))}')
            self.stdout.write(f'Cursor present: {data2.get("cursor") is not None}')
            
            # Continue until no more cursors
            cursor = data2.get('cursor')
            request_count = 2
            
            while cursor:
                request_count += 1
                self.stdout.write(f'\nTesting request {request_count} (with cursor)...')
                
                request = MockRequest(cursor)
                response = view.get_progressive_response(request)
                
                data = response.data
                self.stdout.write(f'Results count: {len(data.get("results", []))}')
                
                cursor = data.get('cursor')
                self.stdout.write(f'Cursor present: {cursor is not None}')
                
                if request_count > 10:  # Safety break
                    break
        
        self.stdout.write(self.style.SUCCESS('Progressive API test completed!')) 