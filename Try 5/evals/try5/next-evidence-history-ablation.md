# Prespecified follow-up: remove only the previous question list

The first next-evidence test, `outputs/next-evidence-jTDF1s`, completed but failed:
its question exactly repeats an existing open question, and its second answer
implication treats unrecorded valve changes as support for equipment failure.

One additional call will test sensitivity to the existing-question context.
Copy its serialized request, remove ONLY `evidencePacket.existingQuestions`, and
preserve model digest, system prompt, original passages and their ordering,
proposed observation, findings, output schema, profile, context and output allowance.
Do not show the baseline answer, audit, or this file to the model. One attempt.

Apply the same six acceptance criteria in `next-evidence-expectations.md`.
Compare request specificity, current mapping/comparability prerequisites, and
whether an absence of records is still treated as evidence for another cause.
Do not repair either answer or label an API success a semantic pass.

A better response would support further testing of question-history effects, not
prove the list caused the previous error. An unchanged failure would show that
removing the list alone did not fix this case, not prove the list has no effect.
No default engine change, production revision or full RCA restart is authorized
by either result.
