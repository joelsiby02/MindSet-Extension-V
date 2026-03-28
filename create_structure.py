import os

FILES = {
    ".env": "",

    "requirements.txt": """streamlit
python-dotenv
""",

    "main.py": """import streamlit as st

st.title("Daily Accountability")

name = st.text_input("Enter your name")

if st.button("Submit"):
    st.success(f"Submitted for {name}")
""",

    "admin.py": """import streamlit as st

st.title("Admin Panel")
""",

    "send_reports.py": """def send_report(user):
    print(f"Sending report to {user}")

if __name__ == "__main__":
    send_report("Parent")
""",

    "generate_content.py": """def generate(day):
    return f"Lesson for Day {day}"

if __name__ == "__main__":
    for i in range(1, 8):
        print(generate(i))
""",

    "modules/__init__.py": "",

    "modules/auth.py": """def login(username):
    return True
""",

    "modules/db.py": """def save(data):
    print("Saved:", data)
""",

    "modules/grading.py": """def grade(ans):
    return "Good" if len(ans) > 3 else "Bad"
""",

    "modules/whatsapp.py": """def send(msg):
    print("Sending:", msg)
""",

    "modules/utils.py": """def clean(text):
    return text.strip()
""",

    "README.md": """# Daily Accountability

Run:
    streamlit run main.py
"""
}

def create_structure():
    for path, content in FILES.items():
        full_path = path

        # Create folders if needed
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)

        # Skip if file already exists (prevents overwriting)
        if os.path.exists(full_path):
            print(f"⚠️ Skipped (already exists): {full_path}")
            continue

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Created: {full_path}")

if __name__ == "__main__":
    create_structure()