"""
api/index.py — Point d'entrée Vercel pour SaaS RH V3
"""
import sys
import os
import traceback

# Ajouter la racine du projet au path Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# ⚠️ IMPORTANT: 'app' doit être déclaré au niveau racine pour Vercel
app = FastAPI(title="SaaS RH V3", version="3.0.0")

# Essayer de charger l'application complète
_import_error = None
try:
    from backend.main import app as _full_app
    app = _full_app
except Exception as e:
    _import_error = {
        "error": str(e),
        "type": type(e).__name__,
        "traceback": traceback.format_exc()
    }

    @app.get("/")
    async def show_error():
        return JSONResponse(status_code=500, content={
            "status": "IMPORT_ERROR",
            "details": _import_error
        })

    @app.get("/health")
    async def health_error():
        return JSONResponse(status_code=500, content={"status": "error", "details": _import_error})
