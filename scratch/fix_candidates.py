import asyncio
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath("c:/Users/Session Youssef/Desktop/RH-IA V3"))

from backend.config import supabase_admin
from backend.events.handlers import on_approval_completed

async def fix_stuck_candidates():
    # Find all approved requests
    res = supabase_admin.table('approval_requests').select('*').eq('status', 'approved').execute()
    approvals = res.data or []
    
    fixed_count = 0
    for app in approvals:
        candidate_id = app['candidate_id']
        
        # Check if they are already in the employees table
        emp_res = supabase_admin.table('employees').select('id').eq('candidate_id', candidate_id).execute()
        if not emp_res.data:
            print(f"Correction du candidat : {app.get('nom_collaborateur', candidate_id)}")
            await on_approval_completed({
                'candidate_id': candidate_id,
                'approval_id': app['id'],
                'tenant_id': app['tenant_id']
            })
            fixed_count += 1
            
    print(f"Terminé. {fixed_count} candidat(s) corrigé(s).")

if __name__ == '__main__':
    asyncio.run(fix_stuck_candidates())
