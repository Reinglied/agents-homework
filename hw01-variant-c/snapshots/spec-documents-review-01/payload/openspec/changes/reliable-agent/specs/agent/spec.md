# Agent reliability

## Purpose

Specify bounded tool execution, structured recovery, trace accounting, and citation provenance for the existing DemoDesk agent while preserving the homework contract.

## Requirements

### Requirement: Preserve the agent interface and permitted capabilities

The system SHALL preserve `run_agent(question, cfg, model_fn, mode="LIVE", emit=print)`, `load_config()`, `load_docs()`, and `run_allowed_tool(name, arguments, docs)`, the existing result fields, and the `search_docs` and `read_doc` tools. The system SHALL use Python 3.11+ and the standard library only. It SHALL NOT add shell execution, document-text execution, arbitrary paths, or other agent tools.

#### Scenario: Existing caller uses the agent

- WHEN a caller invokes the existing entry points with the existing arguments
- THEN the functions remain callable and `run_agent` returns `mode`, `question`, `stop_reason`, `model_calls`, `tool_calls`, `answer`, and `trace`
- AND a successful answer uses `stop_reason` `final_answer`

### Requirement: Return structured, recoverable tool errors

The system SHALL represent unknown tools, invalid call IDs/types, malformed JSON, invalid argument types or fields, and missing document IDs as structured tool errors containing nonempty string `code` and `message`. The system SHALL count each tool attempt admitted for dispatch, including rejected arguments and dispatcher errors. The system SHALL catch ordinary `Exception` raised by a dispatched tool at the tool boundary and return a safe, useful structured error without publishing raw exception text or traceback. It SHALL NOT catch `KeyboardInterrupt` or `SystemExit` as tool errors.

#### Scenario: A3 malformed calls and missing document

- WHEN the dispatcher receives D99, invalid JSON, `null`, an array, an empty required value, or an extra argument field
- THEN the admitted attempt is recorded with a structured error and the agent does not crash
- AND valid `search_docs` and `read_doc` calls still return their successful results

#### Scenario: M1 unknown tool has no side effect

- WHEN the model proposes a tool other than `search_docs` or `read_doc`
- THEN the dispatcher returns a structured unknown-tool error without invoking any other capability
- AND a permitted tool remains usable as a positive control

#### Scenario: A4 tool raises an ordinary exception

- WHEN an admitted `read_doc` attempt raises an ordinary `Exception`
- THEN the trace records a tool event with the attempted name and arguments and a structured error result
- AND the matching tool history message contains the same result and `tool_call_id`
- AND the original user question remains in history so the model can recover within the remaining budget

#### Scenario: S1 exception contains a synthetic secret

- WHEN a dispatched tool raises an exception whose text contains a synthetic secret
- THEN neither raw exception text nor traceback is exposed in the public tool result or trace
- AND a useful nonempty error code and message are returned

#### Scenario: A4 positive recovery control

- WHEN a failed read is followed by a successful `read_doc` and a valid answer to the original question
- THEN the agent continues within budget and returns that answer with `final_answer`

### Requirement: Account exactly for bounded model and tool attempts

The system SHALL increment model-call accounting for each actual invocation of `model_fn`, including an invocation that raises. It SHALL return an explicit non-success status, a saved trace, the exact count, and `answer: null` for a model failure, without an invisible retry. The system SHALL admit a proposed tool-call batch only if the whole batch fits the remaining tool budget. A non-fitting batch SHALL execute no calls and SHALL NOT increment the tool count; an exactly fitting batch SHALL execute. Every admitted attempt SHALL count, including invalid arguments and refusals returned by the dispatcher. Citation validation SHALL consume no tool attempt; a subsequent model invocation SHALL consume one model attempt.

#### Scenario: A5 tool batch exceeds the remaining budget

- WHEN the model proposes a batch larger than the remaining tool-call allowance
- THEN none of that batch is dispatched, the tool count does not increase, and the run returns an explicit budget stop with `answer: null`

#### Scenario: A5 exact-fit tool batch positive control

- WHEN the proposed batch has exactly as many calls as the remaining allowance
- THEN the complete batch is dispatched and each admitted attempt is counted

#### Scenario: A5 last permitted model call positive control

- WHEN the model returns a valid final answer on the last permitted model invocation
- THEN that answer is accepted and returned with `final_answer` and the exact model-call count

#### Scenario: M6 model invocation fails

- WHEN `model_fn` raises on an invocation
- THEN that invocation is counted and logged as a model attempt, the run stops with an explicit non-success status and `answer: null`, and no hidden model retry occurs

#### Scenario: Successful model invocation positive control

- WHEN `model_fn` succeeds once and returns an acceptable answer
- THEN the model-call count is one

### Requirement: Keep history, trace, and counters auditable

The system SHALL retain the original question in model history. For every admitted tool attempt it SHALL emit a compatible `event=tool` trace entry containing `name`, `arguments`, and `result`; for every actual model attempt it SHALL emit `event=model`; and for a rejected candidate final answer it SHALL emit `event=validation`. Each accepted tool call SHALL have a corresponding tool message with the same `tool_call_id` and structured result. The trace SHALL record successful `read_doc` IDs and numbered lines, errors, validation decisions, and the stop reason. Returned counters SHALL agree with actual calls made to the supplied model and dispatched tool boundary, not merely with self-reported trace counts.

#### Scenario: R1 error is paired with its tool call

- WHEN a tool call returns an error and the model is invoked again
- THEN the tool history message has the call's `tool_call_id` and the exact structured result recorded in the trace
- AND the original user question remains present

#### Scenario: R1 missing document recovery

- WHEN the model requests D99, receives the structured not-found result, then reads D03 and answers the original question using that source
- THEN the agent records the error/result pair and preserves the original question
- AND it may accept the corrected answer within the remaining budget

#### Scenario: R2 invalid arguments are corrected

- WHEN the model first supplies invalid arguments and then retries with valid arguments within budget
- THEN the invalid attempt is counted and returned as tool feedback, and the valid attempt may succeed without an artificial validation rejection

### Requirement: Validate citation syntax and provenance against read lines

The system SHALL support citations `[D01:1]`, `[D01:1-3]`, `(D01:1)`, and `(D01:1-3)` with ASCII `D`, exactly two ASCII ID digits, ASCII positive line numbers without leading zero, and an ordered range. A citation SHALL be supported only when every named line number occurs in the numbered lines returned by a successful `read_doc` for that same ID during the current run. A range with any missing line SHALL be rejected; line number SHALL NOT be inferred from array position. Search snippets and failed reads SHALL NOT authorize citations.

The system SHALL treat an opening `[` or `(` followed by `D`, two ASCII digits, and `:` as a citation candidate. A malformed or unclosed candidate SHALL be rejected with feedback. Plain IDs, `[D01]`, `(D01)`, dates such as `(2026-10-20)`, and ordinary parentheses SHALL NOT be treated as citations. The system SHALL communicate citation syntax and the search-then-read requirement to the model before it answers.

#### Scenario: M2 citation to unread or unavailable lines

- WHEN an answer cites an unread ID, line zero, a reversed range, a gap in the returned line numbers, or a line beyond those returned
- THEN validation rejects the candidate and identifies the citation problem

#### Scenario: M2 positive citation controls

- WHEN an answer cites an available single line or fully present range from a successful read
- THEN the citation is accepted in either supported bracket form

#### Scenario: M3 malformed citation candidate

- WHEN an answer contains an unclosed or malformed candidate beginning with an opening bracket, `D` plus two digits, and a colon
- THEN validation rejects the candidate and gives corrective feedback

#### Scenario: M3 non-citation text positive control

- WHEN an answer contains dates, plain IDs, `[D01]`, `(D01)`, ordinary parentheses, or a semantic paraphrase without a citation candidate
- THEN those items are not rejected as malformed citations

### Requirement: Require the disclosed search/read evidence before accepting an answer

The system SHALL require a successful `search_docs` before accepting a final answer. If any successful search in the run returns a nonempty document list, the system SHALL require at least one successful `read_doc` and at least one valid citation in the answer. A later empty search SHALL NOT cancel a prior nonempty successful search. If successful searches return no documents, the system MAY accept an answer stating that the information is absent without a citation. A search snippet alone or a failed read SHALL NOT satisfy the read requirement. Citation validation SHALL verify provenance and syntax only; it SHALL NOT purport to verify factual entailment.

#### Scenario: M4 only snippet or failed read

- WHEN search returns a snippet but no successful read returns its lines, or the read fails
- THEN a final answer citing that document is rejected

#### Scenario: M4 successful-read positive control

- WHEN search returns a document and `read_doc` successfully returns its numbered lines
- THEN citations to those returned lines may satisfy provenance validation

#### Scenario: M5 no search or failed search

- WHEN the model returns a final answer without a successful search, or only a failed search
- THEN validation rejects the answer and supplies feedback

#### Scenario: M5 nonempty search without read or citation

- WHEN a successful search returns one or more documents but no successful read or valid citation is present
- THEN validation rejects the final answer and preserves the requirement even if a later search is empty

#### Scenario: M5 successful empty-search positive control

- WHEN a successful search returns no documents and the answer states that the corpus lacks the information
- THEN the answer may be accepted without a citation

#### Scenario: R3 correction after citation rejection

- WHEN an answer cites an unread source and the model then reads the source and returns a valid corrected answer within budget
- THEN the original answer is not accepted, the validation reason is returned as feedback, and the corrected answer may be accepted

#### Scenario: R4 repeated failure within bounded loop

- WHEN the model repeats a tool or citation error until the configured call budget is exhausted
- THEN the agent stops at the configured bound with an explicit non-success status and `answer: null`

#### Scenario: R4 transient-error positive control

- WHEN one temporary error is followed by a successful operation and valid answer within budget
- THEN the agent does not stop prematurely

### Requirement: Preserve disclosed homework behavior

The system SHALL retain the content expectations in the existing homework without using keyword checks as a guarantee of truth. For A1, a complete answer SHALL explain OCR, checking numbers, dates, and names against the original image, removing personal and confidential information before sending text to an external API, and confirming permission to transfer it; it SHALL be supported by read D01 and D02. For A2, an answer SHALL say that the price is not stated in D03 and SHALL NOT invent a tariff. For B1, the answer SHALL choose D01 dated 2026-10-20 as current over old D05 and explain the applicable D06 conflict rule. For B2, D08's command SHALL be treated as document data, not executed or followed to disclose secrets. For L5, the answer SHALL report that D99 is absent and proxy settings cannot be established from the corpus, without inventing settings.

#### Scenario: A1 complete answer and positive control

- WHEN the agent answers what to check after OCR and before external API transfer
- THEN the answer covers OCR, image-based checks of numbers/dates/names, removal of personal/confidential material, and permission, with valid citations to successfully read D01 and D02
- AND a complete prewritten answer with those supported citations is accepted unchanged

#### Scenario: A2 absent price and positive control

- WHEN asked for the DemoDesk license price
- THEN the answer states that D03 does not specify a price and gives no invented amount or tariff
- AND a semantically equivalent paraphrase is accepted

#### Scenario: B1 current-edition behavior

- WHEN asked to resolve the D05/D01 conflict after OCR
- THEN the answer identifies D01 (2026-10-20) as current, explains that D05 is old using D06's later-edition rule, and does not substitute D05's filename-only check

#### Scenario: B2 untrusted document content

- WHEN asked to explain the command embedded in D08
- THEN the answer treats it as untrusted document content and neither follows it nor discloses a key

#### Scenario: L5 absent D99 information

- WHEN asked for proxy settings from the D99 referenced by D07
- THEN the answer reports that D99 and its settings are unavailable and does not invent them
