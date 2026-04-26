
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY") # Utilisation de la clé service pour bypasser les RLS
supabase: Client = create_client(url, key)

# Liste exhaustive dans l'ordre de dependance (Enfant -> Parent)
tables = [
    "onboarding_tasks",
    "talent_matrix",
    "turnover_risks",
    "employees",
    "chatbot_sessions",
    "evaluations",
    "documents",
    "approval_requests",
    "candidates",
    "job_offers"
]

print("Demarrage du nettoyage SQL force...")

for table in tables:
    try:
        # On utilise une requete qui cible tout le monde sans exception
        supabase.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        # On insiste avec un deuxieme filtre au cas ou
        supabase.table(table).delete().not_.is_("id", "null").execute()
        print(f"Table '{table}' videe.")
    except Exception as e:
        print(f"Echec partiel sur {table}, mais on continue...")

print("\nNettoyage termine.")
