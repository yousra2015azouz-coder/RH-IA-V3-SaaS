import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath('c:/Users/Session Youssef/Desktop/RH-IA V3'))
from backend.config import supabase_admin
from backend.events.handlers import on_employee_created

async def main():
    res = supabase_admin.table('employees').select('id, tenant_id, full_name').execute()
    employees = res.data or []
    count = 0
    for emp in employees:
        tasks_res = supabase_admin.table('onboarding_tasks').select('id').eq('employee_id', emp['id']).execute()
        if not tasks_res.data:
            print(f"Création des tâches pour {emp['full_name']}")
            await on_employee_created({
                'employee_id': emp['id'],
                'tenant_id': emp['tenant_id']
            })
            count += 1
    print(f"Tâches créées pour {count} employé(s).")

if __name__ == '__main__':
    asyncio.run(main())
