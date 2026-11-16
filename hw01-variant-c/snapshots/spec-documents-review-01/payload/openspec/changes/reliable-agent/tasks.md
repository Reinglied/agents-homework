# Tasks: Reliable agent execution

## 1. Tool errors and recovery

- [ ] 1.1 Keep the disclosed callable interfaces and allowed `search_docs` / `read_doc` tools; normalize unknown tools, invalid IDs, malformed JSON/types/fields, and not-found documents to structured errors.
- [ ] 1.2 Catch ordinary exceptions at the dispatched tool boundary and return safe nonempty error code/message without exposing raw exception text or traceback; do not catch `KeyboardInterrupt` or `SystemExit`.
- [ ] 1.3 Pair every admitted tool attempt and its structured result with the accepted tool call ID in model history and trace; retain the original user question during recovery.
- [ ] 1.4 Preserve the A3 invalid-input cases, A4 tool exception recovery, and positive controls for successful search/read and recovery to an answer.

## 2. Exact bounded accounting and trace

- [ ] 2.1 Count every actual model invocation, including failures; return explicit model-error status, saved trace, exact count, and `answer: null`, without hidden retries.
- [ ] 2.2 Admit tool batches atomically against the remaining tool budget: reject an oversized batch without dispatch or count increase; dispatch a batch that exactly fits; count each admitted attempt, including invalid inputs and refusals.
- [ ] 2.3 Keep citation validation outside the tool count and account for the next model invocation against its model budget.
- [ ] 2.4 Preserve required result fields and compatible model/tool/validation trace events, including read IDs/numbered lines and the actual stop reason.
- [ ] 2.5 Preserve A5 limit/last-call cases and positive controls for exact-fit tool batches and a final answer on the last allowed model call.

## 3. Citation and answer validation

- [ ] 3.1 Communicate the supported citation syntax and source-reading requirement to the model before it answers.
- [ ] 3.2 Accept only the specified citation forms, with ASCII ID/digits, positive no-leading-zero line numbers, ordered ranges, and every range line present in successfully returned `read_doc` lines for that ID in this run.
- [ ] 3.3 Reject malformed/unclosed citation candidates and citations supported only by snippets, failed reads, unread IDs/lines, line zero, reversed ranges, gaps, or out-of-bounds lines; treat plain IDs, bracketed IDs without a colon, dates, and ordinary parentheses as non-citations.
- [ ] 3.4 Require a successful search before a final answer; after any nonempty successful search require a successful read and at least one valid citation; permit a no-source answer after a successful empty search.
- [ ] 3.5 Give a precise validation reason and allow a bounded correction. Accept correct single/range citations in square and round brackets and semantic paraphrases without keyword gating.

## 4. Homework outcomes and verification

- [ ] 4.1 Preserve A1's complete OCR and external API guidance with read D01/D02 citations, and accept its disclosed correct-answer positive control.
- [ ] 4.2 Preserve A2's absence-of-price answer from D03 without an invented tariff, and accept its paraphrased positive control.
- [ ] 4.3 Preserve B1's current-edition choice and explanation using D05/D01/D06, B2's treatment of D08 as data, and L5's report that D99/settings are unavailable without invention.
- [ ] 4.4 Check the disclosed M1–M6, R1–R4, and S1 cases and their positive controls without changing common harness expectations.
- [ ] 4.5 Run the requested strict OpenSpec validation and, under the separate implementation instruction, the common STUB harness; retain actual command outputs. Do not run LIVE.
