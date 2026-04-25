"""
api/index.py — Point d'entrée Vercel pour FastAPI
Vercel cherche automatiquement ce fichier comme handler WSGI/ASGI.
"""
import sys
import os

# Ajouter le répertoire racine au path pour que les imports backend fonctionnent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
