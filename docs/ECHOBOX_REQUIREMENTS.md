# EchoBox Requirements Catalog — Project ECHO

This document catalogs the 21 source-grounded requirements extracted from [sohan10012/EchoBox](https://github.com/sohan10012/EchoBox.git) by TraceTest AI. Every requirement carries strict provenance, exact source file and line boundaries, segmented atomic clauses, and verifiable acceptance criteria.

---

## Module Index

- **`ECHO-ROOMS`**: Room Lifecycle
- **`ECHO-DISCOVERY`**: Public Discovery
- **`ECHO-CHAT`**: Anonymous Conversation
- **`ECHO-OWNER`**: Room Ownership
- **`ECHO-IDENTITY`**: EchoBox Identity
- **`ECHO-EXPIRY`**: Ephemeral Lifecycle
- **`ECHO-SECURITY`**: Security & Abuse Protection
- **`ECHO-FRONTEND`**: User Experience

---

## Complete Requirements Matrix

### 1. ECHO-REQ-001: Room Creation and Initial State Initialization
- **Module**: `ECHO-ROOMS`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:153-235`)
- **Objective**: Provide ephemeral discussion spaces with deterministic 24-hour lifespans and unique identifiers.
- **Clauses**:
  - `ECHO-REQ-001.C1`: The system shall generate an 8-character hexadecimal identifier for each newly created room.
  - `ECHO-REQ-001.C2`: The system shall compute an expiration timestamp exactly 86400 seconds (24 hours) after creation.
  - `ECHO-REQ-001.C3`: The system shall persist room metadata under partition key `ROOM#{room_id}` and sort key `METADATA`.
  - `ECHO-REQ-001.C4`: When visibility is 'public', the system shall create an index entry under `DISCOVERY#PUBLIC` with sort key `ROOM#{room_id}`.
- **Acceptance Criterion `ECHO-REQ-001.AC1`**:
  - Quote: `expires_at = now_epoch + 86400  # Exactly 24-hour lifetime`
  - Expected: HTTP 201 with status `active` and `expires_at = created_at + 86400`.

### 2. ECHO-REQ-002: Public Room Discovery and Message Count Aggregation
- **Module**: `ECHO-DISCOVERY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:238-290`)
- **Objective**: Allow users to find public discussion topics without authentication.
- **Clauses**:
  - `ECHO-REQ-002.C1`: The system shall query partition `DISCOVERY#PUBLIC` in reverse chronological order.
  - `ECHO-REQ-002.C2`: Rooms with status 'closed' or whose `expires_at` epoch is in the past shall be omitted from discovery.
  - `ECHO-REQ-002.C3`: If search query is provided, rooms whose name or description does not match shall be filtered out.
  - `ECHO-REQ-002.C4`: For each matching room, the system shall count messages under `ROOM#{room_id}` with sort key beginning with `FEEDBACK#`.

### 3. ECHO-REQ-003: Anonymous Message Posting and Character Boundary
- **Module**: `ECHO-CHAT`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:338-400`)
- **Objective**: Enable anonymous participants to post constructive feedback without requiring account creation.
- **Clauses**:
  - `ECHO-REQ-003.C1`: Feedback messages exceeding 2000 characters shall be rejected with HTTP 400.
  - `ECHO-REQ-003.C2`: Display names shall be truncated to a maximum of 50 characters, defaulting to 'Anonymous' if omitted.
  - `ECHO-REQ-003.C3`: Anonymous session identifiers shall be truncated to a maximum of 64 characters.
  - `ECHO-REQ-003.C4`: The system shall generate a unique 12-character hexadecimal identifier for each feedback submission.

### 4. ECHO-REQ-004: Owner Room Closure and Authorization Boundaries
- **Module**: `ECHO-OWNER`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:600-650`)
- **Clauses**:
  - `ECHO-REQ-004.C1`: When close_room is invoked, the system shall verify caller sub matches room owner_id.
  - `ECHO-REQ-004.C2`: If caller does not match owner_id, the system shall return HTTP 403 Forbidden.
  - `ECHO-REQ-004.C3`: Once a room is closed, subsequent submit_feedback attempts shall be rejected with HTTP 403.
  - `ECHO-REQ-004.C4`: Room owners shall be authorized to delete any feedback item in their owned room.

### 5. ECHO-REQ-005: EchoBox ID Author Post Indexing and Deletion
- **Module**: `ECHO-IDENTITY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:394-400, 516-547`)
- **Clauses**:
  - `ECHO-REQ-005.C1`: Posts submitted with valid EchoBox ID credentials shall be indexed under `USERPOSTS#{author_id}`.
  - `ECHO-REQ-005.C2`: get_my_posts shall return all active posts authored by the caller.
  - `ECHO-REQ-005.C3`: delete_my_post shall verify item.author_id matches caller sub.
  - `ECHO-REQ-005.C4`: Attempts to delete another user's post shall be rejected with HTTP 403 Forbidden.

### 6. ECHO-REQ-006: Ephemeral Expiration and HTTP 410 Gone Status
- **Module**: `ECHO-EXPIRY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:322-327, 366-368`)
- **Clauses**:
  - `ECHO-REQ-006.C1`: The system shall check whether current timestamp exceeds room expires_at epoch.
  - `ECHO-REQ-006.C2`: If current epoch exceeds expires_at, submit_feedback shall return HTTP 410 Gone.
  - `ECHO-REQ-006.C3`: get_room on an expired room shall set status to 'expired' and is_expired to True.
  - `ECHO-REQ-006.C4`: An expired room cannot be reopened by its owner.

### 7. ECHO-REQ-007: Request Payload Size Protection (64KB Limit)
- **Module**: `ECHO-SECURITY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:24-27`)
- **Clauses**:
  - `ECHO-REQ-007.C1`: The system shall inspect raw request body length prior to parsing.
  - `ECHO-REQ-007.C2`: If body length exceeds 65536 bytes, the system shall return HTTP 413 Payload Too Large.

### 8. ECHO-REQ-008: Room Description Length Boundary Inconsistency (`DEF-ECHO-001`)
- **Module**: `ECHO-SECURITY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:167 vs README.md`)
- **Clauses**:
  - `ECHO-REQ-008.C1`: The README and security audit specify a 500-character limit on room descriptions.
  - `ECHO-REQ-008.C2`: The backend implementation allows up to 1000 characters before truncation.
  - `ECHO-REQ-008.C3`: Input exceeding 1000 characters is silently truncated rather than rejected with HTTP 400.

### 9. ECHO-REQ-009: Invalid Visibility Fallback to Public Space (`DEF-ECHO-003`)
- **Module**: `ECHO-SECURITY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:162-165`)
- **Clauses**:
  - `ECHO-REQ-009.C1`: The system shall validate visibility is exactly 'public' or 'private'.
  - `ECHO-REQ-009.C2`: Invalid visibility values currently default to 'public' silently (DEF-ECHO-003).

### 10. ECHO-REQ-010: Frontend Anonymous Participant Landing
- **Module**: `ECHO-FRONTEND`
- **Provenance**: `Directly observed in source` (`src/components/JoinRoom.tsx:1-85`)
- **Clauses**:
  - `ECHO-REQ-010.C1`: The frontend shall present an input field for room ID with autofocus and uppercase formatting.
  - `ECHO-REQ-010.C2`: Entering an invalid or empty room ID shall trigger client-side validation feedback.
  - `ECHO-REQ-010.C3`: Upon entering a valid 8-character room code, the interface shall route to the active conversation.

### 11. ECHO-REQ-011: Live AWS API Gateway Upstream Health Probe (`DEF-ECHO-005`)
- **Module**: `ECHO-SECURITY`
- **Provenance**: `External assumption requiring verification` (`src/api/client.ts:5-8`)
- **Clauses**:
  - `ECHO-REQ-011.C1`: The client specifies default API endpoint `https://bnbpmiljw9.execute-api.ap-south-1.amazonaws.com`.
  - `ECHO-REQ-011.C2`: Production verification probes evaluate live upstream HTTP status codes.
  - `ECHO-REQ-011.C3`: Unseeded upstream cloud infrastructure returning HTTP 500 shall be recorded as an external blocker.

### 12. ECHO-REQ-012: Message History Retrieval and Sequential Ordering
- **Module**: `ECHO-CHAT`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:401-445`)
- **Clauses**:
  - `ECHO-REQ-012.C1`: The system shall query items partitioned under `ROOM#{room_id}` with sort key beginning with `FEEDBACK#`.
  - `ECHO-REQ-012.C2`: Messages shall be returned in forward chronological order (`ScanIndexForward=True`).
  - `ECHO-REQ-012.C3`: The response shall include both messages and count properties.

### 13. ECHO-REQ-013: Room Reopening and Ephemeral Boundary Protection
- **Module**: `ECHO-OWNER`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:651-680`)
- **Clauses**:
  - `ECHO-REQ-013.C1`: The owner of a closed room shall be permitted to reopen it by updating status to active.
  - `ECHO-REQ-013.C2`: If the room has exceeded its `expires_at` epoch, `reopen_room` shall return HTTP 400.
  - `ECHO-REQ-013.C3`: Non-owners attempting to reopen a room shall receive HTTP 403 Forbidden.

### 14. ECHO-REQ-014: Owner Room Portfolio Listing
- **Module**: `ECHO-OWNER`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:549-575`)
- **Clauses**:
  - `ECHO-REQ-014.C1`: The system shall query partition `OWNER#{owner_id}` for all room references.
  - `ECHO-REQ-014.C2`: Only rooms created by the authenticated owner shall be returned.

### 15. ECHO-REQ-015: CORS Permissive Origin Header Configuration
- **Module**: `ECHO-SECURITY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:141-149`)
- **Clauses**:
  - `ECHO-REQ-015.C1`: All HTTP responses shall include `Access-Control-Allow-Origin: *`.
  - `ECHO-REQ-015.C2`: All HTTP responses shall include `Access-Control-Allow-Methods` and `Access-Control-Allow-Headers`.

### 16. ECHO-REQ-016: Health Check Diagnostic Ping Protocol
- **Module**: `ECHO-SECURITY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:35-50`)
- **Clauses**:
  - `ECHO-REQ-016.C1`: When action is `health_check`, the system shall return status healthy.
  - `ECHO-REQ-016.C2`: Health check shall require no authorization headers.

### 17. ECHO-REQ-017: Silent Truncation of Room Name and Description (`DEF-ECHO-002`)
- **Module**: `ECHO-SECURITY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:166-167`)
- **Clauses**:
  - `ECHO-REQ-017.C1`: The implementation slices `room_name` to 100 characters silently.
  - `ECHO-REQ-017.C2`: The implementation slices `room_description` to 1000 characters silently.
  - `ECHO-REQ-017.C3`: No warning or error is returned to the user when truncation occurs.

### 18. ECHO-REQ-018: Discovery Loop N+1 Query Performance Bottleneck (`DEF-ECHO-004`)
- **Module**: `ECHO-DISCOVERY`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:269-274`)
- **Clauses**:
  - `ECHO-REQ-018.C1`: `discover_rooms` loops through all items in `DISCOVERY#PUBLIC`.
  - `ECHO-REQ-018.C2`: For each room item, a separate DynamoDB query executes to count messages.

### 19. ECHO-REQ-019: Frontend Toast Notification and Dismissal Feedback
- **Module**: `ECHO-FRONTEND`
- **Provenance**: `Directly observed in source` (`src/components/Toast.tsx:1-60`)
- **Clauses**:
  - `ECHO-REQ-019.C1`: Toast component shall render with `role='alert'` for accessibility.
  - `ECHO-REQ-019.C2`: Notifications shall automatically disappear after duration timeout.
  - `ECHO-REQ-019.C3`: Manual dismiss button shall immediately remove the notification.

### 20. ECHO-REQ-020: Frontend Responsive Room Conversation
- **Module**: `ECHO-FRONTEND`
- **Provenance**: `Directly observed in source` (`src/components/RoomView.tsx:1-120`)
- **Clauses**:
  - `ECHO-REQ-020.C1`: The view shall display room title, description, and 24-hour expiration countdown.
  - `ECHO-REQ-020.C2`: Textarea shall enforce max length constraint matching backend limit.
  - `ECHO-REQ-020.C3`: If room status is closed or expired, the submission form shall be disabled.

### 21. ECHO-REQ-021: Legacy Room Claiming Protocol
- **Module**: `ECHO-ROOMS`
- **Provenance**: `Directly observed in source` (`backend/lambda_function.py:700-740`)
- **Clauses**:
  - `ECHO-REQ-021.C1`: `claim_legacy_room` shall verify caller authentication.
  - `ECHO-REQ-021.C2`: Successfully claimed rooms shall update the owner index.

