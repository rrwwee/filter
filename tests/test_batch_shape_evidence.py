"""Verify the preserved tensor interventions and arithmetic without model inference."""
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BatchShapeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_path = ROOT / 'measurements/browser-batch-shape-2026-10-22.raw.json'
        cls.raw = json.loads(cls.raw_path.read_text())
        cls.summary = json.loads((ROOT / 'measurements/browser-batch-shape-2026-10-22.json').read_text())

    def test_provenance_and_frozen_boundaries(self):
        for field, path in [('rawSha256', self.raw_path),
                            ('planSha256', ROOT / 'docs/research/browser-batch-shape-plan-2026-10-22.md'),
                            ('driverSha256', ROOT / 'tests/fixtures/browser-batch-shape.html')]:
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.summary[field])
        self.assertEqual(self.raw['parityTolerance'], .001)
        self.assertEqual(self.raw['decisionThreshold'], .5)
        self.assertEqual(self.raw['revision'], '53da62af62275ff5076e29b962dd965f38107c50')
        self.assertEqual(self.raw['modelHash'], '80436dbed1a284548b5e6c3975bb26df81fb493fc4e64629e5a6ef490bf0e0ae')
        self.assertEqual([b['actualDevice'] for b in self.raw['backends']], ['webgpu', 'wasm'])
        for b in self.raw['backends']:
            self.assertTrue(b['complete'] and b['modelReleased'])
            self.assertEqual(b['dtype'], 'q8f16')
            self.assertTrue(all(p['cached'] for p in b['progress']))
            self.assertEqual(len(b['passes']), 11)

    def test_tensor_identity_mask_and_option_mapping(self):
        for b in self.raw['backends']:
            passes = {p['phase']: p for p in b['passes']}
            for p in passes.values():
                B, L = p['shape']
                self.assertEqual(p['inputTypes'], {'ids': 'int64', 'mask': 'int64'})
                self.assertEqual(p['outputType'], 'float32')
                self.assertEqual(len(p['ids']), B * L)
                self.assertEqual(len(p['mask']), B * L)
                f = {k: p[k] for k in ('inputTypes', 'shape', 'ids', 'mask')}
                encoded = json.dumps(f, separators=(',', ':')).encode()
                self.assertEqual(hashlib.sha256(encoded).hexdigest(), p['feedHash'])
                for score in p['scores']:
                    a, z = score['logits']
                    expected = 1 / (1 + math.exp(z - a))
                    self.assertAlmostEqual(score['pKeep'], expected, places=14)
            base = passes['api-single-0']
            padded = passes['single-padded']
            zero = passes['single-padded-masked-zero']
            self.assertEqual(base['ids'], padded['ids'][:96])
            self.assertEqual(padded['ids'][96:], [50283] * 7)
            self.assertEqual(padded['mask'], [1] * 96 + [0] * 7)
            self.assertEqual(zero['ids'][:96], base['ids'])
            self.assertEqual(zero['ids'][96:], [0] * 7)
            self.assertEqual(zero['mask'], padded['mask'])
            for name, source, count in [('two-duplicate-native', base, 2), ('four-duplicate-padded', padded, 4)]:
                self.assertEqual(passes[name]['ids'], source['ids'] * count)
                self.assertEqual(passes[name]['mask'], source['mask'] * count)
            for name, original in [('exact-single-repeat', base), ('exact-batch-repeat', passes['api-batch'])]:
                self.assertEqual(passes[name]['feedHash'], original['feedHash'])
                self.assertEqual(passes[name]['scores'], original['scores'])
            batch = passes['api-batch']; L = batch['shape'][1]
            used = []
            for i, output in enumerate(b['sequential']):
                single = passes[f'api-single-{i}']
                self.assertAlmostEqual(single['scores'][0]['pKeep'], output['answers']['keep']['noul'], places=14)
                matching = [r for r in range(4) if r not in used and
                            [token for token, mask in zip(batch['ids'][r*L:(r+1)*L], batch['mask'][r*L:(r+1)*L]) if mask] == single['ids']]
                self.assertTrue(matching)
                r = matching[0]; used.append(r)
                self.assertAlmostEqual(batch['scores'][r]['pKeep'], b['batch'][i]['answers']['keep']['noul'], places=14)

    def test_summary_retains_numeric_failure_and_separate_decisions(self):
        for b, s in zip(self.raw['backends'], self.summary['backends']):
            pairs = [(x['answers']['keep']['noul'], y['answers']['keep']['noul']) for x, y in zip(b['batch'], b['sequential'])]
            self.assertEqual(max(abs(x-y) for x,y in pairs), s['maxApiBatchSequentialDelta'])
            self.assertEqual(sum((x >= .5) != (y >= .5) for x,y in pairs), s['apiDecisionFlipsAt050'])
            p = {x['phase']: x['scores'][0]['pKeep'] for x in b['passes']}
            for field, a, z in [('paddingDelta', 'single-padded', 'api-single-0'),
                                ('maskedTokenDelta', 'single-padded-masked-zero', 'single-padded'),
                                ('batchDimensionNativeDelta', 'two-duplicate-native', 'api-single-0'),
                                ('batchDimensionPaddedDelta', 'four-duplicate-padded', 'single-padded'),
                                ('singleRepeatDelta', 'exact-single-repeat', 'api-single-0')]:
                self.assertEqual(s[field], p[a]-p[z])
            self.assertEqual(s['apiDecisionFlipsAt050'], 0)
        gpu, cpu = self.summary['backends']
        self.assertGreater(gpu['maxApiBatchSequentialDelta'], self.raw['parityTolerance'])
        self.assertEqual(cpu['maxApiBatchSequentialDelta'], 0)
