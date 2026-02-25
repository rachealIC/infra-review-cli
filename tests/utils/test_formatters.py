import unittest
from unittest.mock import patch
import sys
import types

# Allow formatter imports in minimal environments without jinja2 installed.
if 'jinja2' not in sys.modules:
    jinja2_stub = types.ModuleType('jinja2')

    class _Environment:
        def __init__(self, *args, **kwargs):
            pass

        def get_template(self, *args, **kwargs):
            raise RuntimeError('Template rendering should be mocked in this test.')

    class _FileSystemLoader:
        def __init__(self, *args, **kwargs):
            pass

    jinja2_stub.Environment = _Environment
    jinja2_stub.FileSystemLoader = _FileSystemLoader
    sys.modules['jinja2'] = jinja2_stub

from infra_review_cli.core.models import Pillar, PillarScore, ScanResult
from infra_review_cli.utils import formatters


class TestHtmlFormatterPillarMetadata(unittest.TestCase):
    @patch('infra_review_cli.utils.formatters.render_html_report')
    def test_format_as_html_adds_pillar_scan_metadata(self, mock_render_html):
        captured = {}

        def fake_render(data):
            captured.update(data)
            return 'ok'

        mock_render_html.side_effect = fake_render

        result = ScanResult(
            account_id='123456789012',
            region='us-east-1',
            scan_timestamp='2026-02-25 10:00:00 UTC',
            overall_score=75,
            executive_summary='summary',
            pillar_scores={
                Pillar.SECURITY.value: PillarScore(
                    pillar=Pillar.SECURITY,
                    score=75.0,
                    total_checks_run=2,
                    findings_count=1,
                    critical_count=1,
                ),
                Pillar.SUSTAINABILITY.value: PillarScore(
                    pillar=Pillar.SUSTAINABILITY,
                    score=100.0,
                    total_checks_run=0,
                    findings_count=0,
                ),
            },
        )

        html = formatters.format_as_html(result)

        self.assertEqual(html, 'ok')
        self.assertTrue(captured['report_id'].startswith('IR-123456789012-'))
        self.assertIn('app_version', captured)
        self.assertIn('scan_duration', captured)

        pillars = {pillar['name']: pillar for pillar in captured['pillars']}

        security = pillars[Pillar.SECURITY.value]
        self.assertTrue(security['scanned'])
        self.assertEqual(security['total_checks_run'], 2)
        self.assertEqual(security['score_display'], 75)
        self.assertEqual(security['status_tone'], 'good')
        self.assertIn('not a resource count', security['score_explainer'])

        sustainability = pillars[Pillar.SUSTAINABILITY.value]
        self.assertFalse(sustainability['scanned'])
        self.assertEqual(sustainability['total_checks_run'], 0)
        self.assertEqual(sustainability['score_display'], 'N/A')
        self.assertEqual(sustainability['status'], 'NOT SCANNED')
        self.assertEqual(sustainability['status_tone'], 'neutral')


if __name__ == '__main__':
    unittest.main()
