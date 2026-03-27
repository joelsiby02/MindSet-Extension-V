import streamlit as st
from modules.db import supabase

def login():
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user
            st.success("Logged in")
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")

def signup():
    st.subheader("Sign Up")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    child_name = st.text_input("Child's Name")
    grade = st.number_input("Grade", min_value=1, max_value=12, step=1)
    board = st.selectbox("Board", ["state", "icse", "cbse"])
    parent_phone = st.text_input("Parent Phone (with country code, e.g., +919876543210)")

    if st.button("Sign Up"):
        try:
            # Create auth user
            user = supabase.auth.sign_up({"email": email, "password": password})
            # Create profile
            supabase.table("profiles").insert({
                "user_id": user.user.id,
                "child_name": child_name,
                "grade": grade,
                "board": board,
                "parent_phone": parent_phone,
                "is_active": True
            }).execute()
            st.success("Account created! Please login.")
        except Exception as e:
            st.error(f"Signup failed: {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()