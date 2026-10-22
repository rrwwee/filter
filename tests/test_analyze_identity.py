import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1]/'prototypes/model-evaluation/analyze.py'


class AnalysisIdentityTests(unittest.TestCase):
    def run_rows(self, rows, **capture):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'results.json'
            file.write_text(json.dumps({'runtime':'fixture-runtime','rows':rows,**capture}))
            return subprocess.run([sys.executable,str(SCRIPT),str(file),'--threshold','0.5'],capture_output=True,text=True,check=True).stdout

    def row(self, **changes):
        return dict(id='same-case',candidate='fixture',dtype='fp32',device='cpu',revision='one',template='keep-question',
                    condition='actual',rule='Keep useful posts.',fixedQuestion='Keep?',questionType='noul',yesMeansKeep=True,
                    batchSize=1,callStarted=1,callMs=2,pKeep=.9,label='keep',split='development',**changes)

    def test_opposite_predictions_under_two_templates_remain_separate(self):
        first=self.row();second={**first,'template':'hide-question','fixedQuestion':'Hide?','pKeep':.1,'callStarted':2}
        output=self.run_rows([first,second])
        self.assertEqual(sum('median_call_ms' in line for line in output.splitlines()),2,output)
        self.assertIn('wanted_kept 1/1',output);self.assertIn('wanted_kept 0/1',output)

    def test_model_revision_device_and_execution_configuration_are_distinct(self):
        first=self.row()
        variants=[first,{**first,'revision':'two'},{**first,'device':'wasm'},
                  {**first,'modelMeta':{'weights':'different'}},{**first,'batchSize':4}]
        output=self.run_rows(variants)
        self.assertEqual(sum('median_call_ms' in line for line in output.splitlines()),len(variants),output)


    def test_missing_row_identity_is_not_inferred_from_last_loaded_model(self):
        row=self.row()
        for key in ('candidate','revision','modelMeta'):
            row.pop(key,None)
        output=self.run_rows([row],loadInfo={'candidate':'final-model','revision':'final-revision','modelMeta':{'private':'final'}})
        identity=json.loads(output.split(' rows ',1)[0].removeprefix('identity '))
        self.assertIsNone(identity['candidate']);self.assertIsNone(identity['revision']);self.assertIsNone(identity['modelMeta'])
        self.assertIsNone(identity['runtime'])
        self.assertEqual(identity['captureContext']['runtime'],'fixture-runtime')
