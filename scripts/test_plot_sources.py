"""Retained plot-data checks without rerunning the controller or drawing PDFs."""
from pathlib import Path
from fractions import Fraction as Q
import importlib.util
import json
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('plot_retained', ROOT / 'scripts/plot_retained.py')
ROUTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTE)

class PlotSources(unittest.TestCase):
    def test_theorem_and_slot_coverage(self):
        reserve, controller = ROUTE.validate_inputs(ROOT / 'results')
        self.assertEqual(Q(reserve[0]['theta_exact']), 0)
        self.assertEqual(Q(reserve[-1]['theta_exact']), Q(19, 20))
        self.assertEqual([int(r['slot']) for r in controller], list(range(1, 65)))

    def test_every_controller_point_binds_saved_prices(self):
        _, data = ROUTE.validate_inputs(ROOT / 'results')
        pipeline = json.loads((ROOT / 'results/control_pipeline.json').read_text())
        runs = [r for r in pipeline['runs'] if r['delay'] == 2 and r['start'] == ['4/5', '1']]
        self.assertEqual(len(runs), 2)
        for run in runs:
            mode = run['grid_mode']
            self.assertEqual(len(run['records']), 64)
            for row, record in zip(data, run['records']):
                self.assertEqual(int(row['slot']), record['slot'] + 1)
                price = list(map(Q, record['price']))
                error = max(abs(p - Q(9, 10)) for p in price)
                self.assertEqual(Q(record['state_error']), error)
                self.assertEqual(row[mode], format(float(error), '.14g'))
                self.assertEqual(row[mode + '_bound'], format(float(Q(record['state_bound'])), '.14g'))

    def test_zero_is_rejected_not_silently_filtered_on_log_axis(self):
        reserve, controller = ROUTE.validate_inputs(ROOT / 'results')
        bad = [dict(r) for r in controller]
        bad[0]['constant'] = '0'
        with patch.object(ROUTE, 'read_rows', side_effect=[reserve, bad]):
            with self.assertRaisesRegex(ValueError, 'logarithmic-domain'):
                ROUTE.validate_inputs(ROOT / 'results')

    def test_isolated_route_refuses_paper_and_existing_figures(self):
        for destination in (ROOT.parent / 'paper/figures', ROOT / 'figures', ROOT / 'results'):
            with self.assertRaises(ValueError):
                ROUTE.isolated_output(destination, ROOT / 'results')

if __name__ == '__main__':
    unittest.main()
