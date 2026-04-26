
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

email = "imane.benali.2121@gmail.com"

print(f"Tentative de suppression du compte : {email}")

try:
    # 1. Trouver l'utilisateur par email
    # Note: On cherche dans la table 'users' publique d'abord
    res = supabase.table("users").select("id").eq("email", email).execute()
    
    if res.data:
        user_id = res.data[0]["id"]
        print(f"ID utilisateur trouve : {user_id}")
        
        # 2. Supprimer de auth.users (via admin API si possible, ou via suppression de la table users si le cascade est configuré)
        # Dans Supabase, pour supprimer un utilisateur Auth, il faut utiliser l'API admin.auth
        # Mais si on supprime dans la table 'users' et qu'il y a un lien, cela nettoie le profil.
        # Pour supprimer carrement le compte AUTH :
        auth_res = supabase.auth.admin.delete_user(user_id)
        print(f"Compte Auth supprime pour {user_id}")
        
        print(f"Nettoyage complet termine pour {email}.")
    else:
        print(f"Aucun utilisateur trouve avec l'email {email} dans la table publique.")
        # Tentative via auth list si jamais il n'est pas dans 'users'
        auth_users = supabase.auth.admin.list_users()
        for u in auth_users:
            if u.email == email:
                supabase.auth.admin.delete_user(u.id)
                print(f"Utilisateur trouve uniquement dans Auth et supprime : {u.id}")
                break
except Exception as e:
    print(f"Erreur lors de la suppression : {str(e)}")
