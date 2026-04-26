import asyncio
import json
from datetime import datetime
from backend.config import supabase_admin
from backend.utils.pdf_generator import generate_approval_pdf
from backend.modules.documents.service import document_service

async def force_regenerate_pdf(candidate_name):
    print(f"Regénération forcée pour {candidate_name}...")
    res = supabase_admin.table("approval_requests").select("*").eq("nom_collaborateur", candidate_name).execute()
    if not res.data:
        print("Dossier non trouvé.")
        return
    
    approval = res.data[0]
    
    # Récupérer les noms depuis groq_recommendation (JSON)
    try:
        meta = json.loads(approval.get("groq_recommendation", "{}"))
    except:
        meta = {}

    def get_sig(role):
        db_key = f"signed_{role}_at"
        val = approval.get(db_key)
        if not val: return {"signed": False, "name": "", "date": ""}
        # Si c'est l'ancien format avec |, on le nettoie
        if " | " in val:
            parts = val.split(" | ")
            return {"signed": True, "date": parts[0], "name": parts[1]}
        return {
            "signed": True,
            "date": val[:16].replace('T', ' ') + 'Z',
            "name": meta.get(f"{role}_name", "Directeur")
        }

    sigs = {
        "hierarchic": get_sig("hierarchique"),
        "functional": get_sig("fonctionnel"),
        "hr": get_sig("rh"),
        "dg": get_sig("dg")
    }

    pdf_data = {
        "nom_collaborateur": approval["nom_collaborateur"],
        "job_title": "Responsable SAV & Support Technique",
        "date_embauche": approval["date_embauche"],
        "salaire_base": approval["salaire_base"],
        "salaire_mensuel_net": approval["salaire_mensuel_net"],
        "signatures": sigs
    }

    pdf_bytes = generate_approval_pdf(pdf_data)
    doc_url = await document_service.upload_document(pdf_bytes, f"approbation_{approval['candidate_id']}.pdf", "application/pdf")
    
    # Mettre à jour Document
    supabase_admin.table("documents").update({"file_url": doc_url}).eq("candidate_id", approval["candidate_id"]).eq("type", "approval_request").execute()
    print(f"✅ PDF régénéré avec succès : {doc_url}")

if __name__ == "__main__":
    asyncio.run(force_regenerate_pdf("Imane Benali"))
