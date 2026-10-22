"""Build a local-only replay from reviewed development labels and single-post captures."""
import argparse
import hashlib
import json
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def build(labels, sources):
    if not isinstance(labels, list) or not labels:
        raise ValueError('Expected a nonempty development-only label list')
    cases = {}
    for c in labels:
        if c.get('split') != 'development' or c.get('reviewed') is not True or c.get('label') not in ('keep', 'hide', 'uncertain'):
            raise ValueError('Only reviewed development labels may enter this preview')
        if not isinstance(c.get('id'), str) or c['id'] in cases or not isinstance(c.get('text'), str) or not isinstance(c.get('instruction'), str):
            raise ValueError('Invalid or duplicate case identity')
        cases[c['id']] = c
    captures = []
    for source_name, source_hash, source in sources:
        population = {c['id']: c for c in source.get('cases', []) if c.get('split') == 'development'}
        if set(population) != set(cases):
            raise ValueError('Capture development population does not match labels')
        for id, c in cases.items():
            if any(population[id].get(k) != c.get(k) for k in ('text', 'instruction', 'source', 'kind')):
                raise ValueError('Capture case identity changed')
        groups = {}
        for row in source.get('rows', []):
            if row.get('split') != 'development' or row.get('condition') != 'actual' or row.get('template') != 'minimal-prefix':
                continue
            if row.get('batchSize') != 1:
                raise ValueError('Replay requires actual single-post results')
            c = cases.get(row.get('id'))
            if c is None or row.get('input') != c['text'] or row.get('rule') != c['instruction'] or row.get('label') != c['label']:
                raise ValueError('Result does not match frozen text, rule and label')
            question = f"Filtering instruction:\n{c['instruction']}\n\nDoes this post pass the filter?"
            if row.get('fixedQuestion') != question or row.get('questionType') != 'noul' or row.get('yesMeansKeep') is not True:
                raise ValueError('Unsupported question or score polarity')
            p, ms = row.get('pKeep'), row.get('callMs')
            if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1:
                raise ValueError('Invalid score')
            if isinstance(ms, bool) or not isinstance(ms, (int, float)) or not 0 <= ms < float('inf'):
                raise ValueError('Invalid recorded duration')
            identity = {k: row.get(k) for k in ('candidate', 'device', 'dtype', 'revision', 'template', 'questionType', 'yesMeansKeep', 'modelMeta')}
            if any(not identity[k] for k in ('candidate', 'device', 'dtype', 'revision')):
                raise ValueError('Missing model provenance')
            key = fingerprint(identity)
            group = groups.setdefault(key, {'identity': identity, 'rows': []})
            if any(x['id'] == c['id'] for x in group['rows']):
                raise ValueError('Ambiguous repeated score for one case')
            group['rows'].append({'id': c['id'], 'instruction': c['instruction'], 'question': question, 'pKeep': p, 'callMs': ms})
        for key, group in groups.items():
            if {r['id'] for r in group['rows']} != set(cases):
                raise ValueError('Incomplete single-post population')
            captures.append({'id': fingerprint([source_hash, key]), 'source': source_name, 'sourceSha256': source_hash,
                             'recordedAt': source.get('at'), **group})
    if not captures:
        raise ValueError('No matching single-post development capture')
    catalog = {'schema': 1, 'kind': 'development-score-replay', 'labelSnapshotSha256': fingerprint(labels),
               'labelProvenance': 'Existing reviewed development labels from the blind labeling workflow; no labels newly collected by this preview.',
               'cases': list(cases.values()), 'captures': captures}
    catalog['version'] = fingerprint(catalog)
    return catalog


def safe_output(path, root=None):
    root = (root or Path(__file__).resolve().parents[1]).resolve()
    base = root / 'local-results'
    candidate = path.absolute()
    for part in (candidate, *candidate.parents):
        if part.resolve() == root:
            break
        if part.is_symlink():
            raise ValueError('Replay destination may not contain symlinks')
    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(base)
    except ValueError as error:
        raise ValueError('Replay output must remain inside this checkout local-results') from error
    if not relative.parts:
        raise ValueError('Replay destination must be a file')
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--source', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        args.output = safe_output(args.output)
    except ValueError as error:
        parser.error(str(error))
    sources = [(p.name, hashlib.sha256(p.read_bytes()).hexdigest(), json.loads(p.read_text())) for p in args.source]
    catalog = build(json.loads(args.labels.read_text()), sources)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(catalog, ensure_ascii=False, indent=2)+'\n'
    version_path = safe_output(args.output.with_name('replay-'+catalog['version']+'.json'))
    if version_path.exists() and version_path.read_text() != encoded:
        raise ValueError('Existing replay version has different contents')
    if not version_path.exists():
        version_path.write_text(encoded)
    args.output.write_text(encoded)
    print(f"Built local replay: {len(catalog['cases'])} development cases, {len(catalog['captures'])} captures, version {catalog['version']}")


if __name__ == '__main__':
    main()
