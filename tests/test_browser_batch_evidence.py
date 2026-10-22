"""Keep the published batch diagnostic's arithmetic and failed control honest."""
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BrowserBatchEvidenceTests(unittest.TestCase):
    def test_published_shape_order_and_failed_parity(self):
        data = json.loads((ROOT / 'measurements/browser-batch-contract-2026-10-22.json').read_text())
        rows = data['rows']
        self.assertEqual(len(rows), 4)
        batch = [t for t in data['traces'] if t['phase'] == 'batch']
        singles = [t for t in data['traces'] if t['phase'] == 'sequential']
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]['shape'], [4, 103])
        self.assertEqual(len(singles), 4)
        self.assertTrue(all(t['shape'][0] == 1 for t in singles))
        for i, row in enumerate(rows):
            self.assertTrue(all(math.isfinite(row[k]) and 0 <= row[k] <= 1
                                for k in ('batchProbability', 'sequentialProbability')))
            self.assertAlmostEqual(row['absoluteDelta'], abs(row['batchProbability'] - row['sequentialProbability']))
            self.assertEqual(row['batchTokens'], row['sequentialTokens'])
            self.assertEqual(row['batchTokens'], singles[i]['rows'][0]['tokens'])
        hashes = [t['rows'][0]['sha256'] for t in singles]
        candidates = [[i for i, h in enumerate(hashes) if h == r['sha256']] for r in batch[0]['rows']]
        self.assertEqual(data['internalRowInputCandidates'], candidates)
        self.assertEqual(hashes[0], hashes[2])
        self.assertEqual(rows[0]['batchProbability'], rows[2]['batchProbability'])
        maximum = max(r['absoluteDelta'] for r in rows)
        self.assertEqual(data['maximumAbsoluteDelta'], maximum)
        self.assertEqual(data['parityTolerance'], 0.001)
        self.assertGreater(maximum, data['parityTolerance'])
        self.assertFalse(data['checks']['numericalParity'])
        self.assertTrue(data['checks']['oneFourRowForwardPass'])
        self.assertTrue(data['checks']['cardinality'])
        self.assertTrue(data['checks']['tokenCountOrder'])
        self.assertTrue(data['checks']['duplicateEquality'])
