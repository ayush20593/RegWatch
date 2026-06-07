# RegWatch MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build RegWatch MVP — a multi-tenant compliance monitoring SaaS for Indian NBFCs with AI-powered per-org analysis, a live dashboard, and daily email digests.

**Architecture:** FastAPI backend (Python, migrating existing scraper logic) + React 18/Vite frontend + PostgreSQL replacing flat JSON + APScheduler for background jobs + Ollama/Llama 3.1 8B for AI. All LLM calls go through an abstract `LLMProvider` so the provider is swappable via config.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, PostgreSQL 15, APScheduler 3.x, pypdf, requests, BeautifulSoup4, passlib[bcrypt], itsdangerous, Ollama, React 18, Vite 5, TypeScript, TanStack Query, React Router 6, Axios, Brevo SDK

---

## File Map

```
backend/
  app/
    __init__.py
    main.py                        # FastAPI app, CORS, mounts frontend
    config.py                      # Pydantic-settings (env vars)
    database.py                    # Engine, SessionLocal, Base, get_db
    models/
      __init__.py
      org.py                       # Organisation, OrgDocument
      update.py                    # RegulatoryUpdate, AIAnalysis, FetchRun
      user.py                      # User
    routers/
      __init__.py
      auth.py                      # POST /auth/login, /logout, GET /auth/me
      updates.py                   # GET /updates, GET /updates/{id}, PATCH reviewed
      admin.py                     # Org CRUD, fetch run log, manual trigger, doc upload
      digest.py                    # GET/PATCH /digest/settings
    services/
      __init__.py
      scraper.py                   # HTTP fetch with retry, stable_id, orchestrator
      parsers/
        __init__.py
        base.py                    # ParsedCandidate dataclass, BaseParser ABC
        rbi.py                     # RBINotificationsParser, RBICircularsParser
        sebi.py                    # SEBIParser
        irdai.py                   # IRDAIParser
        mca.py                     # MCAParser
      pdf.py                       # Full PDF extraction + chunking
      llm/
        __init__.py
        base.py                    # LLMProvider ABC
        ollama.py                  # OllamaProvider
        prompts.py                 # build_analysis_prompt(doc_text, org_profile)
      analyzer.py                  # analyse_update(), chunk_and_summarise()
      scheduler.py                 # APScheduler setup, fetch + digest jobs
      digest.py                    # build_digest_html(), send_digest()
    auth/
      __init__.py
      utils.py                     # hash_password, verify_password, session helpers
  tests/
    __init__.py
    conftest.py                    # DB fixtures, test client
    test_parsers.py
    test_pdf.py
    test_analyzer.py
    test_api_auth.py
    test_api_updates.py
    test_digest.py
frontend/
  index.html
  vite.config.ts
  package.json
  tsconfig.json
  src/
    main.tsx
    App.tsx
    theme.ts                       # Design tokens (Slate + Indigo palette)
    api/
      client.ts                    # Axios instance with interceptors
      types.ts                     # TypeScript types matching DB models
    components/
      Layout.tsx                   # Sidebar + main content shell
      Sidebar.tsx
      MetricStrip.tsx
      UpdateCard.tsx
      DetailModal.tsx
      RiskBadge.tsx
      FilterPanel.tsx
    pages/
      LoginPage.tsx
      DashboardPage.tsx
      AdminPage.tsx
    hooks/
      useAuth.ts
      useUpdates.ts                # Polling hook
migrations/
  001_initial.sql
docker-compose.yml
requirements.txt
.env.example
```

---

## Phase 1 — Foundation

### Task 1: Project Bootstrap

**Files:**
- Create: `requirements.txt`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/app/__init__.py`

- [ ] **Step 1: Write `requirements.txt`**

```text
fastapi>=0.111
uvicorn[standard]>=0.29
sqlalchemy>=2.0
psycopg2-binary>=2.9
pydantic-settings>=2.2
passlib[bcrypt]>=1.7
itsdangerous>=2.1
apscheduler>=3.10
requests>=2.32
beautifulsoup4>=4.12
pypdf>=4.3
sib-api-v3-sdk>=7.6
httpx>=0.27
pytest>=8.2
pytest-asyncio>=0.23
```

- [ ] **Step 2: Write `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: regwatch
      POSTGRES_PASSWORD: regwatch
      POSTGRES_DB: regwatch
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  pgdata:
  ollama_data:
```

- [ ] **Step 3: Write `.env.example`**

```bash
DATABASE_URL=postgresql://regwatch:regwatch@localhost:5432/regwatch
SECRET_KEY=change-me-in-production-use-32-random-chars
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
BREVO_API_KEY=
SENDER_EMAIL=
FETCH_SCHEDULE_HOURS=6
DIGEST_TIME_IST=08:00
```

- [ ] **Step 4: Start the DB and pull the LLM model**

```bash
docker compose up -d db ollama
docker compose exec ollama ollama pull llama3.1:8b
```

Expected: `postgres` container healthy, model download completes.

- [ ] **Step 5: Create empty `backend/app/__init__.py`**

```python
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt docker-compose.yml .env.example backend/
git commit -m "feat: project bootstrap — deps, docker-compose, env template"
```

---

### Task 2: Config + Database Foundation

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_config.py
from app.config import settings

def test_settings_load():
    assert settings.database_url.startswith("postgresql")
    assert settings.ollama_model == "llama3.1:8b"
```

- [ ] **Step 2: Run test — expect FAIL (module not found)**

```bash
cd backend && python -m pytest tests/test_config.py -v
```

- [ ] **Step 3: Write `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://regwatch:regwatch@localhost:5432/regwatch"
    secret_key: str = "change-me-in-production"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    brevo_api_key: str = ""
    sender_email: str = ""
    fetch_schedule_hours: int = 6
    digest_time_ist: str = "08:00"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 4: Write `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Run test — expect PASS**

```bash
python -m pytest tests/test_config.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/database.py backend/tests/test_config.py
git commit -m "feat: config + database foundation"
```

---

### Task 3: SQLAlchemy Models + Migration

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/org.py`
- Create: `backend/app/models/update.py`
- Create: `backend/app/models/user.py`
- Create: `migrations/001_initial.sql`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_models.py
from app.models.org import Organisation, OrgDocument
from app.models.update import RegulatoryUpdate, AIAnalysis, FetchRun
from app.models.user import User
from app.database import Base

def test_all_models_importable():
    tables = {t.name for t in Base.metadata.tables.values()}
    assert "organisations" in tables
    assert "regulatory_updates" in tables
    assert "ai_analyses" in tables
    assert "users" in tables
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_models.py -v
```

- [ ] **Step 3: Write `backend/app/models/org.py`**

```python
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base

class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    nbfc_type: Mapped[str] = mapped_column(String(50))
    product_lines: Mapped[str] = mapped_column(Text, default="")
    aum_band: Mapped[str] = mapped_column(String(50), default="")
    geographies: Mapped[str] = mapped_column(Text, default="")
    compliance_risk_areas: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    documents: Mapped[list["OrgDocument"]] = relationship(back_populates="org")
    users: Mapped[list["User"]] = relationship(back_populates="org")

class OrgDocument(Base):
    __tablename__ = "org_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    filename: Mapped[str] = mapped_column(String(255))
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    org: Mapped["Organisation"] = relationship(back_populates="documents")
```

- [ ] **Step 4: Write `backend/app/models/update.py`**

```python
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base

class RegulatoryUpdate(Base):
    __tablename__ = "regulatory_updates"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    regulator: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(50))
    document_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(Text)
    date: Mapped[str] = mapped_column(String(20), default="")
    page_url: Mapped[str] = mapped_column(Text, default="")
    pdf_url: Mapped[str] = mapped_column(Text, default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="unreviewed")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    analysis: Mapped["AIAnalysis"] = relationship(back_populates="update", uselist=False)

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    update_id: Mapped[str] = mapped_column(ForeignKey("regulatory_updates.id"))
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    summary: Mapped[str] = mapped_column(Text, default="")
    applicability: Mapped[str] = mapped_column(Text, default="")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    implementation_json: Mapped[list] = mapped_column(JSON, default=list)
    risk_level: Mapped[str] = mapped_column(String(10), default="Low")
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    update: Mapped["RegulatoryUpdate"] = relationship(back_populates="analysis")

class FetchRun(Base):
    __tablename__ = "fetch_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    source: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updates_found: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
```

- [ ] **Step 5: Write `backend/app/models/user.py`**

```python
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    org: Mapped["Organisation"] = relationship(back_populates="users")
```

- [ ] **Step 6: Write `backend/app/models/__init__.py`**

```python
from .org import Organisation, OrgDocument
from .update import RegulatoryUpdate, AIAnalysis, FetchRun
from .user import User

__all__ = ["Organisation", "OrgDocument", "RegulatoryUpdate", "AIAnalysis", "FetchRun", "User"]
```

- [ ] **Step 7: Write `migrations/001_initial.sql`**

```sql
CREATE TABLE organisations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    nbfc_type VARCHAR(50) NOT NULL,
    product_lines TEXT DEFAULT '',
    aum_band VARCHAR(50) DEFAULT '',
    geographies TEXT DEFAULT '',
    compliance_risk_areas TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE org_documents (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    extracted_text TEXT DEFAULT '',
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE regulatory_updates (
    id VARCHAR(16) PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    regulator VARCHAR(20) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    date VARCHAR(20) DEFAULT '',
    page_url TEXT DEFAULT '',
    pdf_url TEXT DEFAULT '',
    raw_text TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'unreviewed',
    detected_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ai_analyses (
    id SERIAL PRIMARY KEY,
    update_id VARCHAR(16) REFERENCES regulatory_updates(id) ON DELETE CASCADE,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    summary TEXT DEFAULT '',
    applicability TEXT DEFAULT '',
    conclusion TEXT DEFAULT '',
    implementation_json JSONB DEFAULT '[]',
    risk_level VARCHAR(10) DEFAULT 'Low',
    generated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE fetch_runs (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    updates_found INTEGER DEFAULT 0,
    error_message TEXT DEFAULT ''
);

CREATE INDEX idx_updates_org_id ON regulatory_updates(org_id);
CREATE INDEX idx_updates_detected_at ON regulatory_updates(detected_at DESC);
CREATE INDEX idx_analyses_update_id ON ai_analyses(update_id);
```

- [ ] **Step 8: Apply migration**

```bash
docker compose exec -T db psql -U regwatch -d regwatch < migrations/001_initial.sql
```

Expected: All CREATE TABLE/INDEX statements succeed with no errors.

- [ ] **Step 9: Run tests — expect PASS**

```bash
python -m pytest tests/test_models.py -v
```

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/ migrations/001_initial.sql backend/tests/test_models.py
git commit -m "feat: SQLAlchemy models + initial DB migration"
```

---

### Task 4: Auth Utilities

**Files:**
- Create: `backend/app/auth/__init__.py`
- Create: `backend/app/auth/utils.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_auth.py
from app.auth.utils import hash_password, verify_password, make_session_token, decode_session_token

def test_password_round_trip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)

def test_session_token_round_trip():
    token = make_session_token(user_id=42, org_id=7)
    payload = decode_session_token(token)
    assert payload["user_id"] == 42
    assert payload["org_id"] == 7

def test_invalid_token_returns_none():
    assert decode_session_token("garbage") is None
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_auth.py -v
```

- [ ] **Step 3: Write `backend/app/auth/utils.py`**

```python
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature
from ..config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_signer = URLSafeTimedSerializer(settings.secret_key)

def hash_password(plain: str) -> str:
    return _pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)

def make_session_token(user_id: int, org_id: int) -> str:
    return _signer.dumps({"user_id": user_id, "org_id": org_id})

def decode_session_token(token: str, max_age: int = 86400 * 30) -> dict | None:
    try:
        return _signer.loads(token, max_age=max_age)
    except BadSignature:
        return None
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_auth.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/ backend/tests/test_auth.py
git commit -m "feat: auth utilities — bcrypt hashing + signed session tokens"
```

---

### Task 5: FastAPI App + Auth Routes

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write `backend/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import Organisation, User
from app.auth.utils import hash_password

TEST_DB = "sqlite:///./test.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)

def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def db():
    db = TestingSession()
    yield db
    db.close()

@pytest.fixture
def org_and_user(db):
    org = Organisation(name="Test NBFC", nbfc_type="ICC")
    db.add(org)
    db.flush()
    user = User(org_id=org.id, email="test@nbfc.com", password_hash=hash_password("pass123"))
    db.add(user)
    db.commit()
    db.refresh(org)
    db.refresh(user)
    return org, user
```

- [ ] **Step 2: Write failing auth tests**

```python
# backend/tests/test_api_auth.py
def test_login_success(client, org_and_user):
    resp = client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "token" in resp.json()

def test_login_wrong_password(client, org_and_user):
    resp = client.post("/auth/login", json={"email": "test@nbfc.com", "password": "wrong"})
    assert resp.status_code == 401

def test_me_authenticated(client, org_and_user):
    login = client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    token = login.json()["token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@nbfc.com"

def test_me_unauthenticated(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
```

- [ ] **Step 3: Run — expect FAIL**

```bash
python -m pytest tests/test_api_auth.py -v
```

- [ ] **Step 4: Write `backend/app/routers/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import User
from ..auth.utils import verify_password, make_session_token, decode_session_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_session_token(authorization[7:])
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, payload["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = make_session_token(user_id=user.id, org_id=user.org_id)
    return {"token": token, "org_id": user.org_id}

@router.post("/logout")
def logout():
    return {"ok": True}

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "org_id": user.org_id}
```

- [ ] **Step 5: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, updates, admin, digest

app = FastAPI(title="RegWatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(updates.router)
app.include_router(admin.router)
app.include_router(digest.router)
```

- [ ] **Step 6: Create stub routers so imports don't fail**

```python
# backend/app/routers/__init__.py  (empty)

# backend/app/routers/updates.py
from fastapi import APIRouter
router = APIRouter(prefix="/updates", tags=["updates"])

# backend/app/routers/admin.py
from fastapi import APIRouter
router = APIRouter(prefix="/admin", tags=["admin"])

# backend/app/routers/digest.py
from fastapi import APIRouter
router = APIRouter(prefix="/digest", tags=["digest"])
```

- [ ] **Step 7: Run — expect PASS**

```bash
python -m pytest tests/test_api_auth.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/main.py backend/app/routers/ backend/tests/
git commit -m "feat: FastAPI app skeleton + auth routes (login, logout, /me)"
```

---

## Phase 2 — Data Pipeline

### Task 6: PDF Extractor (Full Document + Chunking)

**Files:**
- Create: `backend/app/services/pdf.py`
- Test: `backend/tests/test_pdf.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_pdf.py
from app.services.pdf import extract_pdf_text, chunk_text

def test_chunk_text_short():
    text = "Hello world."
    chunks = chunk_text(text, max_chars=10000)
    assert chunks == ["Hello world."]

def test_chunk_text_splits_on_boundary():
    # 3 sentences, max_chars forces a split
    text = "Sentence one. Sentence two. Sentence three."
    chunks = chunk_text(text, max_chars=25)
    assert len(chunks) == 2
    assert "Sentence one." in chunks[0]

def test_extract_pdf_text_invalid_bytes_returns_empty():
    result = extract_pdf_text(b"not a pdf", max_bytes=10 * 1024 * 1024)
    assert result == ""
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_pdf.py -v
```

- [ ] **Step 3: Write `backend/app/services/pdf.py`**

```python
import re
from io import BytesIO

MAX_BYTES = 10 * 1024 * 1024  # 10 MB

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

def extract_pdf_text(content: bytes, max_bytes: int = MAX_BYTES) -> str:
    if PdfReader is None or not content:
        return ""
    if len(content) > max_bytes:
        return ""
    if not content.lstrip().startswith(b"%PDF"):
        return ""
    try:
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return _clean("\n".join(pages))
    except Exception:
        return ""

def chunk_text(text: str, max_chars: int = 6000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence + " "
        else:
            current += sentence + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text[:max_chars]]

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_pdf.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pdf.py backend/tests/test_pdf.py
git commit -m "feat: full PDF text extraction with chunking for long documents"
```

---

### Task 7: Parser Base + RBI Parsers

**Files:**
- Create: `backend/app/services/parsers/__init__.py`
- Create: `backend/app/services/parsers/base.py`
- Create: `backend/app/services/parsers/rbi.py`
- Test: `backend/tests/test_parsers.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_parsers.py
from app.services.parsers.base import ParsedCandidate
from app.services.parsers.rbi import RBINotificationsParser, RBICircularsParser
from bs4 import BeautifulSoup

RBI_NOTIF_HTML = """<table>
  <tr><td colspan="3">22.05.2026</td></tr>
  <tr>
    <td><a href="/Scripts/NotificationUser.aspx?Id=1">KYC Master Direction Update</a></td>
    <td><a href="/pdfs/kyc.pdf">PDF</a></td>
  </tr>
</table>"""

def test_rbi_notifications_parser_extracts_title():
    soup = BeautifulSoup(RBI_NOTIF_HTML, "html.parser")
    parser = RBINotificationsParser("https://www.rbi.org.in/Scripts/NotificationUser.aspx")
    candidates = list(parser.parse(soup))
    assert len(candidates) >= 1
    assert "KYC" in candidates[0].title

def test_parsed_candidate_fields():
    c = ParsedCandidate(title="Test", page_url="https://rbi.org.in/test", pdf_url="", date="2026-05-22", raw_text="Test text")
    assert c.title == "Test"
    assert c.date == "2026-05-22"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_parsers.py -v
```

- [ ] **Step 3: Write `backend/app/services/parsers/base.py`**

```python
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path

@dataclass
class ParsedCandidate:
    title: str
    page_url: str
    pdf_url: str
    date: str
    raw_text: str

class BaseParser(ABC):
    def __init__(self, source_url: str):
        self.source_url = source_url

    @abstractmethod
    def parse(self, soup: BeautifulSoup) -> list[ParsedCandidate]:
        ...

    def _clean(self, text: str | None) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def _is_pdf(self, url: str) -> bool:
        return ".pdf" in unquote(urlparse(url).path).lower()

    def _abs(self, href: str) -> str:
        return urljoin(self.source_url, href)

    def _parse_date(self, text: str) -> str:
        from datetime import datetime
        patterns = [
            (r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", "%d-%m-%Y"),
            (r"\b(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{4})\b", "%d %b %Y"),
        ]
        for pattern, _ in patterns:
            m = re.search(pattern, text)
            if m:
                raw = m.group(0).replace("/", "-").replace(".", "-").replace(",", "")
                for fmt in ("%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
                    try:
                        return datetime.strptime(raw, fmt).date().isoformat()
                    except ValueError:
                        continue
        return ""

    def _should_skip(self, title: str) -> bool:
        bad = {"home", "about us", "login", "read more", "view", "download", "click here"}
        return len(title) < 12 or title.lower().strip() in bad
```

- [ ] **Step 4: Write `backend/app/services/parsers/rbi.py`**

```python
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

class RBINotificationsParser(BaseParser):
    def parse(self, soup: BeautifulSoup) -> list[ParsedCandidate]:
        results, current_date = [], ""
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            row_text = self._clean(row.get_text(" "))
            row_date = self._parse_date(row_text)
            anchors = row.find_all("a", href=True)
            if row_date and not anchors:
                current_date = row_date
                continue
            if not cells or not anchors:
                continue
            text_anchor = next(
                (a for a in anchors if self._clean(a.get_text()) and not self._is_pdf(self._abs(a["href"]))),
                None,
            )
            if not text_anchor:
                continue
            title = self._clean(text_anchor.get_text())
            if self._should_skip(title):
                continue
            page_url = self._abs(text_anchor["href"])
            pdf_url = next(
                (self._abs(a["href"]) for a in anchors if self._is_pdf(self._abs(a["href"]))),
                "",
            )
            results.append(ParsedCandidate(
                title=title, page_url=page_url, pdf_url=pdf_url,
                date=row_date or current_date, raw_text=row_text,
            ))
        return results

class RBICircularsParser(BaseParser):
    def parse(self, soup: BeautifulSoup) -> list[ParsedCandidate]:
        results = []
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            title = self._clean(cells[3].get_text())
            if self._should_skip(title):
                continue
            anchor = cells[0].find("a", href=True)
            if not anchor:
                continue
            row_text = self._clean(row.get_text(" "))
            results.append(ParsedCandidate(
                title=title,
                page_url=self._abs(anchor["href"]),
                pdf_url=next((self._abs(a["href"]) for a in row.find_all("a", href=True) if self._is_pdf(self._abs(a["href"]))), ""),
                date=self._parse_date(self._clean(cells[1].get_text())),
                raw_text=row_text,
            ))
        return results
```

- [ ] **Step 5: Run — expect PASS**

```bash
python -m pytest tests/test_parsers.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/parsers/ backend/tests/test_parsers.py
git commit -m "feat: parser base class + RBI notifications/circulars parsers"
```

---

### Task 8: SEBI, IRDAI, MCA Parsers

**Files:**
- Create: `backend/app/services/parsers/sebi.py`
- Create: `backend/app/services/parsers/irdai.py`
- Create: `backend/app/services/parsers/mca.py`

- [ ] **Step 1: Add tests to `backend/tests/test_parsers.py`**

```python
from app.services.parsers.sebi import SEBIParser
from app.services.parsers.irdai import IRDAIParser

SEBI_HTML = """<table>
  <tr>
    <td>19 May 2026</td>
    <td><a href="/legal/circulars/may-2026/mcr-format_101522.html">Revision of MCR Format</a></td>
    <td><a href="/sebi_data/attachdocs/may-2026/mcr.pdf">Download</a></td>
  </tr>
</table>"""

def test_sebi_parser_extracts_title():
    soup = BeautifulSoup(SEBI_HTML, "html.parser")
    parser = SEBIParser("https://www.sebi.gov.in")
    candidates = list(parser.parse(soup))
    assert any("MCR" in c.title for c in candidates)

IRDAI_HTML = """<div class="views-row">
  <span class="date">12 May 2026</span>
  <a href="/circulars/motor-insurance-2026">Motor Insurance Circular Update</a>
</div>"""

def test_irdai_parser_extracts_title():
    soup = BeautifulSoup(IRDAI_HTML, "html.parser")
    parser = IRDAIParser("https://irdai.gov.in/circulars")
    candidates = list(parser.parse(soup))
    assert any("Motor" in c.title for c in candidates)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_parsers.py::test_sebi_parser_extracts_title -v
```

- [ ] **Step 3: Write `backend/app/services/parsers/sebi.py`**

```python
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

class SEBIParser(BaseParser):
    def parse(self, soup: BeautifulSoup) -> list[ParsedCandidate]:
        results, seen = [], set()
        for row in soup.find_all("tr"):
            if row.find("th"):
                continue
            row_text = self._clean(row.get_text(" "))
            anchors = row.find_all("a", href=True)
            if not anchors:
                continue
            date = self._parse_date(row_text)
            best = max(anchors, key=lambda a: self._score(a))
            title = self._clean(best.get_text())
            if self._should_skip(title):
                continue
            page_url = self._abs(best["href"])
            if page_url in seen:
                continue
            seen.add(page_url)
            pdf_url = next((self._abs(a["href"]) for a in anchors if self._is_pdf(self._abs(a["href"]))), "")
            results.append(ParsedCandidate(title=title, page_url=page_url, pdf_url=pdf_url, date=date, raw_text=row_text))
        return results

    def _score(self, anchor) -> int:
        text = self._clean(anchor.get_text())
        href = self._abs(anchor.get("href", ""))
        score = min(len(text), 120)
        if text.lower() in {"read more", "download", "view", "click here"}:
            score -= 500
        if self._is_pdf(href):
            score += 300
        return score
```

- [ ] **Step 4: Write `backend/app/services/parsers/irdai.py`**

```python
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

class IRDAIParser(BaseParser):
    def parse(self, soup: BeautifulSoup) -> list[ParsedCandidate]:
        results, seen = [], set()
        containers = soup.select("li, .views-row, article, .card, tr")
        for container in containers:
            anchors = container.find_all("a", href=True)
            if not anchors:
                continue
            container_text = self._clean(container.get_text(" "))
            date = self._parse_date(container_text)
            best = max(anchors, key=lambda a: len(self._clean(a.get_text())))
            title = self._clean(best.get_text())
            if self._should_skip(title):
                continue
            page_url = self._abs(best["href"])
            if page_url in seen:
                continue
            seen.add(page_url)
            pdf_url = next((self._abs(a["href"]) for a in anchors if self._is_pdf(self._abs(a["href"]))), "")
            results.append(ParsedCandidate(title=title, page_url=page_url, pdf_url=pdf_url, date=date, raw_text=container_text))
        return results
```

- [ ] **Step 5: Write `backend/app/services/parsers/mca.py`**

```python
from bs4 import BeautifulSoup
from .base import BaseParser, ParsedCandidate

class MCAParser(BaseParser):
    def parse(self, soup: BeautifulSoup) -> list[ParsedCandidate]:
        results, seen = [], set()
        for anchor in soup.find_all("a", href=True):
            href = self._abs(anchor["href"])
            title = self._clean(anchor.get_text())
            if self._should_skip(title):
                continue
            if "circular" not in href.lower() and "notice" not in href.lower() and "circular" not in title.lower() and "notice" not in title.lower():
                continue
            if href in seen:
                continue
            seen.add(href)
            container_text = self._clean(anchor.parent.get_text(" ") if anchor.parent else title)
            results.append(ParsedCandidate(
                title=title, page_url=href,
                pdf_url=href if self._is_pdf(href) else "",
                date=self._parse_date(container_text),
                raw_text=container_text,
            ))
        return results
```

- [ ] **Step 6: Run all parser tests — expect PASS**

```bash
python -m pytest tests/test_parsers.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/parsers/sebi.py backend/app/services/parsers/irdai.py backend/app/services/parsers/mca.py backend/tests/test_parsers.py
git commit -m "feat: SEBI, IRDAI, MCA parsers"
```

---

### Task 9: Scraper Orchestrator

**Files:**
- Create: `backend/app/services/scraper.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_scraper.py
import hashlib
from app.services.scraper import stable_id, infer_document_type

def test_stable_id_is_deterministic():
    a = stable_id("RBI", "KYC Update", "https://rbi.org.in/1", "2026-05-22")
    b = stable_id("RBI", "KYC Update", "https://rbi.org.in/1", "2026-05-22")
    assert a == b
    assert len(a) == 16

def test_stable_id_differs_on_title_change():
    a = stable_id("RBI", "KYC Update", "https://rbi.org.in/1", "2026-05-22")
    b = stable_id("RBI", "KYC Update v2", "https://rbi.org.in/1", "2026-05-22")
    assert a != b

def test_infer_document_type_circular():
    assert infer_document_type("Master Circular on KYC", "Circulars") == "Circular"

def test_infer_document_type_notification():
    assert infer_document_type("Press Notification on Rates", "Notifications") == "Notification"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_scraper.py -v
```

- [ ] **Step 3: Write `backend/app/services/scraper.py`**

```python
import hashlib
import re
import time
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..models import RegulatoryUpdate, FetchRun
from .parsers.base import ParsedCandidate
from .parsers.rbi import RBINotificationsParser, RBICircularsParser
from .parsers.sebi import SEBIParser
from .parsers.irdai import IRDAIParser
from .parsers.mca import MCAParser
from .pdf import extract_pdf_text

USER_AGENT = "Mozilla/5.0 (compatible; RegWatch/1.0)"

SOURCES = [
    {"regulator": "RBI", "source_type": "Notifications", "url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx"},
    {"regulator": "RBI", "source_type": "Circulars", "url": "https://www.rbi.org.in/scripts/bs_circularindexdisplay.aspx"},
    {"regulator": "SEBI", "source_type": "Circulars", "url": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0"},
    {"regulator": "IRDAI", "source_type": "Circulars", "url": "https://irdai.gov.in/circulars"},
    {"regulator": "IRDAI", "source_type": "Notifications", "url": "https://irdai.gov.in/notifications"},
    {"regulator": "MCA", "source_type": "Notices and Circulars", "url": "https://www.mca.gov.in/content/mca/global/en/home.html"},
]

DOCUMENT_TYPES = {
    "Circular": ["circular", "master circular"],
    "Notification": ["notification"],
    "Guideline": ["guideline"],
    "Master Direction": ["master direction"],
    "Notice": ["notice"],
    "FAQ": ["faq", "frequently asked"],
    "Draft Guideline": ["draft guideline", "draft circular"],
    "Order": ["order"],
}

def stable_id(regulator: str, title: str, url: str, date: str) -> str:
    raw = f"{regulator}|{title}|{url}|{date}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def infer_document_type(title: str, source_type: str) -> str:
    haystack = f"{title} {source_type}".lower()
    for doc_type, keywords in DOCUMENT_TYPES.items():
        if any(k in haystack for k in keywords):
            return doc_type
    return source_type or "Other"

def _is_safe_url(url: str) -> bool:
    return url.startswith("https://") or url.startswith("http://")

def _fetch_html(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return ""

def _fetch_bytes(url: str) -> bytes:
    for attempt in range(3):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, stream=True)
            resp.raise_for_status()
            chunks = []
            total = 0
            for chunk in resp.iter_content(65536):
                chunks.append(chunk)
                total += len(chunk)
                if total > 10 * 1024 * 1024:
                    return b""
            return b"".join(chunks)
        except requests.RequestException:
            if attempt < 2:
                time.sleep(2 ** attempt)
    return b""

def _get_parser(regulator: str, source_type: str, url: str):
    if regulator == "RBI" and source_type == "Notifications":
        return RBINotificationsParser(url)
    if regulator == "RBI" and source_type == "Circulars":
        return RBICircularsParser(url)
    if regulator == "SEBI":
        return SEBIParser(url)
    if regulator == "IRDAI":
        return IRDAIParser(url)
    return MCAParser(url)

def _detail_text(candidate: ParsedCandidate) -> str:
    if candidate.pdf_url and _is_safe_url(candidate.pdf_url):
        content = _fetch_bytes(candidate.pdf_url)
        text = extract_pdf_text(content)
        if text:
            return text
    if candidate.page_url and _is_safe_url(candidate.page_url):
        html = _fetch_html(candidate.page_url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            main = soup.find("main") or soup.find("article") or soup.body
            if main:
                text = re.sub(r"\s+", " ", main.get_text(" ")).strip()
                if len(text) > 200:
                    return text
    return candidate.raw_text

def fetch_and_store(org_id: int, db: Session, limit_per_source: int = 10) -> list[str]:
    new_ids = []
    existing_ids = {r[0] for r in db.query(RegulatoryUpdate.id).filter_by(org_id=org_id).all()}

    for source in SOURCES:
        run = FetchRun(org_id=org_id, source=f"{source['regulator']} {source['source_type']}")
        db.add(run)
        db.flush()
        try:
            html = _fetch_html(source["url"])
            if not html:
                run.error_message = "Empty response"
                continue
            soup = BeautifulSoup(html, "html.parser")
            parser = _get_parser(source["regulator"], source["source_type"], source["url"])
            candidates = parser.parse(soup)[:limit_per_source]
            count = 0
            for c in candidates:
                uid = stable_id(source["regulator"], c.title, c.pdf_url or c.page_url, c.date)
                if uid in existing_ids:
                    continue
                detail_text = _detail_text(c)
                doc_type = infer_document_type(c.title, source["source_type"])
                update = RegulatoryUpdate(
                    id=uid, org_id=org_id, regulator=source["regulator"],
                    source_type=source["source_type"], document_type=doc_type,
                    title=c.title, date=c.date, page_url=c.page_url,
                    pdf_url=c.pdf_url, raw_text=detail_text,
                    detected_at=datetime.now(timezone.utc),
                )
                db.add(update)
                existing_ids.add(uid)
                new_ids.append(uid)
                count += 1
            run.updates_found = count
        except Exception as e:
            run.error_message = str(e)
        finally:
            run.completed_at = datetime.now(timezone.utc)
    db.commit()
    return new_ids
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_scraper.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scraper.py backend/tests/test_scraper.py
git commit -m "feat: scraper orchestrator with retry, dedup, per-org storage"
```

---


## Phase 3 — AI Analysis Engine

### Task 10: LLMProvider + Ollama Implementation

**Files:**
- Create: `backend/app/services/llm/__init__.py`
- Create: `backend/app/services/llm/base.py`
- Create: `backend/app/services/llm/ollama.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_analyzer.py
from unittest.mock import MagicMock, patch
from app.services.llm.base import LLMProvider
from app.services.llm.ollama import OllamaProvider

def test_llm_provider_is_abstract():
    import inspect
    assert inspect.isabstract(LLMProvider)

def test_ollama_provider_calls_api(monkeypatch):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Test output"}
    mock_response.raise_for_status = MagicMock()
    with patch("requests.post", return_value=mock_response) as mock_post:
        provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.1:8b")
        result = provider.generate("Say hello")
    assert result == "Test output"
    mock_post.assert_called_once()
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_analyzer.py::test_llm_provider_is_abstract tests/test_analyzer.py::test_ollama_provider_calls_api -v
```

- [ ] **Step 3: Write `backend/app/services/llm/base.py`**

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        ...
```

- [ ] **Step 4: Write `backend/app/services/llm/ollama.py`**

```python
import requests
from .base import LLMProvider

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str) -> str:
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
```

- [ ] **Step 5: Run — expect PASS**

```bash
python -m pytest tests/test_analyzer.py::test_llm_provider_is_abstract tests/test_analyzer.py::test_ollama_provider_calls_api -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/llm/ backend/tests/test_analyzer.py
git commit -m "feat: LLMProvider ABC + Ollama implementation"
```

---

### Task 11: Analysis Prompts + Analyzer Service

**Files:**
- Create: `backend/app/services/llm/prompts.py`
- Create: `backend/app/services/analyzer.py`

- [ ] **Step 1: Add failing tests**

```python
# append to backend/tests/test_analyzer.py
from app.services.llm.prompts import build_analysis_prompt
from app.services.analyzer import parse_llm_response

def test_prompt_contains_org_context():
    org_profile = {"name": "Test NBFC", "nbfc_type": "ICC", "product_lines": "Digital Lending"}
    prompt = build_analysis_prompt("Some circular text", org_profile, [])
    assert "Test NBFC" in prompt
    assert "ICC" in prompt
    assert "Digital Lending" in prompt

def test_parse_llm_response_valid_json():
    raw = '''{"summary": "Para one.\n\nPara two.", "applicability": "Yes applies.", "conclusion": "Act now.", "implementation": [{"step": 1, "action": "Update DB", "detail": "Remove entries.", "role": "Compliance", "urgency": "Immediate"}], "risk_level": "High"}'''
    result = parse_llm_response(raw)
    assert result["risk_level"] == "High"
    assert len(result["implementation"]) == 1

def test_parse_llm_response_fallback_on_bad_json():
    result = parse_llm_response("not json at all")
    assert result["summary"] != ""
    assert result["risk_level"] == "Low"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_analyzer.py -v
```

- [ ] **Step 3: Write `backend/app/services/llm/prompts.py`**

```python
def build_analysis_prompt(doc_text: str, org_profile: dict, org_doc_texts: list[str]) -> str:
    org_context = f"""Organisation: {org_profile.get('name', 'Unknown')}
NBFC Type: {org_profile.get('nbfc_type', '')}
Product Lines: {org_profile.get('product_lines', '')}
AUM Band: {org_profile.get('aum_band', '')}
Geographies: {org_profile.get('geographies', '')}
Key Compliance Risk Areas: {org_profile.get('compliance_risk_areas', '')}"""

    doc_context = ""
    if org_doc_texts:
        doc_context = "\n\nOrganisation's internal compliance documents (for context):\n" + "\n---\n".join(org_doc_texts[:3])

    return f"""You are a senior compliance analyst at an Indian NBFC. Analyse the following regulatory document and provide a structured JSON response tailored specifically to the organisation described below.

ORGANISATION CONTEXT:
{org_context}{doc_context}

REGULATORY DOCUMENT:
{doc_text[:12000]}

Return ONLY valid JSON (no markdown, no explanation outside the JSON) with exactly these fields:
{{
  "summary": "Flowing prose in 2-3 paragraphs (average 8-9 sentences total). Plain English. Scale length to document complexity. Separate paragraphs with \\n\\n.",
  "applicability": "Does this circular apply to this specific organisation? State yes or no clearly, then explain why referencing the org's NBFC type and product lines.",
  "conclusion": "What does this mean for the organisation in plain English? New obligation, update to existing, or informational? Flag urgency and regulatory risk of non-compliance.",
  "implementation": [
    {{
      "step": 1,
      "action": "Short imperative action title",
      "detail": "Specific instructions for what to do",
      "role": "Suggested responsible role (e.g. Compliance Officer, KYC Team, Legal)",
      "urgency": "One of: Immediate | Within 2 days | Within 1 week | Within 30 days | By YYYY-MM-DD"
    }}
  ],
  "risk_level": "High | Medium | Low"
}}"""
```

- [ ] **Step 4: Write `backend/app/services/analyzer.py`**

```python
import json
import re
from sqlalchemy.orm import Session
from ..models import RegulatoryUpdate, AIAnalysis, Organisation, OrgDocument
from .llm.base import LLMProvider
from .llm.ollama import OllamaProvider
from .llm.prompts import build_analysis_prompt
from .pdf import chunk_text
from ..config import settings

def _get_provider() -> LLMProvider:
    return OllamaProvider(base_url=settings.ollama_url, model=settings.ollama_model)

def parse_llm_response(raw: str) -> dict:
    try:
        cleaned = re.sub(r"^```json\s*|```$", "", raw.strip(), flags=re.MULTILINE)
        data = json.loads(cleaned)
        return {
            "summary": data.get("summary", ""),
            "applicability": data.get("applicability", ""),
            "conclusion": data.get("conclusion", ""),
            "implementation": data.get("implementation", []),
            "risk_level": data.get("risk_level", "Low"),
        }
    except (json.JSONDecodeError, AttributeError):
        return {"summary": raw[:2000] if raw else "Analysis unavailable.", "applicability": "", "conclusion": "", "implementation": [], "risk_level": "Low"}

def _org_profile(org: Organisation) -> dict:
    return {"name": org.name, "nbfc_type": org.nbfc_type, "product_lines": org.product_lines, "aum_band": org.aum_band, "geographies": org.geographies, "compliance_risk_areas": org.compliance_risk_areas}

def analyse_update(update_id: str, org_id: int, db: Session) -> AIAnalysis | None:
    update = db.get(RegulatoryUpdate, update_id)
    org = db.get(Organisation, org_id)
    if not update or not org:
        return None
    existing = db.query(AIAnalysis).filter_by(update_id=update_id, org_id=org_id).first()
    if existing:
        return existing

    org_docs = db.query(OrgDocument).filter_by(org_id=org_id).all()
    org_doc_texts = [d.extracted_text for d in org_docs if d.extracted_text]
    provider = _get_provider()

    doc_text = update.raw_text
    chunks = chunk_text(doc_text, max_chars=12000)

    if len(chunks) > 1:
        summaries = []
        for chunk in chunks:
            prompt = build_analysis_prompt(chunk, _org_profile(org), org_doc_texts)
            summaries.append(provider.generate(prompt))
        final_prompt = build_analysis_prompt("\n\n".join(summaries), _org_profile(org), org_doc_texts)
        raw = provider.generate(final_prompt)
    else:
        prompt = build_analysis_prompt(doc_text, _org_profile(org), org_doc_texts)
        raw = provider.generate(prompt)

    result = parse_llm_response(raw)
    analysis = AIAnalysis(
        update_id=update_id, org_id=org_id,
        summary=result["summary"], applicability=result["applicability"],
        conclusion=result["conclusion"], implementation_json=result["implementation"],
        risk_level=result["risk_level"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
```

- [ ] **Step 5: Run — expect PASS**

```bash
python -m pytest tests/test_analyzer.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/llm/prompts.py backend/app/services/analyzer.py
git commit -m "feat: analysis prompt template + analyzer service with chunk-and-summarise"
```

---

### Task 12: Scheduler

**Files:**
- Create: `backend/app/services/scheduler.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write `backend/app/services/scheduler.py`**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Organisation
from ..config import settings
from .scraper import fetch_and_store
from .analyzer import analyse_update

_scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

def _run_fetch_for_all_orgs():
    db: Session = SessionLocal()
    try:
        orgs = db.query(Organisation).all()
        for org in orgs:
            new_ids = fetch_and_store(org.id, db)
            for uid in new_ids:
                analyse_update(uid, org.id, db)
    finally:
        db.close()

def _run_daily_digest():
    from .digest import send_all_digests
    db: Session = SessionLocal()
    try:
        send_all_digests(db)
    finally:
        db.close()

def start_scheduler():
    _scheduler.add_job(
        _run_fetch_for_all_orgs,
        trigger=IntervalTrigger(hours=settings.fetch_schedule_hours),
        id="fetch_job",
        replace_existing=True,
    )
    h, m = settings.digest_time_ist.split(":")
    _scheduler.add_job(
        _run_daily_digest,
        trigger=CronTrigger(hour=int(h), minute=int(m), timezone="Asia/Kolkata"),
        id="digest_job",
        replace_existing=True,
    )
    _scheduler.start()

def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown()
```

- [ ] **Step 2: Wire scheduler into `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .routers import auth, updates, admin, digest
from .services.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(title="RegWatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(updates.router)
app.include_router(admin.router)
app.include_router(digest.router)
```

- [ ] **Step 3: Verify app starts cleanly**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

Expected: Server starts, no errors, scheduler logs "Added job fetch_job".

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/scheduler.py backend/app/main.py
git commit -m "feat: APScheduler wired — fetch + digest jobs on configurable schedule"
```

---

## Phase 4 — API Routes

### Task 13: Updates API Routes

**Files:**
- Modify: `backend/app/routers/updates.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api_updates.py
from app.models import RegulatoryUpdate, AIAnalysis

def _login(client, org_and_user):
    org, user = org_and_user
    resp = client.post("/auth/login", json={"email": "test@nbfc.com", "password": "pass123"})
    return resp.json()["token"], org.id

def _seed_update(db, org_id):
    u = RegulatoryUpdate(id="abc1234567890001", org_id=org_id, regulator="RBI",
        source_type="Circulars", document_type="Circular",
        title="Test Circular", date="2026-05-22", status="unreviewed")
    a = AIAnalysis(update_id="abc1234567890001", org_id=org_id,
        summary="Summary here.", applicability="Applies.", conclusion="Act now.",
        implementation_json=[{"step":1,"action":"Do it","detail":"Details","role":"Compliance","urgency":"Immediate"}],
        risk_level="High")
    db.add(u); db.add(a); db.commit()
    return u

def test_list_updates(client, org_and_user, db):
    token, org_id = _login(client, org_and_user)
    _seed_update(db, org_id)
    resp = client.get("/updates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["regulator"] == "RBI"

def test_get_update_detail(client, org_and_user, db):
    token, org_id = _login(client, org_and_user)
    u = _seed_update(db, org_id)
    resp = client.get(f"/updates/{u.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["analysis"]["risk_level"] == "High"

def test_mark_reviewed(client, org_and_user, db):
    token, org_id = _login(client, org_and_user)
    u = _seed_update(db, org_id)
    resp = client.patch(f"/updates/{u.id}/review", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "reviewed"

def test_updates_scoped_to_org(client, org_and_user, db):
    token, org_id = _login(client, org_and_user)
    # Seed update for a different org (org_id=999 doesn't exist but update has different org)
    u = RegulatoryUpdate(id="foreignupdate0001", org_id=999,
        regulator="SEBI", source_type="Circulars", document_type="Circular",
        title="Other Org Circular", status="unreviewed")
    db.add(u); db.commit()
    resp = client.get("/updates", headers={"Authorization": f"Bearer {token}"})
    ids = [i["id"] for i in resp.json()["items"]]
    assert "foreignupdate0001" not in ids
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_api_updates.py -v
```

- [ ] **Step 3: Write `backend/app/routers/updates.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import RegulatoryUpdate, AIAnalysis
from ..routers.auth import get_current_user, User

router = APIRouter(prefix="/updates", tags=["updates"])

def _serialize(u: RegulatoryUpdate, include_analysis: bool = False) -> dict:
    base = {"id": u.id, "regulator": u.regulator, "source_type": u.source_type,
            "document_type": u.document_type, "title": u.title, "date": u.date,
            "page_url": u.page_url, "pdf_url": u.pdf_url, "status": u.status,
            "detected_at": u.detected_at.isoformat() if u.detected_at else None,
            "risk_level": u.analysis.risk_level if u.analysis else "Low",
            "applicability_short": (u.analysis.applicability[:120] + "...") if u.analysis and len(u.analysis.applicability) > 120 else (u.analysis.applicability if u.analysis else "")}
    if include_analysis and u.analysis:
        base["analysis"] = {"summary": u.analysis.summary, "applicability": u.analysis.applicability,
                            "conclusion": u.analysis.conclusion, "implementation": u.analysis.implementation_json,
                            "risk_level": u.analysis.risk_level}
    return base

@router.get("")
def list_updates(
    regulator: str | None = Query(None),
    document_type: str | None = Query(None),
    risk_level: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(RegulatoryUpdate).filter_by(org_id=user.org_id)
    if regulator:
        q = q.filter(RegulatoryUpdate.regulator == regulator)
    if document_type:
        q = q.filter(RegulatoryUpdate.document_type == document_type)
    if status:
        q = q.filter(RegulatoryUpdate.status == status)
    if risk_level:
        q = q.join(AIAnalysis).filter(AIAnalysis.risk_level == risk_level)
    if search:
        term = f"%{search}%"
        q = q.filter(RegulatoryUpdate.title.ilike(term))
    total = q.count()
    items = q.order_by(RegulatoryUpdate.detected_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "items": [_serialize(u) for u in items]}

@router.get("/{update_id}")
def get_update(update_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    u = db.query(RegulatoryUpdate).filter_by(id=update_id, org_id=user.org_id).first()
    if not u:
        raise HTTPException(404, "Update not found")
    return _serialize(u, include_analysis=True)

@router.patch("/{update_id}/review")
def mark_reviewed(update_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    u = db.query(RegulatoryUpdate).filter_by(id=update_id, org_id=user.org_id).first()
    if not u:
        raise HTTPException(404)
    u.status = "reviewed"
    db.commit()
    return {"id": u.id, "status": u.status}
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_api_updates.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/updates.py backend/tests/test_api_updates.py
git commit -m "feat: updates API — list with filters, detail view, mark reviewed"
```

---

### Task 14: Admin API Routes

**Files:**
- Modify: `backend/app/routers/admin.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api_admin.py
from app.models import Organisation, User
from app.auth.utils import hash_password

def _superadmin(client, db):
    org = Organisation(name="Admin Org", nbfc_type="ICC")
    db.add(org); db.flush()
    user = User(org_id=org.id, email="admin@regwatch.in", password_hash=hash_password("adminpass"))
    db.add(user); db.commit()
    resp = client.post("/auth/login", json={"email": "admin@regwatch.in", "password": "adminpass"})
    return resp.json()["token"]

def test_create_org(client, db):
    token = _superadmin(client, db)
    resp = client.post("/admin/orgs", json={
        "name": "New NBFC", "nbfc_type": "MFI", "product_lines": "Digital Lending",
        "aum_band": "<100Cr", "geographies": "Maharashtra", "compliance_risk_areas": "KYC"
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "New NBFC"

def test_list_orgs(client, db):
    token = _superadmin(client, db)
    resp = client.get("/admin/orgs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

def test_create_org_user(client, db):
    token = _superadmin(client, db)
    create_resp = client.post("/admin/orgs", json={"name": "NBFC B", "nbfc_type": "ICC"}, headers={"Authorization": f"Bearer {token}"})
    org_id = create_resp.json()["id"]
    resp = client.post(f"/admin/orgs/{org_id}/users", json={"email": "user@nbfcb.com", "password": "pass456"},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_api_admin.py -v
```

- [ ] **Step 3: Write `backend/app/routers/admin.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import Organisation, User, FetchRun
from ..routers.auth import get_current_user
from ..auth.utils import hash_password
from ..services.scraper import fetch_and_store
from ..services.analyzer import analyse_update

router = APIRouter(prefix="/admin", tags=["admin"])

class OrgCreate(BaseModel):
    name: str
    nbfc_type: str
    product_lines: str = ""
    aum_band: str = ""
    geographies: str = ""
    compliance_risk_areas: str = ""

class UserCreate(BaseModel):
    email: str
    password: str

@router.get("/orgs")
def list_orgs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    orgs = db.query(Organisation).all()
    return [{"id": o.id, "name": o.name, "nbfc_type": o.nbfc_type, "created_at": o.created_at.isoformat()} for o in orgs]

@router.post("/orgs", status_code=201)
def create_org(body: OrgCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    org = Organisation(**body.model_dump())
    db.add(org)
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name, "nbfc_type": org.nbfc_type}

@router.post("/orgs/{org_id}/users", status_code=201)
def create_org_user(org_id: int, body: UserCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(404, "Org not found")
    new_user = User(org_id=org_id, email=body.email, password_hash=hash_password(body.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email}

@router.get("/fetch-runs")
def list_fetch_runs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    runs = db.query(FetchRun).filter_by(org_id=user.org_id).order_by(FetchRun.started_at.desc()).limit(50).all()
    return [{"id": r.id, "source": r.source, "started_at": r.started_at.isoformat(),
             "completed_at": r.completed_at.isoformat() if r.completed_at else None,
             "updates_found": r.updates_found, "error": r.error_message} for r in runs]

@router.post("/fetch/trigger")
def trigger_fetch(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    new_ids = fetch_and_store(user.org_id, db)
    for uid in new_ids:
        analyse_update(uid, user.org_id, db)
    return {"new_updates": len(new_ids)}
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_api_admin.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_api_admin.py
git commit -m "feat: admin API — org CRUD, user creation, fetch trigger, run history"
```

---

### Task 15: Email Digest Service + Route

**Files:**
- Create: `backend/app/services/digest.py`
- Modify: `backend/app/routers/digest.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_digest.py
from app.services.digest import build_digest_html
from app.models import RegulatoryUpdate, AIAnalysis, Organisation

def test_build_digest_html_groups_by_regulator(db):
    org = Organisation(name="D NBFC", nbfc_type="ICC")
    db.add(org); db.flush()
    u1 = RegulatoryUpdate(id="dig0000000000001", org_id=org.id, regulator="RBI",
        source_type="Circulars", document_type="Circular", title="RBI Update", status="unreviewed")
    u2 = RegulatoryUpdate(id="dig0000000000002", org_id=org.id, regulator="SEBI",
        source_type="Circulars", document_type="Circular", title="SEBI Update", status="unreviewed")
    a1 = AIAnalysis(update_id="dig0000000000001", org_id=org.id,
        summary="RBI summary.", applicability="Applies.", conclusion="Act.",
        implementation_json=[], risk_level="High")
    a2 = AIAnalysis(update_id="dig0000000000002", org_id=org.id,
        summary="SEBI summary.", applicability="Review.", conclusion="Note.",
        implementation_json=[], risk_level="Low")
    db.add_all([u1, u2, a1, a2]); db.commit()
    html = build_digest_html(org, [u1, u2])
    assert "RBI" in html
    assert "SEBI" in html
    assert "RBI Update" in html
    assert "<script" not in html
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_digest.py -v
```

- [ ] **Step 3: Write `backend/app/services/digest.py`**

```python
import html as html_lib
from collections import defaultdict
from sqlalchemy.orm import Session
from ..models import Organisation, RegulatoryUpdate

def _esc(text: str) -> str:
    return html_lib.escape(str(text or ""))

def build_digest_html(org: Organisation, updates: list[RegulatoryUpdate]) -> str:
    grouped: dict[str, list] = defaultdict(list)
    for u in updates:
        grouped[u.regulator].append(u)

    sections = []
    for regulator, items in sorted(grouped.items()):
        rows = []
        for u in items:
            analysis = u.analysis
            impl_html = ""
            if analysis and analysis.implementation_json:
                steps = "".join(
                    f"<li><strong>{_esc(s.get('action',''))}</strong> — {_esc(s.get('detail',''))} "
                    f"<em>({_esc(s.get('role',''))} · {_esc(s.get('urgency',''))})</em></li>"
                    for s in analysis.implementation_json
                )
                impl_html = f"<ol style='margin:8px 0 0 16px'>{steps}</ol>"

            link = _esc(u.pdf_url or u.page_url or "")
            link_html = f'<p><a href="{link}" style="color:#818cf8">View source document →</a></p>' if link and (link.startswith("https://") or link.startswith("http://")) else ""

            rows.append(f"""
<div style="margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid #1e1b4b">
  <h3 style="margin:0 0 6px;color:#e2e8f0;font-size:15px">{_esc(u.title)}</h3>
  <p style="margin:0 0 4px;font-size:12px;color:#818cf8">{_esc(u.document_type)} · {_esc(u.date or 'Date unknown')} · Risk: {_esc(analysis.risk_level if analysis else 'Low')}</p>
  {'<p style="margin:6px 0;color:#c7d2fe;font-size:13px">' + _esc(analysis.summary) + '</p>' if analysis else ''}
  {'<p style="margin:4px 0;font-size:13px;color:#94a3b8"><strong>Applicability:</strong> ' + _esc(analysis.applicability) + '</p>' if analysis else ''}
  {impl_html}
  {link_html}
</div>""")

        sections.append(f"""
<div style="margin-bottom:28px">
  <h2 style="color:#818cf8;font-size:17px;border-bottom:1px solid #312e81;padding-bottom:8px;margin-bottom:14px">{_esc(regulator)}</h2>
  {''.join(rows)}
</div>""")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>RegWatch Daily Digest</title></head>
<body style="background:#0a0a1a;color:#e2e8f0;font-family:Inter,sans-serif;max-width:680px;margin:0 auto;padding:32px 20px">
  <h1 style="color:#818cf8;font-size:22px;margin-bottom:4px">RegWatch — Daily Compliance Digest</h1>
  <p style="color:#64748b;font-size:13px;margin-bottom:28px">{len(updates)} new update(s) for {_esc(org.name)}</p>
  {''.join(sections)}
  <p style="color:#475569;font-size:11px;margin-top:32px">You are receiving this because you are listed as a digest recipient for {_esc(org.name)}.</p>
</body></html>"""

def send_all_digests(db: Session):
    import os
    from datetime import datetime, timedelta
    from ..config import settings
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException

    if not settings.brevo_api_key or not settings.sender_email:
        return

    since = datetime.utcnow() - timedelta(hours=24)
    orgs = db.query(Organisation).all()
    config = sib_api_v3_sdk.Configuration()
    config.api_key["api-key"] = settings.brevo_api_key
    api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(config))

    for org in orgs:
        digest_settings = db.query(DigestSettings).filter_by(org_id=org.id).first()
        if not digest_settings or not digest_settings.recipients:
            continue
        updates = (db.query(RegulatoryUpdate)
            .filter(RegulatoryUpdate.org_id == org.id, RegulatoryUpdate.detected_at >= since)
            .order_by(RegulatoryUpdate.detected_at.desc()).all())
        if not updates:
            continue
        html = build_digest_html(org, updates)
        recipients = [{"email": e.strip()} for e in digest_settings.recipients.split(",") if e.strip()]
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=recipients,
            sender={"email": settings.sender_email},
            subject=f"{len(updates)} new regulatory update(s) for {org.name} — {datetime.utcnow().strftime('%d %b %Y')}",
            html_content=html,
        )
        try:
            api.send_transac_email(email)
        except ApiException:
            pass
```

- [ ] **Step 4: Write `backend/app/models/digest.py` and add `DigestSettings` model**

```python
# backend/app/models/digest.py
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class DigestSettings(Base):
    __tablename__ = "digest_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), unique=True)
    recipients: Mapped[str] = mapped_column(String(1000), default="")
    send_time_ist: Mapped[str] = mapped_column(String(5), default="08:00")
```

Add to `migrations/001_initial.sql` (run manually):

```sql
CREATE TABLE digest_settings (
    id SERIAL PRIMARY KEY,
    org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE UNIQUE,
    recipients VARCHAR(1000) DEFAULT '',
    send_time_ist VARCHAR(5) DEFAULT '08:00'
);
```

```bash
docker compose exec -T db psql -U regwatch -d regwatch -c "CREATE TABLE digest_settings (id SERIAL PRIMARY KEY, org_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE UNIQUE, recipients VARCHAR(1000) DEFAULT '', send_time_ist VARCHAR(5) DEFAULT '08:00');"
```

- [ ] **Step 5: Write `backend/app/routers/digest.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models.digest import DigestSettings
from ..routers.auth import get_current_user, User

router = APIRouter(prefix="/digest", tags=["digest"])

class DigestSettingsUpdate(BaseModel):
    recipients: str
    send_time_ist: str = "08:00"

@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.query(DigestSettings).filter_by(org_id=user.org_id).first()
    if not s:
        return {"recipients": "", "send_time_ist": "08:00"}
    return {"recipients": s.recipients, "send_time_ist": s.send_time_ist}

@router.patch("/settings")
def update_settings(body: DigestSettingsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.query(DigestSettings).filter_by(org_id=user.org_id).first()
    if not s:
        s = DigestSettings(org_id=user.org_id)
        db.add(s)
    s.recipients = body.recipients
    s.send_time_ist = body.send_time_ist
    db.commit()
    return {"recipients": s.recipients, "send_time_ist": s.send_time_ist}
```

- [ ] **Step 6: Add DigestSettings to models `__init__.py`**

```python
# backend/app/models/__init__.py
from .org import Organisation, OrgDocument
from .update import RegulatoryUpdate, AIAnalysis, FetchRun
from .user import User
from .digest import DigestSettings

__all__ = ["Organisation", "OrgDocument", "RegulatoryUpdate", "AIAnalysis", "FetchRun", "User", "DigestSettings"]
```

- [ ] **Step 7: Run — expect PASS**

```bash
python -m pytest tests/test_digest.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/digest.py backend/app/routers/digest.py backend/app/models/digest.py backend/app/models/__init__.py backend/tests/test_digest.py
git commit -m "feat: email digest builder (HTML-escaped, grouped by regulator) + digest settings API"
```

---

## Phase 5 — Frontend

### Task 16: React + Vite Bootstrap + Theme

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/theme.ts`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "regwatch-frontend",
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.24.0",
    "@tanstack/react-query": "^5.45.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.3.0"
  }
}
```

- [ ] **Step 2: Write `frontend/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/auth": "http://localhost:8000",
      "/updates": "http://localhost:8000",
      "/admin": "http://localhost:8000",
      "/digest": "http://localhost:8000",
    },
  },
  build: { outDir: "../backend/static" },
});
```

- [ ] **Step 3: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>RegWatch</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; } body { font-family: Inter, system-ui, sans-serif; background: #0a0a1a; color: #e2e8f0; }</style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Write `frontend/src/theme.ts`**

```typescript
export const colors = {
  bg: "#0a0a1a",
  surface: "#0f0f23",
  border: "#1e1b4b",
  borderStrong: "#312e81",
  accent: "#818cf8",
  accentDim: "#818cf820",
  textPrimary: "#e2e8f0",
  textSecondary: "#94a3b8",
  textMuted: "#64748b",
  riskHigh: "#f87171",
  riskHighBg: "#450a0a",
  riskMedium: "#fbbf24",
  riskMediumBg: "#451a03",
  riskLow: "#6ee7b7",
  riskLowBg: "#14532d",
  sidebar: "#0a0a1a",
  sidebarActive: "#1e1b4b",
} as const;

export const riskColor = (level: string) => {
  if (level === "High") return { color: colors.riskHigh, bg: colors.riskHighBg };
  if (level === "Medium") return { color: colors.riskMedium, bg: colors.riskMediumBg };
  return { color: colors.riskLow, bg: colors.riskLowBg };
};
```

- [ ] **Step 6: Write `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
```

- [ ] **Step 7: Install deps and verify dev server starts**

```bash
cd frontend && npm install && npm run dev
```

Expected: Vite dev server running at http://localhost:5173 with no errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: React/Vite frontend bootstrap with Slate+Indigo theme tokens"
```

---

### Task 17: API Client + TypeScript Types

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Write `frontend/src/api/types.ts`**

```typescript
export interface ImplementationStep {
  step: number;
  action: string;
  detail: string;
  role: string;
  urgency: string;
}

export interface AIAnalysis {
  summary: string;
  applicability: string;
  conclusion: string;
  implementation: ImplementationStep[];
  risk_level: "High" | "Medium" | "Low";
}

export interface RegulatoryUpdate {
  id: string;
  regulator: string;
  source_type: string;
  document_type: string;
  title: string;
  date: string;
  page_url: string;
  pdf_url: string;
  status: "unreviewed" | "reviewed";
  detected_at: string;
  risk_level: "High" | "Medium" | "Low";
  applicability_short: string;
  analysis?: AIAnalysis;
}

export interface UpdatesResponse {
  total: number;
  page: number;
  items: RegulatoryUpdate[];
}

export interface Organisation {
  id: number;
  name: string;
  nbfc_type: string;
  created_at: string;
}

export interface AuthUser {
  id: number;
  email: string;
  org_id: number;
}

export interface DigestSettings {
  recipients: string;
  send_time_ist: string;
}
```

- [ ] **Step 2: Write `frontend/src/api/client.ts`**

```typescript
import axios from "axios";

export const api = axios.create({ baseURL: "/" });

let _token: string | null = localStorage.getItem("rw_token");

export function setToken(token: string | null) {
  _token = token;
  if (token) localStorage.setItem("rw_token", token);
  else localStorage.removeItem("rw_token");
}

api.interceptors.request.use((config) => {
  if (_token) config.headers.Authorization = `Bearer ${_token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      setToken(null);
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ token: string; org_id: number }>("/auth/login", { email, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get<{ id: number; email: string; org_id: number }>("/auth/me"),
};

export const updatesApi = {
  list: (params: Record<string, string | number | undefined>) =>
    api.get<import("./types").UpdatesResponse>("/updates", { params }),
  get: (id: string) =>
    api.get<import("./types").RegulatoryUpdate>(`/updates/${id}`),
  markReviewed: (id: string) =>
    api.patch<{ id: string; status: string }>(`/updates/${id}/review`),
};

export const adminApi = {
  listOrgs: () => api.get<import("./types").Organisation[]>("/admin/orgs"),
  createOrg: (data: object) => api.post<import("./types").Organisation>("/admin/orgs", data),
  createUser: (orgId: number, data: object) => api.post(`/admin/orgs/${orgId}/users`, data),
  fetchRuns: () => api.get("/admin/fetch-runs"),
  triggerFetch: () => api.post("/admin/fetch/trigger"),
  uploadDocument: (orgId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/admin/orgs/${orgId}/documents`, form);
  },
};

export const digestApi = {
  getSettings: () => api.get<import("./types").DigestSettings>("/digest/settings"),
  updateSettings: (data: import("./types").DigestSettings) => api.patch("/digest/settings", data),
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: typed API client with auth interceptors + all endpoint wrappers"
```

---

### Task 18: Layout Shell + Routing + Auth Hook

**Files:**
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx` (shell)
- Create: `frontend/src/pages/AdminPage.tsx` (shell)

- [ ] **Step 1: Write `frontend/src/hooks/useAuth.ts`**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi, setToken } from "../api/client";

export function useAuth() {
  const qc = useQueryClient();
  const { data: user, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then((r) => r.data),
    retry: false,
  });
  const login = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password).then((r) => { setToken(r.data.token); return r.data; }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
  const logout = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => { setToken(null); qc.clear(); },
  });
  return { user, isLoading, login, logout };
}
```

- [ ] **Step 2: Write `frontend/src/components/Sidebar.tsx`**

```tsx
import { NavLink } from "react-router-dom";
import { colors } from "../theme";
import { useAuth } from "../hooks/useAuth";

const NAV = [
  { to: "/", label: "Dashboard" },
  { to: "/admin", label: "Admin" },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  return (
    <nav style={{ width: 200, minHeight: "100vh", background: colors.sidebar, borderRight: `1px solid ${colors.border}`, padding: "24px 12px", display: "flex", flexDirection: "column" }}>
      <div style={{ color: colors.accent, fontWeight: 700, fontSize: 16, letterSpacing: 1, marginBottom: 32 }}>RegWatch</div>
      {NAV.map((n) => (
        <NavLink key={n.to} to={n.to} end style={({ isActive }) => ({
          display: "block", padding: "8px 12px", borderRadius: 6, marginBottom: 4,
          background: isActive ? colors.sidebarActive : "transparent",
          color: isActive ? colors.accent : colors.textMuted,
          textDecoration: "none", fontSize: 14,
          borderLeft: isActive ? `2px solid ${colors.accent}` : "2px solid transparent",
        })}>
          {n.label}
        </NavLink>
      ))}
      <div style={{ marginTop: "auto", fontSize: 12, color: colors.textMuted }}>
        <div>{user?.email}</div>
        <button onClick={() => logout.mutate()} style={{ marginTop: 8, background: "none", border: "none", color: colors.accent, cursor: "pointer", fontSize: 12 }}>Sign out</button>
      </div>
    </nav>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/Layout.tsx`**

```tsx
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { colors } from "../theme";

export function Layout() {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: colors.bg }}>
      <Sidebar />
      <main style={{ flex: 1, overflow: "auto" }}>
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Write `frontend/src/pages/LoginPage.tsx`**

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { colors } from "../theme";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login.mutateAsync({ email, password });
      navigate("/");
    } catch {
      setError("Invalid email or password.");
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: colors.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <form onSubmit={submit} style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 12, padding: 40, width: 360 }}>
        <h1 style={{ color: colors.accent, fontWeight: 700, fontSize: 24, marginBottom: 8 }}>RegWatch</h1>
        <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: 28 }}>Compliance monitoring for NBFCs</p>
        {error && <p style={{ color: colors.riskHigh, fontSize: 13, marginBottom: 12 }}>{error}</p>}
        <label style={{ display: "block", color: colors.textSecondary, fontSize: 12, marginBottom: 4 }}>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required
          style={{ width: "100%", background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "10px 12px", color: colors.textPrimary, fontSize: 14, marginBottom: 16 }} />
        <label style={{ display: "block", color: colors.textSecondary, fontSize: 12, marginBottom: 4 }}>Password</label>
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required
          style={{ width: "100%", background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "10px 12px", color: colors.textPrimary, fontSize: 14, marginBottom: 24 }} />
        <button type="submit" style={{ width: "100%", background: colors.accent, border: "none", borderRadius: 6, padding: "11px 0", color: "#0a0a1a", fontWeight: 700, fontSize: 14, cursor: "pointer" }}>
          {login.isPending ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 5: Write stub pages and `App.tsx`**

```tsx
// frontend/src/pages/DashboardPage.tsx
import { colors } from "../theme";
export function DashboardPage() {
  return <div style={{ padding: 32, color: colors.textPrimary }}>Dashboard — coming in Task 19</div>;
}

// frontend/src/pages/AdminPage.tsx
import { colors } from "../theme";
export function AdminPage() {
  return <div style={{ padding: 32, color: colors.textPrimary }}>Admin — coming in Task 21</div>;
}
```

```tsx
// frontend/src/App.tsx
import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { AdminPage } from "./pages/AdminPage";
import { useAuth } from "./hooks/useAuth";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<DashboardPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 6: Verify in browser**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173 — should redirect to /login. Log in with a seeded user and reach the dashboard stub.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: layout shell, sidebar nav, login page, auth hook + routing"
```

---

### Task 19: RiskBadge + MetricStrip + UpdateCard

**Files:**
- Create: `frontend/src/components/RiskBadge.tsx`
- Create: `frontend/src/components/MetricStrip.tsx`
- Create: `frontend/src/components/UpdateCard.tsx`

- [ ] **Step 1: Write `frontend/src/components/RiskBadge.tsx`**

```tsx
import { riskColor } from "../theme";

interface Props { level: "High" | "Medium" | "Low"; }

export function RiskBadge({ level }: Props) {
  const { color, bg } = riskColor(level);
  return (
    <span style={{ background: bg, color, fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 10, letterSpacing: 0.5 }}>
      {level.toUpperCase()} RISK
    </span>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/MetricStrip.tsx`**

```tsx
import { colors } from "../theme";

interface Metric { label: string; value: number | string; color?: string; }

export function MetricStrip({ metrics }: { metrics: Metric[] }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${metrics.length}, 1fr)`, gap: 12, marginBottom: 20 }}>
      {metrics.map((m) => (
        <div key={m.label} style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: "14px 16px" }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: m.color ?? colors.textPrimary }}>{m.value}</div>
          <div style={{ fontSize: 12, color: colors.textMuted, marginTop: 4 }}>{m.label}</div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/UpdateCard.tsx`**

```tsx
import { RegulatoryUpdate } from "../api/types";
import { RiskBadge } from "./RiskBadge";
import { colors } from "../theme";

interface Props { update: RegulatoryUpdate; onClick: () => void; }

export function UpdateCard({ update, onClick }: Props) {
  const isUnreviewed = update.status === "unreviewed";
  return (
    <div onClick={onClick} style={{
      background: colors.surface, border: `1px solid ${isUnreviewed ? colors.borderStrong : colors.border}`,
      borderRadius: 8, padding: "14px 16px", cursor: "pointer", transition: "border-color 0.15s",
    }}
    onMouseEnter={(e) => (e.currentTarget.style.borderColor = colors.accent)}
    onMouseLeave={(e) => (e.currentTarget.style.borderColor = isUnreviewed ? colors.borderStrong : colors.border)}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <RiskBadge level={update.risk_level} />
          <span style={{ background: colors.sidebarActive, color: colors.accent, fontSize: 10, padding: "2px 8px", borderRadius: 10 }}>{update.regulator}</span>
          <span style={{ background: colors.sidebarActive, color: colors.accent, fontSize: 10, padding: "2px 8px", borderRadius: 10 }}>{update.document_type}</span>
        </div>
        <span style={{ color: colors.textMuted, fontSize: 11, flexShrink: 0, marginLeft: 12 }}>{update.date || "—"}</span>
      </div>
      <div style={{ color: colors.textPrimary, fontSize: 14, fontWeight: 500, lineHeight: 1.4, marginBottom: 6 }}>{update.title}</div>
      {update.applicability_short && (
        <div style={{ color: colors.accent, fontSize: 12 }}>✓ {update.applicability_short}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/RiskBadge.tsx frontend/src/components/MetricStrip.tsx frontend/src/components/UpdateCard.tsx
git commit -m "feat: RiskBadge, MetricStrip, UpdateCard components"
```

---

### Task 20: FilterPanel + DetailModal

**Files:**
- Create: `frontend/src/components/FilterPanel.tsx`
- Create: `frontend/src/components/DetailModal.tsx`

- [ ] **Step 1: Write `frontend/src/components/FilterPanel.tsx`**

```tsx
import { colors } from "../theme";

interface Filters {
  regulator: string; document_type: string; risk_level: string; status: string; search: string;
}
interface Props { filters: Filters; onChange: (f: Filters) => void; }

const SELECT_STYLE = { width: "100%", background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "8px 10px", color: colors.textPrimary, fontSize: 13 };

export function FilterPanel({ filters, onChange }: Props) {
  const set = (key: keyof Filters) => (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) =>
    onChange({ ...filters, [key]: e.target.value });
  return (
    <div style={{ borderTop: `1px solid ${colors.border}`, paddingTop: 16, marginTop: 16 }}>
      <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1, color: colors.textMuted, marginBottom: 10 }}>Filters</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <select style={SELECT_STYLE} value={filters.regulator} onChange={set("regulator")}>
          <option value="">All regulators</option>
          {["RBI", "SEBI", "IRDAI", "MCA"].map((r) => <option key={r}>{r}</option>)}
        </select>
        <select style={SELECT_STYLE} value={filters.document_type} onChange={set("document_type")}>
          <option value="">All types</option>
          {["Circular", "Notification", "Guideline", "Master Direction", "Notice", "FAQ", "Order"].map((t) => <option key={t}>{t}</option>)}
        </select>
        <select style={SELECT_STYLE} value={filters.risk_level} onChange={set("risk_level")}>
          <option value="">All risk levels</option>
          <option>High</option><option>Medium</option><option>Low</option>
        </select>
        <select style={SELECT_STYLE} value={filters.status} onChange={set("status")}>
          <option value="">All statuses</option>
          <option value="unreviewed">Unreviewed</option>
          <option value="reviewed">Reviewed</option>
        </select>
        <input value={filters.search} onChange={set("search")} placeholder="Search title..."
          style={{ ...SELECT_STYLE, border: `1px solid ${colors.border}` } as React.CSSProperties} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/DetailModal.tsx`**

```tsx
import { useEffect } from "react";
import { RegulatoryUpdate, ImplementationStep } from "../api/types";
import { RiskBadge } from "./RiskBadge";
import { colors } from "../theme";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updatesApi } from "../api/client";

interface Props { update: RegulatoryUpdate; onClose: () => void; }

const URGENCY_COLOR: Record<string, string> = {
  "Immediate": colors.riskHigh, "Within 2 days": colors.riskMedium,
  "Within 1 week": "#fb923c", "Within 30 days": colors.riskLow,
};

export function DetailModal({ update, onClose }: Props) {
  const qc = useQueryClient();
  const markReviewed = useMutation({
    mutationFn: () => updatesApi.markReviewed(update.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["updates"] }),
  });

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const a = update.analysis;
  const safeUrl = (url: string) => url.startsWith("https://") || url.startsWith("http://") ? url : "#";

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "#00000080", zIndex: 50, display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "40px 20px", overflowY: "auto" }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: colors.bg, border: `1px solid ${colors.borderStrong}`, borderRadius: 12, width: "100%", maxWidth: 900, position: "relative" }}>

        {/* Header */}
        <div style={{ background: colors.surface, borderBottom: `1px solid ${colors.border}`, padding: "18px 24px", borderRadius: "12px 12px 0 0" }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10, alignItems: "center" }}>
            <RiskBadge level={update.risk_level} />
            <span style={{ background: colors.sidebarActive, color: colors.accent, fontSize: 11, padding: "2px 9px", borderRadius: 10 }}>{update.regulator}</span>
            <span style={{ background: colors.sidebarActive, color: colors.accent, fontSize: 11, padding: "2px 9px", borderRadius: 10 }}>{update.document_type}</span>
            <span style={{ color: colors.textMuted, fontSize: 11 }}>{update.date}</span>
            <button onClick={onClose} style={{ marginLeft: "auto", background: "none", border: "none", color: colors.textMuted, cursor: "pointer", fontSize: 18 }}>✕</button>
          </div>
          <div style={{ color: colors.textPrimary, fontSize: 17, fontWeight: 600, lineHeight: 1.4 }}>{update.title}</div>
        </div>

        {/* Body */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 0 }}>
          {/* Left: Analysis */}
          <div style={{ padding: "24px", borderRight: `1px solid ${colors.border}` }}>
            {a ? (
              <>
                <Section label="Summary">
                  {a.summary.split("\n\n").map((p, i) => (
                    <p key={i} style={{ color: "#c7d2fe", fontSize: 13.5, lineHeight: 1.75, marginBottom: i < a.summary.split("\n\n").length - 1 ? 14 : 0 }}>{p}</p>
                  ))}
                </Section>
                <Section label="Applicability">
                  <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderLeft: `3px solid ${colors.accent}`, borderRadius: 6, padding: 14 }}>
                    <p style={{ color: colors.textSecondary, fontSize: 13, lineHeight: 1.65 }}>{a.applicability}</p>
                  </div>
                </Section>
                <Section label="Conclusion">
                  <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderLeft: `3px solid ${colors.riskMedium}`, borderRadius: 6, padding: 14 }}>
                    <p style={{ color: colors.textPrimary, fontSize: 13, lineHeight: 1.65 }}>{a.conclusion}</p>
                  </div>
                </Section>
                {a.implementation.length > 0 && (
                  <Section label="Implementation & Changes Required">
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {a.implementation.map((s: ImplementationStep) => (
                        <div key={s.step} style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 6, padding: 12, display: "flex", gap: 12 }}>
                          <div style={{ background: colors.sidebarActive, color: colors.accent, borderRadius: 4, padding: "2px 7px", fontSize: 10, fontWeight: 700, flexShrink: 0, alignSelf: "flex-start", marginTop: 2 }}>{s.step}</div>
                          <div>
                            <div style={{ color: colors.textPrimary, fontSize: 13, fontWeight: 500 }}>{s.action}</div>
                            <div style={{ color: colors.textMuted, fontSize: 12, marginTop: 3 }}>{s.detail}</div>
                            <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                              <span style={{ background: colors.borderStrong, color: "#c7d2fe", fontSize: 10, padding: "2px 7px", borderRadius: 4 }}>{s.role}</span>
                              <span style={{ background: (URGENCY_COLOR[s.urgency] ?? colors.textMuted) + "22", color: URGENCY_COLOR[s.urgency] ?? colors.textMuted, fontSize: 10, padding: "2px 7px", borderRadius: 4 }}>{s.urgency}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Section>
                )}
              </>
            ) : (
              <p style={{ color: colors.textMuted }}>AI analysis not yet generated.</p>
            )}
          </div>

          {/* Right: Metadata */}
          <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
            <MetaCard title="Details">
              <MetaRow label="Regulator" value={update.regulator} />
              <MetaRow label="Type" value={update.document_type} />
              <MetaRow label="Published" value={update.date || "—"} />
              <MetaRow label="Status" value={update.status === "reviewed" ? "✓ Reviewed" : "⏳ Pending"} />
            </MetaCard>
            <MetaCard title="Documents">
              {update.pdf_url && (update.pdf_url.startsWith("https://") || update.pdf_url.startsWith("http://")) && (
                <a href={safeUrl(update.pdf_url)} target="_blank" rel="noreferrer" style={{ display: "flex", gap: 8, color: colors.accent, fontSize: 12, textDecoration: "none", padding: "8px 10px", background: colors.sidebarActive, borderRadius: 6, marginBottom: 6 }}>📄 Open PDF Circular</a>
              )}
              {update.page_url && update.page_url !== update.pdf_url && (update.page_url.startsWith("https://") || update.page_url.startsWith("http://")) && (
                <a href={safeUrl(update.page_url)} target="_blank" rel="noreferrer" style={{ display: "flex", gap: 8, color: colors.textSecondary, fontSize: 12, textDecoration: "none", padding: "8px 10px", background: colors.bg, borderRadius: 6 }}>🔗 Source Page</a>
              )}
            </MetaCard>
            <MetaCard title="Actions">
              {update.status === "unreviewed" && (
                <button onClick={() => markReviewed.mutate()} style={{ width: "100%", background: colors.sidebarActive, border: `1px solid ${colors.borderStrong}`, color: colors.accent, borderRadius: 6, padding: "8px 12px", fontSize: 12, cursor: "pointer", textAlign: "left" }}>
                  {markReviewed.isPending ? "Marking..." : "✓ Mark as Reviewed"}
                </button>
              )}
            </MetaCard>
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1.5, color: "#4338ca", fontWeight: 600, marginBottom: 10 }}>{label}</div>
      {children}
    </div>
  );
}
function MetaCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 8, padding: 14 }}>
      <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1, color: "#4338ca", marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );
}
function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ color: colors.textMuted, fontSize: 10 }}>{label}</div>
      <div style={{ color: colors.textPrimary, fontSize: 13 }}>{value}</div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/FilterPanel.tsx frontend/src/components/DetailModal.tsx
git commit -m "feat: FilterPanel + DetailModal with full AI analysis layout"
```

---

### Task 21: Dashboard Page (Complete) + Live Polling

**Files:**
- Create: `frontend/src/hooks/useUpdates.ts`
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Write `frontend/src/hooks/useUpdates.ts`**

```typescript
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { updatesApi } from "../api/client";
import { UpdatesResponse } from "../api/types";

interface Filters {
  regulator: string; document_type: string; risk_level: string; status: string; search: string;
}

export function useUpdates(filters: Filters) {
  return useQuery<UpdatesResponse>({
    queryKey: ["updates", filters],
    queryFn: () => updatesApi.list({
      regulator: filters.regulator || undefined,
      document_type: filters.document_type || undefined,
      risk_level: filters.risk_level || undefined,
      status: filters.status || undefined,
      search: filters.search || undefined,
    }).then((r) => r.data),
    refetchInterval: 60_000,
  });
}
```

- [ ] **Step 2: Write final `frontend/src/pages/DashboardPage.tsx`**

```tsx
import { useState } from "react";
import { useUpdates } from "../hooks/useUpdates";
import { MetricStrip } from "../components/MetricStrip";
import { UpdateCard } from "../components/UpdateCard";
import { FilterPanel } from "../components/FilterPanel";
import { DetailModal } from "../components/DetailModal";
import { RegulatoryUpdate } from "../api/types";
import { colors } from "../theme";
import { updatesApi } from "../api/client";
import { useQuery } from "@tanstack/react-query";

const DEFAULT_FILTERS = { regulator: "", document_type: "", risk_level: "", status: "", search: "" };

export function DashboardPage() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<RegulatoryUpdate | null>(null);
  const { data, isLoading } = useUpdates(filters);

  const openDetail = async (u: RegulatoryUpdate) => {
    const full = await updatesApi.get(u.id);
    setSelected(full.data);
  };

  const items = data?.items ?? [];
  const highRisk = items.filter((u) => u.risk_level === "High").length;
  const unreviewed = items.filter((u) => u.status === "unreviewed").length;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* Sidebar filters panel */}
      <div style={{ width: 220, borderRight: `1px solid ${colors.border}`, padding: "20px 14px", overflowY: "auto", flexShrink: 0 }}>
        <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1, color: colors.textMuted, marginBottom: 12 }}>Overview</div>
        <MetricStrip metrics={[
          { label: "Total", value: data?.total ?? 0 },
          { label: "High Risk", value: highRisk, color: colors.riskHigh },
          { label: "Unreviewed", value: unreviewed, color: colors.riskMedium },
        ]} />
        <FilterPanel filters={filters} onChange={setFilters} />
      </div>

      {/* Main feed */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px" }}>
        <h1 style={{ color: colors.textPrimary, fontSize: 20, fontWeight: 600, marginBottom: 20 }}>Compliance Updates</h1>
        {isLoading && <p style={{ color: colors.textMuted }}>Loading...</p>}
        {!isLoading && items.length === 0 && (
          <div style={{ border: `1px dashed ${colors.border}`, borderRadius: 8, padding: 28, color: colors.textMuted, textAlign: "center" }}>
            No updates match the current filters.
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {items.map((u) => <UpdateCard key={u.id} update={u} onClick={() => openDetail(u)} />)}
        </div>
      </div>

      {selected && <DetailModal update={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
```

- [ ] **Step 3: Open browser at http://localhost:5173, verify dashboard loads with real data from backend**

Start both services:
```bash
# Terminal 1
cd backend && uvicorn app.main:app --reload --port 8000
# Terminal 2
cd frontend && npm run dev
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useUpdates.ts frontend/src/pages/DashboardPage.tsx
git commit -m "feat: complete dashboard page — live feed, filters, metric strip, detail modal"
```

---

### Task 22: Admin Page

**Files:**
- Modify: `frontend/src/pages/AdminPage.tsx`

- [ ] **Step 1: Write final `frontend/src/pages/AdminPage.tsx`**

```tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, digestApi } from "../api/client";
import { colors } from "../theme";

const INPUT = { width: "100%", background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "9px 12px", color: colors.textPrimary, fontSize: 13, marginBottom: 10 } as const;
const BTN = { background: colors.accent, border: "none", borderRadius: 6, padding: "9px 16px", color: "#0a0a1a", fontWeight: 700, fontSize: 13, cursor: "pointer" } as const;

export function AdminPage() {
  const qc = useQueryClient();
  const { data: orgs = [] } = useQuery({ queryKey: ["orgs"], queryFn: () => adminApi.listOrgs().then((r) => r.data) });
  const { data: runs = [] } = useQuery({ queryKey: ["fetch-runs"], queryFn: () => adminApi.fetchRuns().then((r) => r.data) });
  const { data: digestSettings } = useQuery({ queryKey: ["digest-settings"], queryFn: () => digestApi.getSettings().then((r) => r.data) });

  const [orgForm, setOrgForm] = useState({ name: "", nbfc_type: "ICC", product_lines: "", aum_band: "", geographies: "", compliance_risk_areas: "" });
  const [userForm, setUserForm] = useState({ orgId: 0, email: "", password: "" });
  const [digestForm, setDigestForm] = useState({ recipients: digestSettings?.recipients ?? "", send_time_ist: digestSettings?.send_time_ist ?? "08:00" });

  const createOrg = useMutation({
    mutationFn: () => adminApi.createOrg(orgForm),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["orgs"] }); setOrgForm({ name: "", nbfc_type: "ICC", product_lines: "", aum_band: "", geographies: "", compliance_risk_areas: "" }); },
  });
  const createUser = useMutation({
    mutationFn: () => adminApi.createUser(userForm.orgId, { email: userForm.email, password: userForm.password }),
    onSuccess: () => setUserForm({ orgId: 0, email: "", password: "" }),
  });
  const triggerFetch = useMutation({
    mutationFn: () => adminApi.triggerFetch(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fetch-runs"] }),
  });
  const saveDigest = useMutation({
    mutationFn: () => digestApi.updateSettings(digestForm),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["digest-settings"] }),
  });

  return (
    <div style={{ padding: 32, maxWidth: 900, color: colors.textPrimary }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 28 }}>Admin Panel</h1>

      <Section title="Organisations">
        <div style={{ marginBottom: 20 }}>
          {orgs.map((o: any) => (
            <div key={o.id} style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "10px 14px", marginBottom: 8, display: "flex", justifyContent: "space-between" }}>
              <span>{o.name}</span><span style={{ color: colors.textMuted, fontSize: 12 }}>{o.nbfc_type}</span>
            </div>
          ))}
        </div>
        <h4 style={{ color: colors.textSecondary, marginBottom: 10 }}>Create Organisation</h4>
        <input style={INPUT} placeholder="Name" value={orgForm.name} onChange={(e) => setOrgForm({ ...orgForm, name: e.target.value })} />
        <select style={{ ...INPUT }} value={orgForm.nbfc_type} onChange={(e) => setOrgForm({ ...orgForm, nbfc_type: e.target.value })}>
          {["ICC", "MFI", "HFC", "P2P", "Account Aggregator", "Other"].map((t) => <option key={t}>{t}</option>)}
        </select>
        <input style={INPUT} placeholder="Product lines (e.g. Digital Lending, KYC)" value={orgForm.product_lines} onChange={(e) => setOrgForm({ ...orgForm, product_lines: e.target.value })} />
        <input style={INPUT} placeholder="AUM band" value={orgForm.aum_band} onChange={(e) => setOrgForm({ ...orgForm, aum_band: e.target.value })} />
        <input style={INPUT} placeholder="Geographies" value={orgForm.geographies} onChange={(e) => setOrgForm({ ...orgForm, geographies: e.target.value })} />
        <input style={INPUT} placeholder="Compliance risk areas" value={orgForm.compliance_risk_areas} onChange={(e) => setOrgForm({ ...orgForm, compliance_risk_areas: e.target.value })} />
        <button style={BTN} onClick={() => createOrg.mutate()}>{createOrg.isPending ? "Creating..." : "Create Organisation"}</button>
      </Section>

      <Section title="Create User for Org">
        <select style={{ ...INPUT }} value={userForm.orgId} onChange={(e) => setUserForm({ ...userForm, orgId: Number(e.target.value) })}>
          <option value={0}>Select org</option>
          {orgs.map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
        <input style={INPUT} placeholder="Email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} />
        <input style={INPUT} type="password" placeholder="Password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} />
        <button style={BTN} onClick={() => createUser.mutate()}>{createUser.isPending ? "Creating..." : "Create User"}</button>
      </Section>

      <Section title="Digest Settings">
        <label style={{ color: colors.textSecondary, fontSize: 12, display: "block", marginBottom: 4 }}>Recipients (comma-separated)</label>
        <input style={INPUT} placeholder="a@nbfc.com, b@nbfc.com" value={digestForm.recipients} onChange={(e) => setDigestForm({ ...digestForm, recipients: e.target.value })} />
        <label style={{ color: colors.textSecondary, fontSize: 12, display: "block", marginBottom: 4 }}>Send time (IST, HH:MM)</label>
        <input style={INPUT} placeholder="08:00" value={digestForm.send_time_ist} onChange={(e) => setDigestForm({ ...digestForm, send_time_ist: e.target.value })} />
        <button style={BTN} onClick={() => saveDigest.mutate()}>{saveDigest.isPending ? "Saving..." : "Save Digest Settings"}</button>
      </Section>

      <Section title="Data Fetch">
        <button style={BTN} onClick={() => triggerFetch.mutate()}>{triggerFetch.isPending ? "Fetching..." : "Trigger Manual Fetch Now"}</button>
        <div style={{ marginTop: 16 }}>
          {(runs as any[]).slice(0, 10).map((r: any) => (
            <div key={r.id} style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "8px 12px", marginBottom: 6, fontSize: 12, display: "flex", justifyContent: "space-between" }}>
              <span>{r.source}</span>
              <span style={{ color: r.error ? colors.riskHigh : colors.riskLow }}>{r.error || `${r.updates_found} found`}</span>
              <span style={{ color: colors.textMuted }}>{new Date(r.started_at).toLocaleString("en-IN")}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 22, marginBottom: 20 }}>
      <h3 style={{ color: colors.accent, fontSize: 14, fontWeight: 600, marginBottom: 16 }}>{title}</h3>
      {children}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AdminPage.tsx
git commit -m "feat: admin page — org creation, user setup, digest settings, manual fetch trigger"
```

---

## Phase 6 — Document Upload + Security + Docker

### Task 23: Org Document Upload

**Files:**
- Modify: `backend/app/routers/admin.py`

- [ ] **Step 1: Add document upload endpoint to `backend/app/routers/admin.py`**

Add this import and route:

```python
from fastapi import UploadFile, File

@router.post("/orgs/{org_id}/documents", status_code=201)
async def upload_org_document(
    org_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(404, "Org not found")
    existing_count = db.query(OrgDocument).filter_by(org_id=org_id).count()
    if existing_count >= 3:
        raise HTTPException(400, "Maximum 3 documents per organisation")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    from ..services.pdf import extract_pdf_text
    extracted = extract_pdf_text(content) if file.filename and file.filename.lower().endswith(".pdf") else content.decode("utf-8", errors="ignore")
    doc = OrgDocument(org_id=org_id, filename=file.filename or "upload", extracted_text=extracted[:50000])
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "filename": doc.filename, "chars_extracted": len(doc.extracted_text)}
```

Also add `OrgDocument` to the imports at the top of `admin.py`:
```python
from ..models import Organisation, User, FetchRun, OrgDocument
```

- [ ] **Step 2: Write test**

```python
# append to backend/tests/test_api_admin.py
import io

def test_upload_document(client, db):
    token = _superadmin(client, db)
    create_resp = client.post("/admin/orgs", json={"name": "DocTest NBFC", "nbfc_type": "ICC"},
                              headers={"Authorization": f"Bearer {token}"})
    org_id = create_resp.json()["id"]
    fake_pdf = b"%PDF-1.4 fake content for testing"
    resp = client.post(f"/admin/orgs/{org_id}/documents",
                       files={"file": ("test.pdf", io.BytesIO(fake_pdf), "application/pdf")},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["filename"] == "test.pdf"
```

- [ ] **Step 3: Run — expect PASS**

```bash
python -m pytest tests/test_api_admin.py::test_upload_document -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/admin.py backend/tests/test_api_admin.py
git commit -m "feat: org document upload endpoint (PDF/text, max 3 per org, 10MB limit)"
```

---

### Task 24: Security Hardening

**Files:**
- Modify: `backend/app/services/scraper.py` (URL validation already in `_is_safe_url`)
- Modify: `backend/app/routers/updates.py` (enforce safe URLs in serializer)

- [ ] **Step 1: Verify `_is_safe_url` is used in `scraper.py`**

Open `backend/app/services/scraper.py` and confirm `_detail_text` calls `_is_safe_url` before fetching. It should already — added in Task 9.

- [ ] **Step 2: Enforce safe URLs in the updates serializer**

In `backend/app/routers/updates.py`, update `_serialize` to sanitize URLs:

```python
def _safe_url(url: str) -> str:
    if url and (url.startswith("https://") or url.startswith("http://")):
        return url
    return ""

def _serialize(u: RegulatoryUpdate, include_analysis: bool = False) -> dict:
    base = {
        "id": u.id, "regulator": u.regulator, "source_type": u.source_type,
        "document_type": u.document_type, "title": u.title, "date": u.date,
        "page_url": _safe_url(u.page_url), "pdf_url": _safe_url(u.pdf_url),
        "status": u.status,
        "detected_at": u.detected_at.isoformat() if u.detected_at else None,
        "risk_level": u.analysis.risk_level if u.analysis else "Low",
        "applicability_short": (u.analysis.applicability[:120] + "...") if u.analysis and len(u.analysis.applicability) > 120 else (u.analysis.applicability if u.analysis else ""),
    }
    if include_analysis and u.analysis:
        base["analysis"] = {
            "summary": u.analysis.summary, "applicability": u.analysis.applicability,
            "conclusion": u.analysis.conclusion, "implementation": u.analysis.implementation_json,
            "risk_level": u.analysis.risk_level,
        }
    return base
```

- [ ] **Step 3: Write security test**

```python
# append to backend/tests/test_api_updates.py
def test_javascript_url_stripped_from_response(client, org_and_user, db):
    token, org_id = _login(client, org_and_user)
    u = RegulatoryUpdate(id="xsstest0000000001", org_id=org_id, regulator="RBI",
        source_type="Circulars", document_type="Circular", title="XSS Test",
        page_url="javascript:alert(1)", pdf_url="javascript:void(0)", status="unreviewed")
    db.add(u); db.commit()
    resp = client.get(f"/updates/{u.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["page_url"] == ""
    assert resp.json()["pdf_url"] == ""
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_api_updates.py::test_javascript_url_stripped_from_response -v
```

- [ ] **Step 5: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/updates.py backend/tests/test_api_updates.py
git commit -m "fix: strip non-http(s) URLs from API responses to prevent XSS"
```

---

### Task 25: Final Docker + Serve Frontend from FastAPI

**Files:**
- Modify: `docker-compose.yml`
- Create: `Dockerfile`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Build frontend static files**

```bash
cd frontend && npm run build
```

Expected: `backend/static/` directory created with `index.html` and assets.

- [ ] **Step 2: Serve static files from FastAPI — add to `backend/app/main.py`**

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        from fastapi.responses import FileResponse
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"error": "Frontend not built"}
```

Add `python-multipart` to `requirements.txt` (needed for file uploads):
```
python-multipart>=0.0.9
```

- [ ] **Step 3: Write `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY migrations/ ./migrations/

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Update `docker-compose.yml` to include the app**

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: regwatch
      POSTGRES_PASSWORD: regwatch
      POSTGRES_DB: regwatch
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://regwatch:regwatch@db:5432/regwatch
      OLLAMA_URL: http://ollama:11434
    env_file: .env
    depends_on:
      - db
      - ollama

volumes:
  pgdata:
  ollama_data:
```

- [ ] **Step 5: End-to-end smoke test**

```bash
docker compose up --build -d
# Wait 10s for containers to be healthy
docker compose exec -T db psql -U regwatch -d regwatch < migrations/001_initial.sql
```

Open http://localhost:8000 — should serve the RegWatch login page.

Create a test org and user via the API:
```bash
# Seed via API (requires a pre-existing user — seed directly in DB for smoke test)
docker compose exec -T db psql -U regwatch -d regwatch -c "
INSERT INTO organisations (name, nbfc_type) VALUES ('Smoke Test NBFC', 'ICC');
INSERT INTO users (org_id, email, password_hash) VALUES (1, 'admin@test.com', '\$2b\$12\$placeholder_run_hash_password_in_python');
"
```

Log in at http://localhost:8000/login.

- [ ] **Step 6: Final commit**

```bash
git add Dockerfile docker-compose.yml backend/app/main.py requirements.txt
git commit -m "feat: Dockerfile + docker-compose with app service, serve React SPA from FastAPI"
```

---

## Self-Review: Spec Coverage Check

| Spec Requirement | Task |
|---|---|
| Scrape RBI, SEBI, IRDAI, MCA | Tasks 7, 8, 9 |
| Configurable fetch schedule | Task 12 (scheduler) |
| Full PDF extraction, no page cap | Task 6 |
| Chunking for long docs | Tasks 6, 11 |
| 10MB file size cap | Tasks 6, 9 |
| Retry with exponential backoff | Task 9 |
| Per-org PostgreSQL storage | Tasks 2, 3, 9 |
| Deduplication by stable_id | Task 9 |
| AI: 5 structured output fields | Task 11 |
| AI: dynamic summary paragraphs | Task 11 (prompts) |
| AI: org-specific applicability | Task 11 (prompts) |
| AI: implementation steps with role + urgency | Tasks 11, 20 |
| AI: risk level (AI-inferred, not keyword) | Tasks 11, 14 |
| LLMProvider abstraction | Task 10 |
| Ollama default provider | Task 10 |
| Dashboard: sidebar + feed + modal layout | Tasks 18–21 |
| Slate + Indigo dark theme | Task 16 |
| MetricStrip: total, high risk, unreviewed | Task 19 |
| Filters: regulator, type, risk, status, search | Tasks 13, 20 |
| Detail modal: Summary → Applicability → Conclusion → Implementation | Task 20 |
| Mark as Reviewed | Tasks 13, 20 |
| URL validation (XSS fix) | Task 24 |
| Email digest: grouped by regulator | Task 15 |
| Email digest: HTML-escaped | Task 15 |
| Daily digest at configurable time | Tasks 12, 15 |
| Digest settings (recipients, time) | Task 15 |
| Org onboarding: profile questionnaire | Task 14 |
| Org document upload (max 3, 10MB) | Task 23 |
| Org docs fed into AI prompts | Task 11 |
| Single login per org (MVP) | Task 5 |
| Secure session-based auth | Tasks 4, 5 |
| Admin: create org, create user | Task 14 |
| Admin: manual fetch trigger | Task 14 |
| Admin: fetch run history | Task 14 |
| Multi-tenant data isolation | Task 13 (scoped queries) |
| Docker + PostgreSQL | Task 25 |

All spec requirements covered. ✓

