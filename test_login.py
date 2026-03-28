# test_auth_direct.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Test login via REST API
response = requests.post(
    f"{url}/auth/v1/token?grant_type=password",
    headers={
        "apikey": key,
        "Content-Type": "application/json"
    },
    json={
        "email": "joelag1235@gmail.com",
        "password": "test123456"
    }
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✅ Login successful!")
    print(f"User ID: {response.json()['user']['id']}")
else:
    print(f"❌ Login failed: {response.text}")