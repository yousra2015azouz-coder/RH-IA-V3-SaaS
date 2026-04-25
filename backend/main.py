"""
main.py — SaaS RH V3 API Gateway
"""
import logging
import traceback
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import os

from backend.config import PLATFORM_NAME, CORS_ORIGINS, supabase_admin
from backend.auth.dependencies import resolve_user_from_token
from backend.events.handlers import register_all_handlers
from backend.jobs.scheduler import start_scheduler
from backend.modules.error_tracker.service import log_error

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title=f"{PLATFORM_NAME} — API V3",
    description="Plateforme SaaS RH Multi-Tenant avec IA GROQ (Llama3 & Mixtral)",
    version="3.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En production, restreindre via CORS_ORIGINS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MIDDLEWARE: Auth & Tenant ──────────────────────────────
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip auth for public routes
    public_paths = [
        "/api/v1/auth/login", 
        "/api/v1/auth/signup", 
        "/api/v1/auth/setup-superadmin",
        "/api/v1/jobs/public", 
        "/api/v1/recruitment/jobs", 
        "/api/v1/chatbot",
        "/api/v1/branding",
        "/docs", 
        "/openapi.json", 
        "/static", 
        "/health",
        "/index.html",
        "/job-detail.html",
        "/apply.html",
        "/generated_docs"
    ]
    is_public = (
        any(request.url.path.startswith(p) for p in public_paths) or 
        request.url.path == "/" or 
        request.url.path.endswith(".html") or
        (request.url.path.startswith("/api/v1/jobs") and request.url.path.endswith("/apply"))
    )

    if not is_public:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Token manquant"})
        
        token = auth_header.split(" ")[1]
        try:
            user = await resolve_user_from_token(token)
            request.state.user = user
        except Exception as e:
            return JSONResponse(status_code=401, content={"detail": str(e)})
    
    response = await call_next(request)
    return response

# ── GLOBAL EXCEPTION HANDLER ──────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    user_id = getattr(request.state, "user", {}).get("id")
    tenant_id = getattr(request.state, "user", {}).get("tenant_id")
    
    await log_error(
        message=str(exc),
        module="global",
        endpoint=str(request.url),
        traceback=traceback.format_exc(),
        user_id=user_id,
        tenant_id=tenant_id,
        request_data={"method": request.method}
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne serveur", "error": str(exc)}
    )

# ── ROUTERS ────────────────────────────────────────────────
from backend.auth.router import router as auth_router
from backend.modules.recruitment.router import router as recruit_router
from backend.modules.chatbot.router import router as chatbot_router
from backend.modules.evaluation.router import router as eval_router
from backend.modules.approval.router import router as approval_router
from backend.modules.onboarding.router import router as onboarding_router
from backend.modules.talent.router import router as talent_router
from backend.modules.turnover.router import router as turnover_router
from backend.modules.documents.router import router as documents_router
from backend.modules.branding.router import router as branding_router
from backend.modules.error_tracker.router import router as error_router

app.include_router(auth_router)
app.include_router(recruit_router, prefix="/api/v1")
app.include_router(chatbot_router, prefix="/api/v1")
app.include_router(eval_router, prefix="/api/v1")
app.include_router(approval_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(talent_router, prefix="/api/v1")
app.include_router(turnover_router, prefix="/api/v1")
app.include_router(branding_router, prefix="/api/v1")
app.include_router(error_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")

# ── STATIC FILES & FRONTEND ────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Liste des chemins possibles pour le frontend
possible_frontend_paths = [
    os.path.join(BASE_DIR, "frontend"),
    os.path.join(os.getcwd(), "frontend"),
    "/var/task/frontend"
]

frontend_dir = possible_frontend_paths[0]
for p in possible_frontend_paths:
    if os.path.exists(p):
        frontend_dir = p
        break

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Documents générés — /tmp sur Vercel
IS_VERCEL = os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV")
docs_dir = "/tmp/generated_docs" if IS_VERCEL else os.path.join(BASE_DIR, "backend", "static", "documents")
os.makedirs(docs_dir, exist_ok=True)
app.mount("/generated_docs", StaticFiles(directory=docs_dir), name="generated_docs")

@app.get("/")
async def serve_index():
    # Chercher index.html dans public ou à la racine du frontend
    paths = [
        os.path.join(frontend_dir, "public", "index.html"),
        os.path.join(frontend_dir, "index.html")
    ]
    for p in paths:
        if os.path.exists(p):
            return FileResponse(p)
    
    # Debug : Lister TOUS les fichiers (jusqu'à 100) pour être sûr
    files_found = []
    try:
        for root, dirs, files in os.walk(frontend_dir):
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), frontend_dir).replace("\\", "/")
                files_found.append(rel_path)
    except:
        pass

    return {
        "message": "SaaS RH V3 en ligne — Frontend introuvable",
        "debug": {
            "cwd": os.getcwd(),
            "frontend_dir": frontend_dir,
            "files_total": len(files_found),
            "files_in_frontend": sorted(files_found)[:100]
        }
    }




@app.get("/{filename}.html")
async def serve_html(filename: str):
    path = os.path.join(frontend_dir, "public", f"{filename}.html")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(status_code=404, content={"detail": "Fichier non trouvé"})

# ── LIFECYCLE ──────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    try:
        register_all_handlers()
        logger.info("[EventBus] Handlers enregistrés.")
    except Exception as e:
        logger.warning(f"[EventBus] Erreur init handlers: {e}")

    # APScheduler incompatible avec Vercel serverless — désactivé en prod
    is_vercel = os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV")
    if not is_vercel:
        try:
            start_scheduler()
            logger.info("[Scheduler] Démarré en mode local.")
        except Exception as e:
            logger.warning(f"[Scheduler] Erreur démarrage: {e}")
    else:
        logger.info("[Scheduler] Désactivé (mode Vercel serverless).")

    logger.info("SaaS RH V3 démarré avec succès.")

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
