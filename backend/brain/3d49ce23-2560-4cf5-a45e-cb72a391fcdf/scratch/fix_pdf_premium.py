import asyncio
import os
import sys

# Ajouter le répertoire courant au path pour l'import des modules backend
sys.path.append(os.getcwd())

from backend.modules.documents.service import document_service
from backend.config import supabase_admin, get_data
from backend.utils.pdf_generator import generate_approval_pdf

async def fix():
    print("Recherche du candidat BAQECHAM...")
    res = supabase_admin.table('candidates').select('*, job_offers(*)').eq('last_name', 'BAQECHAM').execute()
    data = get_data(res)
    if not data:
        print("Candidat non trouvé")
        return
    
    cand = data[0]
    cand_id = cand['id']
    tenant_id = cand['tenant_id']
    
    print(f"Candidat trouvé : {cand['first_name']} {cand['last_name']}")
    
    # 1. Rechercher la demande d'approbation
    app_res = supabase_admin.table('approval_requests').select('*').eq('candidate_id', cand_id).execute()
    apps = get_data(app_res)
    if not apps:
        print("Aucune demande d'approbation trouvée pour ce candidat")
        return
    
    app = apps[0]
    app_id = app['id']
    
    # 2. Préparer les données pour le nouveau template
    full_data = app.copy()
    full_data.update({
        'date_naissance': cand.get('birth_date', '07/08/1999'),
        'personnes_a_charge': cand.get('personnes_a_charge', 0),
        'situation_familiale': cand.get('situation_familiale', 'Célibataire'),
        'site': cand['job_offers'].get('site', 'Siège'),
        'entity': cand['job_offers'].get('entity_organisationnelle', 'Service Après Vente VP'),
        'job_title': cand['job_offers'].get('title', 'Responsable Assistance Technique'),
        'ref_job': 'E12.10 - Responsable Support Technique',
        'is_budgeted': cand['job_offers'].get('is_budgeted', True),
        'comments': 'Recrutement pour renforcement de l\'équipe SAV. Profil hautement qualifié.'
    })
    
    print("Génération du PDF avec le nouveau design local...")
    pdf_bytes = generate_approval_pdf(full_data)
    
    # 3. Upload local via le service mis à jour
    file_name = f"approbation_premium_{app_id}.pdf"
    url = await document_service.upload_document(pdf_bytes, file_name)
    
    # 4. Mettre à jour les références en base
    supabase_admin.table('approval_requests').update({'pdf_url': url}).eq('id', app_id).execute()
    
    # Mettre à jour aussi dans la table documents si elle existe
    try:
        supabase_admin.table('documents').update({'file_url': url}).eq('approval_request_id', app_id).execute()
    except:
        pass
    
    print(f"Terminé ! Nouveau PDF disponible ici : {url}")

if __name__ == "__main__":
    asyncio.run(fix())
