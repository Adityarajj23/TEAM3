# Requirements Engine & Provenance Architecture — TraceTest AI

## 1. Overview

The Requirements Engine enforces deterministic structure on natural language specifications. It decomposes requirements into atomic, verifiable clauses, computes cryptographic content hashes for change detection, attaches strict provenance metadata, and generates traceable acceptance criteria.

---

## 2. Immutable Requirement Versioning

In high-assurance quality engineering, requirements must never be mutated in place without an audit record. TraceTest AI implements immutable snapshot versioning:

- When a requirement is created, it receives `version: 1` in `RequirementVersion`.
- Any edit (title, description, or business objective) generates a new version row `version: N + 1` with an automated `content_hash`:
  $$\text{content\_hash} = \text{SHA-256}(\text{title} \mathbin{\Vert} \text{description} \mathbin{\Vert} \text{objective})$$
- When a requirement updates, existing approved tests referencing prior versions are evaluated:
  - If cited clauses are unaffected, tests remain valid.
  - If cited clauses changed or were removed, tests are marked `needs_reapproval` with an automated rationale log.

---

## 3. Deterministic Clause Segmentation (`split_clauses`)

Requirements are divided into numbered clauses using deterministic sentence boundary rules:
- Bullet points (`-`, `*`, numbered lists) become distinct clauses.
- Long paragraphs are split at sentence boundaries (`.`, `;`, `!`, `?`) while protecting common abbreviations (`e.g.`, `i.e.`, `vs.`, `No.`).
- Each clause receives a normalized text hash ($\text{normalized\_hash}$) ignoring whitespace and casing.
- Persistent Clause Identifiers:
  - `ECHO-REQ-001.C1`
  - `ECHO-REQ-001.C2`
  - `DF-PAY-001.C1`

---

## 4. Five-Tier Provenance Classification

To eliminate AI hallucination, every extracted requirement and clause must carry one of five strict provenance labels:

1. **`Directly observed in source`**:
   - The behavior is explicitly implemented in code.
   - Example: `clean_desc = room_desc[:1000]` in `backend/lambda_function.py:167`.
2. **`Documented in README or technical documentation`**:
   - The behavior is described in repository documentation or design specifications.
   - Example: Statement that `room_description` has a maximum length of 500 characters in `README.md`.
3. **`Inferred from implementation`**:
   - The behavior is logically deduced from database schema design or cloud infrastructure patterns.
   - Example: Single-table DynamoDB primary key design with `PK: ROOM#{id}` and `SK: METADATA`.
4. **`External assumption requiring verification`**:
   - An external service dependency whose live status cannot be verified from source code alone.
   - Example: Upstream AWS API Gateway endpoint availability at `https://<api-id>.execute-api.ap-south-1.amazonaws.com`.
5. **`Unable to verify`**:
   - Features referenced in documentation or comments where implementation is absent or inaccessible.

---

## 5. Automated Ambiguity Detection

The engine scans all clause text for non-verifiable, subjective, or ambiguous terminology:
- Ambiguity Dictionary: `promptly`, `timely`, `reasonable`, `appropriate`, `fast`, `user-friendly`, `as needed`, `sufficient`, `should`, `might`.
- When an ambiguity term is detected, an `ambiguity_flag` is attached to the clause, displaying a warning badge in the UI and prompting the QA engineer to clarify the acceptance criterion.

---

## 6. Acceptance Criteria Formulation

Acceptance Criteria (AC) link clauses to concrete validation conditions:
- **Grounded Source Quotation**: The AC must cite a verbatim quotation from the source text or code.
- **Preconditions**: Exact state required before verification (e.g. "Room created with owner credentials").
- **Expected Behaviour**: Observable outcome (e.g. "HTTP 201 with expires_at = now + 86400").
- **Confidence Metric**: Confidence score based on quote match verification (1.0 for verbatim matches).

