import copy
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'prototypes/model-finetuning/factorial_summary.py'
spec=importlib.util.spec_from_file_location('factorial_summary',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class SummaryTests(unittest.TestCase):
    def fixture(self):
        variants=[{'id':f'v{i}','rule_index':0,'polarity':'hide','labels':'boolean','order':order}
                  for i,order in enumerate(['forward','reverse'])]
        rows=[]
        for v in variants:
            for label in [False,True]:
                for injected in [False,True]:
                    rows.append({'id':f'{label}-{injected}','variant':v['id'],'group':'one','injected':injected,
                                 'expected_hide':label,'p_hide':.8 if label else .2,'p_true':.8 if label else .2,'true_logit_margin':1. if label else -1.})
            rows.append({'id':'empty','variant':v['id'],'group':'empty','injected':False,'expected_hide':None,'p_hide':.9,'p_true':.9,'true_logit_margin':2.})
        return {'rows':rows,'seconds':1.,'peak_rss_bytes_macos':100},variants

    def test_empty_controls_never_count_as_correct_or_incorrect(self):
        data,variants=self.fixture();summary=m.summarize(data,variants)
        self.assertEqual(summary['conditions']['v0']['n'],4)
        self.assertEqual(summary['conditions']['v0']['correct'],4)
        self.assertEqual(summary['empty_baselines'],2)
        self.assertEqual(summary['factor_sensitivity']['order']['semantic_decision_flips'],0)

    def test_missing_duplicate_or_labeled_empty_outputs_fail(self):
        data,variants=self.fixture()
        for mutate in [lambda r:r.pop(),lambda r:r.append(copy.deepcopy(r[0])),lambda r:r[-1].update(expected_hide=False)]:
            bad=copy.deepcopy(data);mutate(bad['rows'])
            with self.assertRaises(ValueError):m.summarize(bad,variants)

    def test_duplicate_pair_members_and_changing_metadata_fail(self):
        data,variants=self.fixture()
        duplicates=copy.deepcopy(data)
        for v in variants:
            extra=copy.deepcopy(next(r for r in data['rows'] if r['variant']==v['id'] and r['id']=='False-False'))
            extra['id']='another-case';duplicates['rows'].append(extra)
        with self.assertRaisesRegex(ValueError,'duplicate semantic pair'):
            m.summarize(duplicates,variants)
        changed=copy.deepcopy(data)
        changed['rows'][5]['group']='different'
        with self.assertRaisesRegex(ValueError,'metadata changes'):
            m.summarize(changed,variants)
