import sys
import getpass
import requests
import json
from urllib.parse import urljoin

BASE_URL = "https://malchalab.com"

# Common dj-rest-auth login endpoints
ENDPOINTS = [
    "/dj-rest-auth/login/",
    "/api/auth/login/",
    "/api/login/",
    "/accounts/login/",
    "/auth/login/",
]

def check_cookie(username, password):
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": BASE_URL + "/"
    })

    payload = {
        "username": username,
        "password": password,
        # dj-rest-auth uses 'email' sometimes, handle both if needed or let user retry
        "email": username if "@" in username else None 
    }
    # Clean up None values
    payload = {k: v for k, v in payload.items() if v is not None}

    print(f"\nScanning endpoints on {BASE_URL}...")

    for path in ENDPOINTS:
        url = urljoin(BASE_URL, path)
        print(f"Trying {url} ... ", end="", flush=True)
        
        try:
            response = session.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                print("SUCCESS! (200 OK)")
                print("-" * 60)
                
                # Check Cookies
                cookies = response.cookies
                access_token = None
                
                # 'requests' CookieJar automatically handles domains, 
                # but we want to see the RAW Set-Cookie header to verify 'Domain' attribute.
                # However, requests hides raw headers for merged cookies. 
                # We check 'response.headers' for 'Set-Cookie'.
                
                # Note: 'requests' merges multiple Set-Cookie headers into one? 
                # No, response.headers['Set-Cookie'] returns one string (merged) or list?
                # It behaves differently versions. 
                # Using 'response.raw.headers' is safer? No.
                
                # Let's inspect session cookies
                found_token = False
                for cookie in session.cookies:
                    if cookie.name == "malcha-access-token":
                        found_token = True
                        print(f"[Cookie Found] {cookie.name}")
                        print(f"   Value: {cookie.value[:20]}...")
                        print(f"   Domain: {cookie.domain}")
                        print(f"   Path: {cookie.path}")
                        print(f"   Secure: {cookie.secure}")
                        
                        if cookie.domain == ".malchalab.com":
                            print("\n✅ PASS: Domain is correctly set to '.malchalab.com'")
                        else:
                            print(f"\n❌ FAIL: Domain is '{cookie.domain}'. It MUST be '.malchalab.com'")
                
                if not found_token:
                    print("\n❌ FAIL: 'malcha-access-token' cookie NOT received.")
                    print("Raw Set-Cookie Headers:")
                    print(json.dumps(dict(response.headers), indent=2))
                
                print("-" * 60)
                return True
                
            elif response.status_code == 400:
                # Login failed (wrong credentials)
                print("Failed (400 Bad Request). Check ID/PW.")
                print(response.text)
                return False
                
            else:
                print(f"Status {response.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")

    print("\nCould not find a valid login endpoint or login failed.")
    return False

if __name__ == "__main__":
    print("=== Malcha Login Cookie Verifier ===")
    print("Checks if the login cookie has the correct Domain attribute for SSO.\n")
    
    username = input("Username (or Email): ").strip()
    password = getpass.getpass("Password: ").strip()
    
    if not username or not password:
        print("Username/Password required.")
        sys.exit(1)
        
    check_cookie(username, password)
