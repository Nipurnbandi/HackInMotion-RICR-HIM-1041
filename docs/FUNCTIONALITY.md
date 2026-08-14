# SmartCity — Functional Specification

Complete reference for **how every feature actually behaves**: the rules, formulas, thresholds, and edge cases. Every number here is taken from the code, with the defining file named so you can verify it.

For endpoint signatures see [api-documentation.md](../api-documentation.md); for the system diagram see [architecture.mmd](architecture.mmd).

---

## Table of contents

1. [Roles & permissions](#1-roles--permissions)
2. [Authentication & sessions](#2-authentication--sessions)
3. [The category catalogue](#3-the-category-catalogue-master-table)
4. [Reporting an issue](#4-reporting-an-issue)
5. [Photo upload & validation](#5-photo-upload--validation)
6. [Duplicate detection & case grouping](#6-duplicate-detection--case-grouping)
7. [Department routing](#7-department-routing)
8. [Priority scoring](#8-priority-scoring)
9. [SLA escalation](#9-sla-escalation)
10. [Citizen upvoting](#10-citizen-upvoting)
11. [Issue lifecycle & status workflow](#11-issue-lifecycle--status-workflow)
12. [Resolution evidence](#12-resolution-evidence)
13. [Confirm & reopen](#13-confirm--reopen)
14. [Status history (audit trail)](#14-status-history-audit-trail)
15. [AI photo verification](#15-ai-photo-verification)
16. [Department notifications](#16-department-notifications)
17. [The live city map](#17-the-live-city-map)
18. [Admin analytics](#18-admin-analytics)
19. [Hotspot detection](#19-hotspot-detection)
20. [Public transparency scoring](#20-public-transparency-scoring)
21. [Search, filtering & pagination](#21-search-filtering--pagination)
22. [Internationalisation](#22-internationalisation)
23. [Error handling catalogue](#23-error-handling-catalogue)
24. [Data model](#24-data-model)
25. [Configuration reference](#25-configuration-reference)

---

## 1. Roles & permissions

Two roles, defined in `app/core/roles.py`. **Enforcement is server-side** — the `require_roles(...)` dependency guards every protected route, so a citizen who forges a URL or calls the API directly still gets `403`. The frontend `RoleRoute` guard is a convenience, never the security boundary.

| Capability | Citizen | Admin |
|---|:---:|:---:|
| Sign up (self-service) | ✅ | ❌ (created via `scripts/create_admin.py`) |
| Submit a report | ✅ | ❌ |
| View **own** reports + full history | ✅ | — |
| View any other citizen's report | ❌ (`404`, not `403` — see below) | ✅ |
| Live city map | ✅ | ✅ |
| Upvote a case | ✅ | ❌ |
| Confirm / reopen a resolved case | ✅ (own reports) | ❌ |
| Work queue, analytics, department inbox | ❌ | ✅ |
| Change status, add resolution note/photo | ❌ | ✅ |
| Delete an issue | ❌ | ✅ |
| Public transparency report card | ✅ | ✅ |

The transparency report card is additionally reachable with **no account at all** — it is the only unauthenticated data endpoint in the system.

**Why `404` and not `403` for another citizen's report:** `get_citizen_issue` treats "does not exist" and "not yours" identically, so the API never leaks whether a given tracking ID is real. Role mismatches (citizen hitting an admin route) return `403`.

**Signup cannot escalate.** The signup schema ignores any client-supplied role; every self-service account is created as `CITIZEN`. Covered by `test_signup_cannot_escalate_to_admin`.

---

## 2. Authentication & sessions

| Aspect | Behaviour |
|---|---|
| Password storage | bcrypt via passlib (`app/core/security.py`) |
| Token | JWT, HS256, carrying `sub` (user id), `role`, `type: "access"`, `exp` |
| Transport | HTTP-only cookie (also accepted as `Authorization: Bearer <token>`) |
| Lifetime | `ACCESS_TOKEN_EXPIRE_MINUTES`, default **30 minutes** |
| Token-type check | A token without `type: "access"` is rejected — refresh-style tokens can't be replayed as access tokens |
| Expiry behaviour | Expired token → `401`; the frontend redirects to `/login` |

The API is otherwise **stateless** — no server-side session store.

---

## 3. The category catalogue (master table)

Seven categories, each carrying five independent behavioural constants. This single table drives duplicate detection, routing, queue order, and escalation. Defined in `app/core/issue_types.py` and `app/services/routing.py`.

| Category | Label | Dedup radius | Dedup window | Severity weight | SLA | Routed to |
|---|---|---:|---:|:---:|---:|---|
| `POTHOLE` | Pothole | 25 m | 60 days | 4 | 7 days | Roads Department |
| `STREETLIGHT` | Streetlight | 30 m | 45 days | 3 | 7 days | Electrical & Streetlighting |
| `DAMAGED_PUBLIC_PROPERTY` | Damaged Public Property | 30 m | 60 days | 3 | 10 days | Public Works |
| `GARBAGE_OVERFLOW` | Overflowing Garbage | 50 m | 3 days | 2 | 2 days | Sanitation Department |
| `ILLEGAL_DUMPING` | Illegal Dumping | 60 m | 7 days | 2 | 4 days | Sanitation Department |
| `WATER_LEAKAGE` | Water Leakage | 80 m | 10 days | 5 | 3 days | Water & Drainage |
| `BROKEN_DRAINAGE` | Broken Drainage | 80 m | 30 days | 5 | 5 days | Water & Drainage |

**How to read the constants:**

- **Dedup radius** — how far apart two reports can be and still be the same problem. A pothole is a point defect (25 m); a burst water main affects a whole street (80 m).
- **Dedup window** — how long the same problem plausibly persists. Garbage is collected within days (3), so a bin reported two weeks later is genuinely a *new* overflow; a pothole lingers for months (60).
- **Severity weight** — the multiplier in the priority score. Utilities that endanger people or property rank highest (5); nuisance categories rank lowest (2).
- **SLA** — days before the case escalates to higher authority. Inversely related to urgency, *not* to severity weight: garbage must be cleared in 2 days even though its severity weight is low.

A **fallback department** (`GENERAL` — General Administration) receives anything with no explicit route, and is also the escalation target.

---

## 4. Reporting an issue

Five wizard steps (`frontend/src/citizen/pages/ReportIssue.jsx`). Each step validates before advancing; the final submit re-validates everything and jumps back to the first broken step if anything fails.

| # | Step | Field | Validation |
|---|---|---|---|
| 1 | Category | `category` | Must be one of the seven enum values |
| 2 | Location | `latitude`, `longitude` | Required. Latitude −90…90, longitude −180…180 (Pydantic bounds). Address is optional and auto-filled |
| 3 | Photo | `photo` | Optional. See [§5](#5-photo-upload--validation) |
| 4 | Description | `description` | Trimmed; **10–2000 characters** |
| 5 | Review | — | Read-only summary; every row has an *Edit* link back to its step |

**Location capture** offers two paths, and neither can hard-fail the report:

- **"Use my current location"** → browser Geolocation API, `enableHighAccuracy: true`, 10-second timeout. Denial or timeout shows *"We couldn't get your location. Allow location access, or tap the map to place the marker."* and the map remains usable.
- **Tap or drag on the map** → sets the pin directly.

Either way a **reverse-geocode** request goes to Nominatim to fill the human-readable address. The request is abortable (a new pin cancels the in-flight lookup), and any failure — offline, rate-limited, 500 — resolves to `null` rather than throwing, so the report is submitted with coordinates only.

**On successful submit** the server assigns:

- `tracking_id` — `SMC-{year}-{id:06d}`, e.g. `SMC-2026-000012`. Shown to the citizen and used for search.
- `case_id` — either the matched existing case, or a new `CASE-{id:06d}`.
- `status` — `SUBMITTED`.
- `department_id` — resolved by category ([§7](#7-department-routing)).

---

## 5. Photo upload & validation

Defined in `validate_photo` / `sniff_image_type` (`app/services/citizen.py`). Applies identically to citizen report photos and admin proof-of-resolution photos.

| Check | Rule | Failure |
|---|---|---|
| Non-empty | File must have content | `400` "The uploaded photo is empty." |
| Size | ≤ `MAX_UPLOAD_SIZE_BYTES` (default **5 MB**) | `413` "Photo is too large. Maximum size is 5 MB." |
| Declared type | `Content-Type` must be JPEG/PNG/WEBP if present | `400` "Unsupported image type…" |
| **Actual content** | **Magic-byte sniff** must identify JPEG, PNG or WEBP | `400` "That file is not a valid JPEG, PNG, or WEBP image." |

The magic-byte check is the security-relevant one: a `.exe` renamed to `.jpg` with a spoofed `Content-Type` is still rejected, because the file's leading bytes are inspected directly:

| Format | Signature |
|---|---|
| JPEG | `FF D8 FF` |
| PNG | `89 50 4E 47 0D 0A 1A 0A` |
| WEBP | `RIFF` … `WEBP` at offset 8 |

**Storage.** Files are written by `LocalDiskStorage` (`app/core/storage.py`) to `{UPLOAD_DIR}/{prefix}/` — `issues/` for report photos, `resolutions/` for proof photos. Filenames are regenerated as `uuid4().hex + token_hex(4) + extension`, so the user-supplied filename never reaches the filesystem (no path traversal, no collisions, no information leak). The storage layer is a `Protocol`, so swapping in S3 means one new class.

The client also pre-checks size and type before upload and shows a live progress bar via `XMLHttpRequest.upload.onprogress`.

---

## 6. Duplicate detection & case grouping

**The problem it solves:** fifteen people report the same pothole. Naively that's fifteen tickets. Here it's **one case with fifteen reports** — and the count of reporters becomes a *signal* that raises its priority instead of noise that buries the queue.

### The algorithm

`find_open_case_id` in `app/services/citizen.py`, executed **before** the new row is committed.

**Step 1 — build a bounding box.** Convert the category's radius in metres into degrees, correcting longitude for latitude convergence:

```
lat_delta = radius_m / 111_320
lon_delta = radius_m / max(111_320 × cos(latitude), 1.0)
```

The `cos(latitude)` term matters: one degree of longitude is ~111 km at the equator but ~96 km at 30° N. Without it, the search box would be too wide in northern cities. The `max(…, 1.0)` guard prevents a division blow-up at the poles.

**Step 2 — query for a candidate.** Find issues satisfying **all** of:

| Condition | Meaning |
|---|---|
| `category == new.category` | Same kind of problem |
| `latitude BETWEEN lat ± lat_delta` | Inside the box |
| `longitude BETWEEN lon ± lon_delta` | Inside the box |
| `created_at > now − window_days` | Recent enough to still be the same occurrence |
| `status NOT IN (RESOLVED, REJECTED)` | Still open — a fixed pothole that returns is a new case |
| `case_id IS NOT NULL` | Already grouped |

Ordered by `created_at ASC, id ASC` and limited to 1, so the **oldest** matching case wins — reports always attach to the original, never to a later duplicate.

**Step 3 — attach or create.**

- **Match** → `case_id` = matched case, `is_primary = False`. The history entry records *"Report submitted and linked to existing case CASE-000012."*
- **No match** → `case_id` = `CASE-{own id:06d}`, `is_primary = True`. This report becomes the case's primary.

### Consequences of the primary/member split

| Concern | Behaviour |
|---|---|
| Admin queue | Lists **primaries only** — one row per real-world problem |
| Status | Members have no independent status; they inherit the primary's *effective status* (`issue_effective_status`) |
| Citizen view | Each reporter still sees their own report and tracking ID, showing the case's status |
| Resolution | Resolving the primary resolves the problem for every reporter attached to it |
| Reopen | A member reopening reopens the **primary**, i.e. the whole case ([§13](#13-confirm--reopen)) |
| Counting | `citizen_count` = distinct citizens on the case; `report_count` = total reports |

### Worked example

Bounding box for a pothole (25 m) at latitude 23.2599:

```
lat_delta = 25 / 111_320                      = 0.000225°
lon_delta = 25 / (111_320 × cos 23.2599°)     = 0.000244°
```

A second pothole report at `23.2601, 77.4128` (≈ 30 m away) falls inside that box and within the 60-day window → linked. The same report filed 61 days later, or 90 m away, → new case.

**Design note.** This is a rectangular (bounding-box) test, not a true great-circle radius, so the corners of the box reach ~1.41× the nominal radius. That is deliberate: it is one indexed SQL range query (`ix_issues_dup_lookup` covers `category, latitude, longitude`) with no trigonometry per row, and slight over-matching is the safer error — a wrongly-linked report is visible and correctable, a missed duplicate silently splits a case.

---

## 7. Department routing

Six departments seeded by `seed_departments` (`app/services/routing.py`), routed by a **database table**, not code branches.

| Code | Name | Email |
|---|---|---|
| `ROADS` | Roads Department | roads@city.gov |
| `ELECTRICAL` | Electrical & Streetlighting | electrical@city.gov |
| `SANITATION` | Sanitation Department | sanitation@city.gov |
| `WATER` | Water & Drainage | water@city.gov |
| `PUBLIC_WORKS` | Public Works | works@city.gov |
| `GENERAL` | General Administration | admin@city.gov |

`resolve_department(db, category)` reads the `category_routes` table (one row per category, unique on `category`) and returns the mapped department; with no row it falls back to `GENERAL`. Seeding is **idempotent** — it only inserts departments and routes that don't already exist, so it is safe to re-run.

**Why this is extensible.** Adding a category or re-pointing an existing one is one `INSERT`/`UPDATE` in `category_routes` — no `if/elif` chain to extend, no redeploy. Reorganising the city (splitting Sanitation into two teams, say) is a data migration.

---

## 8. Priority scoring

The admin work queue is sorted by a score computed per case in `list_admin_cases` (`app/services/admin.py`):

```
people_affected = citizen_count + vote_count
priority        = severity_weight × people_affected × (1 + days_open / 7)
if escalated:  priority × 1.5
```

then `round(..., 1)`, sorted descending.

| Factor | Source | Effect |
|---|---|---|
| `severity_weight` | Category constant, 2–5 | Water leak outranks illegal dumping at equal size and age |
| `people_affected` | Distinct reporters **+** upvotes | Mass-affecting problems climb |
| `(1 + days_open / 7)` | Age of the case | +1× per week waited — nothing can be ignored indefinitely |
| `× 1.5` | SLA breach flag | A breached case outranks comparable un-breached ones |

`days_open` is whole days since `created_at`, floored at 0.

**Worked example** — a 3-day-old water leak (weight 5) reported by 2 citizens with 1 upvote:

```
people_affected = 2 + 1 = 3
priority = 5 × 3 × (1 + 3/7) = 5 × 3 × 1.4286 = 21.4
```

If it later breaches its 3-day SLA: `21.4 × 1.5 ≈ 32.1`.

The frontend colour-codes the badge: **≥ 20 high** (red), **≥ 10 medium** (amber), otherwise low (neutral).

---

## 9. SLA escalation

`run_sla_escalations` (`app/services/escalation.py`) runs opportunistically on **every** admin dashboard, analytics, and queue request — no cron job or worker to keep alive.

**Selection.** A case escalates when *all* hold:

- `is_primary == True`
- `status NOT IN (RESOLVED, REJECTED)`
- `escalated_at IS NULL` — the idempotency guard
- `now >= created_at + SLA_DAYS[category]`

**Actions per escalated case:**

1. Stamp `escalated_at = now` — this is what makes the sweep idempotent. A case escalates **exactly once**, no matter how many times an admin reloads.
2. Append a status-history entry (role `ADMIN`) reading *"Escalated to higher authority — unresolved beyond the 2-day SLA for Overflowing Garbage."* The reporter sees this in their own activity trail.
3. Queue a notification to **General Administration** whose body begins `SLA BREACH — case escalated to higher authority` and names the category, case ID, location, owning department, and the exceeded limit.
4. Set `escalated = true` on the case, which the admin queue renders as a **⚠ SLA breached** badge and which applies the ×1.5 priority boost.

The whole sweep commits once; if nothing is overdue it returns immediately without a write.

---

## 10. Citizen upvoting

`toggle_vote` (`app/services/votes.py`). Lets citizens amplify problems they didn't report themselves.

| Rule | Behaviour |
|---|---|
| Target | Must be a **primary** issue (the case). Non-primary or missing → `404` |
| Self-vote | If the citizen has *any* report in that case, `400` — *"You reported this problem — your report already counts."* |
| Toggle | Voting again removes the vote; the endpoint is a switch, not an increment |
| Uniqueness | `UNIQUE(issue_id, citizen_id)` at the database level — double-submission cannot double-count |
| Response | `{issue_id, vote_count, has_voted}` so the UI can update without a refetch |

Votes surface as `vote_count` / `has_voted` on map markers, as a "👍 N supporters" chip in the admin queue, and — most importantly — inside `people_affected` in the [priority score](#8-priority-scoring).

---

## 11. Issue lifecycle & status workflow

Five statuses (`IssueStatus`). The forward path is `STATUS_FLOW`; `REJECTED` is a terminal branch off it.

```
SUBMITTED ──▶ UNDER_REVIEW ──▶ IN_PROGRESS ──▶ RESOLVED
     │              │                │              │
     └──────────────┴────────────────┴──▶ REJECTED  │
                                                    │
                    UNDER_REVIEW ◀── citizen reopens┘
```

| Status | Meaning shown to the citizen | Set by |
|---|---|---|
| `SUBMITTED` | "We have received your report." | System, on creation |
| `UNDER_REVIEW` | "A city officer is verifying the details." | Admin, or a citizen reopening |
| `IN_PROGRESS` | "Work has started on this issue." | Admin |
| `RESOLVED` | "The issue has been fixed." | Admin |
| `REJECTED` | "This report could not be actioned." | Admin |

**Transitions are not mechanically restricted** — an admin may move a case to any status (including straight to `RESOLVED`), because real municipal work doesn't always advance one step at a time. What the system guarantees instead is that **every transition is recorded** ([§14](#14-status-history-audit-trail)), so any shortcut is visible in the audit trail.

`CLOSED_STATUSES = (RESOLVED, REJECTED)` drives "open case" counts everywhere: the department chips, analytics, escalation eligibility, and duplicate detection (a closed case cannot absorb new reports).

The citizen-facing `StatusTimeline` renders the four-step flow with the current step marked; a rejected report instead renders a two-step *Submitted → Rejected* timeline.

---

## 12. Resolution evidence

Admins close the loop with two artefacts, both optional and independently settable.

**Resolution note** — free text up to 2000 characters, sent via `PUT /api/admin/issues/{id}` as `resolution_note`. Stored on the issue and echoed into the status history so it appears in the trail at the moment it was written. Visible to the reporter under a **Resolution** card.

**Proof-of-resolution photo** — `POST /api/admin/issues/{id}/resolution-photo`, multipart. Runs the identical validation as citizen photos ([§5](#5-photo-upload--validation)), stores under `resolutions/`, sets `resolution_photo_url`, and writes a history entry *"Proof of resolution uploaded."* carrying the photo URL. Also triggers [AI verification](#15-ai-photo-verification) of the proof.

Status changes and resolution details are separate operations, so an admin can attach a note while a case is still `IN_PROGRESS`, or upload proof after marking it resolved.

---

## 13. Confirm & reopen

The reporter gets the final say (`app/services/lifecycle.py`). Both endpoints require the case's **effective status to be `RESOLVED`** — otherwise `400` *"Only resolved reports can be confirmed/reopened."*

| Action | Endpoint | Effect |
|---|---|---|
| **Confirm** | `POST /api/citizen/issues/{id}/confirm` | Status unchanged (`RESOLVED`). Writes a `CITIZEN` history entry *"Reporter confirmed the problem is fixed."* The UI then shows a thank-you instead of the buttons |
| **Reopen** | `POST /api/citizen/issues/{id}/reopen` | Sets the status back to **`UNDER_REVIEW`**, writes *"Reporter reopened the report — the problem is not fixed."* |

**Both act on the case primary, not the individual report.** `case_primary()` resolves a member to its primary first. So if five people reported one pothole and any one of them reopens it, the case reopens for everyone and returns to the admin queue — a fix that didn't actually work can't be closed by resolving one reporter's row.

Confirmation deliberately does **not** introduce a sixth status. It is an audit-trail event, which keeps the state machine small while still recording citizen sign-off.

---

## 14. Status history (audit trail)

Every meaningful event appends an immutable row to `status_history` (`app/services/lifecycle.py`). Nothing is ever updated or deleted.

| Column | Contents |
|---|---|
| `issue_id` | The issue the event belongs to |
| `old_status` | Status before (null for the creation entry) |
| `new_status` | Status after (equal to `old_status` for note-only or proof-only events) |
| `note` | Human-readable description |
| `photo_url` | Set when the event carried a photo |
| `changed_by_role` | `CITIZEN` or `ADMIN` — rendered as *"Reporter"* / *"City administration"* |
| `created_at` | Timestamp |

**Events recorded:** report submitted (with a distinct note when it was linked to an existing case) · admin status change · admin resolution note · proof photo uploaded · SLA escalation · citizen confirmation · citizen reopen.

**Case-level assembly.** `list_issue_history` returns the union of *this report's* entries and *its primary's* entries, ordered chronologically. A duplicate reporter therefore sees their own submission plus everything that happened to the shared case — without seeing other reporters' private rows.

Migration `005` **backfills** a synthetic `SUBMITTED` entry for every issue that predates the audit trail, so no report has an empty history.

---

## 15. AI photo verification

Optional, powered by Claude vision (`app/services/photo_verification.py`). Two independent checks:

| Photo | Question asked | Stored in |
|---|---|---|
| Report photo | "Does this photo plausibly show a *{category}*?" — given the citizen's description, and explicitly tolerant of casual phone-photo framing and lighting | `photo_verdict`, `photo_verdict_note` |
| Proof photo | "Does this photo plausibly show that issue repaired or resolved?" | `resolution_photo_verdict`, `resolution_photo_verdict_note` |

**Verdicts:** `MATCH`, `MISMATCH`, or `UNVERIFIED`.

**Execution model.** Both run as **FastAPI background tasks** — the HTTP response returns before the model is called, so submission latency is unaffected by API latency. The task re-opens its own database session, calls the model, and writes the verdict.

**Structured output.** The call uses a JSON schema (`{match: boolean, reason: string}`) with `effort: "low"`, so the response is machine-readable without parsing prose. The reason is truncated to 500 characters and surfaced as the badge tooltip.

**Degradation is total and silent.** Every failure path returns `UNVERIFIED` with an explanatory note rather than raising:

| Situation | Note stored |
|---|---|
| No `ANTHROPIC_API_KEY` configured | "AI verification is not configured (no ANTHROPIC_API_KEY)." |
| Model declined the request (`stop_reason: refusal`) | "AI verification declined to assess this photo." |
| Any exception — network, timeout, malformed response | "AI verification was unavailable — checked manually instead." |

A report is **never** blocked, rejected, or delayed by the AI verdict. It is advisory information for the officer reviewing the queue: `MATCH` renders a green *🤖 Photo verified* badge, `MISMATCH` an amber *🤖 Photo mismatch?*, and `UNVERIFIED` renders nothing at all.

---

## 16. Department notifications

`app/services/notification.py`. Two-phase so that a slow or broken mail server can never fail a citizen's submission.

**Phase 1 — record (synchronous).** When a new **primary** case is created, a `notifications` row is written with the target department, issue, and a message naming the category, case ID, location, and description. Duplicate reports do *not* re-notify.

**Phase 2 — deliver (background).** `send_pending_notifications` picks up every row with `sent_at IS NULL` and attempts delivery through the configured notifier:

| `NOTIFIER` | Behaviour |
|---|---|
| `console` (default) | Prints the email to the server log — safe for development and demos |
| `email` | Real SMTP delivery using the `SMTP_*` settings |

On success `sent_at` is stamped. On failure the transaction rolls back and the row stays pending, so the **next** submission's background pass retries it — delivery is at-least-once with automatic retry, and no message is lost.

The admin **inbox** (`GET /api/admin/notifications`) shows the 50 most recent with an unread count, and distinguishes *"Email delivered {time}"* from *"Email pending — will retry"*, so an operator can see mail-server trouble immediately. Escalation alerts ([§9](#9-sla-escalation)) flow through the same pipeline.

---

## 17. The live city map

One component, `shared/components/CityMap.jsx`, used by both portals.

| Aspect | Behaviour |
|---|---|
| Data | `GET /api/citizen/map` or `/api/admin/map` — **primary issues with coordinates only**; members are folded into their case |
| Tiles | OpenStreetMap (citizen, light) / CARTO Dark Matter (admin, dark), chosen by a `theme` prop |
| Markers | `L.divIcon` emoji chips — the category emoji inside a coloured ring |
| Colour modes | **Status** or **Category**, toggled in the toolbar |
| Viewport | Auto `fitBounds` over all pins, padded, capped at zoom 16 |
| Legend | Built from what is actually on screen — statuses/categories with zero pins are omitted, each with a live count |
| Popup | Category, status badge, escalation badge, address, report count, department, tracking ID, date, and the vote button |
| Voting | Citizen map only; the admin map shows the supporter count read-only |

**Accessibility of the colour coding.** Both palettes were validated for contrast and colour-vision deficiency against the dark admin surface. Crucially, **state never rides on hue alone**: resolved pins are dimmed and scaled down, and rejected pins are drawn hollow with a dashed ring — so status is distinguishable in greyscale or with any form of colour blindness.

---

## 18. Admin analytics

`GET /api/admin/analytics` (`get_admin_analytics`). Every figure is aggregated from the database on each request — nothing is cached, precomputed, or seeded.

| Metric | Definition |
|---|---|
| `total_issues` | Count of **primary** issues (= real-world problems) |
| `total_reports` | Count of **all** issue rows (= submissions, including duplicates) |
| `open_issues` | Primaries whose status is not `RESOLVED`/`REJECTED` |
| `closed_issues` | `total_issues − open_issues` |
| `total_citizens` | Users with role `CITIZEN` |
| `avg_resolution_days` | Mean of `updated_at − created_at` over **resolved** primaries, in days, rounded to 1 dp. `null` when none are resolved |
| `by_category` | Count per category — **including zero-count categories**, so the chart axis is stable — sorted by count descending |
| `by_status` | Count per status, in enum order, including zeros |
| `departments` | Per department: `total_cases`, `open_cases`, `resolved_cases`, `avg_resolution_days`. Departments with no cases appear with zeros/`null`; an extra **"Unassigned"** row appears only if unrouted cases exist |
| `hotspots` | See [§19](#19-hotspot-detection) |

The gap between `total_reports` and `total_issues` is the direct measure of how much noise duplicate detection removed.

`avg_resolution_days` uses `updated_at` as the resolution timestamp, so it reflects the last modification of a resolved case.

**Rendering.** The dashboard draws hand-built SVG — a donut for status split (with a 2 px gap between segments and a centred total), horizontal bars for categories (zero-count rows render no bar, avoiding a misleading sliver), a department comparison table with inline caseload bars, and a ranked hotspot list. Charts are lazy-loaded: the analytics endpoint is only called when the tab is opened, and it is re-fetched after any status change.

---

## 19. Hotspot detection

Finds locations that keep generating reports — recurring-problem areas rather than one-off incidents.

**Algorithm** (`_find_hotspots`, `app/services/admin.py`):

1. **Grid.** Round each primary's latitude/longitude to **3 decimal places**, giving cells of ~110 m × 110 m. The rounded pair is the cell key.
2. **Weight by reports, not cases.** Each cell's `report_count` sums the *total reports* of every case in it — so one case with six reporters counts as six, correctly outranking three unrelated single-report cases.
3. **Threshold.** Cells with fewer than **2 reports** are discarded — a lone report is not a hotspot.
4. **Label.** `top_category` is the most common category in the cell; the display address is taken from the **most recently created** issue in the cell that has one (older addresses may be stale), falling back to the rounded coordinates.
5. **Rank & cap.** Sorted by `report_count` then `case_count`, both descending; the top **8** are returned.

Issues without coordinates are skipped entirely.

---

## 20. Public transparency scoring

`GET /api/public/transparency` — **no authentication**, computed live (`app/services/transparency.py`).

### The formula

```
score = 100 × ( 0.50 × resolution_rate
              + 0.30 × on_time_rate
              + 0.20 × speed_factor )
```

| Component | Weight | Definition |
|---|---:|---|
| `resolution_rate` | 50 % | resolved cases ÷ total cases |
| `on_time_rate` | 30 % | resolved cases fixed within their category's SLA ÷ resolved cases |
| `speed_factor` | 20 % | `max(0, 1 − avg_resolution_days / 14)` — full marks at instant, zero at 14+ days |

`on_time_rate` and `speed_factor` are **0 when nothing is resolved**, so a department that never closes anything scores 0 rather than being flattered by an empty average.

### Grades

| Score | Grade |
|---:|---|
| ≥ 85 | **A+** |
| ≥ 70 | **A** |
| ≥ 55 | **B** |
| ≥ 40 | **C** |
| < 40 | **D** |

A department with **zero cases** gets `score: null` and `grade: null` — rendered as *"No data"*, never as an F. Departments are sorted best-first, with scoreless ones last.

### What's published

Per department: `total_cases`, `open_cases`, `resolved_cases`, `escalated_cases`, `resolution_rate`, `on_time_rate`, `avg_resolution_days`, `score`, `grade`. Plus a **city-wide** row computed over all primaries, a `generated_at` timestamp, and the methodology sentence itself — so the page explains its own scoring rather than asking readers to trust a number.

### Worked example

One pothole case, resolved in 2 days (SLA 7):

```
resolution_rate = 1/1 = 1.0
on_time_rate    = 1/1 = 1.0            (2 ≤ 7)
speed_factor    = 1 − 2/14 = 0.857
score = 100 × (0.5 + 0.3 + 0.2×0.857) = 97  →  A+
```

---

## 21. Search, filtering & pagination

**Citizen — "My Reports"** (`GET /api/citizen/issues`):

| Parameter | Behaviour |
|---|---|
| `status` | Filters on **effective status**, so duplicates filter by their case's status |
| `search` | Case-insensitive substring across **description, address, and tracking ID** |
| `page` | ≥ 1, default 1 |
| `page_size` | 1–100, default 20 (UI uses 10) |

Results are ordered newest-first (`created_at DESC, id DESC`). The response carries `total`, `page`, and `page_size` for pagination controls. The search box debounces 300 ms and resets to page 1 on change.

**Admin — work queue** (`GET /api/admin/issues`): optional `department` filter by department code; always sorted by [priority score](#8-priority-scoring) descending. Department chips show live open-case counts.

---

## 22. Internationalisation

A dependency-free i18n layer (`frontend/src/shared/i18n.jsx`).

| Aspect | Behaviour |
|---|---|
| Languages | English (default) and **हिन्दी** |
| Switching | 🌐 toggle in the citizen header; swaps to the other language |
| Persistence | `localStorage` under `smartcity-language`; unreadable storage (private mode) falls back to English without error |
| Document language | Sets `document.documentElement.lang` for screen readers |
| Lookup | `t(key, fallback)` — a missing key returns the inline English fallback, so a partial translation **can never render a blank or a raw key** |

**Covered surfaces:** navigation, dashboard, report wizard (all five steps, categories and their hints), statuses and their descriptions, the status timeline, My Reports (filters, search, pagination), issue details, the activity history, resolution and confirm/reopen prompts, the city map (toolbar, legend, popups), and AI verification notes.

Free-text — descriptions and addresses — is stored and displayed verbatim in whatever script the citizen typed. Adding a third language is one dictionary object; no component changes.

---

## 23. Error handling catalogue

| Failure | Handling |
|---|---|
| GPS permission denied / unavailable / timeout (10 s) | Inline message; map tap remains available. Reporting continues |
| Browser lacks Geolocation | *"Your browser doesn't support location access."* |
| Reverse geocoding fails or is rate-limited | Resolves `null`; the report is filed with coordinates. Readout shows *"No address found — coordinates will be used."* |
| Stale geocode response | Previous request is `AbortController`-cancelled when a new pin is placed |
| Map tiles fail to load | Leaflet renders empty tiles; pins, popups and submission still work |
| Oversized / wrong-type / corrupt photo | Rejected with a specific `400`/`413`; client pre-checks before upload |
| Upload interrupted | `XMLHttpRequest.onerror` → *"…check your connection and try again."*; form state is preserved |
| Backend validation error (422) | Field errors are mapped to their wizard step and the wizard jumps back to the first broken one |
| Network failure on any fetch | `isNetworkError` flag → *"We couldn't reach the server…"* |
| Any load failure | `ErrorState` component with a **Try again** button that re-runs the request |
| Expired / invalid JWT | `401` → redirect to login |
| Wrong role for an endpoint | `403` |
| Another citizen's issue, or nonexistent | `404` (indistinguishable, by design) |
| Confirm/reopen on a non-resolved case | `400` with an explanatory message |
| Voting on your own case | `400` with an explanatory message |
| AI verification unavailable | Silent `UNVERIFIED` — never surfaced as an error |
| SMTP delivery failure | Notification stays pending and is retried on the next background pass |
| Empty result sets | Purpose-written `EmptyState` per screen (no reports / no matches / nothing on the map / no data to analyse) |

---

## 24. Data model

PostgreSQL via SQLAlchemy 2, evolved through **7 Alembic migrations**. All tables carry `created_at` / `updated_at`.

| Table | Purpose | Key columns |
|---|---|---|
| `users` | Accounts | `email` (unique, indexed), `hashed_password`, `role` |
| `issues` | Reports **and** cases | `tracking_id` (unique), `citizen_id`, `category`, `description`, `latitude`, `longitude`, `address`, `photo_url`, `photo_verdict`, `photo_verdict_note`, `status`, `resolution_note`, `resolution_photo_url`, `resolution_photo_verdict`, `resolution_photo_verdict_note`, `case_id`, `is_primary`, `department_id`, `escalated_at` |
| `status_history` | Immutable audit trail | `issue_id`, `old_status`, `new_status`, `note`, `photo_url`, `changed_by_role` |
| `departments` | Owning teams | `code` (unique), `name`, `email` |
| `category_routes` | Category → department map | `category` (unique), `department_id` |
| `issue_votes` | Citizen upvotes | `issue_id`, `citizen_id`, **unique together** |
| `notifications` | Department inbox + mail queue | `department_id`, `issue_id`, `message`, `is_read`, `sent_at` |

**Indexes that matter:** `ix_issues_dup_lookup` on `(category, latitude, longitude)` backs duplicate detection; `case_id`, `status`, `category`, and `department_id` are individually indexed for the queue and analytics queries.

**Cascades:** deleting a user deletes their issues; deleting an issue deletes its history, votes, and notifications.

**Migration history:** `001` users & issues · `002` civic issue fields · `003` case grouping · `004` departments, routing & notifications · `005` status history & resolution evidence (with backfill) · `006` escalation timestamp & votes · `007` AI photo-verification verdicts.

---

## 25. Configuration reference

Backend, via `.env` (see `backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Hack API` | FastAPI title |
| `DEBUG` | `true` | FastAPI debug mode |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `DATABASE_URL` | local Postgres | SQLAlchemy URL |
| `JWT_SECRET_KEY` | *(required)* | Token signing secret — no default, the app refuses to start without it |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token lifetime |
| `UPLOAD_DIR` | `uploads` | Photo storage root |
| `UPLOAD_URL_PREFIX` | `/uploads` | Public URL prefix for stored photos |
| `MAX_UPLOAD_SIZE_BYTES` | `5242880` | 5 MB upload cap |
| `ANTHROPIC_API_KEY` | *(empty)* | Enables AI photo verification; empty disables it cleanly |
| `PHOTO_VERIFICATION_MODEL` | `claude-opus-5` | Vision model used for verification |
| `NOTIFIER` | `console` | `console` logs emails, `email` sends them |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | — | SMTP credentials when `NOTIFIER=email` |

Frontend, via Vite env (all optional — sensible defaults are built in):

| Variable | Default | Purpose |
|---|---|---|
| `VITE_MAP_TILE_URL` | OpenStreetMap | Light-theme tile server |
| `VITE_MAP_TILE_URL_DARK` | CARTO Dark Matter | Dark-theme tile server |
| `VITE_MAP_TILE_ATTRIBUTION` | OSM attribution | Attribution string |
| `VITE_GEOCODING_URL` | OSM Nominatim | Reverse-geocoding endpoint |

Swapping any map provider is therefore a configuration change, not a code change.
