import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# For admin operations (service role)
service_key = os.getenv("SUPABASE_SERVICE_KEY")
admin_supabase: Client = create_client(url, service_key) if service_key else None