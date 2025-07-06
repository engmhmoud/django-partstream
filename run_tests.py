#!/usr/bin/env python
"""
Simple test runner for the progressive delivery package.
"""

import os
import sys
import subprocess


def run_standalone_test():
    """Run the standalone test without Django."""
    print("🧪 Running standalone tests...")
    try:
        subprocess.run([sys.executable, "test_progressive_delivery.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Standalone test failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ test_progressive_delivery.py not found")
        return False


def setup_django_environment():
    """Setup Django environment for testing."""
    print("⚙️  Setting up Django environment...")
    
    # Change to example project directory
    os.chdir("example_project")
    
    try:
        # Run migrations
        print("Running migrations...")
        subprocess.run([sys.executable, "manage.py", "migrate"], check=True)
        
        # Create sample data
        print("Creating sample data...")
        subprocess.run([
            sys.executable, "manage.py", "test_progressive", 
            "--create-data"
        ], check=True)
        
        # Test progressive API
        print("Testing progressive API...")
        subprocess.run([
            sys.executable, "manage.py", "test_progressive", 
            "--test-api"
        ], check=True)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Django setup failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ Django manage.py not found")
        return False


def start_django_server():
    """Start the Django development server."""
    print("🚀 Starting Django development server...")
    
    try:
        os.chdir("example_project")
        subprocess.run([sys.executable, "manage.py", "runserver", "8000"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")


def main():
    """Main test runner."""
    print("🎯 DRF Progressive Delivery Test Suite")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "standalone":
            run_standalone_test()
        elif command == "django":
            setup_django_environment()
        elif command == "server":
            start_django_server()
        else:
            print(f"Unknown command: {command}")
            show_help()
    else:
        # Run all tests
        print("Running all tests...")
        
        # 1. Run standalone tests
        if run_standalone_test():
            print("✅ Standalone tests passed!")
        else:
            print("❌ Standalone tests failed!")
            return
        
        # 2. Setup Django and run tests
        if setup_django_environment():
            print("✅ Django tests passed!")
        else:
            print("❌ Django tests failed!")
            return
        
        print("\n🎉 All tests completed successfully!")
        print("\nNext steps:")
        print("1. Run 'python run_tests.py server' to start the Django server")
        print("2. Visit http://127.0.0.1:8000/api/order-analytics/ to test the API")


def show_help():
    """Show help message."""
    print("Usage: python run_tests.py [command]")
    print("\nCommands:")
    print("  standalone  - Run standalone tests only")
    print("  django      - Setup Django and run Django tests")
    print("  server      - Start Django development server")
    print("  (no args)   - Run all tests")


if __name__ == "__main__":
    main() 