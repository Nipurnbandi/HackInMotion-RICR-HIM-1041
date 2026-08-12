# Hack

Full-stack starter with **FastAPI** backend and **React + Vite** frontend.

## Project structure

```
hack/
├── backend/
│   ├── alembic/          # DB migrations
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config & database
│   │   ├── schemas/      # Pydantic models
│   │   ├── services/     # Business logic
│   │   ├── main.py
│   │   └── models.py     # SQLAlchemy models
│   ├── alembic.ini
│   └── requirements.txt
└── frontend/
    └── src/
```

## Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env

uvicorn app.main:app --reload
```

API runs at http://localhost:8000  
Docs at http://localhost:8000/docs

## Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at http://localhost:5173 (proxies `/api` to the backend).

## Endpoints

| Method | Path         | Description   |
|--------|--------------|---------------|
| GET    | `/`          | Welcome       |
| GET    | `/api/health`| Health check  |
