import streamlit as st
from modules.api_client import api

def login():
    with st.form("login_form"):
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            try:
                result = api.login(email, password)
                st.session_state.user = api.user
                st.session_state.access_token = api.access_token
                if "signup_msg" in st.session_state:
                    del st.session_state.signup_msg
                st.success(f"✅ Logged in as {email}")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")

def signup():
    with st.form("signup_form"):
        st.subheader("Sign Up")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        child_name = st.text_input("Child's Name", key="signup_child_name")
        grade = st.number_input("Grade", min_value=1, max_value=12, step=1, key="signup_grade")
        board = st.selectbox("Board", ["state", "icse", "cbse"], key="signup_board")
        parent_phone = st.text_input("Parent Phone (with country code, e.g., +919876543210)", key="signup_phone")
        
        submitted = st.form_submit_button("Sign Up")
        
        if submitted:
            try:
                with st.spinner("Creating account..."):
                    api.signup(email, password, child_name, grade, board, parent_phone)
                    st.session_state.signup_msg = "✨ Account created successfully! Please login to continue."
                    st.rerun()
            except Exception as e:
                st.error(f"Signup failed: {str(e)}")

def logout():
    """Complete logout - wipe everything and force rerun"""
    api.logout()
    st.session_state.clear()
    st.rerun()