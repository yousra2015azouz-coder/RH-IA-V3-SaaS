"""
api/index.py — Point d'entrée Vercel avec diagnostic d'erreur d'import
"""
import sys
import os
import traceback

# Ajouter la racine du projet au path Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Essayer d'importer l'app complète
_import_error = None
try:
    from backend.main import app
except Exception as e:
    _import_error = {
        "error": str(e),
        "traceback": traceback.format_exc(),
        "python_path": sys.path[:5]
    }
    # App de fallback pour afficher l'erreur
    app = FastAPI()

    @app.get("/")
    async def show_error():
        return JSONResponse(status_code=500, content={
            "status": "IMPORT_ERROR",
            "message": "L'application backend a échoué à l'import.",
            "details": _import_error
        })

    @app.get("/health")
    async def health():
        return JSONResponse(status_code=500, content={"status": "error", "import_error": _import_error})
