# Preserved failed attempt

This attempt ended after eight consolidated candidates. All raw requests,
responses and completed checkpoints are preserved.

Observed defect: a question/rejected disposition with an unused proposition
object failed a cross-field validator, even though that object would never be
used as a board node. An invented claim identifier also triggered a whole-batch
retry. One repair changed the disposition to board. This is a harness error to
fix, not a reason to promote the proposition or blame missing documents.

The correction makes the explicit disposition authoritative for field consumption,
handles malformed merges per candidate, and records/excludes unresolved claim
references without treating them as source evidence. Raw responses remain in
audit; none of these actions establish the candidate's truth.

Continuation: `../qwen-v2-consolidated-btG98n/`. Matching successful calls are
available in its checkpoint cache. Failed calls are not represented as completed.
The same ten original discovery calls, source package, model and four answers are
retained. No app version or evidence record was overwritten.
