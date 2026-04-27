import asyncio
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

async def main():
    # 1. Obtenir le candidat
    res = supabase.table('candidates').select('*').eq('email', 'boumyouness620@gmail.com').execute()
    if not res.data:
        print('Candidat non trouve')
        return
    cand = res.data[0]
    
    # 2. Obtenir l'offre
    job_res = supabase.table('job_offers').select('requirements').eq('id', cand['job_offer_id']).execute()
    req = job_res.data[0]['requirements'] if job_res.data else ''
    
    # 3. Lancer le process
    from backend.modules.recruitment.service import process_cv_and_score
    print(f"Lancement du scoring pour {cand['id']}...")
    try:
        await process_cv_and_score(cand['id'], cand['tenant_id'], cand['cv_text'], req)
        print('Scoring termine avec succes!')
    except Exception as e:
        print(f'Erreur: {e}')

asyncio.run(main())
