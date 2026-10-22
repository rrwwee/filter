"""Fail-closed checks for local raw experiment inputs. No inference or label oracle."""
import hashlib
import json
import math
from pathlib import Path
import re

SPLITS = ('train', 'validation', 'test')
IDENTITY = ('post_id', 'policy_id', 'family', 'suite', 'pair_id', 'style', 'origin')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def normalized(text):
    return re.sub(r'\W+', ' ', text.casefold()).strip()


def read_dataset(directory, required_test_families=()):
    """Validate exact hashes/counts, labels and post-level exact split separation.

    This does not detect paraphrases, establish semantic label truth, or establish
    that test data were genuinely unseen during prior experimentation.
    """
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    require(isinstance(manifest, dict), 'manifest must be an object')
    data, by_post, texts = {}, {}, {}
    for split in SPLITS:
        raw = (directory / (split + '.jsonl')).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(manifest.get('hashes', {}).get(split) == digest, f'{split}: hash mismatch')
        rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
        require(bool(rows), f'{split}: empty split')
        seen, posts, inputs = set(), {}, {}
        for row in rows:
            require(isinstance(row, dict), f'{split}: row must be an object')
            for key in ('id', 'post_id', 'policy_id', 'family', 'suite', 'style', 'origin', 'state', 'instruction'):
                require(isinstance(row.get(key), str) and bool(row[key].strip()), f'{split}: invalid {key}')
            require(row['id'] not in seen, f'{split}: duplicate row ID')
            seen.add(row['id'])
            require('gold' not in row, f'{split}: gold overrides are not supported; expected.hide is authoritative')
            require(isinstance(row.get('expected'), dict) and set(row['expected']) == {'hide'}, f'{split}: expected must contain only hide')
            require(isinstance(row.get('questions'), dict) and set(row['questions']) == {'hide'}, f'{split}: questions must contain only hide')
            require(type(row.get('expected', {}).get('hide')) is bool, f'{split}: hide label must be boolean')
            require(row.get('pair_id') is None or isinstance(row['pair_id'], str) and bool(row['pair_id']), f'{split}: invalid pair ID')
            require(row.get('questions', {}).get('hide', {}).get('instructions') == 'Filtering rules:\n' + row['instruction'] + '\n\nShould this post be hidden?', f'{split}: instruction differs from model input')
            question = row['questions']['hide']
            require(question.get('type') == 'noul' and question.get('criteria') == {'false': 'Keep the post visible.', 'true': 'Hide the post.'}, f'{split}: unsupported hide option mapping')
            text = normalized(row['state'])
            require(bool(text), f'{split}: empty normalized post')
            require(row['post_id'] not in posts or posts[row['post_id']] == text, f'{split}: post ID maps to different text')
            posts[row['post_id']] = text
            key = (text, normalized(row['instruction']))
            require(key not in inputs or inputs[key] == row['expected']['hide'], f'{split}: contradictory duplicate input labels')
            inputs[key] = row['expected']['hide']
        pairs = {}
        for row in rows:
            if row['pair_id']:
                pairs.setdefault(row['pair_id'], []).append(row)
        for pair in pairs.values():
            require(len(pair) == 2 and len({r['post_id'] for r in pair}) == 1 and len({normalized(r['state']) for r in pair}) == 1 and {r['expected']['hide'] for r in pair} == {False, True}, f'{split}: invalid opposite pair')
        require({r['expected']['hide'] for r in rows} == {False, True}, f'{split}: both label classes required')
        counts = {'rows': len(rows), 'posts': len(posts), 'hide': sum(r['expected']['hide'] for r in rows)}
        recorded = manifest.get('counts', {}).get(split)
        require(isinstance(recorded, dict) and all(type(recorded.get(k)) is int and recorded[k] == v for k, v in counts.items()), f'{split}: manifest counts differ from data')
        data[split], by_post[split], texts[split] = rows, set(posts), set(posts.values())
    for i, first in enumerate(SPLITS):
        for second in SPLITS[i + 1:]:
            require(not by_post[first] & by_post[second], f'{first}/{second}: post ID leakage')
            require(not texts[first] & texts[second], f'{first}/{second}: normalized post-text leakage')
    for family in required_test_families:
        group = [r for r in data['test'] if r['family'] == family]
        require(bool(group), f'test: required family {family} is empty')
        require({r['expected']['hide'] for r in group} == {False, True}, f'test: required family {family} lacks both classes')
    return manifest, data


def checkpoint_identity(directory):
    """Hash actual local files; a fingerprint is not proof of upstream origin."""
    directory = Path(directory)
    require(directory.is_dir(), 'checkpoint directory missing')
    files = {}
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(), 'checkpoint symlink is not a stable artifact')
        if path.is_file():
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            files[str(path.relative_to(directory))] = digest.hexdigest()
    require(bool(files), 'checkpoint has no files')
    return {'files': files, 'sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}


def prediction_rows(rows, records):
    """Convert binary calibration records without silent zip truncation."""
    records = list(records)
    require(len(rows) == len(records), 'prediction count does not match input count')
    require(bool(rows), 'no input rows')
    out = []
    for row, record in zip(rows, records):
        require(len(record) == 4, 'calibration record must have four fields')
        values = record[1]
        require(len(values) == 2, 'binary hide decision requires exactly two logits')
        z = [float(value) for value in values]
        require(all(math.isfinite(value) for value in z), 'nonfinite logit')
        exp = [math.exp(value - max(z)) for value in z]
        p = [value / sum(exp) for value in exp]
        out.append({key: row[key] for key in ('id',) + IDENTITY} | {
            'expected_hide': row['expected']['hide'], 'p_hide': p[1],
            'p_keep': p[0], 'logits': z})
    return out


def validate_predictions(source, predictions):
    require(isinstance(predictions, list) and len(predictions) == len(source), 'prediction population differs from source')
    expected = {row['id']: row for row in source}
    require(len(expected) == len(source) and bool(source), 'source IDs duplicate or empty')
    seen = set()
    for row in predictions:
        require(isinstance(row, dict) and row.get('id') in expected, 'unknown prediction ID')
        require(row['id'] not in seen, 'duplicate prediction ID')
        seen.add(row['id'])
        original = expected[row['id']]
        require(all(row.get(key) == original.get(key) for key in IDENTITY), 'prediction metadata differs from source')
        require(type(row.get('expected_hide')) is bool and row['expected_hide'] == original['expected']['hide'], 'prediction label differs from source')
        for key in ('p_hide', 'p_keep'):
            require(finite_number(row.get(key)) and 0 <= row[key] <= 1, 'invalid probability')
        require(abs(row['p_hide'] + row['p_keep'] - 1) < 1e-7, 'probabilities do not sum to one')
        logits = row.get('logits')
        require(isinstance(logits, list) and len(logits) == 2 and all(finite_number(x) for x in logits), 'invalid binary logits')
        exp = [math.exp(x - max(logits)) for x in logits]
        require(abs(row['p_hide'] - exp[1] / sum(exp)) < 1e-7, 'probability does not match uncalibrated logits')
    return True


def validate_results(manifest, data, results):
    require(results.get('plan', {}).get('dataset_hashes') == manifest['hashes'], 'result dataset hashes differ')
    require(results.get('test_unlocked_after_training') is True, 'missing recorded test-unlock assertion')
    # An assertion in a file records intent; it cannot prove historical execution order.
    stages = results.get('stages', {})
    require(set(stages) == {'base', 'previous', 'new'}, 'missing or unexpected comparison stage')
    for name, stage in stages.items():
        require(isinstance(stage, dict), f'{name}: invalid stage')
        validate_predictions(data['test'], stage.get('rows'))
    for name in ('validation', 'base_validation'):
        require(isinstance(results.get(name), dict), f'missing {name}')
        validate_predictions(data['validation'], results[name].get('rows'))
    return True


def audit(directory, with_results=False, required_test_families=()):
    manifest, data = read_dataset(directory, required_test_families)
    if with_results:
        validate_results(manifest, data, json.loads((Path(directory) / 'results.json').read_text()))
    coverage = {}
    for split, rows in data.items():
        families = {}
        for family in sorted({r['family'] for r in rows}):
            group = [r for r in rows if r['family'] == family]
            families[family] = {'rows': len(group), 'posts': len({r['post_id'] for r in group}), 'keep': sum(not r['expected']['hide'] for r in group), 'hide': sum(r['expected']['hide'] for r in group)}
        coverage[split] = families
    return {'status': 'PASS', 'scope': 'raw data and comparison integrity, not model quality',
            'dataset_hashes': manifest['hashes'], 'coverage': coverage,
            'results_checked': with_results,
            'limits': ['semantic labels not independently verified', 'no near-duplicate or historical exposure proof', 'expanded rows are correlated; do not treat as independent samples']}


if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--results', action='store_true')
    parser.add_argument('--require-family', action='append', default=[])
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.directory, args.results, args.require_family), indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(json.dumps({'status': 'BLOCKED', 'error': str(error)}))
        sys.exit(1)
