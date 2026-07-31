import google.generativeai as genai
import json

from app.core.config import settings
from app.repositories.feedback_repository import FeedbackRepository

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

# Create Gemini model
model = genai.GenerativeModel("gemini-2.5-flash")


def analyze_feedback(db):
    # Get all feedback from MySQL
    repository = FeedbackRepository(db)
    feedbacks = repository.get_all()

    # Convert feedback into one text
    feedback_text = "\n".join(
        feedback.feedback_text for feedback in feedbacks
    )

    # Prompt for Gemini
    prompt = f"""
You are an AI Product Feedback Analyst.

Analyze the customer feedback and identify the major product feedback themes.

Instructions:
1. Group similar feedback under one common theme.
2. Count how many feedback entries belong to each theme.
3. Use concise theme names such as:
   - Battery
   - Performance
   - Camera
   - Display
   - Software
   - Design
   - Charging
4. If feedback is positive and negative about the same feature, keep them under the same theme and mention both in the summary.
5. Return ONLY valid JSON.
6. Do NOT return markdown or explanations.

Return this format:

{{
  "themes": [
    {{
      "theme": "",
      "count": 0,
      "summary": ""
    }}
  ]
}}

Customer Feedback:

{feedback_text}
"""


    # Call Gemini
    response = model.generate_content(prompt)

    result = response.text.strip()

    # Remove Markdown code fences if present
    if result.startswith("```json"):
        result = result.replace("```json", "").replace("```", "").strip()
    elif result.startswith("```"):
        result = result.replace("```", "").strip()

    return json.loads(result)