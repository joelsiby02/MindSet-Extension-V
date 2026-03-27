import os
import json
from dotenv import load_dotenv
from google import genai
from modules.db import admin_supabase

# Load environment variables
load_dotenv()

# Init Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def clean_json(text):
    """Cleans Gemini output to ensure valid JSON"""
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def generate_for_topic(board, grade, subject, topic):
    prompt = f"""
Generate a micro-learning session for a {grade}th grade student following {board.upper()} board, subject {subject}, topic "{topic}".

Output STRICTLY in valid JSON (no markdown, no explanation):

{{
  "micro_lesson": "A short 2-3 sentence explanation of the concept.",
  "gk_fact": "A fun, surprising fact related to the topic.",
  "thinking_question": "An open-ended question.",
  "mock_test_question": "A single test question.",
  "mock_test_type": "mcq or short"
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        text = clean_json(response.text)
        data = json.loads(text)

        return data

    except Exception as e:
        print(f"❌ Error generating content for {topic}: {e}")
        return None


# Example topics (expand this later)
topics = [
    ("cbse", 5, "Science", "Why do we see the moon during the day?"),
    ("cbse", 5, "Science", "How do plants make their own food?"),
]


def main():
    for board, grade, subject, topic in topics:
        content = generate_for_topic(board, grade, subject, topic)

        if not content:
            print(f"❌ Failed for {topic}")
            continue

        try:
            admin_supabase.table("daily_assignments").insert({
                "board": board,
                "grade": grade,
                "subject": subject,
                "topic": topic,
                "micro_lesson": content.get("micro_lesson"),
                "gk_fact": content.get("gk_fact"),
                "thinking_question": content.get("thinking_question"),
                "mock_test_question": content.get("mock_test_question"),
                "mock_test_type": content.get("mock_test_type"),
                "approved": False
            }).execute()

            print(f"✅ Generated + saved: {topic}")

        except Exception as e:
            print(f"❌ DB error for {topic}: {e}")


if __name__ == "__main__":
    main()