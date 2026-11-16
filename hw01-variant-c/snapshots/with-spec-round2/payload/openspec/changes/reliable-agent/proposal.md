# Change: Reliable tool handling, budgets, and source validation

## Why

The current agent needs to turn tool failures into recoverable model feedback, account for every actual model and admitted tool attempt at the documented boundaries, and accept citations only when their exact numbered lines were returned by a successful `read_doc` call in the current run. These changes preserve the homework's bounded loop, interfaces, trace, synthetic corpus, and Python 3.11+ standard-library constraint.

## What Changes

- Specify structured handling for unknown tools, invalid arguments, missing document IDs, and ordinary exceptions raised by a dispatched tool.
- Specify exact model/tool budget admission and accounting, including whole-batch admission and explicit budget/model-failure stop results.
- Specify trace and tool-history correspondence, retention of the original question, and recovery feedback within the existing bounded loop.
- Specify citation syntax, malformed-candidate rejection, provenance against successfully read numbered lines, and the search/read/answer acceptance conditions.
- Preserve the homework behaviors for OCR and external API handling (A1), absent pricing (A2), tool errors (A3), tool-exception recovery (A4), and exact limits (A5), with the matrix's positive controls.
- Preserve the disclosed curriculum controls for choosing the current edition (B1), treating document text as data (B2), and reporting the missing D99 source (L5).

## Capabilities

### Modified Capabilities

- `agent`: reliable tool dispatch, bounded execution, trace accounting, and evidence-based citation validation.

## Impact

- Behavioral contract for `run_agent(question, cfg, model_fn, mode="LIVE", emit=print)`, `run_allowed_tool(name, arguments, docs)`, and the existing `search_docs` / `read_doc` tools.
- Result and trace fields remain compatible as documented in `contract.md`; new details may be added without removing the required fields/events.
- No new tools, dependencies, I/O powers, corpus changes, test expectation changes, or unbounded retry behavior.
