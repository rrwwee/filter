import {validateCases} from './contracts.mjs';

const labels = new Set(['keep', 'hide', 'uncertain']);
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const identity = row => JSON.stringify(canonical(Object.fromEntries(Object.entries(row).filter(([key]) => !['label', 'reviewed'].includes(key)))));

export function validateLabelCases(cases) {
  if (!Array.isArray(cases)) throw new Error('Cases must be an array.');
  // Labeling also covers unreadable/image-only posts; inference stays stricter.
  validateCases(cases.map(row => row && ({...row, text: row.text == null || row.text === '' ? '[No readable post text]' : row.text})));
  if (!cases.length) throw new Error('No labeling cases available.');
  for (const row of cases) {
    if (typeof row.instruction !== 'string') throw new Error('A labeling instruction is missing.');
    if (row.reviewed !== undefined && typeof row.reviewed !== 'boolean') throw new Error('Invalid reviewed flag.');
    if (row.reviewed && !labels.has(row.label)) throw new Error('A reviewed case has an invalid label.');
    if (row.label != null && !labels.has(row.label)) throw new Error('Invalid label.');
  }
  return cases;
}

export function validateLabelSnapshot(snapshot, sourceCases) {
  if (!snapshot || snapshot.type !== 'human-labels') throw new Error('Invalid saved labeling state.');
  validateLabelCases(snapshot.cases);
  if (!Number.isInteger(snapshot.index) || snapshot.index < 0 || snapshot.index >= snapshot.cases.length) throw new Error('Invalid saved case index.');
  if (sourceCases && (sourceCases.length !== snapshot.cases.length || sourceCases.some((row, i) => identity(row) !== identity(snapshot.cases[i])))) {
    throw new Error('Saved cases do not match the source cases.');
  }
  return snapshot;
}
