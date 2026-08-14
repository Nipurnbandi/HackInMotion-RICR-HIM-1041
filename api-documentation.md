# SmartCity API Reference

Base URL: `/api`. Authentication uses a JWT sent as an HTTP-only cookie (set on login) or a `Authorization: Bearer <token>` header. Role enforcement happens on the backend: citizen endpoints require the `CITIZEN` role, admin endpoints require `ADMIN` — the other role receives `403`.

## Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | — | Create a citizen account (`email`, `password`). Role escalation via signup is blocked. |
| POST | `/auth/login` | — | Log in; sets the auth cookie. |
| POST | `/auth/logout` | any | Clear the auth cookie. |
| GET | `/auth/me` | any | Current user (`id`, `email`, `role`). |

## Citizen

| Method | Path | Description |
|---|---|---|
| GET | `/citizen/dashboard` | Greeting, per-status stats, and recent reports. |
| GET | `/citizen/map` | All active cases with coordinates for the live city map (category, status, location, report/citizen counts, department). |
| GET | `/citizen/issues` | Own reports, paginated; filters: `status`, `search`, `page`, `page_size`. |
| GET | `/citizen/issues/stats` | Own per-status counts. |
| POST | `/citizen/issues` | Multipart form: `category`, `description`, `latitude`, `longitude`, `address?`, `photo?` (JPEG/PNG/WEBP ≤ 5 MB, content-sniffed). Runs duplicate detection + department routing; returns the created report with its tracking ID. |
| GET | `/citizen/issues/{id}` | One own report **with the full status history**, resolution note, and proof photo. Members of a case show the case's effective status and shared history. |
| POST | `/citizen/issues/{id}/confirm` | Reporter confirms a **resolved** case is actually fixed (recorded in history). `400` if not resolved. |
| POST | `/citizen/issues/{id}/reopen` | Reporter reopens a **resolved** case → status returns to `UNDER_REVIEW` for the whole case. `400` if not resolved. |

## Admin

| Method | Path | Description |
|---|---|---|
| GET | `/admin/dashboard` | Headline totals (open cases, citizens). |
| GET | `/admin/analytics` | City-wide metrics from the live DB: totals, splits by category/status/department, average resolution days (overall + per department), department performance, hotspot cells. |
| GET | `/admin/map` | All active cases with coordinates for the live map. |
| GET | `/admin/departments` | Departments with open-case counts. |
| GET | `/admin/issues` | Case queue (one row per real-world problem), sorted by priority score; filter: `department=<code>`. |
| PUT | `/admin/issues/{id}` | Update `status`, `title`, `description`, and/or `resolution_note`. Status changes and notes are recorded in the status history. |
| POST | `/admin/issues/{id}/resolution-photo` | Multipart upload of a proof-of-resolution photo (same validation as citizen photos); stored and linked in the history. |
| DELETE | `/admin/issues/{id}` | Remove a report. |
| GET | `/admin/notifications` | Department notification inbox with unread count and email delivery state. |
| POST | `/admin/notifications/{id}/read` | Mark a notification as read. |

## Statuses & categories

- Statuses: `SUBMITTED → UNDER_REVIEW → IN_PROGRESS → RESOLVED` (+ `REJECTED`). Citizens can reopen a resolved case (`→ UNDER_REVIEW`) or confirm the fix.
- Categories: `STREETLIGHT`, `POTHOLE`, `GARBAGE_OVERFLOW`, `WATER_LEAKAGE`, `DAMAGED_PUBLIC_PROPERTY`, `ILLEGAL_DUMPING`, `BROKEN_DRAINAGE` — each mapped to a department via the `category_routes` table.

## Status history entry shape

```json
{
  "id": 3,
  "old_status": "IN_PROGRESS",
  "new_status": "RESOLVED",
  "note": "Filled and re-surfaced.",
  "photo_url": "/uploads/resolutions/….png",
  "changed_by_role": "ADMIN",
  "created_at": "2026-08-14T10:20:00Z"
}
```
