from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers import auth, updates, admin

STATIC_DIR = Path(__file__).parent.parent / "static"


def _seed_demo() -> None:
    """On a fresh DB, create the demo org + admin user. On existing DB, update the org profile."""
    import os
    from .database import SessionLocal
    from .models.org import Organisation, DigestSettings
    from .models.user import User
    from .auth.utils import hash_password

    demo_email = os.environ.get("DEMO_ADMIN_EMAIL", "demo@regwatch.app")
    demo_password = os.environ.get("DEMO_ADMIN_PASSWORD", "RegWatch2026")

    db = SessionLocal()
    try:
        org = db.query(Organisation).first()
        if not org:
            org = Organisation(
                name="Lendingkart Finance Limited",
                nbfc_type="NBFC-ICC",
                product_lines="MSME business loans, working capital finance, term loans, supply chain finance, digital lending",
                aum_band="₹5,000–10,000 Cr",
                geographies="Pan-India (30+ states), focus on Tier 2 & Tier 3 cities",
                compliance_risk_areas=(
                    "RBI Digital Lending Guidelines, KYC/AML/PMLA, Credit Bureau Reporting (CIBIL/CRIF), "
                    "Fair Practice Code, FLDG norms, Account Aggregator framework, "
                    "Co-lending regulations, MSME lending guidelines, Penal Charges circular"
                ),
            )
            db.add(org)
            db.flush()
            if not db.query(User).filter(User.email == demo_email).first():
                db.add(User(org_id=org.id, email=demo_email, password_hash=hash_password(demo_password)))
            db.add(DigestSettings(org_id=org.id))
            db.commit()
        else:
            # Keep org profile up to date on existing deployments
            org.name = "Lendingkart Finance Limited"
            org.nbfc_type = "NBFC-ICC"
            org.product_lines = "MSME business loans, working capital finance, term loans, supply chain finance, digital lending"
            org.aum_band = "₹5,000–10,000 Cr"
            org.geographies = "Pan-India (30+ states), focus on Tier 2 & Tier 3 cities"
            org.compliance_risk_areas = (
                "RBI Digital Lending Guidelines, KYC/AML/PMLA, Credit Bureau Reporting (CIBIL/CRIF), "
                "Fair Practice Code, FLDG norms, Account Aggregator framework, "
                "Co-lending regulations, MSME lending guidelines, Penal Charges circular"
            )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .database import engine, Base
    from . import models  # noqa: F401 — ensure all models are registered before create_all
    Base.metadata.create_all(bind=engine)
    from .services.scheduler import start_scheduler, stop_scheduler
    _seed_demo()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="RegWatch API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(updates.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve React SPA — must be after API routes
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        return FileResponse(str(STATIC_DIR / "index.html"))
