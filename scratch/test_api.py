import asyncio
import httpx
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from supabase import create_client

async def test_api():
    # 1. Login with the user to get token
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    auth_resp = client.auth.sign_in_with_password({
        "email": "boumyouness620@gmail.com",
        "password": "password123" # assuming password used by user
    })
    token = auth_resp.session.access_token

    # 2. Call /api/v1/candidate/profile
    async with httpx.AsyncClient() as http_client:
        res = await http_client.get(
            "http://127.0.0.1:8000/api/v1/candidate/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = res.json()
        print("API Response:", data)

if __name__ == "__main__":
    asyncio.run(test_api())
