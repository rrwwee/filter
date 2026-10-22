"""Small frozen wording/content factorial; empty states are unlabeled baselines."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import time
from acceptance_replay import digest, fingerprint
from polarity_probe import canonical_probabilities


def question_for(rule, variant):
    if variant['polarity'] not in ('hide', 'keep') or variant['labels'] not in ('boolean', 'neutral') or variant['order'] not in ('forward', 'reverse'):
        raise ValueError('invalid factor level')
    hide = variant['polarity'] == 'hide'
    q = {'type': 'noul', 'instructions': rule+'\n\n'+('Should this post be hidden?' if hide else 'Should this post be kept visible?'),
         'criteria': {'false': 'Keep the post visible.', 'true': 'Hide the post.'} if hide else {'false': 'Hide the post.', 'true': 'Keep the post visible.'}}
    if variant['labels'] == 'neutral':
        q['labels'] = {'false': 'A', 'true': 'B'}
    return q, 1 if hide else 0, [0, 1] if variant['order'] == 'forward' else [1, 0]


def scoreable(case):
    """An empty baseline has no truth label and must never enter accuracy counts."""
    return type(case.get('expected_hide')) is bool


def run(directory, checkpoint, alias):
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    import torch
    from laya.train import load_checkpoint, to_internal, make_item, encode_item, _forward
    from laya.common import encode_text, build_sequence, collate_items
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    path = directory/(alias+'-results.json')
    if path.exists():
        raise ValueError('preserve completed results')
    plan = json.loads((directory/'plan.json').read_text())
    if plan['runner_sha256'] != digest(Path(__file__)) or plan['threshold'] != 0.5:
        raise ValueError('runner or threshold changed')
    dependencies = dict(plan['dependencies'], **{'plan.json': digest(directory/'plan.json')})
    def verify():
        if any(digest(directory/file) != value for file, value in dependencies.items()):
            raise ValueError('frozen input changed')
    verify()
    cases = json.loads((directory/'frozen-cases.json').read_text())
    review = {r['id']: r for r in json.loads((directory/'independent-labels.json').read_text())}
    rules = json.loads((directory/'rules.json').read_text())
    variants = json.loads((directory/'variants.json').read_text())
    if not cases or len({c['id'] for c in cases}) != len(cases) or len({v['id'] for v in variants}) != len(variants):
        raise ValueError('empty or duplicate design')
    for case in cases:
        if not scoreable(case) or review[case['id']]['expected_hide'] is not case['expected_hide']:
            raise ValueError('unresolved label review')
    baseline = {'id': 'empty', 'group': 'empty', 'injected': False, 'state': '', 'expected_hide': None}
    identity = fingerprint(checkpoint)
    if identity['sha256'] != plan['checkpoint_bindings'][alias]:
        raise ValueError('checkpoint alias changed')
    started = time.monotonic()
    model, tok, cfg = load_checkpoint(str(checkpoint)); model.eval()
    device = torch.device('cpu'); model.to(device)
    rows = []
    with torch.inference_mode():
        for case in cases+[baseline]:
            state_ids = encode_text(tok, case['state'].replace(tok.mask_token, ' '), add_special_tokens=False)['input_ids']
            for variant in variants:
                q, hide_index, order = question_for(rules[variant['rule_index']], variant)
                internal = to_internal('decision', q)
                # No true labels enter tokenization or the forward call.
                item, error = make_item(tok, internal, [.5, .5], state_ids, cfg['head_max_len'], cfg['max_len'])
                if error:
                    raise ValueError(error)
                encoded = encode_item(tok, item, cfg['max_len'], cfg['head_max_len'], option_order=order)
                ids, markers, truncation = build_sequence(tok, None, internal, cfg['max_len'], cfg['head_max_len'], state_ids=state_ids, option_order=order, return_truncation_stats=True)
                if truncation['truncated'] or ids != encoded['ids'] or markers != encoded['markers']:
                    raise ValueError('truncated or mismatched encoding')
                logits = _forward(model, collate_items([[encoded]], tok.pad_token_id), device, amp=False, detach_encoder=False)[0].tolist()
                probabilities = canonical_probabilities(logits, order)
                canonical_logits = [0., 0.]
                for slot, index in enumerate(order): canonical_logits[index] = logits[slot]
                rows.append({k:case[k] for k in ('id','group','injected','expected_hide')} | {
                    'variant':variant['id'], 'p_true':probabilities[1], 'p_hide':probabilities[hide_index],
                    'true_logit_margin':canonical_logits[1]-canonical_logits[0], 'slot_logits':logits,
                    'canonical_logits':canonical_logits, 'input_ids':ids, 'marker_positions':markers,
                    'state_tokens':len(state_ids), 'truncation':truncation})
    if len(rows) != (len(cases)+1)*len(variants):
        raise ValueError('incomplete factorial')
    verify()
    if fingerprint(checkpoint) != identity:
        raise ValueError('checkpoint changed')
    result = {'alias':alias, 'checkpoint':identity, 'dependencies':dependencies, 'rows':rows,
              'seconds':time.monotonic()-started, 'peak_rss_bytes_macos':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'versions':{p:importlib.metadata.version(p) for p in ('laya','torch','transformers','tokenizers')}, 'device':'cpu','threads':2}
    with path.open('x') as stream: json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','dependencies','checkpoint')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path);p.add_argument('checkpoint',type=Path)
    p.add_argument('alias',choices=['local-base','local-tuned'])
    args=p.parse_args();run(args.directory,args.checkpoint,args.alias)
