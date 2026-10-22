"""Polarity must follow meaning after physical option permutation."""
import importlib.util
import math
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]/'prototypes/model-finetuning'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('polarity_probe', SCRIPTS/'polarity_probe.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class PolarityTests(unittest.TestCase):
    def test_swapped_physical_logits_preserve_semantic_probability(self):
        normal = m.canonical_probabilities([2., -1.], [0, 1])
        swapped = m.canonical_probabilities([-1., 2.], [1, 0])
        self.assertEqual(normal, swapped)
        self.assertLess(normal[1], .1)

    def test_question_inversion_moves_hide_to_false(self):
        q, hide, order = m.render_variant('Rule', {'type':'noul','polarity':'keep','order':'reverse'})
        self.assertEqual(hide, 0)
        self.assertEqual(q['criteria']['false'], 'Hide the post.')
        self.assertEqual(order, [1, 0])
        self.assertGreater(m.canonical_probabilities([-1., 2.], order)[hide], .9)

    def test_neutral_labels_follow_descriptions(self):
        q, hide, _ = m.render_variant('Rule', {'type':'choice','polarity':'A-hide','order':'forward'})
        self.assertEqual(list(q['criteria']), ['A', 'B'])
        self.assertEqual(hide, 0)
        self.assertEqual(q['criteria']['A'], 'Hide the post.')

    def test_invalid_outputs_and_mapping_fail(self):
        for logits, order in [([math.nan, 0], [0,1]), ([0], [0,1]), ([0,1], [0,0])]:
            with self.assertRaises(ValueError): m.canonical_probabilities(logits, order)
        with self.assertRaises(ValueError):
            m.render_variant('Rule', {'type':'noul','polarity':'guess','order':'forward'})


if __name__ == '__main__': unittest.main()
