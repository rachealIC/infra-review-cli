

from enum import Enum
from dataclasses import dataclass

class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class Effort(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class Pillar(str, Enum):
    SECURITY = "Security"
    COST = "Cost Optimization"
    RELIABILITY = "Reliability"
    PERFORMANCE = "Performance Efficiency"
    OPERATIONAL = "Operational Excellence"
    SUSTAINABILITY = "Sustainability"

@dataclass
class Finding:
    finding_id: str
    resource_id: str
    region: str
    pillar: Pillar
    severity: Severity
    headline: str
    detailed_description: str
    remediation_steps: str
    effort: Effort
    estimated_savings: float = 0.0 
