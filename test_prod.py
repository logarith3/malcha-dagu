import requests
import json

# Test production API
url = "https://malchalab.com/dagu/api/search/"
params = {"q": "ds-1"}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Total Count: {data.get('total_count', 'N/A')}")
    print(f"User Items Count: {len(data.get('user_items', []))}")
    print(f"Naver Items Count: {len(data.get('naver_items', []))}")
    
    print("\n=== User Items ===")
    for item in data.get('user_items', [])[:3]:
        print(f"  ID: {item.get('id')}")
        print(f"  Title: {item.get('title')}")
        print(f"  lprice: {item.get('lprice')}")
        print(f"  source: {item.get('source')}")
        print("  ---")
        
except Exception as e:
    print(f"ERROR: {e}")
