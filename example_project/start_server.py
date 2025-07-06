#!/usr/bin/env python
"""
Simple server startup script for the example project.
"""

import os
import sys
import subprocess


def main():
    """Start the Django server with setup."""
    print("🚀 Starting Django Progressive Delivery Server")
    print("=" * 50)
    
    try:
        # Run migrations
        print("📦 Running migrations...")
        subprocess.run([sys.executable, "manage.py", "migrate"], check=True)
        
        # Create sample data
        print("📊 Creating sample data...")
        result = subprocess.run([
            sys.executable, "manage.py", "test_progressive", "--create-data"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Sample data created")
        else:
            print("ℹ️  Sample data may already exist")
        
        # Start server
        print("🌟 Starting server on http://127.0.0.1:8000")
        print("Available endpoints:")
        print("  - http://127.0.0.1:8000/api/order-analytics/")
        print("  - http://127.0.0.1:8000/api/simple-progressive/")
        print("  - http://127.0.0.1:8000/api/reports/")
        print("  - http://127.0.0.1:8000/api/reports/comprehensive_report/")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 50)
        
        subprocess.run([sys.executable, "manage.py", "runserver", "8000"], check=True)
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main() 