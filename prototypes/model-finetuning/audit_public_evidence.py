"""Audit published aggregate arithmetic, not model quality or private provenance."""
import argparse
import json
import math
from pathlib import Path

DEFAULT_INPUT = Path(__file__).resolve().parents[2] / 'measurements/fine-tuning-aggregate.json'
COUNTS = ('n', 'posts', 'wanted', 'wanted_kept', 'unwanted', 'unwanted_hidden')


def audit(document):
    """Return deterministic diagnostics without inference or access to private data."""
    errors, warnings, records = [], [], []
    try:
        slices = document['format_robust']['slices']
        if not isinstance(slices, dict) or not slices:
            raise ValueError('slices must be a nonempty object')
    except (KeyError, TypeError, ValueError) as exc:
        return {'errors': [f'Invalid format_robust.slices: {exc}'], 'warnings': [], 'records': []}
    for name, models in slices.items():
        if not isinstance(models, dict):
            errors.append(f'{name}: models must be an object')
            continue
        if not models:
            warnings.append(f'{name}: empty slice; no evidence for this claim')
            continue
        reference = None
        for model, row in models.items():
            label = f'{name}/{model}'
            if not isinstance(row, dict) or any(type(row.get(k)) is not int or row[k] < 0 for k in COUNTS):
                errors.append(f'{label}: counts must be nonnegative integers (including posts)')
                continue
            n, posts, wanted, kept, unwanted, hidden = (row[k] for k in COUNTS)
            if wanted + unwanted != n or kept > wanted or hidden > unwanted or posts > n or (n > 0 and posts == 0):
                errors.append(f'{label}: inconsistent count totals or bounds')
                continue
            population = (n, posts, wanted, unwanted)
            if reference is not None and population != reference:
                errors.append(f'{label}: model populations differ within slice')
            reference = population
            if n == 0:
                warnings.append(f'{label}: zero pairs; rates are undefined')
            else:
                expected = (kept + hidden) / n
                accuracy = row.get('accuracy')
                if type(accuracy) not in (int, float) or not math.isfinite(accuracy) or not math.isclose(accuracy, expected, rel_tol=0, abs_tol=1e-12):
                    errors.append(f'{label}: accuracy does not match counts')
            visible = kept + unwanted - hidden
            if 'unwanted_fraction_visible' in row and visible:
                rate = row['unwanted_fraction_visible']
                if type(rate) not in (int, float) or not math.isfinite(rate) or not math.isclose(rate, (unwanted - hidden) / visible, rel_tol=0, abs_tol=1e-12):
                    errors.append(f'{label}: unwanted_fraction_visible does not match counts')
            records.append({'slice': name, 'model': model, 'pairs': n, 'posts': posts,
                            'wanted_kept': kept, 'wanted': wanted,
                            'unwanted_hidden': hidden, 'unwanted': unwanted,
                            'wanted_retention': kept / wanted if wanted else None,
                            'unwanted_removal': hidden / unwanted if unwanted else None})
    warnings.append('Pairs reuse posts; do not treat pair counts as independent sample sizes or sum overlapping slices. Post counts alone do not establish independence.')
    warnings.append('Aggregates cannot reproduce AUC, uncertainty, split integrity, labels, checkpoint provenance, or training. No production threshold is selected.')
    return {'errors': errors, 'warnings': warnings, 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    try:
        result = audit(json.loads(args.input.read_text()))
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Cannot read aggregate: {exc}\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
