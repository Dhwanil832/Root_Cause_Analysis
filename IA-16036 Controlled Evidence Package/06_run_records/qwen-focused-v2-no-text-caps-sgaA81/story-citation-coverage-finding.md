# Observed storyteller citation-catalog defect

Recorded after story generation, while V2 runs. Evaluator-only; not supplied to either model. No prompt, evidence, or runtime modification was made in response.

Calling the unchanged `storyPassages` implementation on the frozen `story-scenario.json` demonstrates missing portions of the available source records:

- The P01 pressure table has no selectable passage containing its rows. Passage `IA-P01:p5` instead starts with `8 | 1 |`, the tail after the final decimal in the table, and continues into the alarm journal and later prose.
- The P02 point-register table likewise has no complete selectable passage. Passage `IA-P02:p3` starts with `0 bar |`, the tail after the final decimal in that table, then continues with the display-label description.
- P01's alarm journal and P02's prose mapping of COMP FAULT to receiving pressure are still present in selectable passages. The omission therefore does not explain every observed miss.

The sentence regex excludes periods from the sentence body, but only accepts them as sentence endings when followed by whitespace or end-of-input. Decimal points satisfy neither condition. The matching operation can skip unmatched material instead of retaining every source character.

The model also received the full original source texts in `scenario.sources`. This is a missing **selectable citation** problem, not evidence that the model lacked every view of the table. It constrains grounded answering and confounds attribution of the pressure/mapping misses solely to model reasoning. It does not excuse the unsupported 10:02 acknowledgment assertion.

The complete P01/P02 originals are separately uploaded to RCA for V2, with original byte hashes checked and extracted text compared against the original text after the extractor's documented outer-whitespace trim. Storyteller raw outputs and this diagnosis remain preserved separately. A later fix must be a separately identified comparison, not an in-place change to this experiment.
