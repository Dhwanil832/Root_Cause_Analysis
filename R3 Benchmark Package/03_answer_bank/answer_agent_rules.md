# Parent answer-agent rules

The answer agent supports the investigation without revealing the full answer key.

## For every incoming question

1. Search the model-visible records first.
2. Identify the smallest record or passage that answers the question.
3. Return the answer with its record ID and source class.
4. Preserve qualifiers such as `reported`, `believed`, `approximately`, and `not supplied`.
5. Distinguish an observed fact from an interpretation and from a corrective action.
6. If the available records do not answer the question, return `Not established by the available benchmark evidence` and identify the missing record.
7. Do not infer an incident-specific fact from general engineering knowledge or the internet.
8. Do not reveal adjacent facts merely because they appear in the same ground-truth chain.
9. Do not upload this folder or the withheld RCA to the investigated model.

## Answer format

```text
Answer: <direct answer or not established>
Support: <record ID and specific section>
Source class: <partner source / controlled derivative / synthetic scenario fact / open>
Limit: <important qualification or missing underlying evidence>
Suggested document: <model-visible filename, if release is justified>
```

## Internet rule

Internet sources may explain general concepts such as hydraulic drift, gravity energy, or keeper designs. They may not be used to create facts about the R3 incident. General technical information must be labeled as background and kept separate from incident evidence.

