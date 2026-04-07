# tenders/services/ai_summarizer.py
"""
Azure OpenAI integration for generating structured tender summaries.
Uses the detailed procurement-expert prompt to extract maximum information.
"""

import json
import logging

from django.conf import settings
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a senior government tender analyst and procurement expert. "
    "Return only valid JSON. No explanation, no markdown."
)

USER_PROMPT_TEMPLATE = """You are a senior government tender analyst and procurement expert.

Your task is to extract maximum useful, decision-making information from a tender/RFP document.

The document may be long, complex, and unstructured.

Ignore:
- Legal boilerplate
- Repeated clauses
- Irrelevant text

Extract detailed structured information.

Return ONLY JSON.

Rules:
- Be precise and concise
- Use null if data not found
- Normalize dates to YYYY-MM-DD
- Extract as many relevant parameters as possible

OUTPUT STRUCTURE:

{{
  "basic_information": {{
    "title": "...",
    "tender_id": "...",
    "issuing_authority": "...",
    "department": "...",
    "location": "...",
    "tender_type": "...",
    "project_type": "..."
  }},

  "financial_details": {{
    "estimated_budget": "...",
    "emd_amount": "...",
    "tender_fee": "...",
    "payment_terms": "...",
    "penalties": "...",
    "performance_security": "..."
  }},

  "timeline": {{
    "publication_date": "...",
    "bid_start_date": "...",
    "bid_submission_deadline": "...",
    "bid_opening_date": "...",
    "project_duration": "..."
  }},

  "technical_requirements": {{
    "project_scope": "...",
    "work_description": "...",
    "technical_specifications": "...",
    "deliverables": "...",
    "standards": "..."
  }},

  "eligibility_criteria": {{
    "experience_required": "...",
    "financial_criteria": "...",
    "certifications_required": "...",
    "documents_required": "...",
    "blacklisting_conditions": "..."
  }},

  "evaluation_criteria": {{
    "selection_method": "...",
    "technical_weightage": "...",
    "financial_weightage": "...",
    "evaluation_process": "..."
  }},

  "contract_details": {{
    "contract_type": "...",
    "warranty": "...",
    "sla_terms": "...",
    "liquidated_damages": "...",
    "termination_conditions": "..."
  }},

  "important_contacts": {{
    "contact_person": "...",
    "email": "...",
    "phone": "...",
    "office_address": "..."
  }},

  "risk_insights": {{
    "key_risks": "...",
    "complexity_level": "...",
    "critical_clauses": "..."
  }},

  "summary": {{
    "short_summary": "...",
    "key_highlights": "..."
  }}
}}

DOCUMENT:

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
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY in your .env file."
        )

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=getattr(
            settings, 'AZURE_OPENAI_API_VERSION', '2024-05-01-preview'
        ),
    )


def _parse_json_response(content: str) -> dict:
    """
    Parse the AI response, handling markdown code fences and raw JSON.
    """
    content = content.strip()

    # Strip markdown code fences if present
    if content.startswith('```'):
        first_newline = content.index('\n')
        content = content[first_newline + 1:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response as JSON: %s", e)
        logger.debug("Raw response: %s", content[:500])
        return {"raw_summary": content, "parse_error": str(e)}


def generate_summary(document_text: str) -> dict:
    """
    Send extracted tender text to Azure OpenAI and return structured summary.

    Args:
        document_text: The extracted text from the tender PDF.

    Returns:
        A dict containing the structured 10-section summary.

    Raises:
        ValueError: If no document text is provided or credentials missing.
        RuntimeError: If the API call fails.
    """
    if not document_text or not document_text.strip():
        raise ValueError("No document text provided for summarization")

    prompt = USER_PROMPT_TEMPLATE.format(document_text=document_text)

    logger.info("Sending %d chars to Azure OpenAI for summarization", len(document_text))

    try:
        client = _get_client()
        deployment = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT', 'gpt-4o-mini')

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4000,
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
        logger.error("Azure OpenAI API error: %s", e)
        raise RuntimeError(f"AI summarization failed: {e}")
