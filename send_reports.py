import streamlit as st
import pandas as pd
import datetime
import time
import webbrowser
import pyautogui
import pyperclip
import re
import urllib.parse
from modules.db import admin_supabase

st.set_page_config(
    page_title="Parent Reports",
    page_icon="✨",
    layout="wide"
)

st.title("✨ Premium Parent Reports")
st.markdown("Deliver ₹1000/month value with honest, actionable insights")

# Get pending reports
pending = admin_supabase.table("student_answers")\
    .select("*, profiles(*)")\
    .eq("reported", False)\
    .order("submitted_at", desc=True)\
    .execute()

if not pending.data:
    st.success("✅ No pending reports! All caught up!")
    st.stop()

# Group by student
unique_reports = {}
for ans in pending.data:
    student_id = ans.get("student_id")
    if student_id not in unique_reports:
        unique_reports[student_id] = ans

reports = list(unique_reports.values())

st.info(f"📬 {len(pending.data)} submissions → {len(reports)} unique daily reports")

# ============================================
# PREMIUM ANALYTICS FUNCTIONS
# ============================================

def format_full_answer(thinking_answer):
    """Format full answer cleanly for WhatsApp"""
    lines = thinking_answer.split('\n')
    formatted = []
    for line in lines:
        if line.strip():
            clean_line = line.strip()
            if "(Score:" in clean_line:
                clean_line = clean_line.split("(Score:")[0].strip()
            formatted.append(clean_line)
    return "\n".join(formatted)

def extract_main_answer_preview(thinking_answer):
    """Extract just the first meaningful sentence for preview"""
    lines = thinking_answer.split('\n')
    for line in lines:
        if line.startswith("Q1:"):
            answer = line.replace("Q1:", "").strip()
            if "(Score:" in answer:
                answer = answer.split("(Score:")[0].strip()
            if len(answer) > 80:
                answer = answer[:77] + "..."
            return answer
    return thinking_answer[:80] + "..."

def analyze_answer_quality(answer, score, topic, child_name):
    """Deep analysis of answer quality"""
    answer_lower = answer.lower()
    word_count = len(answer.split())
    
    # Check for swear words
    swear_words = ["shit", "damn", "hell", "fuck", "bloody", "crap"]
    has_swear = any(word in answer_lower for word in swear_words)
    
    # Check for explanation quality
    explanation_words = ["because", "since", "example", "like", "means", "happens", "when", "then", "so"]
    has_explanation = any(word in answer_lower for word in explanation_words)
    
    # Determine insight
    insights = []
    
    if has_swear:
        insights.append(f"• {child_name} understands the basic idea but used casual/inappropriate language. A gentle conversation about respectful language would help.")
    
    if word_count < 8:
        insights.append(f"• The answer was very brief — just {word_count} {'word' if word_count == 1 else 'words'}. {child_name} knows the concept but didn't explain it properly.")
    
    if not has_explanation and score < 7:
        insights.append("• No explanation given — just stated a fact without showing understanding.")
    
    if score >= 7 and word_count > 15:
        insights.append("• Good effort! Your child tried to explain properly with detail.")
    
    if not insights:
        if score >= 7:
            insights.append(f"• {child_name} understood this well! They can explain the key ideas.")
        elif score >= 4:
            insights.append("• Your child has the basic idea but needs help connecting the dots.")
        else:
            insights.append("• Your child is familiar with the topic but struggling to explain it. A different approach might help.")
    
    return insights, has_swear, word_count

def get_honest_score_interpretation(score, has_swear):
    """What the score actually means (honest)"""
    if score >= 9:
        return "🌟 MASTERED — Can explain clearly with examples"
    elif score >= 7:
        return "📘 GOOD UNDERSTANDING — Gets the main ideas, needs depth"
    elif score >= 5:
        return "📚 BASIC UNDERSTANDING — Knows the surface, needs help connecting"
    elif score >= 3:
        return "⚠️ PARTIAL UNDERSTANDING — Recognizes the topic, can't explain well"
    else:
        if has_swear:
            return "💪 NEEDS SUPPORT — Understood the idea but didn't engage seriously"
        return "💪 NEEDS SUPPORT — Familiar with the term, struggling with the concept"

def get_parent_actions(score, has_swear, topic, answer, word_count):
    """Specific, actionable steps"""
    actions = []
    answer_lower = answer.lower()
    
    if has_swear:
        actions.append("🗣️ Have a calm 2-minute chat: 'In learning, we use respectful words. Let's try explaining things properly.'")
    
    if score < 5:
        actions.append(f"🎬 Watch a short 5-minute video about {topic} together")
        actions.append(f"🗣️ Ask: 'If you had to explain {topic} to a friend, what would you say?'")
    
    if word_count < 8 and score < 7:
        actions.append(f"📝 Encourage: 'Can you write one more sentence about {topic}? What else do you remember?'")
    
    if score >= 7:
        actions.append(f"🌟 Challenge: 'Can you teach me something new about {topic}?'")
    
    if "idk" in answer_lower or "don't know" in answer_lower:
        actions.append(f"💬 Ask: 'What part of {topic} do you remember from class? Even one thing.'")
    
    if not actions:
        actions.append(f"🎯 Ask: 'What was the most interesting thing you learned about {topic}?'")
    
    return actions[:3]

def get_what_this_means(answer, score, topic):
    """Translate answer into what it reveals about learning"""
    answer_lower = answer.lower()
    
    if "shit" in answer_lower or "damn" in answer_lower:
        return f"Your child understood the core idea but used casual language instead of explaining properly. The knowledge is there — the effort wasn't."
    
    if "idk" in answer_lower or "don't know" in answer_lower:
        return f"Your child isn't confident about {topic} yet. Try a video or real-life example."
    
    if len(answer.split()) < 8:
        return f"Your child knows the basic idea but couldn't explain it in detail. A quick review will help."
    
    if score >= 7:
        return f"Your child understood this well! They can explain the concept and are ready for deeper questions."
    
    return f"Your child has the right idea but needs help organizing their thoughts. Ask them to give examples."

def get_fun_fact(topic):
    """Engaging, shareable facts"""
    facts = {
        "fractions": "Ancient Egyptians used fractions 4,000 years ago — only unit fractions like 1/2, 1/3!",
        "photosynthesis": "A single tree produces enough oxygen for 4 people every single day!",
        "water cycle": "The water you drink could have been drunk by dinosaurs!",
        "electricity": "Lightning strikes Earth about 100 times every second!",
        "reproduction": "A single bacteria can become 16 million in just 24 hours!",
        "traders": "The world's oldest known market is in Turkey, dating back 9,000 years!",
        "towns": "The first cities appeared about 6,000 years ago in Mesopotamia!",
        "flora": "There are over 390,000 known plant species on Earth!",
        "fauna": "There are over 8.7 million animal species on Earth!",
    }
    topic_lower = topic.lower()
    for key, fact in facts.items():
        if key in topic_lower:
            return fact
    return "Every day is a chance to learn something new!"

# ============================================
# AUTO-SEND SECTION
# ============================================
st.markdown("---")

st.warning("""
⚠️ **Auto-Send Instructions:**
1. Keep **WhatsApp Web** open in Chrome
2. Do NOT touch mouse/keyboard during sending
3. Make sure your phone is connected
""")

# Select reports to send
st.subheader("📋 Select Reports to Send")

selected_reports = []
for idx, ans in enumerate(reports):
    profile = ans.get("profiles", {})
    child_name = profile.get("child_name", "Child")
    parent_phone = profile.get("parent_phone", "")
    thinking_score = ans.get("thinking_score", 0)
    topic = ans.get("topic", "Unknown")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        selected = st.checkbox("", key=f"select_{idx}")
    with col2:
        st.markdown(f"**{child_name}** | Score: {thinking_score}/10 | {topic} | 📞 {parent_phone}")
    
    if selected:
        selected_reports.append(ans)

if selected_reports:
    if st.button(f"🚀 AUTO-SEND {len(selected_reports)} PREMIUM REPORT(S)", type="primary", use_container_width=True):
        
        st.info("Starting in 10 seconds...")
        countdown = st.empty()
        for i in range(10, 0, -1):
            countdown.info(f"Starting in {i} seconds...")
            time.sleep(1)
        countdown.empty()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        for idx, ans in enumerate(selected_reports):
            profile = ans.get("profiles", {})
            
            child_name = profile.get("child_name", "Child")
            parent_phone = profile.get("parent_phone", "")
            thinking_answer = ans.get("thinking_answer", "No answer")
            thinking_score = ans.get("thinking_score", 0)
            topic = ans.get("topic", "Learning Session")
            
            # Format date
            submitted_date = ans.get("submitted_at", datetime.datetime.now().isoformat())
            try:
                date_obj = datetime.datetime.fromisoformat(submitted_date.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%B %d, %Y")
                day_name = date_obj.strftime("%A")
            except:
                formatted_date = datetime.datetime.now().strftime("%B %d, %Y")
                day_name = datetime.datetime.now().strftime("%A")
            
            # Extract answers
            full_answer = format_full_answer(thinking_answer)
            answer_preview = extract_main_answer_preview(thinking_answer)
            
            # Generate premium insights
            insights, has_swear, word_count = analyze_answer_quality(answer_preview, thinking_score, topic, child_name)
            score_interpretation = get_honest_score_interpretation(thinking_score, has_swear)
            what_this_means = get_what_this_means(answer_preview, thinking_score, topic)
            parent_actions = get_parent_actions(thinking_score, has_swear, topic, answer_preview, word_count)
            fun_fact = get_fun_fact(topic)
            
            # Build message (WhatsApp-friendly, no HTML)
            message = f"""
✨ *DAILY LEARNING INSIGHTS* ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👧 *{child_name}* · {day_name}, {formatted_date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 *Topic*
{topic}

🎯 *Score* · {thinking_score}/10
{score_interpretation}

✍️ *What They Wrote*
"{answer_preview}"

📝 *Complete Answer*
{full_answer}

💡 *What This Tells Us*
{what_this_means}

📊 *Insights*
"""
            
            for insight in insights:
                message += f"\n{insight}"
            
            message += f"""

🎯 *How to Help*
"""
            
            for action in parent_actions:
                message += f"\n{action}"
            
            message += f"""

⭐ *Did You Know?*
{fun_fact}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*Daily Learning* · Honest feedback for real progress
"""
            
            if not parent_phone:
                results.append({"Child": child_name, "Status": "❌ No phone number"})
                status_text.text(f"⚠️ No phone for {child_name}")
            else:
                status_text.text(f"📤 Sending to {child_name}...")
                
                try:
                    clean_phone = re.sub(r'[^\d]', '', parent_phone)
                    encoded_message = urllib.parse.quote(message)
                    whatsapp_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_message}"
                    webbrowser.open(whatsapp_url)
                    time.sleep(14)
                    pyautogui.press('enter')
                    time.sleep(2)
                    pyautogui.press('enter')
                    time.sleep(2)
                    pyautogui.hotkey('ctrl', 'w')
                    time.sleep(1)
                    
                    admin_supabase.table("student_answers")\
                        .update({"reported": True})\
                        .eq("id", ans["id"])\
                        .execute()
                    results.append({"Child": child_name, "Status": "✅ Sent"})
                    st.success(f"✅ Sent to {child_name}")
                except Exception as e:
                    results.append({"Child": child_name, "Status": "❌ Failed"})
                    st.error(f"❌ Failed to send to {child_name}")
            
            progress_bar.progress((idx + 1) / len(selected_reports))
            time.sleep(2)
        
        # Show summary
        st.markdown("---")
        st.subheader("📊 Sending Summary")
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)
        success_count = len([r for r in results if "✅" in r["Status"]])
        st.success(f"🎉 Sent {success_count}/{len(selected_reports)} reports!")

# ============================================
# MANUAL COPY-PASTE MODE (BACKUP)
# ============================================
st.markdown("---")
st.subheader("📋 Manual Copy-Paste Mode")

all_messages = []
batch_data = []

for idx, ans in enumerate(reports):
    profile = ans.get("profiles", {})
    
    child_name = profile.get("child_name", "Child")
    parent_phone = profile.get("parent_phone", "No phone")
    thinking_answer = ans.get("thinking_answer", "No answer")
    thinking_score = ans.get("thinking_score", 0)
    topic = ans.get("topic", "Learning Session")
    
    submitted_date = ans.get("submitted_at", datetime.datetime.now().isoformat())
    try:
        date_obj = datetime.datetime.fromisoformat(submitted_date.replace('Z', '+00:00'))
        formatted_date = date_obj.strftime("%B %d, %Y")
        day_name = date_obj.strftime("%A")
    except:
        formatted_date = datetime.datetime.now().strftime("%B %d, %Y")
        day_name = datetime.datetime.now().strftime("%A")
    
    full_answer = format_full_answer(thinking_answer)
    answer_preview = extract_main_answer_preview(thinking_answer)
    insights, has_swear, word_count = analyze_answer_quality(answer_preview, thinking_score, topic, child_name)
    score_interpretation = get_honest_score_interpretation(thinking_score, has_swear)
    what_this_means = get_what_this_means(answer_preview, thinking_score, topic)
    parent_actions = get_parent_actions(thinking_score, has_swear, topic, answer_preview, word_count)
    fun_fact = get_fun_fact(topic)
    
    message = f"""
✨ *DAILY LEARNING INSIGHTS* ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👧 *{child_name}* · {day_name}, {formatted_date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 *Topic*
{topic}

🎯 *Score* · {thinking_score}/10
{score_interpretation}

✍️ *What They Wrote*
"{answer_preview}"

📝 *Complete Answer*
{full_answer}

💡 *What This Tells Us*
{what_this_means}

📊 *Insights*
"""
    
    for insight in insights:
        message += f"\n{insight}"
    
    message += f"""

🎯 *How to Help*
"""
    
    for action in parent_actions:
        message += f"\n{action}"
    
    message += f"""

⭐ *Did You Know?*
{fun_fact}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*Daily Learning* · Honest feedback for real progress
"""
    
    all_messages.append(message)
    batch_data.append({
        "Child": child_name,
        "Phone": parent_phone,
        "Topic": topic,
        "Score": thinking_score,
        "Date": formatted_date,
        "Status": "⏳"
    })
    
    with st.expander(f"✨ {child_name} | {topic} | Score: {thinking_score}/10", expanded=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.text_area("Premium WhatsApp Message", message.strip(), height=600, key=f"manual_msg_{idx}", label_visibility="collapsed")
        with col2:
            st.markdown(f"**📞 Phone:** `{parent_phone}`")
            st.markdown(f"**📊 Score:** {thinking_score}/10")
            if st.button(f"✅ Mark Sent", key=f"manual_mark_{idx}", use_container_width=True):
                admin_supabase.table("student_answers").update({"reported": True}).eq("id", ans["id"]).execute()
                st.success(f"✅ Marked {child_name}")
                st.rerun()

# Batch copy
col1, col2 = st.columns(2)
with col1:
    if st.button("📋 Copy ALL Messages (Manual)", use_container_width=True):
        full_text = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n".join(all_messages)
        st.code(full_text, language="text")
with col2:
    if st.button("✅ Mark ALL as Sent", use_container_width=True):
        for ans in reports:
            admin_supabase.table("student_answers").update({"reported": True}).eq("id", ans["id"]).execute()
        st.success(f"✅ Marked all {len(reports)} reports as sent!")
        st.rerun()

# Stats
st.markdown("---")
col1, col2, col3 = st.columns(3)
avg_score = sum(r.get("thinking_score", 0) for r in reports) / len(reports) if reports else 0
high_scores = len([r for r in reports if r.get("thinking_score", 0) >= 7])
needs_help = len([r for r in reports if r.get("thinking_score", 0) < 5])

with col1: st.metric("📊 Avg Score", f"{avg_score:.1f}/10")
with col2: st.metric("🌟 Good Scores (7+)", high_scores)
with col3: st.metric("💪 Needs Support", needs_help)

st.info("✨ **Premium reports include:** Honest score interpretation, deep insights, actionable guidance, and complete answers")