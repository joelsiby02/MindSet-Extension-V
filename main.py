import streamlit as st
import datetime
from modules.db import supabase
from modules.auth import login, signup, logout
from modules.grading import grade_thinking_answer

# Page config
st.set_page_config(page_title="Daily Accountability", page_icon="📚", layout="centered")

# Authentication
if "user" not in st.session_state:
    st.title("Daily Accountability System")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        login()
    with tab2:
        signup()
    st.stop()

# Logged in
st.sidebar.button("Logout", on_click=logout)

# Fetch profile
profile = supabase.table("profiles").select("*").eq("user_id", st.session_state.user.id).execute()
if not profile.data:
    st.error("Profile not found. Please contact support.")
    st.stop()

profile = profile.data[0]
student_id = profile["id"]
board = profile["board"]
grade = profile["grade"]

# Get today's assignment (simple logic: use assignment id based on day of year)
def get_todays_assignment():
    assignments = supabase.table("daily_assignments").select("*")\
        .eq("board", board).eq("grade", grade).eq("approved", True)\
        .order("created_at").execute()
    if not assignments.data:
        return None
    day_index = (datetime.date.today() - datetime.date(2025, 1, 1)).days % len(assignments.data)
    return assignments.data[day_index]

assignment = get_todays_assignment()
if not assignment:
    st.warning("No assignment available for today. Please check back later.")
    st.stop()

# Check if already answered today
existing = supabase.table("student_answers").select("*")\
    .eq("student_id", student_id).eq("assignment_id", assignment["id"]).execute()
if existing.data:
    st.info("You've already completed today's session. Come back tomorrow!")
    st.write("### Your answers")
    st.write(f"**Thinking answer:** {existing.data[0]['thinking_answer']}")
    st.write(f"**Score:** {existing.data[0]['thinking_score']}/10")
    st.stop()

# Show today's content
st.title(f"Daily Study: {assignment['topic']}")
st.markdown(f"### 📖 Micro‑Lesson\n{assignment['micro_lesson']}")
if assignment.get("youtube_url"):
    st.video(assignment["youtube_url"])
st.markdown(f"### 💡 Did You Know?\n{assignment['gk_fact']}")
st.markdown(f"### 🤔 Thinking Question\n{assignment['thinking_question']}")

thinking_answer = st.text_area("Your answer (in your own words)", height=150)

# Mock test (simplified as a text input)
st.markdown("### 📝 Mock Test")
mock_answer = st.text_input("Answer the mock test question")

if st.button("Submit"):
    if not thinking_answer.strip():
        st.error("Please provide an answer to the thinking question.")
    else:
        # Grade
        score, confidence = grade_thinking_answer(thinking_answer, assignment["thinking_question"], student_id)
        # Insert
        supabase.table("student_answers").insert({
            "student_id": student_id,
            "assignment_id": assignment["id"],
            "thinking_answer": thinking_answer,
            "mock_test_answer": mock_answer,
            "thinking_score": score,
            "confidence": confidence,
            "reported": False
        }).execute()
        st.success("Submitted! Your parent will receive the report.")