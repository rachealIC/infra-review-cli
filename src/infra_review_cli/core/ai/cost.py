from .llm_client import call_ai
from infra_review_cli.utils.utility import extract_number


def estimate_savings(resource_type: str, usage: str, region: str, instance_id: str = "") -> float:
    prompt = f"""
    Estimate how much money (in USD) could be saved monthly if the following AWS resource is removed or downsized:

    - Resource: {resource_type}
    - Usage pattern: {usage}
    - Region: {region}

    Respond with just the dollar amount as a number. No extra text.
    """

    result = call_ai(prompt)
    if result:
        try:
            return float(extract_number(result))
        except (ValueError, TypeError):
            pass

    return 10.0  # fallback
