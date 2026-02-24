import re





def _parse_ec2_suggestion(response_text: str) -> dict:
    """Parses the AI's key-value response into a dictionary."""
    if not response_text or not isinstance(response_text, str):
        return {}
    suggestion = {}
    lines = response_text.strip().splitlines()
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            # Create a simple key name (e.g., "Suggested Instance Type" -> "suggested_instance_type")
            clean_key = key.strip().lower().replace(' ', '_')
            suggestion[clean_key] = value.strip()

    # Clean up the savings value to be a float
    savings_str = suggestion.get("estimated_monthly_savings", "$0.0")
    savings_match = re.search(r'(\d+\.\d+)', savings_str)
    if savings_match:
        suggestion["estimated_monthly_savings"] = float(savings_match.group(1))
    else:
        suggestion["estimated_monthly_savings"] = 0.0

    return suggestion


def suggest_ec2_rightsizing(
        instance_id: str,
        instance_type: str,
        architecture: str,
        region: str,
        current_price: float,
        cpu_avg: float,
        cpu_max: float,
        network_gb_total: float,
        mem_avg: float = 0.0,  # Optional memory data
        idle_cpu_threshold: float = 2.0,  # Max CPU to be considered idle
) -> dict:
    """
    Generates a prompt to get an EC2 rightsizing or termination recommendation.
    """
    HOURS_PER_MONTH = 730
    prompt = ""

    # 1. Choose the correct prompt based on usage
    if cpu_max < idle_cpu_threshold:
        # --- IDLE INSTANCE PROMPT ---
        savings = round(current_price * HOURS_PER_MONTH, 2)
        prompt = f"""
You are an expert AWS FinOps engineer.

The following EC2 instance appears to be completely idle or unused based on its metrics over the last 14 days.

### Instance Details & Metrics
- **Instance ID:** {instance_id}
- **Instance Type:** {instance_type}
- **Region:** {region}
- **CPU Utilization (Maximum):** {cpu_max:.1f}%
- **Network Traffic (Total GB):** {network_gb_total} GB
- **Current Hourly Price:** ${current_price:.4f} USD

### Your Recommendation
Your entire response MUST be ONLY the following key-value pairs in this exact format. Do not add any other text.

**Suggested Instance Type:** Terminate
**Reasoning:** The instance shows no significant CPU or network activity.
**Estimated Monthly Savings:** ${savings}
**Notes:** Before termination, confirm the instance is not required for disaster recovery or other specific, intermittent needs. Create a final snapshot if data preservation is necessary.
"""
    else:
        # --- UNDERUTILIZED (RIGHTSIZING) INSTANCE PROMPT ---
        prompt = f"""
You are an expert AWS FinOps engineer specializing in EC2 cost optimization.

Your task is to analyze the following EC2 instance's metrics and recommend a modern, more cost-effective instance type. Prioritize ARM-based Graviton instances (like t4g, m7g, c7g) where appropriate, as they offer the best price-performance.

### Current Instance Details
- **Instance ID:** {instance_id}
- **Instance Type:** {instance_type}
- **Architecture:** {architecture}
- **Region:** {region}
- **Current Hourly Price:** ${current_price:.4f} USD

### Performance Metrics (14-day period)
- **CPU Utilization (Average):** {cpu_avg:.1f}%
- **CPU Utilization (Maximum):** {cpu_max:.1f}%
- **Memory Utilization (Average):** {mem_avg:.1f}% (if available)
- **Network Traffic (Total GB):** {network_gb_total} GB

### Your Recommendation
Your entire response MUST be ONLY the following key-value pairs in this exact format. Do not add any other text, explanations, or introductory sentences.

**Suggested Instance Type:** [The new instance type, e.g., t4g.medium]
**Reasoning:** [A concise, one-sentence explanation for the choice.]
**Estimated Monthly Savings:** $[The estimated monthly savings as a number]
**Notes:** [Any critical warnings, e.g., "Requires application compatibility with ARM64/Graviton."]
"""

    # 2. Call the AI model and parse the response
    from infra_review_cli.core.ai.llm_client import call_ai
    response_text = call_ai(prompt)
    suggestion = _parse_ec2_suggestion(response_text)

    if not response_text or not isinstance(response_text, str):
        print(f"⚠️ AI call returned invalid response for {instance_id}. Got: {response_text}")
        return {}  # No suggestion

    return suggestion

