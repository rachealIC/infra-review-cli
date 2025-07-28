from src.infra_review_cli.core.ai.llm_client import call_gemini, call_openai


def generate_ai_remediation(headline: str, description: str) -> str:
    prompt = f"""
    You are an expert cloud security engineer. Your advice is precise and to the point.

    A cloud scan found:
    - Headline: "{headline}"
    - Description: {description}

   Provide exactly 3–4 short, clear remediation steps as bullet points.

    Each step must be:
    - One line only
    - Actionable
    - Without explanation or justification
    - Use bullet points like this: "- <step>"
    
    Do not add any intro or summary. Just the bullets.
    """

    try:
        print("🔍 Calling Gemini for remediation...")
        return call_gemini(prompt)
    except Exception as e:
        print(" Gemini failed:", e)

    try:
        print("🔍 Calling OpenAI for remediation...")
        return call_openai(prompt)
    except Exception as e:
        print(" OpenAI failed:", e)

    return "AI remediation unavailable. Try manual review."
