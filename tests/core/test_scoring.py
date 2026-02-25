import unittest
import sys
import types

# Allow imports in minimal environments where optional deps are unavailable.
if 'dotenv' not in sys.modules:
    dotenv_stub = types.ModuleType('dotenv')
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    sys.modules['dotenv'] = dotenv_stub

from infra_review_cli.core.models import Pillar, PillarScore
from infra_review_cli.core.scoring import overall_health_score


class TestOverallHealthScore(unittest.TestCase):
    @staticmethod
    def make_score(pillar: Pillar, score: float, checks: int) -> PillarScore:
        return PillarScore(
            pillar=pillar,
            score=score,
            total_checks_run=checks,
            findings_count=0,
        )

    def test_overall_score_excludes_unscanned_pillars(self):
        pillar_scores = {
            Pillar.SECURITY.value: self.make_score(Pillar.SECURITY, 50.0, 2),
            Pillar.COST.value: self.make_score(Pillar.COST, 100.0, 0),
        }

        # Cost pillar has zero checks and must not influence overall score.
        self.assertEqual(overall_health_score(pillar_scores), 50.0)

    def test_overall_score_uses_only_scanned_weighted_pillars(self):
        pillar_scores = {
            Pillar.SECURITY.value: self.make_score(Pillar.SECURITY, 70.0, 3),
            Pillar.RELIABILITY.value: self.make_score(Pillar.RELIABILITY, 40.0, 2),
            Pillar.OPERATIONAL.value: self.make_score(Pillar.OPERATIONAL, 100.0, 0),
        }

        # Weighted average among scanned pillars only:
        # (70*2 + 40*2) / (2+2) = 55.0
        self.assertEqual(overall_health_score(pillar_scores), 55.0)


if __name__ == '__main__':
    unittest.main()
