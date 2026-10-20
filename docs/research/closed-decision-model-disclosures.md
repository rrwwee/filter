# What closed decision-model vendors disclose

Research date: 2026-10-19. Scope: a bounded review of TypeSafe's first-party Jev documentation and launch post, with a limited Fastino comparison. This is evidence about published methods, not a reverse engineering of either service.

## Jev: public contract, private internals

TypeSafe describes Jev as a model that takes shared state and typed questions, evaluates questions independently in parallel, and returns typed values and distributions without generating output text. The launch post names three separate developments: model architecture, parallel sampler, and Reinforcement Learning for Calibrated Decisions (RLCD). These are vendor disclosures, not a reproducible architecture specification. The same post explains that its “zero hallucination” result means schema matching, not zero incorrect decisions. [Introduction](https://docs.typesafe.ai/introduction) · [Launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

The reviewed first-party sources do **not** specify whether Jev is encoder-only, decoder-only, encoder-decoder, or something else; its parameter/layer counts; attention masks; tokenizer; model-side serialization; exact RLCD reward/loss; training schedule; or a reproducible checkpoint. Parallel typed outputs do not establish the internal architecture. Public SDKs expose the service interface, not the model. [Official repositories](https://github.com/typesafe-ai)

The API accepts a string, object, or array for state. Instructions and criterion descriptions can also contain JSON structure. TypeSafe says the models were trained to understand structure and recommends meaningful field names. This establishes what the API accepts, **not** whether the backend flattens JSON into text tokens, uses special structural tokens, or uses another representation. [State](https://docs.typesafe.ai/concepts/state) · [Structured inputs](https://docs.typesafe.ai/primitives/advanced)

## Probability, calibration, and confidence are different

RLCD's published objective is to produce calibrated decisions: events assigned 0.8 should occur roughly 80% of the time across a suitable population. The primer gives this target but no executable training recipe. A probability-valued output is not, by itself, evidence of calibration on our filtering task. [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer)

TypeSafe does publish the **derived confidence formulas**. For a Choice with n options and highest probability p, confidence is `(p - 1/n) / (1 - 1/n)`. Noul returns its yes probability without separate confidence; `abs(2*p - 1)` is an optional analogous statistic. Score confidence uses probability-weighted distance from the modal level, normalized against an even distribution. These summarize the returned distribution; they do not independently certify it is calibrated or correct. The docs explicitly recommend setting thresholds using domain-specific data. [Confidence](https://docs.typesafe.ai/confidence)

## Same API does not mean same method

TypeSafe itself publishes an adapter which obtains the same decision-shaped outputs from ordinary hosted LLMs. It uses provider structured outputs or prompts for JSON, supports asking for distributions or discrete answers, validates responses, and can normalize generated probabilities. This is an interface-compatible implementation, **not** Jev's disclosed internal method; normalization only makes numbers sum to one. [Official System One adapter](https://github.com/typesafe-ai/system-one-adapter-python)

## Limited comparison: Fastino

Fastino's 2025 TLM announcement claimed purpose-built architecture and task-specific training but did not supply a reproducible architecture or calibration method there. Its later Pioneer product describes an agent that curates data, trains and evaluates existing model families, and can export weights. That is a different disclosed mechanism from Jev's proprietary RLCD claim, and Pioneer is not one closed model architecture. [TLM announcement](https://fastino.ai/blog/fastino-raises-25m-to-launch-tlms-task-specific-language-models) · [Pioneer introduction](https://fastino.ai/blog/introducing-pioneer)

Conclusion: some vendors disclose meaningful pipeline details, but the reviewed Jev materials do not let us reproduce Jev or claim that open implementations copy its internals. Compare open implementations using their actual code, architecture, loss and calibration evidence.

## Option order: disclosed counterexample to equivariance

A subsequent focused check found an explicit vendor disclosure: [Jev 1.13 jaggedness, choice option order](https://docs.typesafe.ai/model-jaggedness/jev-1.13#choice-option-order), reviewed by TypeSafe on 2026-10-02, says option order can affect the answer and recommends reordering to check consistency. This disproves exact permutation equivariance for that version; it does not establish the behavior of every later version. [Archestra's original experiment](https://archestra.ai/blog/we-tested-jev-on-100-real-agent-calls) also reports order-dependent labels and probabilities, including changes in three-way choices. Neither disclosure reveals Jev's attention architecture.
