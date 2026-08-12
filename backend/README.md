# FastAPI Backend

## Structure

```
backend/
├── alembic/           # Database migrations
├── app/
│   ├── api/           # Route handlers
│   ├── core/          # Config, database, security
│   ├── schemas/       # Pydantic request/response models
│   ├── services/      # Business logic
│   ├── main.py        # App entry point
│   └── models.py      # SQLAlchemy models
├── alembic.ini
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```
