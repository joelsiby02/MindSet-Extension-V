import openai
import google.generativeai as genai
import os
import json
from modules.db import supabase  # for logging
from modules.utils import log_api_call

openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def grade_thinking_answer(student_answer, question, student_id=None):
    """
    Returns (score, confidence). Tries OpenAI first, falls back to Gemini.
    """
    prompt = f"""You are a teacher grading a student's answer to the question: "{question}"

Student's answer: "{student_answer}"

Give a score from 0 to 10 based on:
- Accuracy (does it correctly address the question)
- Clarity (is it well explained)
- Originality (is it in the student's own words)

Also give a confidence score from 0 to 1 (how sure you are about this grade).

Output JSON: {{"score": int, "confidence": float}}"""
    
    # Try OpenAI first
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        # Log cost (rough estimate: gpt-4o-mini is $0.15/1M input tokens, $0.6/1M output)
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens / 1_000_000) * 0.15 + (output_tokens / 1_000_000) * 0.60
        log_api_call("openai", input_tokens, output_tokens, cost, student_id)
        return result["score"], result["confidence"]
    except Exception as e:
        print(f"OpenAI failed: {e}, falling back to Gemini")
        # Fallback to Gemini
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            # Gemini returns text; try to parse JSON
            text = response.text.strip()
            # Sometimes it includes backticks; clean
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            result = json.loads(text)
            # Approximate token counts: rough, but we'll log as 0 for now
            log_api_call("gemini", 0, 0, 0.0, student_id)
            return result["score"], result["confidence"]
        except Exception as e2:
            print(f"Gemini also failed: {e2}")
            return 0, 0.0