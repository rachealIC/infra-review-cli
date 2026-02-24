# tests/core/checks/test_ec2_rightsizing.py

import unittest
from unittest.mock import patch
from infra_review_cli.core.checks.ec2 import check_ec2_rightsizing
from infra_review_cli.core.models import Finding

class TestEC2Rightsizing(unittest.TestCase):
    
    @patch("infra_review_cli.core.checks.ec2.suggest_ec2_rightsizing")
    def test_underutilized_instances_are_flagged(self, mock_suggest):
        # Mock the AI suggestion
        mock_suggest.return_value = {
            "suggested_instance_type": "t4g.small",
            "reasoning": "Low CPU usage.",
            "estimated_monthly_savings": 15.0,
            "notes": "Test note"
        }

        instance_data = [
            {
                "instance_id": "i-low-1",
                "cpu_avg": 5.0,
                "cpu_max": 25.0,
                "instance_type": "t3.medium",
                "region": "us-east-1",
                "current_price": 0.0416
            },
            {
                "instance_id": "i-ok-1",
                "cpu_avg": 45.0,
                "cpu_max": 80.0,
                "instance_type": "t3.medium",
                "region": "us-east-1",
                "current_price": 0.0416
            }
        ]

        # Use a threshold of 20%
        findings = check_ec2_rightsizing(instance_data, threshold=20.0)
        flagged_ids = [f.resource_id for f in findings]

        self.assertIn("i-low-1", flagged_ids)
        self.assertNotIn("i-ok-1", flagged_ids)
        self.assertEqual(len(findings), 1)
        
        finding = findings[0]
        self.assertEqual(finding.resource_id, "i-low-1")
        self.assertEqual(finding.estimated_savings, 15.0)

if __name__ == "__main__":
    unittest.main()
