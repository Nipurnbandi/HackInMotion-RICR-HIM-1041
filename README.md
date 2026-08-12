# CivicFix — Smart City Issue Reporting & Resolution Platform

> Because a pothole reported today shouldn't still be a pothole six months from now.

Built for **[Hackathon Name]** — Theme: Smart Cities and Civic Tech

A two-role platform where **citizens** report civic issues (potholes, streetlights, garbage, etc.) with location and photo evidence, and **administrators** manage, route, and resolve them through a structured workflow with real-time tracking and analytics.

---

## 👥 Team

[Om Kumar Singh] · [Nipurn Bandi] · [Sonu Yadav] · [Vishal Kumar]

---

## ✨ Key Features

- **Two-role auth** (Citizen / Admin) with backend-enforced access control
- **Map-based reporting** — pin location, category, description, photo
- **Duplicate detection** — flags/links similar nearby reports
- **Auto department routing** based on issue category
- **Status workflow** — Reported → Acknowledged → In Progress → Resolved → Verified
- **Live city map** with color-coded issue markers
- **Admin analytics dashboard** — resolution times, hotspots, department performance
- **Responsive UI** for mobile-first citizen reporting

---

## 🛠️ Tech Stack

**Frontend:** React + Vite · **Backend:** FastAPI (Python) · **Database:** PostgreSQL (SQLAlchemy + Alembic) · **Auth:** JWT · **Maps:** [Leaflet.js / your choice] · **Charts:** Chart.js · **Deployment:** [your choice]

---

## ⚙️ Setup

**Backend**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```
Runs at `http://localhost:8000` (docs at `/docs`)

**Frontend**
```bash
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`

---

## 🔌 API Overview

Full details in [`api-documentation.md`](./api-documentation.md)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Register user |
| POST | `/api/auth/login` | Login (JWT) |
| POST | `/api/issues` | Report an issue |
| GET | `/api/issues` | List/filter issues |
| PATCH | `/api/issues/{id}/status` | Update status (admin) |
| GET | `/api/admin/analytics` | Dashboard metrics |

---

## 🗄️ Database (Overview)

`users` (id, name, email, role) · `issues` (id, citizen_id, category, lat, lng, photo_url, status, department) · `status_history` (id, issue_id, status, note, timestamp)

---

## 🏗️ Architecture

See [`architecture-diagram.png`](./architecture-diagram.png)

---

## 🚀 Live Demo

**App:** [link] · **Video:** [link]

---

## 🔮 Future Scope

AI photo verification · SLA-based escalation · citizen upvoting · multi-language support · predictive hotspot alerts


| Method | Path         | Description   |
|--------|--------------|---------------|
| GET    | `/`          | Welcome       |
| GET    | `/api/health`| Health check  |
