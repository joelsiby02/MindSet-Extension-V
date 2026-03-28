import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
service_key = os.getenv("SUPABASE_SERVICE_KEY")

# Validate environment variables
if not url:
    raise ValueError("SUPABASE_URL is not set in .env")
if not key:
    raise ValueError("SUPABASE_KEY is not set in .env")

# Public client (for main app)
supabase: Client = create_client(url, key)

# Admin client (for scripts, optional)
admin_supabase: Client = create_client(url, service_key) if service_key else None

print(f"Supabase initialized with URL: {url}")  # Debug line