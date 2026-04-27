"""
modules/chatbot/router.py — Endpoints chatbot candidat
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from backend.config import supabase_admin, get_data
from backend.modules.chatbot.service import get_chatbot_response, score_chatbot_session
from backend.events.bus import event_bus

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


class ChatMessage(BaseModel):
    message: str
    session_id: str = None


@router.post("/session/{candidate_id}")
async def start_session(candidate_id: str):
    """Démarre une session chatbot pour un candidat."""
    # Vérifier si session existante
    existing = supabase_admin.table("chatbot_sessions").select("id").eq(
        "candidate_id", candidate_id).eq("is_completed", False).execute()
    if existing.data:
        return {"session_id": existing.data[0]["id"], "existing": True}

    # Récupérer tenant_id depuis le candidat
    cand_res = supabase_admin.table("candidates").select("tenant_id, job_offer_id").eq(
        "id", candidate_id).execute()
    cands = get_data(cand_res) or []
    if not cands:
        raise HTTPException(404, "Candidat non trouvé")

    session_res = supabase_admin.table("chatbot_sessions").insert({
        "candidate_id": candidate_id,
        "tenant_id": cands[0]["tenant_id"],
        "messages": [],
        "is_completed": False
    }).execute()

    # Mettre à jour le stage du candidat
    supabase_admin.table("candidates").update({
        "pipeline_stage": "chatbot"
    }).eq("id", candidate_id).execute()

    session = get_data(session_res)
    return {"session_id": session[0]["id"] if session else None}


@router.post("/message")
async def send_message(body: ChatMessage):
    """Envoie un message et reçoit la réponse du chatbot."""
    if not body.session_id:
        raise HTTPException(400, "session_id requis")

    # Récupérer la session
    sess_res = supabase_admin.table("chatbot_sessions").select("*").eq(
        "id", body.session_id).execute()
    sessions = get_data(sess_res) or []
    if not sessions:
        raise HTTPException(404, "Session non trouvée")
    session = sessions[0]

    if session.get("is_completed"):
        raise HTTPException(400, "Session déjà terminée")

    # Récupérer nom tenant
    tenant_res = supabase_admin.table("tenants").select("name").eq(
        "id", session["tenant_id"]).execute()
    tenants = get_data(tenant_res) or []
    company_name = tenants[0]["name"] if tenants else "Notre Entreprise"

    history = session.get("messages", [])
    result = await get_chatbot_response(
        session_id=body.session_id,
        candidate_message=body.message,
        conversation_history=history,
        company_name=company_name
    )

    # Sauvegarder messages
    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": result["response"]})

    update_data = {"messages": history}
    if result["is_completed"]:
        score = await score_chatbot_session(body.session_id)
        update_data["is_completed"] = True
        # Sauvegarde AVANT le publish pour garantir la cohérence
        supabase_admin.table("chatbot_sessions").update(update_data).eq(
            "id", body.session_id).execute()
        
        await event_bus.publish("chatbot_completed", {
            "candidate_id": session["candidate_id"],
            "score": score.get("score", 0)
        }, session["tenant_id"])
    else:
        supabase_admin.table("chatbot_sessions").update(update_data).eq(
            "id", body.session_id).execute()

    return {
        "response": result["response"],
        "is_completed": result["is_completed"],
        "question_number": result["question_number"]
    }
