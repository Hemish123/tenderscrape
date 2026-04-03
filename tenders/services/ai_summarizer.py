# tenders/services/ai_summarizer.py
"""
Azure OpenAI integration for generating structured tender summaries.
Uses category-aware prompts to extract relevant information from tender documents.
"""

import json
import logging

from django.conf import settings
from openai import AzureOpenAI

logger = logging.getLogger('scrapers')


def _build_prompt(document_text: str, category: str) -> str:
    """
    Build the structured prompt for Azure OpenAI based on tender category.
    """
    return f"""You are an expert government tender analyst.

Extract only important and useful information from the tender document.

Ignore legal boilerplate and repetition.

Return structured JSON only.

Rules:
- Keep output concise
- No explanation
- Use null if missing
- Normalize dates to YYYY-MM-DD

Category: {category}

For IT:
{{
  "project_scope": "...",
  "technologies_required": "...",
  "eligibility_criteria": "...",
  "submission_deadline": "...",
  "estimated_budget": "...",
  "contact_details": "..."
}}

For Infrastructure / Construction:
{{
  "project_location": "...",
  "estimated_cost": "...",
  "work_description": "...",
  "timeline": "...",
  "contractor_requirements": "...",
  "submission_deadline": "..."
}}

For Other:
{{
  "title": "...",
  "department": "...",
  "key_requirements": "...",
  "important_dates": "...",
  "contact_details": "..."
}}

Document:
{document_text}
"""


def _get_client() -> AzureOpenAI:
    """
    Create and return an Azure OpenAI client using Django settings.
    """
    endpoint = getattr(settings, 'AZURE_OPENAI_ENDPOINT', '')
    api_key = getattr(settings, 'AZURE_OPENAI_KEY', '')

    if not endpoint or not api_key:
        raise ValueError(
            "Azure OpenAI credentials not configured. "
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables."
        )

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=getattr(settings, 'AZURE_OPENAI_API_VERSION', '2024-02-15-preview'),
    )


def _parse_json_response(content: str) -> dict:
    """
    Parse the AI response, handling markdown code fences and raw JSON.
    """
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith('```'):
        # Remove opening fence (```json or ```)
        first_newline = content.index('\n')
        content = content[first_newline + 1:]
        # Remove closing fence
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.debug(f"Raw response: {content[:500]}")
        # Return it as a raw text summary instead
        return {"raw_summary": content, "parse_error": str(e)}


def generate_summary(document_text: str, category: str = 'Other') -> dict:
    """
    Send extracted tender text to Azure OpenAI and return structured summary.

    Args:
        document_text: The extracted text from the tender PDF.
        category: The tender category (IT, Infrastructure, Construction, Other).

    Returns:
        A dict containing the structured summary.
    """
    if not document_text or not document_text.strip():
        raise ValueError("No document text provided for summarization")

    # Normalize category for prompt
    cat = (category or 'Other').strip()
    if cat in ('IT & Technology', 'IT'):
        cat = 'IT'
    elif cat in ('Infrastructure', 'Construction'):
        cat = 'Infrastructure / Construction'
    else:
        cat = 'Other'

    prompt = _build_prompt(document_text, cat)

    logger.info(f"Sending {len(document_text)} chars to Azure OpenAI (category: {cat})")

    try:
        client = _get_client()
        deployment = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are a government tender document analyst. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.2,
            max_tokens=2000,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from Azure OpenAI")

        summary = _parse_json_response(content)
        logger.info("AI summary generated successfully")
        return summary

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Azure OpenAI API error: {e}")
        raise RuntimeError(f"AI summarization failed: {e}")
