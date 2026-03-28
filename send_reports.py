import streamlit as st
import pandas as pd
import datetime
import random
from modules.db import admin_supabase

st.set_page_config(
    page_title="Parent Reports",
    page_icon="📱",
    layout="wide"
)

st.title("📱 Parent Reports")
st.markdown("Send daily learning reports to parents")

# Get pending reports
pending = admin_supabase.table("student_answers")\
    .select("*, profiles(*), daily_assignments(*)")\
    .eq("reported", False)\
    .order("submitted_at", desc=True)\
    .execute()

if not pending.data:
    st.success("✅ No pending reports! All caught up!")
    st.stop()

# Group by student to get only latest per day
unique_reports = {}
for ans in pending.data:
    student_id = ans.get("student_id")
    if student_id not in unique_reports:
        unique_reports[student_id] = ans

reports = list(unique_reports.values())

st.info(f"📬 {len(pending.data)} submissions → {len(reports)} unique daily reports")

# ============================================
# SMART MESSAGE GENERATORS
# ============================================

def detect_spelling_mistakes(text):
    """Detect common spelling mistakes"""
    common_mistakes = {
        "reflecs": "reflects", "sunlite": "sunlight", "visibl": "visible",
        "becuz": "because", "thier": "their", "recieve": "receive",
        "acheive": "achieve", "photosinthesis": "photosynthesis",
        "frakshuns": "fractions", "elektricity": "electricity",
        "gravaty": "gravity", "atmosfear": "atmosphere", "exampel": "example",
        "importent": "important", "diferent": "different", "becuase": "because",
        "shcool": "school", "tution": "tuition", "knowlege": "knowledge"
    }
    mistakes = []
    words = text.lower().split()
    for word in words:
        word_clean = word.strip('.,!?;:')
        if word_clean in common_mistakes:
            mistakes.append({"wrong": word_clean, "correct": common_mistakes[word_clean]})
    
    # Remove duplicates
    seen = set()
    unique = []
    for m in mistakes:
        if m['wrong'] not in seen:
            seen.add(m['wrong'])
            unique.append(m)
    return unique[:2]  # Max 2 spelling tips

def analyze_thinking_quality(answer, score):
    """Analyze the thinking quality from the answer"""
    word_count = len(answer.split())
    
    if score >= 8:
        return "great", "Your child showed excellent understanding and could explain the concept well!"
    elif score >= 6:
        if word_count < 20:
            return "good_brief", "Good understanding! Encourage adding more details next time."
        else:
            return "good", "Your child understood the key concepts well. Keep it up!"
    elif score >= 4:
        return "partial", "Getting there! The basic idea is there. A quick review will help solidify understanding."
    else:
        return "needs_work", "This topic needs more practice. A short video or discussion together would help."

def get_personalized_message(score, mistakes, thinking_quality, topic, child_name):
    """Generate a personalized, contextual message based on performance"""
    
    messages = []
    
    # 1. Score-based encouragement
    if score >= 9:
        messages.append(f"🌟 {child_name} did EXCELLENT today! Really understood {topic} well.")
    elif score >= 7:
        messages.append(f"✅ {child_name} did great! Shows good understanding of {topic}.")
    elif score >= 5:
        messages.append(f"📚 {child_name} is making progress! A little review on {topic} will help.")
    else:
        messages.append(f"💪 {child_name} needs some extra help with {topic}. Let's review together.")
    
    # 2. Spelling/grammar feedback (if mistakes found)
    if mistakes:
        spelling_tip = random.choice([
            f"🔤 Found a few spelling opportunities: {mistakes[0]['wrong']} → {mistakes[0]['correct']}",
            f"📝 Spelling practice: '{mistakes[0]['wrong']}' is usually spelled '{mistakes[0]['correct']}'",
            f"✍️ Great effort! One spelling tip: '{mistakes[0]['wrong']}' → '{mistakes[0]['correct']}'"
        ])
        messages.append(spelling_tip)
    
    # 3. Thinking quality feedback
    if thinking_quality == "great":
        messages.append(f"🧠 Loved how {child_name} explained this in their own words. Great thinking!")
    elif thinking_quality == "good":
        messages.append(f"💡 Good reasoning! Encourage {child_name} to add real-life examples.")
    elif thinking_quality == "good_brief":
        messages.append(f"📝 Understanding is there! Ask '{child_name} can you tell me more?' to build confidence.")
    elif thinking_quality == "partial":
        messages.append(f"🎯 The core idea is there! A quick 5-minute review will make it stick.")
    else:
        messages.append(f"🤝 Let's watch a short video about {topic} together. Sometimes a different view helps!")
    
    # 4. Parent action suggestion (specific)
    action = random.choice([
        f"💬 Ask: 'What was the most interesting thing you learned about {topic}?'",
        f"🎨 Can {child_name} draw a picture or give an example?",
        f"📖 Let's find a fun fact about {topic} to share at dinner!",
        f"👩‍🏫 Ask {child_name} to teach you what they learned - teaching helps learning!"
    ])
    messages.append(action)
    
    return messages

def extract_main_answer(thinking_answer):
    """Extract just the first meaningful sentence from the answer"""
    lines = thinking_answer.split('\n')
    for line in lines:
        if line.startswith("Q1:"):
            answer = line.replace("Q1:", "").strip()
            if "(Score:" in answer:
                answer = answer.split("(Score:")[0].strip()
            if "." in answer:
                answer = answer.split(".")[0] + "."
            if len(answer) > 100:
                answer = answer[:97] + "..."
            return answer
    return thinking_answer[:100] + "..."

def extract_fun_fact(topic):
    fun_facts = {
        "fractions": "Fractions were used by ancient Egyptians over 4,000 years ago!",
        "photosynthesis": "A single tree can produce oxygen for 4 people every day!",
        "water cycle": "The water you drink today could have been drunk by dinosaurs!",
        "electricity": "Lightning strikes Earth about 100 times every second!",
        "moon": "The moon is moving away from Earth by 3.8 cm every year!",
        "reproduction": "All living things reproduce to continue their species!",
    }
    topic_lower = topic.lower()
    for key, fact in fun_facts.items():
        if key in topic_lower:
            return fact
    return "Keep exploring! Every day is a chance to learn something new!"

# ============================================
# DISPLAY REPORTS
# ============================================
st.markdown("---")

all_messages = []
batch_data = []

for idx, ans in enumerate(reports):
    profile = ans.get("profiles", {})
    assignment = ans.get("daily_assignments", {})
    
    child_name = profile.get("child_name", "Child")
    parent_phone = profile.get("parent_phone", "No phone")
    thinking_answer = ans.get("thinking_answer", "No answer")
    thinking_score = ans.get("thinking_score", 0)
    mock_score = ans.get("mock_score", 0)
    
    # Get topic
    topic = ans.get("topic")
    if not topic and assignment:
        topic = assignment.get("topic", "Unknown Topic")
    if not topic:
        topic = "Learning Session"
    
    # Get fun fact
    gk_fact = extract_fun_fact(topic)
    
    # Detect spelling mistakes
    spelling_mistakes = detect_spelling_mistakes(thinking_answer)
    
    # Analyze thinking quality
    thinking_quality, thinking_feedback = analyze_thinking_quality(thinking_answer, thinking_score)
    
    # Get personalized message collection
    personalized_messages = get_personalized_message(
        thinking_score, spelling_mistakes, thinking_quality, topic, child_name
    )
    
    # Format date
    submitted_date = ans.get("submitted_at", datetime.datetime.now().isoformat())
    try:
        date_obj = datetime.datetime.fromisoformat(submitted_date.replace('Z', '+00:00'))
        formatted_date = date_obj.strftime("%b %d")
        day_name = date_obj.strftime("%A")
    except:
        formatted_date = datetime.datetime.now().strftime("%b %d")
        day_name = datetime.datetime.now().strftime("%A")
    
    # Extract main answer
    main_answer = extract_main_answer(thinking_answer)
    
    # Score summary
    if thinking_score >= 8:
        score_emoji = "🌟"
        score_text = "Excellent!"
    elif thinking_score >= 6:
        score_emoji = "✅"
        score_text = "Good!"
    elif thinking_score >= 4:
        score_emoji = "📚"
        score_text = "Getting there!"
    else:
        score_emoji = "💪"
        score_text = "Needs practice"
    
    # Build the final message (compact but personal)
    message = f"""
📚 *{child_name}* – {day_name}, {formatted_date}

📖 {topic}
🎯 Score: {thinking_score}/10 {score_emoji} {score_text}

✍️ "{main_answer}"

{personalized_messages[0]}
{personalized_messages[1] if len(personalized_messages) > 1 else ''}

{personalized_messages[-1]}

💡 {gk_fact}
"""
    
    all_messages.append(message)
    batch_data.append({
        "Child": child_name,
        "Phone": parent_phone,
        "Topic": topic,
        "Score": thinking_score,
        "Quiz": f"{mock_score}/3" if mock_score > 0 else "-",
        "Date": formatted_date,
        "Spelling": len(spelling_mistakes),
        "Status": "⏳ Pending"
    })
    
    # Display in expander
    with st.expander(f"{child_name} | {topic} | Score: {thinking_score}/10", expanded=(idx == 0)):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.text_area(
                "WhatsApp Message",
                message.strip(),
                height=380,
                key=f"msg_{idx}",
                label_visibility="collapsed"
            )
        
        with col2:
            st.markdown(f"**📞 Phone:** `{parent_phone}`")
            st.markdown(f"**📊 Score:** {thinking_score}/10")
            if mock_score > 0:
                st.markdown(f"**📝 Quiz:** {mock_score}/3")
            
            if spelling_mistakes:
                st.markdown("**🔤 Spelling Tips:**")
                for m in spelling_mistakes[:2]:
                    st.markdown(f"- '{m['wrong']}' → '{m['correct']}'")
            
            st.markdown(f"**🧠 {thinking_feedback}**")
            
            if st.button(f"✅ Mark Sent", key=f"mark_{idx}", use_container_width=True):
                admin_supabase.table("student_answers")\
                    .update({"reported": True})\
                    .eq("id", ans["id"])\
                    .execute()
                st.success(f"✅ Marked {child_name} as sent!")
                st.rerun()

# Batch actions
st.markdown("---")
st.subheader("⚡ Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📋 Copy ALL Messages", use_container_width=True, type="primary"):
        full_text = "\n━━━━━━━━━━━━━━━━━━━━\n".join(all_messages)
        st.code(full_text, language="text")
        st.info("✅ Copied! Now paste in WhatsApp Web")

with col2:
    if st.button("📊 Show Summary", use_container_width=True):
        df = pd.DataFrame(batch_data)
        st.dataframe(df, use_container_width=True)

with col3:
    if st.button("✅ Mark ALL Sent", use_container_width=True):
        for ans in reports:
            admin_supabase.table("student_answers")\
                .update({"reported": True})\
                .eq("id", ans["id"])\
                .execute()
        st.success(f"✅ Marked all {len(reports)} reports as sent!")
        st.balloons()
        st.rerun()

# Stats
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
avg_score = sum(r.get("thinking_score", 0) for r in reports) / len(reports) if reports else 0
high_scores = len([r for r in reports if r.get("thinking_score", 0) >= 7])
needs_help = len([r for r in reports if r.get("thinking_score", 0) < 5])
with col1: st.metric("📊 Avg Score", f"{avg_score:.1f}/10")
with col2: st.metric("🌟 High Scores (7+)", high_scores)
with col3: st.metric("🔴 Needs Help", needs_help)
with col4: st.metric("📬 Total", len(reports))

st.markdown("---")
st.info("💡 Messages are personalized based on your child's score, spelling, and thinking quality!")