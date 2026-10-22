// Input and output boundaries for the browser harness; no model dependencies.
const knownSplits = new Set(['smoke', 'development', 'heldout', 'heldout-pool', 'agent-diagnostic']);
const heldoutSplits = new Set(['heldout', 'heldout-pool']);

export function validateCases(cases) {
  if (!Array.isArray(cases)) throw new Error('Cases must be an array.');
  const ids = new Set();
  for (const c of cases) {
    if (!c || typeof c !== 'object' || typeof c.id !== 'string' || !c.id.trim() || ids.has(c.id)) throw new Error('Cases require unique nonempty string IDs.');
    ids.add(c.id);
    if (typeof c.text !== 'string' || !c.text.trim()) throw new Error(`Missing post text: ${c.id}`);
    if (!knownSplits.has(c.split)) throw new Error(`Unknown or missing split: ${c.id}`);
    if (c.instruction !== undefined && typeof c.instruction !== 'string') throw new Error(`Invalid instruction: ${c.id}`);
  }
  return cases;
}

export function runnableCases(cases, mode = 'ordinary') {
  validateCases(cases);
  if (!['ordinary', 'bullet'].includes(mode)) throw new Error('Unknown run mode.');
  const allowed = mode === 'bullet' ? new Set(['agent-diagnostic']) : new Set(['smoke', 'development']);
  const selected = [];
  for (const c of cases) {
    if (heldoutSplits.has(c.split) && mode === 'ordinary') continue;
    if (!allowed.has(c.split)) throw new Error(`Split ${c.split} is not permitted for ${mode} runs.`);
    selected.push(c);
  }
  if (!selected.length) throw new Error('No permitted cases available.');
  return selected;
}

const direct = {
  tech: ['Is the main subject of this post technology, software, AI, product development, or technology-related policy, rather than an unrelated personal story or general politics?', true],
  dating: ['Is the main subject of this post a personal dating story? Incidental mentions of a partner and technical explanations of dating apps do not count.', false],
  teaser: ['Does this post deliberately withhold its substantive point to induce a click? Useful previews with links to further details do not count.', false],
  combined: ['Is this post mainly about technology, software, AI, product development, or technology-related policy, without being a personal dating story or deliberately withholding its substantive point to induce a click?', true],
};
export function directQuestion(kind) {
  if (!Object.hasOwn(direct, kind)) throw new Error(`Unsupported direct-question kind: ${kind}`);
  return [...direct[kind]];
}

function probability(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) throw new Error('Model probabilities must be finite numbers in [0, 1].');
  return value;
}

export function decodeBatch(outputs, expectedCount, {template, isChoice = false, yesMeansKeep = true}) {
  if (!Number.isInteger(expectedCount) || expectedCount < 1 || !Array.isArray(outputs) || outputs.length !== expectedCount) throw new Error('Model batch cardinality does not match inputs.');
  // Validate the whole batch before the caller appends any results.
  return outputs.map(o => {
    const answer = o?.answers?.keep;
    if (!answer || typeof answer !== 'object') throw new Error('Missing model answer.');
    let target, probabilities;
    if (isChoice) {
      const neutral = ['minimal-ab', 'minimal-ba'].includes(template);
      const keys = neutral ? ['A', 'B'] : ['keep', 'hide'];
      probabilities = answer.probabilities;
      if (!probabilities || keys.some(k => !Object.hasOwn(probabilities, k)) || Object.keys(probabilities).length !== 2) throw new Error('Missing or unexpected choice probabilities.');
      const values = keys.map(k => probability(probabilities[k]));
      if (Math.abs(values[0] + values[1] - 1) > 1e-5) throw new Error('Choice probabilities are not normalized.');
      target = probabilities[neutral ? (template === 'minimal-ab' ? 'A' : 'B') : 'keep'];
    } else {
      target = probability(answer.noul);
      probabilities = {true: target, false: 1 - target};
    }
    return {target, pKeep: yesMeansKeep ? target : 1 - target, probabilities};
  });
}
