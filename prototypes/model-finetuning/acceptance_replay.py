"""Small offline, prediction-blind acceptance replay; never trains or sets thresholds."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import time
from evaluation_contract import binary_record_logits, checkpoint_identity


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(directory):
    # Exclude cache/lock metadata; identify every file actually supplied to the loader.
    return checkpoint_identity(directory, include_cache=False, reject_symlinks=False)


def wilson(correct, count):
    if not count:
        return None
    z = 1.959963984540054
    p = correct / count
    center = (p + z*z/(2*count))/(1+z*z/count)
    radius = z*math.sqrt(p*(1-p)/count+z*z/(4*count*count))/(1+z*z/count)
    return [center-radius, center+radius]


def metrics(rows, threshold):
    wanted = [r for r in rows if not r['expected_hide']]
    unwanted = [r for r in rows if r['expected_hide']]
    correct = sum((r['p_hide'] >= threshold) == r['expected_hide'] for r in rows)
    return {'n': len(rows), 'correct': correct, 'accuracy': correct/len(rows),
            'illustrative_wilson_95': wilson(correct, len(rows)),
            'wanted': len(wanted), 'wanted_kept': sum(r['p_hide'] < threshold for r in wanted),
            'unwanted': len(unwanted), 'unwanted_hidden': sum(r['p_hide'] >= threshold for r in unwanted)}


def run(directory, checkpoint, name):
    # Set before model imports. No Hub calls or network/model downloads are permitted.
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    import importlib.metadata
    import torch
    from laya.train import load_checkpoint, items_from_rows, calibration_records
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan_digest = digest(directory/'plan.json')
    plan = json.loads((directory/'plan.json').read_text())
    dependencies = {'frozen-cases.json': plan['cases_sha256'],
                    'independent-labels.json': plan['review_sha256'],
                    'overlap-audit.json': plan['overlap_sha256'], 'plan.json': plan_digest}
    if any(digest(directory/file) != expected for file, expected in dependencies.items()):
        raise ValueError('frozen dependency changed')
    if plan['thresholds'] != [0.25, 0.5, 0.75]:
        raise ValueError('unexpected threshold plan')
    cases = json.loads((directory/'frozen-cases.json').read_text())
    path = directory/(name+'-results.json')
    if path.exists():
        raise ValueError('results already exist; preserve the frozen run')
    review = {r['id']: r for r in json.loads((directory/'independent-labels.json').read_text())}
    if not cases or len({r['id'] for r in cases}) != len(cases):
        raise ValueError('empty or duplicate acceptance cases')
    source = []
    for row in cases:
        if type(row['expected_hide']) is not bool or review[row['id']]['expected_hide'] is not row['expected_hide']:
            raise ValueError('unresolved independent label review')
        source.append({'state': row['state'], 'expected': {'hide': row['expected_hide']},
                       'questions': {'hide': {'type': 'noul', 'criteria': {'false': 'Keep the post visible.', 'true': 'Hide the post.'},
                         'instructions': 'Filtering rules:\n'+row['instruction']+'\n\nShould this post be hidden?'}}})
    identity = fingerprint(checkpoint)
    if identity['sha256'] != plan['checkpoint_bindings'][name]:
        raise ValueError('checkpoint does not match frozen alias binding')
    started = time.monotonic()
    model, tokenizer, cfg = load_checkpoint(str(checkpoint))
    model.to(torch.device('cpu')); model.eval()
    items, skipped = items_from_rows(tokenizer, source, cfg['max_len'], cfg['head_max_len'])
    if skipped or len(items) != len(source):
        raise ValueError('tokenization lost or expanded rows')
    predictions = []
    with torch.inference_mode():
        for case, item in zip(cases, items):
            records = calibration_records(model, tokenizer, [item], torch.device('cpu'), cfg['max_len'], cfg['head_max_len'], batch_size=1)
            if len(records) != 1:
                raise ValueError('prediction population mismatch')
            values = binary_record_logits(records[0], case['expected_hide'])
            exp = [math.exp(x-max(values)) for x in values]
            predictions.append({'id': case['id'], 'slice': case['slice'], 'expected_hide': case['expected_hide'],
                                'p_hide': exp[1]/sum(exp), 'logits': values})
    if fingerprint(checkpoint) != identity or any(digest(directory/file) != expected for file, expected in dependencies.items()):
        raise ValueError('inputs changed during replay')
    result = {'model_alias': name, 'checkpoint': identity, 'device': 'cpu', 'threads': 2,
              'seconds': time.monotonic()-started, 'peak_rss_bytes_macos': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'versions': {p: importlib.metadata.version(p) for p in ('laya','torch','transformers','tokenizers','numpy','safetensors')},
              'plan_sha256': plan_digest, 'cases_sha256': plan['cases_sha256'],
              'rows': predictions, 'metrics': {str(t): {s: metrics([r for r in predictions if s == 'all' or r['slice'] == s], t)
                    for s in ['all']+sorted({r['slice'] for r in predictions})} for t in plan['thresholds']}}
    with path.open('x') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','checkpoint')}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('checkpoint', type=Path)
    p.add_argument('name', choices=['local-base','local-tuned'])
    args = p.parse_args()
    run(args.directory, args.checkpoint, args.name)
