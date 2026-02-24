# src/infra_review_cli/config.py
"""
Central configuration for Infra Review CLI.
All environment variables, thresholds, and constants live here.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# AI Provider Keys
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

# ---------------------------------------------------------------------------
# EC2 / CloudWatch Thresholds
# ---------------------------------------------------------------------------
CPU_UNDERUTIL_THRESHOLD: float = float(os.getenv("CPU_UNDERUTIL_THRESHOLD", "20.0"))
CPU_OVERUTIL_THRESHOLD: float = float(os.getenv("CPU_OVERUTIL_THRESHOLD", "85.0"))
CPU_PEAK_SPIKE_THRESHOLD: float = float(os.getenv("CPU_PEAK_SPIKE_THRESHOLD", "90.0"))
CLOUDWATCH_LOOKBACK_DAYS: int = int(os.getenv("CLOUDWATCH_LOOKBACK_DAYS", "14"))

# ---------------------------------------------------------------------------
# EBS Thresholds
# ---------------------------------------------------------------------------
EBS_MIN_AGE_DAYS: int = int(os.getenv("EBS_MIN_AGE_DAYS", "30"))

# ---------------------------------------------------------------------------
# ECS Thresholds
# ---------------------------------------------------------------------------
ECS_CPU_THRESHOLD: float = float(os.getenv("ECS_CPU_THRESHOLD", "20.0"))
ECS_MEM_THRESHOLD: float = float(os.getenv("ECS_MEM_THRESHOLD", "20.0"))

# ---------------------------------------------------------------------------
# RDS Thresholds
# ---------------------------------------------------------------------------
RDS_MIN_BACKUP_RETENTION_DAYS: int = int(os.getenv("RDS_MIN_BACKUP_RETENTION_DAYS", "7"))

# ---------------------------------------------------------------------------
# Tagging Policy
# ---------------------------------------------------------------------------
REQUIRED_TAGS: list[str] = os.getenv(
    "REQUIRED_TAGS", "Name,Environment,Owner"
).split(",")

# ---------------------------------------------------------------------------
# AWS Region → Pricing API Location mapping
# Extend this when adding support for new regions.
# ---------------------------------------------------------------------------
REGION_LOCATION_MAP: dict[str, str] = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-west-3": "EU (Paris)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-north-1": "EU (Stockholm)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "sa-east-1": "South America (Sao Paulo)",
    "ca-central-1": "Canada (Central)",
    "af-south-1": "Africa (Cape Town)",
    "me-south-1": "Middle East (Bahrain)",
}

# ---------------------------------------------------------------------------
# ELB Pricing constants (hourly, in USD)
# Used when Pricing API is unavailable.
# ---------------------------------------------------------------------------
ELB_HOURLY_PRICE: dict[str, float] = {
    "classic": 0.025,
    "application": 0.0225,
    "network": 0.0225,
    "gateway": 0.0100,
}

# ---------------------------------------------------------------------------
# EBS Fallback Prices (per GB / month, in USD)
# ---------------------------------------------------------------------------
EBS_FALLBACK_PRICES: dict[str, float] = {
    "gp2": 0.10,
    "gp3": 0.08,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.025,
}

# Unassociated Elastic IP: $0.005/hr = $3.65/month
ELASTIC_IP_MONTHLY_FALLBACK: float = 3.65

# ---------------------------------------------------------------------------
# Scoring Weights
# Deducted from 100 per finding of each severity.
# ---------------------------------------------------------------------------
SEVERITY_SCORE_WEIGHTS: dict[str, int] = {
    "Critical": 25,
    "High": 15,
    "Medium": 8,
    "Low": 3,
}

# ---------------------------------------------------------------------------
# Pillar display order (for consistent report ordering)
# ---------------------------------------------------------------------------
PILLAR_DISPLAY_ORDER: list[str] = [
    "Security",
    "Reliability",
    "Operational Excellence",
    "Performance Efficiency",
    "Cost Optimization",
]
