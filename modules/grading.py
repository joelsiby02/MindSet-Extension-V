import os
import json
import re
from dotenv import load_dotenv
from modules.utils import log_api_call

load_dotenv()

# Initialize clients (lazy loading - only when needed)
groq_client = None
gemini_client = None
openai_client = None

def get_groq_client():
    global groq_client
    if groq_client is None:
        try:
            from groq import Groq
            groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        except:
            pass
    return groq_client

def get_gemini_client():
    global gemini_client
    if gemini_client is None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            gemini_client = genai
        except:
            pass
    return gemini_client

def get_openai_client():
    global openai_client
    if openai_client is None:
        try:
            from openai import OpenAI
            openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            openai_client = openai
        except:
            pass
    return openai_client

def clean_json(text):
    """Clean JSON from LLM response"""
    text = text.strip()
    
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    return text.strip()

def is_idk_answer(answer):
    """Strict check for 'I don't know' answers"""
    answer_lower = answer.lower().strip()
    
    # Exact patterns for "I don't know"
    idk_patterns = [
        "idk",
        "i don't know",
        "i dont know",
        "no idea",
        "dont know",
        "don't know",
        "not sure",
        "i don't",
        "i dont",
        "dunno",
        "donno",
        "???",
        "??",
        "idk."
    ]
    
    # Check for exact matches or patterns
    for pattern in idk_patterns:
        if pattern in answer_lower:
            return True
    
    # Very short answers (1-2 words that aren't meaningful)
    words = answer_lower.split()
    if len(words) <= 2:
        # Check if it's just filler words
        filler_words = ["idk", "no", "yes", "maybe", "dunno", "hmm", "um", "uh"]
        if all(word in filler_words for word in words):
            return True
    
    return False

def is_meaningful_answer(answer):
    """Check if answer has substance"""
    answer_lower = answer.lower().strip()
    
    # Minimum length for meaningful answer
    if len(answer) < 10:
        return False
    
    # Check if answer contains actual content
    meaningful_words = ["because", "since", "therefore", "example", "like", "such as", "for instance"]
    if any(word in answer_lower for word in meaningful_words):
        return True
    
    # Check if answer has reasonable length
    if len(answer.split()) >= 5:
        return True
    
    return False

def calculate_length_score(answer):
    """Calculate score based on answer length"""
    word_count = len(answer.split())
    
    if word_count <= 2:
        return 0
    elif word_count <= 5:
        return 2
    elif word_count <= 10:
        return 4
    elif word_count <= 15:
        return 6
    elif word_count <= 20:
        return 8
    else:
        return 10

def grade_with_groq(prompt, student_id):
    """Grade using Groq (Llama)"""
    client = get_groq_client()
    if not client:
        return None
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a strict teacher. Give 0 for 'I don't know' answers. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Lower temperature for consistent grading
            max_tokens=100,
            timeout=10.0  # Fail fast if Groq is slow
        )
        
        text = response.choices[0].message.content
        text = clean_json(text)
        data = json.loads(text)
        
        score = max(0, min(10, int(data.get("score", 5))))
        confidence = float(data.get("confidence", 0.5))
        
        # Extract usage and calculate cost
        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        # Llama 3.1 8B approx pricing: $0.05/1M in, $0.08/1M out
        cost = (input_tokens * 0.05 / 1_000_000) + (output_tokens * 0.08 / 1_000_000)

        if student_id:
            log_api_call("groq", input_tokens, output_tokens, cost, student_id)
        
        return score, confidence
        
    except Exception as e:
        print(f"⚠️ Groq grading failed: {e}")
        return None

def grade_with_gemini(prompt, student_id):
    """Grade using Gemini"""
    client = get_gemini_client()
    if not client:
        return None
    
    try:
        model = client.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, request_options={'timeout': 10})
        
        text = response.text.strip()
        text = clean_json(text)
        data = json.loads(text)
        
        score = max(0, min(10, int(data.get("score", 5))))
        confidence = float(data.get("confidence", 0.5))
        
        # Extract usage and calculate cost
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        # Gemini 1.5 Flash approx pricing: $0.075/1M in, $0.30/1M out
        cost = (input_tokens * 0.075 / 1_000_000) + (output_tokens * 0.30 / 1_000_000)

        if student_id:
            log_api_call("gemini", input_tokens, output_tokens, cost, student_id)
        
        return score, confidence
        
    except Exception as e:
        print(f"⚠️ Gemini grading failed: {e}")
        return None

def grade_with_openai(prompt, student_id):
    """Grade using OpenAI GPT"""
    client = get_openai_client()
    if not client:
        return None
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"},
            timeout=10.0
        )
        
        text = response.choices[0].message.content
        text = clean_json(text)
        data = json.loads(text)
        
        score = max(0, min(10, int(data.get("score", 5))))
        confidence = float(data.get("confidence", 0.5))
        
        # Approximate cost calculation
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens / 1_000_000) * 0.15 + (output_tokens / 1_000_000) * 0.60
        
        if student_id:
            log_api_call("openai", input_tokens, output_tokens, cost, student_id)
        
        return score, confidence
        
    except Exception as e:
        print(f"⚠️ OpenAI grading failed: {e}")
        return None

def grade_thinking_answer(student_answer, question, student_id=None):
    """
    Grade student's answer with:
    1. Pre-filter for "I don't know"
    2. Length-based fallback
    3. AI grading with fallback chain
    """
    
    # Step 1: Pre-filter for "I don't know" answers
    if is_idk_answer(student_answer):
        print(f"⚠️ 'I don't know' answer detected -> Score: 0")
        return 0, 0.95
    
    # Step 2: Check if answer has any substance
    if not is_meaningful_answer(student_answer):
        # If very short but not "idk", give low score
        length_score = calculate_length_score(student_answer)
        if length_score <= 2:
            print(f"⚠️ Very short answer ({len(student_answer.split())} words) -> Score: {length_score}")
            return length_score, 0.6
    
    # Step 3: AI Grading with strict rubric
    prompt = f"""
You are a STRICT teacher grading a student's answer. Use this rubric:

SCORING RUBRIC (0-10):
0: Answer is "idk", "I don't know", "no idea", or completely irrelevant
1-2: Very short, lacks substance, major errors (1-2 words, no explanation)
3-4: Some attempt but missing key concepts, very brief
5-6: Basic understanding, some correct points, but incomplete
7-8: Good understanding, mostly correct, missing minor details
9-10: Excellent, complete, accurate, with examples

Question: {question}

Student Answer: {student_answer}

Evaluate based on:
- Accuracy (does it correctly answer the question)
- Completeness (does it cover all parts)
- Clarity (is it well explained)
- Originality (in student's own words)

Return ONLY valid JSON:
{{
  "score": number from 0 to 10,
  "confidence": number from 0 to 1,
  "reason": "brief reason for score"
}}
"""
    
    # Try Groq first
    result = grade_with_groq(prompt, student_id)
    if result:
        score, confidence = result
        print(f"✅ Groq grading: {score}/10 (conf: {confidence:.0%})")
        return score, confidence
    
    # Try Gemini next
    result = grade_with_gemini(prompt, student_id)
    if result:
        score, confidence = result
        print(f"✅ Gemini grading: {score}/10 (conf: {confidence:.0%})")
        return score, confidence
    
    # Try OpenAI last
    result = grade_with_openai(prompt, student_id)
    if result:
        score, confidence = result
        print(f"✅ OpenAI grading: {score}/10 (conf: {confidence:.0%})")
        return score, confidence
    
    # Ultimate fallback - use length-based score
    length_score = calculate_length_score(student_answer)
    print(f"❌ All AI services failed. Using length-based score: {length_score}/10")
    return length_score, 0.5