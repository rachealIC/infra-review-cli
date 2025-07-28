from src.infra_review_cli.core.ai.llm_client import call_gemini, call_openai
from src.infra_review_cli.core.utility import extract_number


def estimate_savings(resource_type: str, usage: str, region: str, instance_id: str = "") -> float:
    prompt = f"""
    Estimate how much money (in USD) could be saved monthly if the following AWS resource is removed or downsized:

    - Resource: {resource_type}
    - Usage pattern: {usage}
    - Region: {region}

    Respond with just the dollar amount as a number. No extra text.
    """

    try:
        return float(extract_number(call_gemini(prompt)))
    except Exception as e:
        print("⚠️ Gemini failed:", e)

    try:
        return float(extract_number(call_openai(prompt)))
    except Exception as e:
        print("⚠️ OpenAI failed:", e)

    return 10.0  # fallback
