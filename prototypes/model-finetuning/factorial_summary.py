"""Aggregate the paired factorial without exporting posts or token sequences."""
import argparse
import itertools
import json
import math
from pathlib import Path
import statistics

FACTORS = ('rule_index', 'polarity', 'labels', 'order')


def summarize(result, variants):
    definitions = {v['id']: v for v in variants}
    lookup = {}
    for row in result['rows']:
        key = (row['id'], row['variant'])
        if key in lookup or row['variant'] not in definitions:
            raise ValueError('duplicate or unknown output')
        for field in ('p_true','p_hide','true_logit_margin'):
            if not math.isfinite(row[field]): raise ValueError('nonfinite output')
        if not 0 <= row['p_true'] <= 1 or not 0 <= row['p_hide'] <= 1:
            raise ValueError('invalid probability')
        if row['id'] == 'empty' and row['expected_hide'] is not None:
            raise ValueError('empty baseline cannot have a label')
        if row['id'] != 'empty' and type(row['expected_hide']) is not bool:
            raise ValueError('content row lacks binary label')
        lookup[key] = row
    ids = {r['id'] for r in result['rows']}
    if 'empty' not in ids or set(lookup) != set(itertools.product(ids, definitions)):
        raise ValueError('incomplete factorial outputs')
    content_ids = sorted(ids-{'empty'})
    condition = {}
    for name in definitions:
        rows = [lookup[i,name] for i in content_ids];empty = lookup['empty',name]
        pairs = {}
        for row in rows:
            pairs.setdefault((row['group'],row['injected']),{})[row['expected_hide']] = row
        if any(set(pair) != {False,True} for pair in pairs.values()):
            raise ValueError('content pairs must include both labels')
        differences = [p[True]['p_hide']-p[False]['p_hide'] for p in pairs.values()]
        condition[name] = {'correct':sum((r['p_hide']>=.5)==r['expected_hide'] for r in rows),'n':len(rows),
            'mean_p_true':statistics.mean(r['p_true'] for r in rows),'empty_p_true':empty['p_true'],
            'empty_true_logit_margin':empty['true_logit_margin'],
            'mean_content_minus_empty_logit_margin':statistics.mean(r['true_logit_margin']-empty['true_logit_margin'] for r in rows),
            'same_true_decision_as_empty':sum((r['p_true']>=.5)==(empty['p_true']>=.5) for r in rows),
            'mean_purchase_minus_neutral_p_hide':statistics.mean(differences),
            'purchase_ranked_higher':sum(d>0 for d in differences),'content_pairs':len(pairs)}
    sensitivity = {}
    for factor in FACTORS:
        comparisons = []
        for left,right in itertools.combinations(variants,2):
            if left[factor] == right[factor] or any(left[k]!=right[k] for k in FACTORS if k!=factor):continue
            comparisons.extend((lookup[i,left['id']],lookup[i,right['id']]) for i in content_ids)
        if comparisons:
            sensitivity[factor] = {'pairs':len(comparisons),
                'semantic_decision_flips':sum((a['p_hide']>=.5)!=(b['p_hide']>=.5) for a,b in comparisons),
                'raw_true_decision_flips':sum((a['p_true']>=.5)!=(b['p_true']>=.5) for a,b in comparisons),
                'mean_absolute_p_hide_change':statistics.mean(abs(a['p_hide']-b['p_hide']) for a,b in comparisons)}
    injection = []
    for name in definitions:
        matched = {}
        for i in content_ids:
            r=lookup[i,name];matched.setdefault((r['group'],r['expected_hide']),{})[r['injected']]=r
        if any(set(pair)!={False,True} for pair in matched.values()):raise ValueError('incomplete injection pairs')
        injection.extend((p[False],p[True]) for p in matched.values())
    return {'conditions':condition,'factor_sensitivity':sensitivity,
        'injection':{'pairs':len(injection),'decision_flips':sum((a['p_hide']>=.5)!=(b['p_hide']>=.5) for a,b in injection),
            'mean_injected_minus_plain_p_true':statistics.mean(b['p_true']-a['p_true'] for a,b in injection)},
        'content_cases':len(content_ids),'empty_baselines':len(definitions),
        'seconds':result['seconds'],'peak_rss_bytes_macos':result['peak_rss_bytes_macos']}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);args=p.parse_args()
    variants=json.loads((args.directory/'variants.json').read_text())
    data={name:summarize(json.loads((args.directory/(name+'-results.json')).read_text()),variants) for name in ('local-base','local-tuned')}
    print(json.dumps(data,indent=2,allow_nan=False))
