"""
api/index.py — Point d'entrée Vercel MINIMAL pour diagnostic
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "OK", "message": "SaaS RH V3 - Vercel Python fonctionne !"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0"}
