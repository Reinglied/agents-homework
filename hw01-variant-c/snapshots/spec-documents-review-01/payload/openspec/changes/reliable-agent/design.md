# Design: Reliable agent execution

## Context

The agent is a bounded Python 3.11+ document agent. Its tools are local `search_docs` and `read_doc`; the model is supplied through `model_fn`. The disclosed contract fixes the callable interfaces, result keys, compatible trace events, tool error shape, whole-batch budget policy, and current-run citation evidence. The public matrix separately evaluates deterministic mechanics (STUB) and model behavior (LIVE).

## Decisions

### Tool failures stay in the tool protocol

Validate the tool name, call ID/type, JSON, and exact argument schema at the dispatch boundary. A dispatched attempt that cannot be carried out produces a result with a nonempty `error.code` and `error.message`. Catch ordinary `Exception` from the tool boundary and return safe, useful feedback; do not expose raw exception text or traceback in the public trace. Do not catch `KeyboardInterrupt` or `SystemExit`. Append the same structured result to the trace and to the matching tool message, keyed by the accepted `tool_call_id`, so the model can repair the original task.

### Admit complete batches before dispatch

Count every call to `model_fn`, even one that raises. Count a tool attempt when it is admitted to dispatch, including invalid arguments, unknown tools, and refusals returned by the dispatcher. Check the full model-proposed tool batch before executing any member. If the batch does not fit, dispatch none of it and do not increase the tool count; if it exactly fits, dispatch the entire batch. Citation validation consumes no tool attempt, while any following model call consumes a model attempt. Do not retry model errors invisibly.

### Preserve bounded, inspectable outcomes

Return the existing result fields and compatible `model`, `tool`, and `validation` events. Record failed model attempts as well as successful ones; retain actual model/tool counts, successful read IDs and numbered lines, errors, validation decisions, and the stop reason. A model failure or exhausted budget has an explicit non-success stop reason and `answer: null`. No final unsupported answer is returned on an exhausted run.

### Validate citation provenance, not wording

An accepted citation must use the disclosed syntax and every cited line number must exist in a successful `read_doc` result for that ID during this run. A range is valid only if all its lines are present; do not infer lines from a search snippet or array position. A successful search is required. A nonempty successful search additionally requires a successful read and at least one valid citation. A successful empty search permits an answer that states the information is absent without a citation. Malformed citation candidates and unsupported citations produce specific validation feedback and another bounded opportunity to answer. Validation does not claim to establish factual or semantic truth.

### Keep the homework scope fixed

The accepted answer for A1 must cover OCR, checking numbers/dates/names against the image, removing personal/confidential information before external transfer, and having permission; it must cite read D01 and D02. A2 must state that D03 gives no price and must not invent a tariff. A3–A5 exercise the disclosed mechanical failure and budget cases. B1 and B2 retain their stated LIVE behavior. D08 remains untrusted document content; only the two existing tools are available.

## Compatibility and constraints

- Keep `run_agent(question, cfg, model_fn, mode="LIVE", emit=print)`, `load_config()`, `load_docs()`, and `run_allowed_tool(name, arguments, docs)` callable.
- Preserve result keys `mode`, `question`, `stop_reason`, `model_calls`, `tool_calls`, `answer`, `trace`; preserve required trace event shapes and success status `final_answer`.
- Standard library only; Python 3.11+; no shell, document execution, arbitrary path access, or added agent tools.
- Keep public harness and expected results unchanged. Do not launch LIVE.

## Risks and trade-offs

- A citation gate can verify provenance and syntax, not whether a sentence is entailed by its source. Content scoring remains a separate disclosed evaluation.
- The checker must handle both square and round bracket forms for REPLAY compatibility while rejecting malformed candidate citations.
- Batch admission must occur before side effects; per-call admission could violate the documented all-or-none behavior.
