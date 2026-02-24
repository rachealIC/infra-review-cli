import hashlib
import re
from datetime import datetime


def generate_finding_id(check_id: str, resource_id: str, region: str) -> str:
    """Generates a deterministic, unique ID for a finding."""
    # Create a unique string from the core properties
    unique_string = f"{check_id}-{resource_id}-{region}"

    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()[:16]


def extract_number(text: str) -> str:
    """Extracts the first number (int or float) from a string."""
    match = re.search(r"[\d]+(?:\.\d+)?", text)
    return match.group(0) if match else "0.0"


def generate_filename(fmt: str) -> str:
    """Generate a timestamped filename like 'infra_report_20240723.html'"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"infra_report_{timestamp}.{fmt.lower()}"
