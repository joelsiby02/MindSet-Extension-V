from modules.db import supabase

def log_api_call(api_name, input_tokens, output_tokens, cost_usd, user_id=None):
    try:
        supabase.table("api_logs").insert({
            "api_name": api_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "user_id": user_id
        }).execute()
    except Exception as e:
        print(f"Failed to log API call: {e}")