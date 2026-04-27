import asyncio
import os
import sys
import json
from decimal import Decimal

# Ajouter le chemin du projet au PYTHONPATH
sys.path.append(os.getcwd())

from backend.config import supabase_admin, get_data
from backend.modules.documents.service import document_service

async def force_regen():
    candidate_id = "68526e6e-0499-4332-9551-04336c887819"
    tenant_id = "a0000000-0000-0000-0000-000000000001" # Default tenant from metadata usually
    
    print(f"--- Régénération des documents pour Imane ({candidate_id}) ---")
    
    # 1. Régénérer Doc 5.1 (Compte Rendu)
    # On va simuler ou chercher l'évaluation
    eval_res = supabase_admin.table("evaluations").select("*").eq("candidate_id", candidate_id).execute()
    eval_data = eval_res.data[0] if eval_res.data else {
        "score_final": 92,
        "remarques": "Candidature excellente. Imane démontre une maîtrise parfaite du SAV technique et du g\u00e9nie m\u00e9canique.",
        "details_score": {
            "Technique": {"score": 95, "comment": "Expertise EMI irr\u00e9prochable"},
            "Communication": {"score": 88, "comment": "Tr\u00e8s fluide en 3 langues"},
            "Management": {"score": 92, "comment": "Exp\u00e9rience solide de pilotage"}
        }
    }
    
    print("Génération Doc 5.1...")
    url_51 = await document_service.generate_and_store_interview_report(candidate_id, eval_data, tenant_id)
    print(f"Nouveau URL 5.1: {url_51}")
    
    # Mettre à jour l'entrée existante dans 'documents' pour le type INTERVIEW_REPORT
    supabase_admin.table("documents").update({"file_url": url_51}).eq("candidate_id", candidate_id).eq("type", "INTERVIEW_REPORT").execute()

    # 2. Régénérer Doc 5.2 (Demande d'Approbation)
    # Chercher l'ID de la demande d'approbation
    app_res = supabase_admin.table("approval_requests").select("id").eq("candidate_id", candidate_id).execute()
    if app_res.data:
        app_id = app_res.data[0]["id"]
        print(f"Génération Doc 5.2 pour approval_id: {app_id}...")
        url_52 = await document_service.generate_and_store_approval_pdf(app_id, tenant_id)
        print(f"Nouveau URL 5.2: {url_52}")
        
        # Mettre à jour l'entrée existante dans 'documents' pour le type approval_request (ou APPROVAL_FORM)
        supabase_admin.table("documents").update({"file_url": url_52}).eq("candidate_id", candidate_id).eq("type", "approval_request").execute()
    else:
        print("Pas de demande d'approbation trouvée pour Imane.")

    print("--- Terminé ---")

if __name__ == "__main__":
    asyncio.run(force_regen())
