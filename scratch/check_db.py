import asyncio
from backend.config import supabase_admin, get_data

async def check():
    res = supabase_admin.table("candidates").select("email, ai_skills, ai_summary, birth_date").execute()
    print("DB Data:", get_data(res))

if __name__ == "__main__":
    asyncio.run(check())
