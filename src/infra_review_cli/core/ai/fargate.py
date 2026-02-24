import re




def extract_cpu_memory_savings(response_text: str) -> dict:
    """
    Parses AI response into a dict with CPU, memory, and savings.
    Handles both keyword-based and line-based formats.
    """
    try:
        print("🧪 Parsing response:", response_text)
        lines = [line.strip() for line in response_text.strip().splitlines() if line.strip()]

        cpu = None
        mem = None
        savings = 0.0

        for line in lines:
            # Try to find CPU (e.g., "256 mCPU")
            if re.search(r'mcpu', line, re.IGNORECASE):
                cpu_match = re.search(r'(\d{3,4})', line)
                if cpu_match:
                    cpu = int(cpu_match.group(1))

            # Try to find memory (e.g., "2048 MB")
            elif re.search(r'mb', line, re.IGNORECASE):
                mem_match = re.search(r'(\d{3,5})', line)
                if mem_match:
                    mem = int(mem_match.group(1))

            # Try to find savings (e.g., "$22.16" or "22.16 USD")
            elif re.search(r'\$|usd', line, re.IGNORECASE):
                savings_match = re.search(r'(\d+(\.\d+)?)', line)
                if savings_match:
                    savings = float(savings_match.group(1))

        # Fallback: validate values
        if cpu not in [256, 512, 1024, 2048, 4096]:
            print("⚠️ Invalid CPU value from AI")
            cpu = None

        if mem not in list(range(512, 30721, 512)):
            print("⚠️ Invalid memory value from AI")
            mem = None

        if cpu is None or mem is None:
            raise ValueError("Could not extract valid CPU or memory recommendation.")

        return {
            "cpu": cpu,
            "memory": mem,
            "estimated_savings": round(savings, 2)
        }
    except Exception as e:
        print("⚠️ Failed to extract CPU/memory/savings:", e)
        return None


def suggest_cpu_memory(cpu, mem, avg_cpu, avg_mem):
    # --- PROMPT MODIFICATION ---
    # The prompt is rewritten to be extremely specific about the output format.
    prompt = f"""
    You are an AWS cost optimization expert.
    A Fargate task has these stats:
    - CPU provisioned: {cpu} mCPU
    - Memory provisioned: {mem} MB
    - Average CPU used: {avg_cpu:.1f}%
    - Average Memory used: {avg_mem:.1f}%

    Recommend a smaller AWS Fargate CPU/memory configuration that provides 20-30% headroom above the average usage.

    Use these valid AWS Fargate combinations:
    - 256 mCPU: 512, 1024, 2048 MB
    - 512 mCPU: 1024-4096 MB (in 1024 MB increments)
    - 1024 mCPU: 2048-8192 MB (in 1024 MB increments)
    - 2048 mCPU: 4096-16384 MB (in 1024 MB increments)
    - 4096 mCPU: 8192-30720 MB (in 1024 MB increments)

    **IMPORTANT**: Your entire response MUST be ONLY the following three lines, with no other text, explanation, or notes.

    Example of the required format:
    CPU: 256 mCPU
    Memory: 512 MB
    Savings: $10.55

    Now, provide the recommendation for the given stats in that exact format.
    """
    # --- END OF MODIFICATION ---

    try:
        from infra_review_cli.core.ai.llm_client import call_ai
        response = call_ai(prompt)
        if not response:
            return None
    except Exception:
        return None

    suggestion = extract_cpu_memory_savings(response)

    if suggestion is None:
        print("⚠️ Could not extract a valid suggestion.")
        return None

    # Check if AI just echoed the same input
    if suggestion["cpu"] == cpu and suggestion["memory"] == mem:
        print("ℹ️ Already using minimum config or no better suggestion found.")
        suggestion[
            "note"] = "Already at smallest Fargate config. Consider shutting down idle tasks or switching to Lambda if idle."

    return suggestion