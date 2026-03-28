import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"URL: {url}")
print(f"Key: {key[:20]}...")  # Show first 20 chars only

try:
    supabase = create_client(url, key)
    
    # Test query
    response = supabase.table("profiles").select("*").limit(1).execute()
    print("✅ Connection successful!")
    print(f"Response: {response.data}")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")