import streamlit as st
from modules.db import admin_supabase  # using service role for full access
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
from_whatsapp = os.getenv("TWILIO_WHATSAPP_FROM")

st.title("WhatsApp Report Sender")
st.write("Click the button to send all unreported reports.")

if st.button("Send Pending Reports"):
    # Fetch unreported answers
    answers = admin_supabase.table("student_answers").select("*, profiles(*), daily_assignments(*)")\
        .eq("reported", False).execute()
    if not answers.data:
        st.info("No pending reports.")
    else:
        for ans in answers.data:
            profile = ans["profiles"]
            parent_phone = profile["parent_phone"]
            child_name = profile["child_name"]
            assignment = ans["daily_assignments"]
            message = f"""
📚 Daily Report for {child_name} – {ans['submitted_at'][:10]}

✅ Studied: Yes
📖 Topic: {assignment['topic']}
🎯 Thinking Answer Score: {ans['thinking_score']}/10
💬 Child's Answer: {ans['thinking_answer'][:150]}...
⚠️ Weak area: {"Needs improvement" if ans['thinking_score'] < 7 else "Good"}
📊 Mock Test: {ans['mock_test_answer'] or "Not evaluated"}

💡 Did You Know? {assignment['gk_fact']}
"""
            try:
                twilio_client.messages.create(
                    body=message,
                    from_=from_whatsapp,
                    to=f"whatsapp:{parent_phone}"
                )
                # Mark as reported
                admin_supabase.table("student_answers").update({"reported": True}).eq("id", ans["id"]).execute()
                st.success(f"Sent to {parent_phone}")
            except Exception as e:
                st.error(f"Failed for {parent_phone}: {e}")