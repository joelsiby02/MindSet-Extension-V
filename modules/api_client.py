import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SupabaseAPI:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.access_token = None
        self.user = None

    def _get_auth_headers(self):
        """Get headers for authenticated requests"""
        headers = {
            "apikey": self.key,
            "Content-Type": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    # ---------- LOGIN ----------
    def login(self, email, password):
        """Login and get access token"""
        response = requests.post(
            f"{self.url}/auth/v1/token?grant_type=password",
            headers={
                "apikey": self.key,
                "Content-Type": "application/json"
            },
            json={
                "email": email,
                "password": password
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.user = data["user"]
            print(f"✅ Login successful - User: {self.user['email']}")
            return data
        else:
            raise Exception(f"Login failed: {response.text}")

    # ---------- PROFILE ----------
    def get_profile(self, user_id=None):
        """Get profile for a user"""
        if not user_id and self.user:
            user_id = self.user.get("id")
        
        if not user_id:
            raise Exception("No user ID available. Please login first.")
        
        if not self.access_token:
            raise Exception("Not authenticated. Please login first.")
        
        headers = self._get_auth_headers()
        
        response = requests.get(
            f"{self.url}/rest/v1/profiles?user_id=eq.{user_id}&select=*",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Profile found for user {user_id}")
            return data[0] if data else None
        elif response.status_code == 406:
            raise Exception("Authentication expired. Please login again.")
        else:
            print(f"⚠️ Profile not found - Status: {response.status_code}")
            return None

    # ---------- ASSIGNMENTS ----------
    def get_assignments(self, board, grade):
        """Get approved assignments for a student"""
        if not self.access_token:
            return []
        
        headers = self._get_auth_headers()
        
        response = requests.get(
            f"{self.url}/rest/v1/daily_assignments?board=eq.{board}&grade=eq.{grade}&approved=eq.true&select=*&order=created_at.asc",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data)} assignments for grade {grade} {board}")
            return data
        else:
            print(f"⚠️ No assignments found - Status: {response.status_code}")
            return []

    # ---------- CACHED LESSONS ----------
    def get_cached_lesson(self, topic, grade, board):
        """Check if we already have a cached lesson for this topic"""
        if not self.access_token:
            return None
        
        headers = self._get_auth_headers()
        
        response = requests.get(
            f"{self.url}/rest/v1/cached_lessons",
            headers=headers,
            params={"topic": f"eq.{topic}", "grade": f"eq.{grade}", "board": f"eq.{board}", "select": "*"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                print(f"✅ Found cached lesson for '{topic}' (used {data[0].get('usage_count', 0)} times)")
                self._increment_usage_count(data[0]['id'])
                return data[0]
        print(f"📝 No cached lesson for '{topic}'")
        return None

    def _increment_usage_count(self, lesson_id):
        """Increment the usage count for a cached lesson"""
        if not self.access_token:
            return
        
        headers = self._get_auth_headers()
        
        try:
            response = requests.get(
                f"{self.url}/rest/v1/cached_lessons?id=eq.{lesson_id}&select=usage_count",
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    current_count = data[0].get('usage_count', 0)
                    new_count = current_count + 1
                    
                    requests.patch(
                        f"{self.url}/rest/v1/cached_lessons?id=eq.{lesson_id}",
                        headers=headers,
                        json={
                            "usage_count": new_count,
                            "last_used": datetime.now().isoformat()
                        }
                    )
                    print(f"📊 Incremented usage count for lesson {lesson_id} to {new_count}")
        except Exception as e:
            print(f"⚠️ Error updating usage count: {e}")

    def save_cached_lesson(self, topic, subject, grade, board, content):
        """Save generated content to cache for future use"""
        if not self.access_token:
            return False
        
        headers = self._get_auth_headers()
        
        check_response = requests.get(
            f"{self.url}/rest/v1/cached_lessons",
            headers=headers,
            params={"topic": f"eq.{topic}", "grade": f"eq.{grade}", "board": f"eq.{board}", "select": "id"}
        )
        
        if check_response.status_code == 200 and check_response.json():
            print(f"📝 Cached lesson for '{topic}' already exists")
            return True
        
        data = {
            "topic": topic,
            "subject": subject,
            "grade": grade,
            "board": board,
            "micro_lesson": content.get("micro_lesson", {}),
            "micro_lesson_example": content.get("micro_lesson", {}).get("example", ""),
            "did_you_know": content.get("did_you_know", []),
            "thinking_questions": content.get("thinking_questions", []),
            "quiz_questions": content.get("quiz_questions", []),
            "usage_count": 1,
            "last_used": datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{self.url}/rest/v1/cached_lessons",
            headers=headers,
            json=data
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Saved new cached lesson for '{topic}'")
            return True
        else:
            print(f"⚠️ Failed to save cached lesson - {response.text}")
            return False

    # ---------- SAVE ANSWER ----------
    def save_answer(self, student_id, assignment_id, thinking_answer, mock_answer, thinking_score, mock_score, confidence, topic=None):
        """Save student's answer to database with mock_score"""
        if not self.access_token:
            raise Exception("Not authenticated. Please login first.")
        
        headers = self._get_auth_headers()
        headers["Prefer"] = "return=representation"
        
        data = {
            "student_id": student_id,
            "thinking_answer": thinking_answer,
            "mock_test_answer": mock_answer,
            "thinking_score": thinking_score,
            "mock_score": mock_score,  # ADDED: Store quiz score
            "confidence": confidence,
            "reported": False
        }
        
        # Only add assignment_id if it exists
        if assignment_id:
            data["assignment_id"] = assignment_id
        
        # Add topic if provided
        if topic:
            data["topic"] = topic
        
        print(f"🔍 Saving answer - Student: {student_id}, Score: {thinking_score}, Mock Score: {mock_score}, Topic: {topic}")
        
        response = requests.post(
            f"{self.url}/rest/v1/student_answers",
            headers=headers,
            json=data
        )
        
        print(f"🔍 Response status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            
            # Supabase returns a list of records when return=representation is used
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
                
            print(f"✅ Answer saved successfully! ID: {result.get('id') if isinstance(result, dict) else 'N/A'}")
            return result
        else:
            raise Exception(f"Save failed: {response.text}")

    def check_existing_answer(self, student_id, assignment_id):
        """Check if student already answered"""
        if not self.access_token:
            return []
        
        headers = self._get_auth_headers()
        
        response = requests.get(
            f"{self.url}/rest/v1/student_answers?student_id=eq.{student_id}&assignment_id=eq.{assignment_id}&select=*",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return []

    def get_student_answers(self, student_id, limit=10):
        """Get all answers for a student"""
        if not self.access_token:
            return []
        
        headers = self._get_auth_headers()
        
        response = requests.get(
            f"{self.url}/rest/v1/student_answers?student_id=eq.{student_id}&order=submitted_at.desc&limit={limit}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        return []

    # ---------- SIGNUP ----------
    def signup(self, email, password, child_name, grade, board, parent_phone):
        """Create new user"""
        response = requests.post(
            f"{self.url}/auth/v1/signup",
            headers={
                "apikey": self.key,
                "Content-Type": "application/json"
            },
            json={
                "email": email,
                "password": password,
                "data": {
                    "child_name": child_name,
                    "grade": grade,
                    "board": board
                }
            }
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Signup failed: {response.text}")

        data = response.json()
        
        if not data.get("user"):
            raise Exception("Email confirmation required. Please check your inbox.")
        
        user_id = data["user"]["id"]
        access_token = data.get("access_token")
        
        # Create profile
        headers = {
            "apikey": self.key,
            "Content-Type": "application/json"
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        profile_response = requests.post(
            f"{self.url}/rest/v1/profiles",
            headers=headers,
            json={
                "user_id": user_id,
                "child_name": child_name,
                "grade": grade,
                "board": board,
                "parent_phone": parent_phone,
                "is_active": True
            }
        )
        
        if profile_response.status_code not in [200, 201]:
            print(f"⚠️ Profile creation warning: {profile_response.text}")
        else:
            print(f"✅ Profile created for {child_name}")
        
        return data

    # ---------- LOGOUT ----------
    def logout(self):
        """Clear session data"""
        self.access_token = None
        self.user = None
        print("🔓 Logged out")

# Global instance
api = SupabaseAPI()