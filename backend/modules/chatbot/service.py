"""
modules/chatbot/service.py — Chatbot GROQ pré-qualification (5 questions)
"""
import json
import logging
from backend.modules.ai.groq_client import call_groq
from backend.config import supabase_admin, get_data

logger = logging.getLogger(__name__)

CHATBOT_SYSTEM = """Tu es un assistant RH bienveillant et professionnel.
Tu mènes un entretien de pré-qualification en posant exactement 5 questions séquentielles.
Questions à poser dans l'ordre :
1. Présentez-vous et expliquez votre motivation pour ce poste.
2. Quelle est votre expérience la plus pertinente par rapport à ce poste ?
3. Quelles sont vos principales compétences techniques ?
4. Quelles sont vos prétentions salariales et quel est votre salaire actuel (pour étude de package) ?
5. Quelle est votre situation familiale (marié/célibataire, enfants) et votre disponibilité ?

Règles :
- Pose UNE seule question à la fois
- Sois chaleureux, professionnel et encourageant
- Maximum 100 mots par réponse
- Important : Collecte les infos sur la situation familiale et le salaire actuel de manière fluide.
- Après la 5ème réponse, conclus poliment et dis que l'entretien est terminé"""


async def get_chatbot_response(
    session_id: str,
    candidate_message: str,
    conversation_history: list,
    company_name: str = "Notre Entreprise"
) -> dict:
    """Génère une réponse chatbot et détermine si la session est complète."""
    system = CHATBOT_SYSTEM.replace("Notre Entreprise", company_name)
    messages = [{"role": "system", "content": system}]

    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": candidate_message})

    from backend.config import groq_client, GROQ_MODEL_MAIN
    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL_MAIN,
        messages=messages,
        temperature=0.7,
        max_tokens=400
    )
    response_text = completion.choices[0].message.content

    # Compter les échanges pour détecter la fin (5 questions)
    user_messages = [m for m in conversation_history if m.get("role") == "user"]
    question_count = len(user_messages) + 1
    is_completed = question_count >= 5

    return {
        "response": response_text,
        "is_completed": is_completed,
        "question_number": question_count
    }


async def score_chatbot_session(session_id: str) -> dict:
    """Score la session chatbot complète via GROQ."""
    res = supabase_admin.table("chatbot_sessions").select("*").eq("id", session_id).execute()
    sessions = get_data(res) or []
    if not sessions:
        return {}
    session = sessions[0]
    messages = session.get("messages", [])

    system = """Analyse cette conversation de pré-qualification RH.
    Évalue le candidat et retourne UNIQUEMENT un JSON:
    {
      "score": 0,
      "communication": 0,
      "motivation": 0,
      "competences": 0,
      "professionnalisme": 0,
      "current_salary": "montant",
      "marital_status": "Célibataire/Marié",
      "children_count": 0,
      "resume": "résumé de l'évaluation",
      "decision": "PROCEED ou REJECT"
    }
    Chaque sous-critère est sur 25. Score total sur 100."""

    raw = await call_groq(
        system_prompt=system,
        user_content=f"Conversation:\n{json.dumps(messages, ensure_ascii=False)}",
        temperature=0.2,
        max_tokens=800,
        json_mode=True
    )
    try:
        result = json.loads(raw)
        supabase_admin.table("chatbot_sessions").update({
            "qualification_score": result.get("score", 0),
            "groq_analysis": result,
            "is_completed": True
        }).eq("id", session_id).execute()

        # Update candidate table with extracted data (Filtered for DB compatibility)
        cand_update = {
            "situation_familiale": result.get("marital_status"),
            "personnes_a_charge": result.get("children_count", 0)
        }
        # current_salary n'est pas encore en base, on peut le mettre dans ai_summary
        if result.get("current_salary"):
            cand_update["ai_summary"] = f"Salaire actuel: {result.get('current_salary')}. " + (session.get("groq_analysis", {}).get("resume", ""))

        supabase_admin.table("candidates").update(cand_update).eq("id", session.get("candidate_id")).execute()
        
        return result
    except Exception:
        return {}
