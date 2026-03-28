import os
import json
import time
from dotenv import load_dotenv
from groq import Groq
from modules.db import admin_supabase

load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Configuration
MODEL = "llama-3.1-8b-instant"  # Fast, cheap, good enough for content
RETRIES = 3
DELAY_BETWEEN_REQUESTS = 1  # seconds to avoid rate limits

def clean_json(text):
    """Extract and clean JSON from LLM response"""
    text = text.strip()
    
    # Remove markdown code blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    # Remove any leading/trailing whitespace
    text = text.strip()
    
    # Try to find JSON if there's extra text
    if text.startswith("{") and text.endswith("}"):
        return text
    
    # If there's text before/after JSON, extract it
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1
    if start_idx != -1 and end_idx > start_idx:
        return text[start_idx:end_idx]
    
    return text

def generate_for_topic(board, grade, subject, topic, retries=RETRIES):
    """Generate content for a topic using Groq"""
    
    prompt = f"""Generate a micro-learning session for a {grade}th grade student following {board.upper()} board, subject {subject}, topic "{topic}".

STRICT RULES:
- Output ONLY valid JSON (no markdown, no explanation, no extra text)
- Make it engaging and age-appropriate for a {grade}th grader
- Keep responses concise (max 2-3 sentences each field)

FORMAT (exactly this structure):
{{
  "micro_lesson": "A short 2-3 sentence explanation of the concept. Make it simple and clear.",
  "gk_fact": "A fun, surprising fact related to the topic that will make the kid curious.",
  "thinking_question": "An open-ended question that requires the student to think and explain in their own words.",
  "mock_test_question": "A single test question (multiple choice or short answer) to check understanding.",
  "mock_test_type": "mcq or short"
}}

Example for a good response:
{{
  "micro_lesson": "The moon doesn't make its own light. It reflects sunlight. During the day, the moon is sometimes still in the sky because it's orbiting Earth.",
  "gk_fact": "Did you know? The moon is moving away from Earth by 3.8 cm every year!",
  "thinking_question": "Why can we sometimes see the moon during the day? Explain in your own words.",
  "mock_test_question": "What causes the moon to appear bright in the sky? A) It makes its own light B) It reflects sunlight C) It absorbs light from stars",
  "mock_test_type": "mcq"
}}

Generate content now:"""

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a strict JSON generator. You output only valid JSON objects."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Low temp for consistency
                max_tokens=500
            )
            
            text = response.choices[0].message.content
            cleaned = clean_json(text)
            data = json.loads(cleaned)
            
            # Validate required fields
            required_fields = ["micro_lesson", "gk_fact", "thinking_question", "mock_test_question", "mock_test_type"]
            for field in required_fields:
                if field not in data or not data[field]:
                    raise ValueError(f"Missing field: {field}")
            
            # Validate mock_test_type
            if data["mock_test_type"] not in ["mcq", "short"]:
                data["mock_test_type"] = "short"  # Default to short if invalid
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decode error for {topic} (attempt {attempt+1}): {e}")
            print(f"Raw response: {text[:200]}...")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"⚠️ Error for {topic} (attempt {attempt+1}): {e}")
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    return None

# Expanded topics list for your MVP
topics = [
    # Grade 5 - Science
    ("cbse", 5, "Science", "Why do we see the moon during the day?"),
    ("cbse", 5, "Science", "How do plants make their own food?"),
    ("cbse", 5, "Science", "What causes day and night?"),
    ("cbse", 5, "Science", "Why do we need to drink water?"),
    ("cbse", 5, "Science", "How do birds fly?"),
    
    # Grade 5 - Math
    ("cbse", 5, "Math", "What are fractions and why do we need them?"),
    ("cbse", 5, "Math", "How to multiply large numbers easily?"),
    ("cbse", 5, "Math", "What is the difference between area and perimeter?"),
    
    # Grade 6 - Science
    ("cbse", 6, "Science", "Why do we see different phases of the moon?"),
    ("cbse", 6, "Science", "How does the digestive system work?"),
    ("cbse", 6, "Science", "What is the water cycle?"),
    
    # ICSE examples
    ("icse", 5, "Science", "Why do leaves change color in autumn?"),
    ("icse", 6, "Science", "How do magnets work?"),
    
    # State board examples
    ("state", 5, "Science", "Why do we have seasons?"),
    ("state", 6, "Science", "What is electricity and how does it flow?"),
]

def verify_database_connection():
    """Test database connection before generating"""
    try:
        # Try to fetch one record
        test = admin_supabase.table("daily_assignments").select("count").limit(1).execute()
        print("✅ Database connection verified")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    """Main function to generate and store content"""
    
    print("🚀 Starting content generation...")
    print("=" * 50)
    
    # Verify database connection
    if not verify_database_connection():
        print("Exiting due to database connection issue.")
        return
    
    # Check existing assignments to avoid duplicates
    print("📊 Checking existing assignments...")
    existing_topics = set()
    try:
        existing = admin_supabase.table("daily_assignments").select("board, grade, topic").execute()
        for item in existing.data:
            existing_topics.add(f"{item['board']}_{item['grade']}_{item['topic']}")
        print(f"📋 Found {len(existing_topics)} existing assignments")
    except Exception as e:
        print(f"⚠️ Could not fetch existing assignments: {e}")
    
    # Generate content
    success_count = 0
    fail_count = 0
    
    for board, grade, subject, topic in topics:
        # Skip if already exists
        key = f"{board}_{grade}_{topic}"
        if key in existing_topics:
            print(f"⏭️ Skipping existing: {board} grade {grade} - {topic}")
            continue
        
        print(f"\n📝 Generating: {board.upper()} Grade {grade} - {topic}")
        
        content = generate_for_topic(board, grade, subject, topic)
        
        if not content:
            print(f"❌ Failed to generate for: {topic}")
            fail_count += 1
            continue
        
        # Display preview
        print(f"  📖 Lesson: {content['micro_lesson'][:60]}...")
        print(f"  💡 Fact: {content['gk_fact'][:60]}...")
        
        # Save to database
        try:
            admin_supabase.table("daily_assignments").insert({
                "board": board,
                "grade": grade,
                "subject": subject,
                "topic": topic,
                "micro_lesson": content["micro_lesson"],
                "gk_fact": content["gk_fact"],
                "thinking_question": content["thinking_question"],
                "mock_test_question": content["mock_test_question"],
                "mock_test_type": content["mock_test_type"],
                "approved": False  # Need manual approval
            }).execute()
            
            print(f"✅ Saved to database: {topic}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Database error for {topic}: {e}")
            fail_count += 1
        
        # Small delay to avoid rate limits
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Generation Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   📚 Total processed: {success_count + fail_count}")
    print("\n💡 Next steps:")
    print("1. Check generated content in Supabase: daily_assignments table")
    print("2. Review and approve assignments (set approved = true)")
    print("3. Run main.py to see the content in your app")

if __name__ == "__main__":
    main()