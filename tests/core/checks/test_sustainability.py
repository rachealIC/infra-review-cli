import unittest

from infra_review_cli.core.checks.sustainability import (
    check_graviton_instance_usage,
    check_lambda_overprovisioned_memory,
    check_s3_lifecycle_policies,
    suggest_graviton_equivalent,
)


class TestSustainabilityChecks(unittest.TestCase):
    def test_suggest_graviton_equivalent_common_families(self):
        self.assertEqual(suggest_graviton_equivalent('t3.medium'), 't4g.medium')
        self.assertEqual(suggest_graviton_equivalent('m5.large'), 'm6g.large')
        self.assertEqual(suggest_graviton_equivalent('c6i.xlarge'), 'c6g.xlarge')
        self.assertIsNone(suggest_graviton_equivalent('m6g.large'))

    def test_graviton_check_flags_non_graviton_instances(self):
        findings = check_graviton_instance_usage(
            [
                {'instance_id': 'i-1', 'instance_type': 't3.medium', 'current_price': 0.05},
                {'instance_id': 'i-2', 'instance_type': 't4g.medium', 'current_price': 0.04},
            ],
            region='us-east-1',
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].resource_id, 'i-1')
        self.assertGreater(findings[0].estimated_savings, 0)

    def test_s3_lifecycle_flags_missing_policy(self):
        findings = check_s3_lifecycle_policies(
            [
                {'Name': 'logs-bucket', 'HasLifecycleRules': False},
                {'Name': 'archive-bucket', 'HasLifecycleRules': True},
            ],
            region='us-east-1',
        )

        self.assertEqual(len(findings), 1)
        self.assertIn('no lifecycle policy', findings[0].headline.lower())

    def test_lambda_memory_check_uses_2x_threshold(self):
        findings = check_lambda_overprovisioned_memory(
            [
                {'FunctionName': 'fn-over', 'ConfiguredMemoryMB': 1024, 'MaxMemoryUsedMB': 300},
                {'FunctionName': 'fn-ok', 'ConfiguredMemoryMB': 512, 'MaxMemoryUsedMB': 300},
            ],
            region='us-east-1',
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].resource_id, 'fn-over')


if __name__ == '__main__':
    unittest.main()
