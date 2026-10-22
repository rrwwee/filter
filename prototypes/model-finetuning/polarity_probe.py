"""Offline diagnostic: separate decision semantics from physical answer positions."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import resource
import time
from acceptance_replay import digest, fingerprint


def render_variant(instruction, variant):
    kind, polarity = variant['type'], variant['polarity']
    if kind == 'noul':
        if polarity not in ('hide', 'keep'):
            raise ValueError('invalid question polarity')
        text = 'Should this post be hidden?' if polarity == 'hide' else 'Should this post be kept visible?'
        criteria = {'false': 'Keep the post visible.', 'true': 'Hide the post.'} if polarity == 'hide' else {'false': 'Hide the post.', 'true': 'Keep the post visible.'}
        hide_index = 1 if polarity == 'hide' else 0
    elif kind == 'choice':
        text = 'Should this post be kept visible or hidden?'
        if polarity == 'named':
            criteria, hide_index = {'keep': 'Keep the post visible.', 'hide': 'Hide the post.'}, 1
        elif polarity == 'A-keep':
            criteria, hide_index = {'A': 'Keep the post visible.', 'B': 'Hide the post.'}, 1
        elif polarity == 'A-hide':
            criteria, hide_index = {'A': 'Hide the post.', 'B': 'Keep the post visible.'}, 0
        else:
            raise ValueError('invalid choice mapping')
    else:
        raise ValueError('invalid question type')
    if variant['order'] not in ('forward', 'reverse'):
        raise ValueError('invalid physical order')
    question = {'type': kind, 'criteria': criteria, 'instructions': 'Filtering rules:\n'+instruction+'\n\n'+text}
    return question, hide_index, [0, 1] if variant['order'] == 'forward' else [1, 0]


def canonical_probabilities(slot_logits, order):
    if sorted(order) != [0, 1] or len(slot_logits) != 2 or not all(math.isfinite(x) for x in slot_logits):
        raise ValueError('invalid binary output')
    exps = [math.exp(x-max(slot_logits)) for x in slot_logits]
    probabilities = [0., 0.]
    for slot, canonical in enumerate(order):
        probabilities[canonical] = exps[slot]/sum(exps)
    return probabilities


def run(directory, checkpoint, alias):
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    import torch
    from laya.train import load_checkpoint, to_internal, make_item, encode_state, encode_item, _forward
    from laya.common import collate_items
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    path = directory/(alias+'-results.json')
    if path.exists():
        raise ValueError('preserve the completed diagnostic')
    plan = json.loads((directory/'plan.json').read_text())
    if digest(Path(__file__)) != plan['runner_sha256'] or plan['threshold'] != 0.5:
        raise ValueError('runner or prespecified threshold changed')
    dependencies = dict(plan['dependencies'], **{'plan.json': digest(directory/'plan.json')})
    def verify():
        if any(digest(directory/name) != expected for name, expected in dependencies.items()):
            raise ValueError('frozen input changed')
    verify()
    identity = fingerprint(checkpoint)
    if identity['sha256'] != plan['checkpoint_bindings'][alias]:
        raise ValueError('checkpoint alias mismatch')
    cases = json.loads((directory/'frozen-cases.json').read_text())
    variants = json.loads((directory/'variants.json').read_text())
    review = {r['id']: r for r in json.loads((directory/'independent-labels.json').read_text())}
    if len({c['id'] for c in cases}) != len(cases) or len({v['id'] for v in variants}) != len(variants):
        raise ValueError('duplicate case or variant')
    started = time.monotonic()
    model, tok, cfg = load_checkpoint(str(checkpoint)); model.eval()
    device = torch.device('cpu')
    model.to(device)
    outputs = []
    with torch.inference_mode():
        for case in cases:
            if type(case['expected_hide']) is not bool or review[case['id']]['expected_hide'] is not case['expected_hide']:
                raise ValueError('unresolved label')
            for variant in variants:
                question, hide_index, order = render_variant(case['instruction'], variant)
                internal = to_internal('decision', question)
                # Targets are validated scaffolding only; _forward never passes them to the model.
                target = [0., 0.]; target[hide_index if case['expected_hide'] else 1-hide_index] = 1.
                item, error = make_item(tok, internal, target, encode_state(tok, case['state'], cfg['max_len']), cfg['head_max_len'], cfg['max_len'])
                if error:
                    raise ValueError(error)
                encoded = encode_item(tok, item, cfg['max_len'], cfg['head_max_len'], option_order=order)
                batch = collate_items([[encoded]], tok.pad_token_id)
                logits = _forward(model, batch, device, amp=False, detach_encoder=False)[0].tolist()
                probabilities = canonical_probabilities(logits, order)
                outputs.append({'id': case['id'], 'slice': case['slice'], 'group': case['group'], 'variant': variant['id'],
                                'expected_hide': case['expected_hide'], 'p_hide': probabilities[hide_index],
                                'slot_logits': logits, 'canonical_probabilities': probabilities, 'hide_index': hide_index,
                                'slot_order': order, 'token_count': len(encoded['ids']),
                                'encoding_sha256': hashlib.sha256(json.dumps(encoded['ids']).encode()).hexdigest()})
    if len(outputs) != len(cases)*len(variants):
        raise ValueError('incomplete comparison')
    verify()
    if fingerprint(checkpoint) != identity:
        raise ValueError('model changed')
    result = {'alias': alias, 'checkpoint': identity, 'dependencies': dependencies,
              'seconds': time.monotonic()-started, 'peak_rss_bytes_macos': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'device': 'cpu', 'threads': 2, 'rows': outputs,
              'versions': {p: importlib.metadata.version(p) for p in ('torch','laya','transformers','tokenizers')}}
    with path.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','checkpoint','dependencies')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path); p.add_argument('checkpoint', type=Path)
    p.add_argument('alias', choices=['local-base','local-tuned'])
    args = p.parse_args(); run(args.directory, args.checkpoint, args.alias)
