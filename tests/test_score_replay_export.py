import copy
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/'tools/build_score_replay.py'
spec=importlib.util.spec_from_file_location('replay_export',P);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ReplayExportTests(unittest.TestCase):
    def fixture(self):
        labels=[dict(id='one',text='Synthetic post',instruction='Keep tech.',source='https://example.org',kind='tech',split='development',label='keep',reviewed=True)]
        row=dict(id='one',input='Synthetic post',rule='Keep tech.',fixedQuestion='Filtering instruction:\nKeep tech.\n\nDoes this post pass the filter?',label='keep',split='development',condition='actual',template='minimal-prefix',batchSize=1,questionType='noul',yesMeansKeep=True,pKeep=.6,callMs=10,candidate='fixture',device='webgpu',dtype='q8f16',revision='fixture',modelMeta={})
        return labels,dict(cases=copy.deepcopy(labels),rows=[row],at='fixture')
    def test_preserves_text_labels_identity_and_version(self):
        labels,source=self.fixture();result=mod.build(labels,[('fixture','sourcehash',source)])
        self.assertEqual(result['cases'],labels);self.assertEqual(result['captures'][0]['rows'][0]['pKeep'],.6)
        source['rows'][0]['pKeep']=.7
        self.assertNotEqual(result['version'],mod.build(labels,[('fixture','sourcehash',source)])['version'])
    def test_rejects_wrong_split_input_rule_duplicate_or_batch(self):
        for field,value in [('input','Changed'),('rule','Changed'),('batchSize',4),('pKeep',float('nan'))]:
            labels,source=self.fixture();source['rows'][0][field]=value
            with self.assertRaises(ValueError):mod.build(labels,[('fixture','hash',source)])
        labels,source=self.fixture();labels[0]['split']='heldout'
        with self.assertRaises(ValueError):mod.build(labels,[('fixture','hash',source)])
        labels,source=self.fixture();source['rows']*=2
        with self.assertRaises(ValueError):mod.build(labels,[('fixture','hash',source)])
    def test_output_cannot_escape_ignored_directory_or_follow_symlink(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'local-results').mkdir()
            self.assertEqual(mod.safe_output(root/'local-results'/'replay.json',root),(root/'local-results'/'replay.json').resolve())
            with self.assertRaises(ValueError):mod.safe_output(root/'local-results'/'..'/'public.json',root)
            (root/'elsewhere').mkdir();(root/'local-results'/'link').symlink_to(root/'elsewhere',target_is_directory=True)
            with self.assertRaises(ValueError):mod.safe_output(root/'local-results'/'link'/'replay.json',root)
            (root/'local-results'/'file.json').symlink_to(root/'local-results'/'another.json')
            with self.assertRaises(ValueError):mod.safe_output(root/'local-results'/'file.json',root)
