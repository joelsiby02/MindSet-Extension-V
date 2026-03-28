import streamlit as st
import datetime
import requests
import json
from modules.api_client import api
from modules.auth import login, signup, logout
from modules.grading import grade_thinking_answer
from groq import Groq
import os

# ============================================
# RESTORE API SESSION (ONLY IF USER EXISTS)
# ============================================
if "user" in st.session_state and "access_token" in st.session_state:
    api.user = st.session_state.user
    api.access_token = st.session_state.access_token

st.set_page_config(
    page_title="Daily Learning",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium CSS
st.markdown("""
<style>
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 30px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .topic-card {
        background: white;
        border-radius: 24px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eef2ff;
        margin-bottom: 1.5rem;
    }
    .fact-card {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        padding: 1rem;
        border-radius: 16px;
        border-left: 4px solid #f59e0b;
    }
    .question-card {
        background: #f8fafc;
        border-radius: 20px;
        padding: 1.2rem;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    .answer-area {
        background: #fef9e6;
        border-radius: 16px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #10b981;
    }
    .save-success {
        background: #d1fae5;
        border-radius: 16px;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #10b981;
    }
    .save-error {
        background: #fee2e2;
        border-radius: 16px;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #ef4444;
    }
    hr {
        margin: 2rem 0;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        font-weight: 600;
        border-radius: 40px;
        padding: 0.5rem 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

def clean_json_response(text):
    """Extract JSON from LLM response"""
    text = text.strip()
    text = text.replace("```json", "").replace("```", "")
    text = text.strip()
    
    start = text.find("{")
    end = text.rfind("}")
    
    if start != -1 and end != -1 and start < end:
        return text[start:end+1]
    return text

# ============================================
# CRITICAL: CHECK IF USER IS LOGGED IN FIRST
# ============================================
if "user" not in st.session_state:
    # Show login screen
    st.markdown("""
    <div style="text-align: center; padding: 3rem;">
        <div style="font-size: 4rem;">🌟</div>
        <h1 style="font-size: 2.5rem;">Daily Learning</h1>
        <p style="font-size: 1.2rem; color: #666;">What you learn in school → Master it today</p>
        <p style="color: #10b981;">⭐ Parents see daily proof of understanding</p>
    </div>
    """, unsafe_allow_html=True)
    
    if "signup_msg" in st.session_state:
        st.success(st.session_state.signup_msg)
    
    tab1, tab2 = st.tabs(["🔑 Login", "✨ Sign Up"])
    with tab1:
        login()
    with tab2:
        signup()
    st.stop()  # CRITICAL: Stop execution here - nothing after this runs

# ============================================
# AT THIS POINT, WE ARE 100% SURE USER IS LOGGED IN
# So it's safe to load profile and show main app
# ============================================

try:
    profile = api.get_profile(st.session_state.user["id"])
    if not profile:
        st.error("Profile not found. Please contact support.")
        st.stop()
    
    child_name = profile["child_name"]
    grade = profile["grade"]
    board = profile["board"]
    student_id = profile["id"]
    
except Exception as e:
    st.error(f"Error loading profile: {str(e)}")
    st.stop()

# ============================================
# CHECK TODAY'S SUBMISSION
# ============================================
today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

existing_answer = None
try:
    existing = requests.get(
        f"{api.url}/rest/v1/student_answers?student_id=eq.{student_id}&submitted_at=gte.{today_start}&select=*&order=submitted_at.desc&limit=1",
        headers={"apikey": api.key, "Authorization": f"Bearer {api.access_token}"}
    )
    if existing.status_code == 200 and existing.json():
        existing_answer = existing.json()[0]
except Exception:
    # Silent fail for network issues, but don't swallow control flow exceptions
    pass

if existing_answer:
    topic = existing_answer.get("topic", existing_answer.get("daily_assignments", {}).get("topic", "Unknown"))
    score = existing_answer.get("thinking_score", 0)
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 30px; padding: 2rem; text-align: center; color: white;">
        <div style="font-size: 4rem;">🏆</div>
        <h2>Great job, {child_name}!</h2>
        <p>You already mastered <strong>{topic}</strong> today</p>
        <p style="font-size: 1.5rem;">Score: {score}/10</p>
        <p>🎯 Come back tomorrow for a new adventure</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📝 View your answers"):
        st.write(existing_answer.get("thinking_answer", "No answer"))
    
    # Logout button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary", key="logout_today"):
            logout()
    
    st.stop()

# ============================================
# INITIALIZE SESSION STATE
# ============================================
if "current_topic" not in st.session_state:
    st.session_state.current_topic = None
if "current_content" not in st.session_state:
    st.session_state.current_content = None
if "assignment_id" not in st.session_state:
    st.session_state.assignment_id = None
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = {}
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "saved_answer_id" not in st.session_state:
    st.session_state.saved_answer_id = None

# ============================================
# MAIN INTERFACE
# ============================================
st.markdown(f"""
<div class="hero">
    <div style="font-size: 3rem;">🌟</div>
    <h1 style="margin: 0;">Hi, {child_name}!</h1>
    <p style="margin: 0.5rem 0;">Grade {grade} • {board.upper()} Board</p>
    <p style="margin-top: 1rem;">What did you learn in school today?</p>
</div>
""", unsafe_allow_html=True)

# Topic input
st.markdown("### 📚 Tell us your topic")

topic_input = st.text_input(
    "",
    placeholder="e.g., Fractions, Photosynthesis, The Water Cycle",
    key="topic_input",
    label_visibility="collapsed"
)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_btn = st.button("✨ Create My Lesson", use_container_width=True, type="primary")

if generate_btn and topic_input.strip():
    topic = topic_input.strip()
    
    with st.spinner(f"Creating your personalized lesson about {topic}..."):
        cached = api.get_cached_lesson(topic, grade, board)
        
        if cached:
            content = {
                "micro_lesson": cached.get("micro_lesson", {}),
                "did_you_know": cached.get("did_you_know", [])[:3],
                "thinking_questions": cached.get("thinking_questions", [])[:5],
                "quiz_questions": cached.get("quiz_questions", [])[:3]
            }
            assignment_id = cached.get("id")
        else:
            groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            prompt = f"""
A {grade}th grade student learned about "{topic}" in school.

Create a lesson. Output in this exact JSON format:

{{
  "micro_lesson": {{
    "explanation": "simple explanation",
    "example": "real-world example"
  }},
  "did_you_know": ["fact1", "fact2", "fact3"],
  "thinking_questions": [
    "What is {topic}? Explain in your own words.",
    "Why is {topic} important? Give a reason.",
    "Give an example of {topic} from daily life.",
    "What would happen if we didn't understand {topic}?",
    "How would you explain {topic} to a friend?"
  ],
  "quiz_questions": [
    {{
      "question": "Easy question about {topic}",
      "options": ["Option A", "Option B", "Option C"],
      "correct": "Option A"
    }},
    {{
      "question": "Medium question about {topic}",
      "options": ["Option A", "Option B", "Option C"],
      "correct": "Option B"
    }},
    {{
      "question": "Hard question about {topic}",
      "options": ["Option A", "Option B", "Option C"],
      "correct": "Option C"
    }}
  ]
}}

Only output JSON, no other text.
"""
            
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a teacher. Output only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=1000
                )
                
                content_text = response.choices[0].message.content.strip()
                content_text = content_text.replace("```json", "").replace("```", "").strip()
                
                start_idx = content_text.find("{")
                end_idx = content_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    content_text = content_text[start_idx:end_idx+1]
                
                content = json.loads(content_text)
                assignment_id = None
                api.save_cached_lesson(topic, "General", grade, board, content)
                
            except Exception as e:
                st.warning("Using default lesson.")
                content = {
                    "micro_lesson": {
                        "explanation": f"{topic} is an important concept to understand.",
                        "example": f"Here's a simple example of {topic} in daily life."
                    },
                    "did_you_know": [
                        f"Learning about {topic} helps you understand the world better.",
                        f"Many people use {topic} every day.",
                        f"Understanding {topic} can help you in school."
                    ],
                    "thinking_questions": [
                        f"What is {topic}? Explain in your own words.",
                        f"Why is {topic} important? Give a reason.",
                        f"Give an example of {topic} from daily life.",
                        f"What would happen if we didn't understand {topic}?",
                        f"How would you explain {topic} to a friend?"
                    ],
                    "quiz_questions": [
                        {"question": f"What is {topic}?", "options": ["Yes", "No"], "correct": "Yes"},
                        {"question": f"Is {topic} useful?", "options": ["Yes", "No"], "correct": "Yes"},
                        {"question": f"Should we learn {topic}?", "options": ["Yes", "No"], "correct": "Yes"}
                    ]
                }
                assignment_id = None
        
        st.session_state.current_topic = topic
        st.session_state.current_content = content
        st.session_state.assignment_id = assignment_id
        st.session_state.answers = {}
        st.session_state.edit_mode = {}
        st.session_state.quiz_answers = {}
        st.session_state.submitted = False
        st.rerun()

# ============================================
# DISPLAY LESSON (if not submitted)
# ============================================
if st.session_state.current_content and st.session_state.current_topic and not st.session_state.submitted:
    content = st.session_state.current_content
    topic = st.session_state.current_topic
    
    st.markdown("---")
    
    # Topic header
    micro = content.get("micro_lesson", {})
    st.markdown(f"""
    <div class="topic-card">
        <h1>📖 {topic}</h1>
        <p>{micro.get('explanation', '')}</p>
        <p>💡 <em>{micro.get('example', '')}</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fun facts
    facts = content.get("did_you_know", [])
    if facts:
        st.markdown("### 💡 Did You Know?")
        cols = st.columns(min(len(facts), 3))
        for i, fact in enumerate(facts[:3]):
            with cols[i]:
                st.markdown(f"""
                <div class="fact-card">
                    <span class="fun-fact-badge">✨</span>
                    <p>{fact}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # 5 Questions with Submit and Edit buttons
    st.markdown("### 🤔 Think & Explain")
    st.markdown("Answer each question below:")
    
    thinking_questions = content.get("thinking_questions", [])[:5]
    
    for i, question in enumerate(thinking_questions, 1):
        q_key = f"q{i}"
        
        with st.container():
            st.markdown(f"""
            <div class="question-card">
                <strong>Question {i}</strong><br>
                {question}
            </div>
            """, unsafe_allow_html=True)
            
            # Check if answer exists and is saved
            if q_key in st.session_state.answers and st.session_state.answers[q_key]:
                # Show saved answer with Edit button
                st.markdown(f"""
                <div class="answer-area">
                    <strong>Your answer:</strong><br>
                    "{st.session_state.answers[q_key]}"
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"✏️ Edit Answer", key=f"edit_{q_key}"):
                    st.session_state.edit_mode[q_key] = True
                    st.rerun()
            else:
                # Show input with Submit button
                new_answer = st.text_area(
                    f"Your answer",
                    height=100,
                    key=f"input_{q_key}",
                    placeholder="Write your answer here...",
                    label_visibility="collapsed"
                )
                
                if st.button(f"📝 Submit Answer", key=f"submit_{q_key}"):
                    if new_answer.strip():
                        st.session_state.answers[q_key] = new_answer
                        st.rerun()
                    else:
                        st.warning("Please write an answer first!")
            
            # Edit mode
            if st.session_state.edit_mode.get(q_key, False):
                edit_answer = st.text_area(
                    "Edit your answer",
                    value=st.session_state.answers.get(q_key, ""),
                    height=100,
                    key=f"edit_input_{q_key}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"💾 Save Changes", key=f"save_{q_key}"):
                        if edit_answer.strip():
                            st.session_state.answers[q_key] = edit_answer
                            st.session_state.edit_mode[q_key] = False
                            st.rerun()
                with col2:
                    if st.button(f"❌ Cancel", key=f"cancel_{q_key}"):
                        st.session_state.edit_mode[q_key] = False
                        st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
    
    # Quiz questions
    quiz_questions = content.get("quiz_questions", [])
    if quiz_questions:
        st.markdown("### 📝 Quick Quiz")
        
        for i, q in enumerate(quiz_questions[:3], 1):
            if isinstance(q, dict):
                question_text = q.get('question', '')
                options = q.get('options', ['A', 'B', 'C'])
                correct = q.get('correct', options[0] if options else 'A')
            else:
                question_text = str(q)
                options = ['Yes', 'No']
                correct = 'Yes'
            
            st.markdown(f"**Q{i}. {question_text}**")
            selected = st.radio(
                "Select answer",
                options,
                key=f"quiz_{i}",
                index=None,
                label_visibility="collapsed"
            )
            if selected:
                st.session_state.quiz_answers[f"q{i}"] = {
                    "selected": selected,
                    "correct": correct
                }
            st.markdown("---")
    
    # Submit all to database
    st.markdown("---")
    
    answered_count = len([a for a in st.session_state.answers.values() if a.strip()])
    total_questions = len(thinking_questions)
    
    if answered_count > 0:
        st.info(f"📊 Progress: {answered_count}/{total_questions} questions answered")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        final_submit = st.button("💾 SUBMIT❤️ 💾", use_container_width=True, type="primary")
    
    if final_submit:
        if answered_count < total_questions:
            missing = total_questions - answered_count
            st.error(f"📝 Please answer {missing} more question(s) before saving!")
        else:
            with st.spinner("📝 Grading your answers..."):
                total_score = 0
                all_answers_with_scores = []
                
                for i, question in enumerate(thinking_questions, 1):
                    q_key = f"q{i}"
                    answer = st.session_state.answers.get(q_key, "")
                    if answer:
                        score, confidence = grade_thinking_answer(answer, question, student_id)
                        total_score += score
                        all_answers_with_scores.append(f"Q{i}: {answer} (Score: {score}/10)")
                
                avg_score = total_score / total_questions if total_questions > 0 else 5
                
                quiz_score = 0
                quiz_total = 0
                for i in range(1, 4):
                    if f"q{i}" in st.session_state.quiz_answers:
                        selected = st.session_state.quiz_answers[f"q{i}"].get("selected")
                        correct = st.session_state.quiz_answers[f"q{i}"].get("correct")
                        if selected:
                            quiz_total += 1
                            if selected == correct:
                                quiz_score += 1
                
                quiz_percentage = (quiz_score / quiz_total * 10) if quiz_total > 0 else 0
                final_score = int((avg_score * 0.8) + (quiz_percentage * 0.2))
                final_score = max(0, min(10, final_score))
                
                combined_answer = "\n\n".join(all_answers_with_scores)
                
                # Create mock_answer string for display
                mock_answer_text = f"Quiz: {quiz_score}/{quiz_total} ({(quiz_score/quiz_total*100):.0f}%)" if quiz_total > 0 else "No quiz taken"
                
                try:
                    assignment_id = st.session_state.assignment_id
                    
                    # FIXED: Added mock_score parameter
                    result = api.save_answer(
                        student_id=student_id,
                        assignment_id=assignment_id,
                        thinking_answer=combined_answer,
                        mock_answer=mock_answer_text,
                        thinking_score=final_score,
                        mock_score=quiz_score,  # 👈 ADDED THIS - stores quiz score in database
                        confidence=0.8,
                        topic=topic
                    )
                    
                    st.markdown(f"""
                    <div class="save-success">
                        <strong>✅ SUCCESS! Your answers have been saved!</strong><br>
                        📊 Final Score: {final_score}/10<br>
                        📝 Quiz Score: {quiz_score}/{quiz_total}<br>
                        🆔 Answer ID: {result.get('id', 'N/A')[:8]}...<br>
                        👪 Your parent will receive a report shortly
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.saved_answer_id = result.get('id')
                    st.session_state.submitted = True
                    st.rerun()
                    
                except Exception as e:
                    st.markdown(f"""
                    <div class="save-error">
                        <strong>❌ Database Error</strong><br>
                        {str(e)}
                    </div>
                    """, unsafe_allow_html=True)

# ============================================
# SUBMITTED SCREEN
# ============================================
if st.session_state.submitted:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 30px; padding: 2rem; text-align: center; color: white;">
        <div style="font-size: 4rem;">🎉</div>
        <h1>Amazing, {child_name}!</h1>
        <p style="font-size: 1.2rem;">Your answers are saved!</p>
        <p>✅ Your parent will receive a report</p>
        <p>🎯 Come back tomorrow for a new adventure!</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.saved_answer_id:
        st.success(f"📌 Your Answer ID: `{st.session_state.saved_answer_id[:8]}...`")
    
    with st.expander("📝 View All Your Answers", expanded=False):
        thinking_questions = st.session_state.current_content.get("thinking_questions", [])[:5]
        for i, q in enumerate(thinking_questions, 1):
            q_key = f"q{i}"
            answer = st.session_state.answers.get(q_key, "")
            if answer:
                st.markdown(f"**Q{i}:** {q}")
                st.markdown(f"*Your answer:* \"{answer}\"")
                st.markdown("---")
    
    st.markdown("---")
    st.markdown("### 👋 Ready to leave?")
    st.markdown("Click below to log out of your account.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            logout()
    
    st.caption("💡 You can log back in anytime with your email and password")
    
    st.stop()

# ============================================
# SIDEBAR - ONLY SHOW IF USER IS LOGGED IN
# ============================================
with st.sidebar:
    # At this point we know user is logged in because we passed the auth check
    st.markdown(f"### 🌟 {child_name}")
    st.markdown(f"Grade {grade} | {board.upper()}")
    st.markdown("---")
    
    if st.session_state.get("submitted", False):
        st.success("✅ Today's session completed!")
        st.info("🎯 Come back tomorrow for more learning!")
    else:
        st.markdown("### How it works")
        st.markdown("""
        1. Tell us what you learned 📚
        2. Answer 5 questions ✍️
        3. Edit answers anytime ✏️
        4. Take a quick quiz 📝
        5. Click SAVE & SHARE 💾
        """)
    
    st.markdown("---")
    
    if not st.session_state.get("submitted", False) and "answers" in st.session_state and st.session_state.answers:
        answered = len([a for a in st.session_state.answers.values() if a.strip()])
        st.markdown("### Today's Progress")
        st.progress(answered / 5)
        st.caption(f"{answered}/5 questions answered")
    
    st.markdown("---")
    
    if st.button("🚪 Logout", use_container_width=True):
        logout()
    
    st.caption(f"Logged in as: {st.session_state.user.get('email', 'user')}")