#!/usr/bin/env python
"""
HTTP client to test the progressive delivery API endpoints.
"""

import requests
import json
import time
from urllib.parse import urljoin


class ProgressiveAPIClient:
    """Client for testing progressive delivery API."""
    
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def fetch_progressive_data(self, endpoint, max_requests=10):
        """
        Fetch all data from a progressive delivery endpoint.
        
        Args:
            endpoint: API endpoint path
            max_requests: Maximum number of requests to prevent infinite loops
            
        Returns:
            List of all results
        """
        print(f"🔄 Fetching data from: {endpoint}")
        print("-" * 50)
        
        url = urljoin(self.base_url, endpoint)
        all_results = []
        cursor = None
        request_count = 0
        
        while request_count < max_requests:
            request_count += 1
            
            # Build request parameters
            params = {}
            if cursor:
                params['cursor'] = cursor
            
            print(f"📡 Request {request_count}:")
            print(f"   URL: {url}")
            if cursor:
                print(f"   Cursor: {cursor[:50]}...")
            
            try:
                # Make request
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Display response info
                print(f"   Status: {response.status_code}")
                print(f"   Parts received: {len(data.get('results', []))}")
                
                # Show part names
                for i, result in enumerate(data.get('results', [])):
                    if isinstance(result, dict):
                        part_names = list(result.keys())
                        print(f"     Part {i+1}: {part_names}")
                
                # Add to results
                all_results.extend(data.get('results', []))
                
                # Get cursor for next request
                cursor = data.get('cursor')
                print(f"   Next cursor: {'Yes' if cursor else 'No (end of data)'}")
                
                if not cursor:
                    break
                
                # Small delay between requests
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Request failed: {e}")
                break
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {e}")
                break
            
            print()
        
        print(f"✅ Complete! Total requests: {request_count}")
        print(f"Total parts received: {len(all_results)}")
        
        return all_results
    
    def test_endpoints(self):
        """Test all available progressive delivery endpoints."""
        endpoints = [
            "/api/order-analytics/",
            "/api/simple-progressive/",
            "/api/reports/",
            "/api/reports/comprehensive_report/",
        ]
        
        print("🎯 Testing Progressive Delivery API Endpoints")
        print("=" * 60)
        
        for endpoint in endpoints:
            print(f"\n🔍 Testing endpoint: {endpoint}")
            try:
                results = self.fetch_progressive_data(endpoint)
                print(f"✅ {endpoint} - Success ({len(results)} parts)")
            except Exception as e:
                print(f"❌ {endpoint} - Failed: {e}")
            
            print("\n" + "=" * 60)
    
    def interactive_test(self):
        """Interactive testing mode."""
        print("🎮 Interactive Progressive Delivery Test")
        print("=" * 50)
        
        while True:
            print("\nAvailable endpoints:")
            print("1. /api/order-analytics/")
            print("2. /api/simple-progressive/")
            print("3. /api/reports/")
            print("4. /api/reports/comprehensive_report/")
            print("5. Custom endpoint")
            print("0. Exit")
            
            choice = input("\nEnter your choice (0-5): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.fetch_progressive_data("/api/order-analytics/")
            elif choice == "2":
                self.fetch_progressive_data("/api/simple-progressive/")
            elif choice == "3":
                self.fetch_progressive_data("/api/reports/")
            elif choice == "4":
                self.fetch_progressive_data("/api/reports/comprehensive_report/")
            elif choice == "5":
                endpoint = input("Enter endpoint path (e.g., /api/my-endpoint/): ").strip()
                if endpoint:
                    self.fetch_progressive_data(endpoint)
            else:
                print("Invalid choice. Please try again.")


def main():
    """Main function."""
    client = ProgressiveAPIClient()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            client.test_endpoints()
        elif command == "interactive":
            client.interactive_test()
        elif command.startswith("/"):
            # Custom endpoint
            client.fetch_progressive_data(command)
        else:
            print(f"Unknown command: {command}")
            show_help()
    else:
        # Default: test all endpoints
        client.test_endpoints()


def show_help():
    """Show help message."""
    print("Usage: python test_client.py [command]")
    print("\nCommands:")
    print("  test        - Test all progressive delivery endpoints")
    print("  interactive - Interactive testing mode")
    print("  /endpoint   - Test specific endpoint")
    print("  (no args)   - Test all endpoints")
    print("\nExamples:")
    print("  python test_client.py test")
    print("  python test_client.py interactive")
    print("  python test_client.py /api/order-analytics/")


if __name__ == "__main__":
    import sys
    main() 