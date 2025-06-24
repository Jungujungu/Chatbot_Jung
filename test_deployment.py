#!/usr/bin/env python3
"""
Deployment test script for Amazon Keyword Performance AI Chatbot.
Run this after deployment to verify everything is working.
"""

import requests
import json
import sys
import os
from datetime import datetime

def test_backend_health(api_url):
    """Test backend health endpoint"""
    print(f"🔍 Testing backend health at {api_url}")
    
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend health check passed")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Snowflake: {'✅' if data.get('snowflake_connected') else '❌'}")
            print(f"   Claude: {'✅' if data.get('claude_connected') else '❌'}")
            
            if data.get('data_summary'):
                summary = data['data_summary']
                print(f"   Total Keywords: {summary.get('TOTAL_KEYWORDS', 'N/A'):,}")
                print(f"   Total Impressions: {summary.get('TOTAL_IMPRESSIONS', 'N/A'):,}")
            
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Backend health check error: {e}")
        return False

def test_chat_endpoint(api_url):
    """Test chat endpoint"""
    print(f"\n💬 Testing chat endpoint at {api_url}")
    
    try:
        response = requests.post(
            f"{api_url}/chat",
            json={"message": "Show me top 5 keywords by purchases"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Chat endpoint test passed")
            print(f"   Response length: {len(data.get('response', ''))} characters")
            
            if data.get('sql_query'):
                print(f"   SQL generated: {data['sql_query'][:100]}...")
            
            if data.get('data'):
                print(f"   Data returned: {len(data['data'])} rows")
            
            return True
        else:
            print(f"❌ Chat endpoint test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chat endpoint test error: {e}")
        return False

def test_summary_endpoint(api_url):
    """Test summary endpoint"""
    print(f"\n📊 Testing summary endpoint at {api_url}")
    
    try:
        response = requests.get(f"{api_url}/summary", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Summary endpoint test passed")
            print(f"   Total Keywords: {data.get('TOTAL_KEYWORDS', 'N/A'):,}")
            print(f"   Total Impressions: {data.get('TOTAL_IMPRESSIONS', 'N/A'):,}")
            return True
        else:
            print(f"❌ Summary endpoint test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Summary endpoint test error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Amazon Keyword Performance AI Chatbot - Deployment Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Get API URL from environment or use default
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    if not api_url.startswith(("http://", "https://")):
        api_url = f"http://{api_url}"
    
    print(f"Testing API at: {api_url}")
    print("=" * 60)
    
    # Run tests
    tests = [
        ("Backend Health", lambda: test_backend_health(api_url)),
        ("Chat Endpoint", lambda: test_chat_endpoint(api_url)),
        ("Summary Endpoint", lambda: test_summary_endpoint(api_url))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your deployment is working correctly.")
        return True
    else:
        print("\n⚠️ Some tests failed. Please check your deployment configuration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 