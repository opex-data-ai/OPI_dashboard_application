from google import genai
import os
import logging

# Set up logging for AI operations
logger = logging.getLogger(__name__)

# Initialize GenAI Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MAX_WORDS = 80  # fits cleanly in a dialog popup

def ai_insight_in_chart(
    chart_title: str,
    chart_description: str,
    chart_data: dict | list,
    schema_explanation: str,
) -> str:
    """
    Generates a concise AI insight for a dashboard metric card.
    """
    logger.info(f"Generating AI insight for chart: '{chart_title}'")
    
    prompt = f"""
You are a concise data analyst assistant embedded in a business dashboard.

You will be given a metric's details and must return a short, plain-English insight.

Rules:
- Maximum {MAX_WORDS} words. No exceptions.
- No bullet points, no headers, no markdown.
- Write in 2–3 flowing sentences.
- First sentence: interpret what the data shows.
- Second sentence: identify what is notable, surprising, or concerning.
- Third sentence (optional): one clear, actionable recommendation.
- Tone: professional but plain. Avoid jargon.
- **Privacy Note**: If you see values starting with "HIDDEN_", these are anonymized unique identifiers (e.g., hashed organization names) to protect PII. Treat them as the actual entities they represent and refer to them as "Organization [Identifier]" or similar if needed.

Metric Title: {chart_title}
Metric Description: {chart_description}
Schema Explanation: {schema_explanation}
Current Data: {chart_data}

Respond with the insight only. Nothing else.
""".strip()

    try:
        # Use new client.models.generate_content API
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        logger.debug(f"AI Model call successful for '{chart_title}'")
        
        # Safety: trim to word count just in case
        text = response.text.replace(" * ", "").strip()
        words = text.split()
        if len(words) > MAX_WORDS:
            logger.warning(f"AI response for '{chart_title}' exceeded word limit ({len(words)} words). Trimming.")
            trimmed = " ".join(words[:MAX_WORDS])
            # End cleanly at last full sentence
            for punct in ['.', '!', '?']:
                last = trimmed.rfind(punct)
                if last != -1:
                    return trimmed[:last + 1]
            return trimmed + "..."

        return text
    except Exception as e:
        logger.error(f"Error calling AI model for '{chart_title}': {str(e)}")
        raise
