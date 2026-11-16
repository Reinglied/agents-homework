# Manual coverage review

Inputs reviewed: this project copy's `contract.md` and `matrix.md`; specification target: `openspec/changes/reliable-agent/specs/agent/spec.md`.

| Disclosed requirement/scenario | Coverage in spec |
|---|---|
| Existing interfaces, result keys, tools, Python/stdlib, restricted capabilities | Preserve interface and permitted capabilities |
| Structured errors for unknown tools/IDs/JSON/types/fields; catch ordinary Exception, not process-control exceptions | Return structured, recoverable tool errors; A3, A4, S1 |
| Count actual model attempts, including errors; explicit stop and null answer, no hidden retry | Exact bounded accounting; M6 |
| Count admitted tool attempts incl. invalid/refusal; whole-batch admission; exact-fit execution; over-limit none/count unchanged | Exact bounded accounting; A5 scenarios |
| Validation free of tool calls; next model call consumes budget | Exact bounded accounting |
| Result keys and compatible model/tool/validation event shapes; ID pairing; original question; actual counters | Auditable history/trace/counters; R1/R2 |
| Journal success and errors, validation, read IDs/numbered rows, stop reason | Auditable history/trace/counters |
| Citation forms, ASCII syntax, positive no-zero-prefix lines, ordered complete range, successful current-run read provenance; actual line IDs rather than array index | Citation syntax/provenance requirement; M2 |
| Malformed/unclosed candidates rejected; dates, bare/bracketed IDs, ordinary parentheses are not candidates | Citation syntax/provenance requirement; M3 |
| Successful search needed; nonempty search requires read + citation across any searches; empty search may answer absence without citation | Search/read evidence requirement; M4/M5 |
| Snippet/failed read do not authorize citations | Search/read evidence requirement; M4 |
| Incorrect answer validation gives exact feedback and bounded repair; paraphrases pass, no keyword truth guarantee | Search/read evidence; R3/R4; homework behavior |
| A1: OCR, verify numbers/dates/names on image; redact personal/confidential; permission; D01/D02 | Homework behavior; A1 and positive control |
| A2: no price in D03, don't invent tariff; paraphrase positive control | Homework behavior; A2 |
| A3: invalid inputs and successful tool controls | Structured errors; A3 |
| M1: unknown tool has no side effect; allowed tool positive control | M1 scenario |
| A4: read exception logged/returned; recovery and successful-read control | Structured errors; A4 |
| A5: model/tool bounds, over-budget packet, exact-fit packet, final last model call | Bounded accounting; A5 scenarios |
| Matrix M1/M2/M3/M4/M5/M6 | Covered under structured errors, citation, search/read, and model failure requirements |
| Matrix R1 exact D99 → D03 correction and call-ID/result correspondence; R2/R3/R4 and S1 | R1 missing-document and trace-pairing scenarios; R2/R3/R4/S1 scenarios |
| Matrix B1/B2 and L5 | Homework behavior; B1/B2/L5 scenarios |
| Positive controls and unchanged expected outcomes | Named positive-control scenarios for A1/A2/A3/A4/A5, M2/M3/M4/M5/M6, R4 |
| No LIVE, unchanged common tests and external-data assumptions | No LIVE run; spec preserves expectations; task verification scoped to future instruction |

Manual conclusion: the disclosed contract and matrix requirements are represented. The citation gate checks format and provenance only; content truth remains separately evaluated as required by contract.
