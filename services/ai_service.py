"""
AI Service Module
Handles AI integration for session notes and teaching insights.
Uses Claude Sonnet 4.5 via AWS Bedrock.

Auth: ABSK keys are bearer tokens — set via AWS_BEARER_TOKEN_BEDROCK env var.
boto3 detects the bearer token automatically, no IAM credential decoding needed.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Bedrock setup — set bearer token so boto3 picks it up automatically
_CLAUDE_BEDROCK_API_KEY = os.getenv('CLAUDE_BEDROCK_API_KEY', '')
if _CLAUDE_BEDROCK_API_KEY:
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = _CLAUDE_BEDROCK_API_KEY

_bedrock_client = None


def _get_bedrock_client():
    """Lazy-init Bedrock Runtime client. Auth via AWS_BEARER_TOKEN_BEDROCK env var."""
    global _bedrock_client
    if _bedrock_client is not None:
        return _bedrock_client

    import boto3

    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    _bedrock_client = boto3.client("bedrock-runtime", region_name=aws_region)
    return _bedrock_client


def _generate(prompt: str, max_tokens: int = 500) -> str:
    """Generate text using Claude Sonnet 4.5 via Bedrock."""
    client = _get_bedrock_client()
    model_id = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0')

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


class AIService:
    """Service for AI-powered insights and content generation"""

    @staticmethod
    def enhance_session_notes(notes: str, student_name: str, student_role: str) -> str:
        """
        Generate AI-enhanced overview from session notes.
        Returns original notes as fallback if AI fails.
        """
        try:
            prompt = f"""You are an AI assistant helping to summarize educational sessions about AI and technology.

Session Notes:
{notes}

Student Information:
- Name: {student_name}
- Role: {student_role}

Task:
Create a concise, professional summary of this AI learning session that can be emailed to the student. Use the following format:

Key Topics Covered:
\u2022 [Topic 1]
\u2022 [Topic 2]
\u2022 [Topic 3]

Main Takeaways:
\u2022 [Takeaway 1]
\u2022 [Takeaway 2]
\u2022 [Takeaway 3]

Tools & Resources Mentioned:
\u2022 [Resource 1]
\u2022 [Resource 2]

Next Steps for Learning:
\u2022 [Action 1]
\u2022 [Action 2]

Summary:
[1-2 sentences wrapping it up in a friendly, encouraging tone]

Keep the entire summary between 150-300 words. Use bullet points throughout - DO NOT write it as paragraphs or a letter. DO NOT use markdown formatting like asterisks or bold text in your response."""

            overview = _generate(prompt, max_tokens=600)

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
        """Generate teaching insights for instructor based on session patterns."""
        try:
            topics = session_data.get('topics', [])
            duration = session_data.get('duration', 30)
            questions = session_data.get('student_questions', [])
            difficulty = session_data.get('difficulty_level', 3)

            prompt = f"""You are an educational AI consultant helping an instructor improve their AI teaching sessions.

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

Keep the response concise (150-250 words) and actionable. Focus on practical improvements."""

            insights = _generate(prompt, max_tokens=500)
            print(f"[OK] Generated teaching insights ({len(insights)} chars)")
            return insights

        except Exception as e:
            print(f"[ERROR] Teaching insights generation failed: {e}")
            return None

    @staticmethod
    def generate_follow_up_resources(topics: list, skill_level: str) -> Optional[str]:
        """Generate personalized learning resource recommendations."""
        try:
            prompt = f"""Generate personalized AI learning resources for a {skill_level} student who just learned about: {', '.join(topics)}

Provide:
1. 3 recommended online courses or tutorials
2. 2-3 hands-on project ideas
3. 2 articles or documentation links
4. 1 community or forum to join

Keep it concise and practical. Focus on free or accessible resources."""

            resources = _generate(prompt, max_tokens=500)
            print(f"[OK] Generated learning resources ({len(resources)} chars)")
            return resources

        except Exception as e:
            print(f"[ERROR] Resource generation failed: {e}")
            return None
