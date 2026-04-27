import asyncio
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Erreur: Variables d'environnement Supabase manquantes (URL ou SERVICE_ROLE_KEY).")
    exit(1)

# Client avec Service Role Key pour bypasser les sécurités
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

async def cleanup_test_user(email: str):
    print(f"Nettoyage complet du candidat : {email}...")
    
    try:
        # 1. Trouver l'utilisateur dans Auth
        users_res = supabase.auth.admin.list_users()
        target_user = next((u for u in users_res if u.email == email), None)
        
        if target_user:
            user_id = target_user.id
            print(f"Utilisateur trouvé ID: {user_id}")
            
            # Trouver l'ID candidat lié
            cand_res = supabase.table("candidates").select("id").eq("user_id", user_id).execute()
            candidate_ids = [c["id"] for c in cand_res.data] if cand_res.data else []
            
            # 2. Supprimer les dépendances du candidat
            for c_id in candidate_ids:
                supabase.table("chatbot_sessions").delete().eq("candidate_id", c_id).execute()
                supabase.table("evaluations").delete().eq("candidate_id", c_id).execute()
                supabase.table("approval_requests").delete().eq("candidate_id", c_id).execute()
                supabase.table("documents").delete().eq("candidate_id", c_id).execute()
                print(f"Dépendances pour le candidat {c_id} supprimées.")

            # 3. Supprimer les dépendances de l'utilisateur
            supabase.table("notifications").delete().eq("user_id", user_id).execute()
            supabase.table("audit_logs").delete().eq("user_id", user_id).execute()
            print("Dépendances de l'utilisateur supprimées.")

            # 4. Supprimer le candidat et l'utilisateur
            supabase.table("candidates").delete().eq("user_id", user_id).execute()
            supabase.table("users").delete().eq("id", user_id).execute()
            print("Candidat et Profil User supprimés.")
            
            # 5. Supprimer de Auth en dernier
            supabase.auth.admin.delete_user(user_id)
            print(f"Utilisateur {email} supprimé de Auth.")
            
        else:
            print(f"Utilisateur {email} non trouvé dans Auth.")

    except Exception as e:
        print(f"Erreur globale : {e}")

    print("Nettoyage terminé.")

if __name__ == "__main__":
    asyncio.run(cleanup_test_user("boumyouness620@gmail.com"))
