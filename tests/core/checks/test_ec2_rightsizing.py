# tests/core/checks/test_ec2_rightsizing.py

import unittest
from src.infra_review_cli.core.checks.ec2 import check_ec2_rightsizing

class TestEC2Rightsizing(unittest.TestCase):
    def test_underutilized_instances_are_flagged(self):
        cpu_data = {
            "i-low-1": [12.1, 9.8, 13.5],      # Under threshold
            "i-low-2": [35.2, 38.9],           # Under threshold
            "i-ok":    [50.1, 65.3],           # Over threshold
        }

        findings = check_ec2_rightsizing(cpu_data, region="us-east-1")
        flagged_ids = [f.resource_id for f in findings]

        self.assertIn("i-low-1", flagged_ids)
        self.assertIn("i-low-2", flagged_ids)
        self.assertNotIn("i-ok", flagged_ids)
        self.assertEqual(len(findings), 2)

if __name__ == "__main__":
    unittest.main()
