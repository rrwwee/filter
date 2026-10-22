import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'prototypes/model-finetuning'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('factorial_probe',SCRIPTS/'factorial_probe.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class FactorialTests(unittest.TestCase):
    def test_neutral_names_do_not_change_truth_semantics(self):
        q,hide,order=m.question_for('Rule',{'polarity':'keep','labels':'neutral','order':'reverse'})
        self.assertEqual(q['labels'],{'false':'A','true':'B'})
        self.assertEqual(q['criteria']['false'],'Hide the post.')
        self.assertEqual((hide,order),(0,[1,0]))

    def test_empty_baseline_is_not_scored_as_keep(self):
        self.assertFalse(m.scoreable({'expected_hide':None}))
        self.assertFalse(m.scoreable({'expected_hide':0}))
        self.assertTrue(m.scoreable({'expected_hide':False}))

    def test_invalid_factor_cannot_silently_fall_through(self):
        with self.assertRaises(ValueError):
            m.question_for('Rule',{'polarity':'hide','labels':'unknown','order':'forward'})
