import asyncio
from backend.modules.candidate.service import parse_cv_for_profile

cv_text = """
## Youness BOUM
**Développeur Full-Stack Senior**
Email : boumyouness620@gmail.com
Téléphone : +212 6 00 00 00 00
Date de Naissance : 15/06/1996
Ville : Casablanca
Situation Familiale : Célibataire

### EXPÉRIENCES PROFESSIONNELLES

**TechSolutions | Casablanca (2021 - 2024)**
- Lead Developer sur un projet SaaS de gestion d'entreprise.
- Architecture Backend : Migration vers FastAPI pour des performances asynchrones.
- Base de données : Gestion de clusters PostgreSQL et intégration Supabase.
- IA : Mise en place d'un moteur de recommandation basé sur l'API Groq.

### COMPÉTENCES
- Python, FastAPI, React, PostgreSQL
"""

async def main():
    result = await parse_cv_for_profile(cv_text)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
