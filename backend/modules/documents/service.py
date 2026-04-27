"""
modules/documents/service.py — Gestion des documents et upload Supabase
"""
import logging
import uuid
from backend.config import supabase_admin, get_data
from backend.modules.error_tracker.service import log_error

logger = logging.getLogger(__name__)

class DocumentService:
    async def upload_document(self, file_bytes: bytes, file_name: str, content_type: str = "application/pdf") -> str:
        """Sauvegarde le fichier localement (dev) ou sur Supabase (Vercel/Prod)."""
        import os
        from backend.config import supabase_admin
        
        is_prod = os.environ.get("VERCEL") or os.environ.get("PRODUCTION")
        
        if not is_prod:
            try:
                # Stockage Local (Développement)
                save_dir = "backend/static/documents"
                os.makedirs(save_dir, exist_ok=True)
                file_path_local = f"{uuid.uuid4().hex[:8]}_{file_name}"
                full_path = os.path.join(save_dir, file_path_local)
                with open(full_path, "wb") as f:
                    f.write(file_bytes)
                return f"http://localhost:8000/generated_docs/{file_path_local}"
            except Exception as e:
                logger.error(f"Erreur sauvegarde locale: {str(e)}")
                # Si erreur locale, on tente quand même Supabase en fallback
                pass

        # Stockage Cloud (Supabase)
        try:
            file_path_cloud = f"generated/{uuid.uuid4().hex[:8]}_{file_name}"
            # Utiliser le bucket 'documents' (Assurez-vous qu'il est créé dans Supabase)
            res = supabase_admin.storage.from_("documents").upload(
                path=file_path_cloud,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            return supabase_admin.storage.from_("documents").get_public_url(file_path_cloud)
        except Exception as e:
            logger.error(f"Erreur Supabase Storage: {str(e)}")
            raise e

    async def generate_and_store_approval_pdf(self, approval_id: str, tenant_id: str) -> str | None:
        """Génère le PDF d'approbation et l'upload sur Supabase Storage."""
        from backend.utils.pdf_generator import generate_approval_pdf
        try:
            res = supabase_admin.table("approval_requests").select("*, job_offers(*), candidates(*)").eq("id", approval_id).execute()
            data_list = get_data(res) or []
            if not data_list: return None
            
            approval_data = data_list[0]
            # Mapper les données candidat à la racine pour plus de facilité dans le template
            if approval_data.get("candidates"):
                cand = approval_data["candidates"]
                approval_data["date_naissance"] = cand.get("birth_date") or cand.get("date_naissance")
                approval_data["email"] = cand.get("email")
                if not approval_data.get("situation_familiale"):
                    approval_data["situation_familiale"] = cand.get("family_status")
            
            pdf_bytes = generate_approval_pdf(approval_data)

            url = await self.upload_document(pdf_bytes, f"approbation_{approval_id}.pdf")
            
            # Enregistrement dans la table documents
            supabase_admin.table("documents").insert({
                "tenant_id": tenant_id,
                "approval_request_id": approval_id,
                "type": "APPROVAL_FORM",
                "file_url": url
            }).execute()

            # Mise à jour de la demande pour compatibilité rapide UI
            supabase_admin.table("approval_requests").update({"pdf_url": url}).eq("id", approval_id).execute()
            
            return url
        except Exception as e:
            import traceback
            logger.error(f"Erreur PDF Approval: {str(e)}\n{traceback.format_exc()}")
            await log_error(module="documents", message=str(e), tenant_id=tenant_id)
            return None

    async def generate_and_store_interview_report(self, candidate_id: str, evaluation_data: dict, tenant_id: str) -> str | None:
        """Génère le PDF du compte rendu d'entretien (Doc 5.1) et l'upload."""
        from backend.utils.pdf_generator import generate_interview_report
        try:
            # Récupérer infos candidat
            res = supabase_admin.table("candidates").select("*, job_offers(*)").eq("id", candidate_id).execute()
            data_list = get_data(res) or []
            if not data_list: return None
            
            cand = data_list[0]
            report_data = {
                "candidate_name": f"{cand['first_name']} {cand['last_name']}",
                "job_title": cand["job_offers"]["title"] if cand.get("job_offers") else "N/A",
                "date": evaluation_data.get("created_at", "Aujourd'hui"),
                "global_score": evaluation_data.get("score_final", 0),
                "final_opinion": "Favorable" if evaluation_data.get("score_final", 0) >= 70 else "À revoir",
                "comments": evaluation_data.get("remarques", ""),
                "criteria": evaluation_data.get("details_score", {})
            }
            
            pdf_bytes = generate_interview_report(report_data)
            url = await self.upload_document(pdf_bytes, f"compte_rendu_{candidate_id}.pdf")
            
            # Enregistrement dans la table documents
            supabase_admin.table("documents").insert({
                "tenant_id": tenant_id,
                "candidate_id": candidate_id,
                "type": "INTERVIEW_REPORT",
                "file_url": url
            }).execute()
            
            return url
        except Exception as e:
            await log_error(module="documents", message=f"Doc 5.1 error: {str(e)}", tenant_id=tenant_id)
            return None

document_service = DocumentService()
