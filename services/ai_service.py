"""
AI Service Module
Handles Google Gemini API integration for session notes and teaching insights.
"""

import os
import google.generativeai as genai
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("[WARNING] Warning: GEMINI_API_KEY not configured")


class AIService:
    """Service for AI-powered insights and content generation"""

    @staticmethod
    def enhance_session_notes(notes: str, student_name: str, student_role: str) -> str:
        """
        Generate AI-enhanced overview from session notes

        Args:
            notes: Raw session notes from instructor
            student_name: Student's full name
            student_role: Student's role (student/faculty/staff)

        Returns:
            Enhanced session overview string (returns original notes as fallback if AI fails)
        """
        if not GEMINI_API_KEY:
            print("[ERROR] Gemini API key not configured - using original notes")
            return notes

        try:
            model = genai.GenerativeModel('gemini-flash-2.5')

            prompt = f"""
You are an AI assistant helping to summarize educational sessions about AI and technology.

**Session Notes:**
{notes}

**Student Information:**
- Name: {student_name}
- Role: {student_role}

**Task:**
Create a concise, professional summary of this AI learning session that can be emailed to the student. The summary should:

1. Highlight the main topics covered
2. List key takeaways and concepts learned
3. Include any specific tools or resources mentioned
4. Provide actionable next steps for continued learning
5. Be written in a friendly, encouraging tone

Keep the summary between 150-300 words. Format it as clear paragraphs (no markdown headers).
"""

            response = model.generate_content(prompt)
            overview = response.text.strip()

            if not overview:
                print("[WARNING] AI returned empty response - using original notes")
                return notes

            print(f"[OK] Generated session overview ({len(overview)} chars)")
            return overview

        except Exception as e:
            print(f"[ERROR] Session notes enhancement failed: {e} - using original notes as fallback")
            return notes

    @staticmethod
    def get_teaching_insights(session_data: dict) -> Optional[str]:
        """
        Generate teaching insights for instructor based on session patterns
        
        Args:
            session_data: Dictionary containing session metadata
                - topics: List of topics covered
                - duration: Session length in minutes
                - student_questions: List of student questions
                - difficulty_level: Perceived difficulty (1-5)
                
        Returns:
            Teaching insights string or None if failed
        """
        if not GEMINI_API_KEY:
            print("[ERROR] Gemini API key not configured")
            return None
            
        try:
            model = genai.GenerativeModel('gemini-pro')
            
            topics = session_data.get('topics', [])
            duration = session_data.get('duration', 30)
            questions = session_data.get('student_questions', [])
            difficulty = session_data.get('difficulty_level', 3)
            
            prompt = f"""
You are an educational AI consultant helping an instructor improve their AI teaching sessions.

**Session Metrics:**
- Topics Covered: {', '.join(topics)}
- Duration: {duration} minutes
- Student Questions: {len(questions)}
- Perceived Difficulty: {difficulty}/5

**Student Questions:**
{chr(10).join(f'- {q}' for q in questions)}

**Task:**
Provide brief teaching insights and recommendations:

1. Were the topics appropriate for the time allocated?
2. What do the student questions reveal about their understanding?
3. Suggest 2-3 ways to improve future sessions
4. Recommend related topics to cover in follow-up sessions

Keep the response concise (150-250 words) and actionable. Focus on practical improvements.
"""

            response = model.generate_content(prompt)
            insights = response.text.strip()
            
            print(f"[OK] Generated teaching insights ({len(insights)} chars)")
            return insights
            
        except Exception as e:
            print(f"[ERROR] Teaching insights generation failed: {e}")
            return None

    @staticmethod
    def generate_follow_up_resources(topics: list, skill_level: str) -> Optional[str]:
        """
        Generate personalized learning resource recommendations
        
        Args:
            topics: List of topics covered in session
            skill_level: Student's skill level (beginner/intermediate/advanced)
            
        Returns:
            Resource recommendations or None if failed
        """
        if not GEMINI_API_KEY:
            print("[ERROR] Gemini API key not configured")
            return None
            
        try:
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""
Generate personalized AI learning resources for a {skill_level} student who just learned about: {', '.join(topics)}

Provide:
1. 3 recommended online courses or tutorials
2. 2-3 hands-on project ideas
3. 2 articles or documentation links
4. 1 community or forum to join

Keep it concise and practical. Focus on free or accessible resources.
"""

            response = model.generate_content(prompt)
            resources = response.text.strip()
            
            print(f"[OK] Generated learning resources ({len(resources)} chars)")
            return resources
            
        except Exception as e:
            print(f"[ERROR] Resource generation failed: {e}")
            return None
