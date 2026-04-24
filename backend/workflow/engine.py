"""
workflow/engine.py — Moteur FSM pour les transitions candidat
"""
import logging
from datetime import datetime
from backend.config import supabase_admin, get_data
from backend.workflow.states import CANDIDATE_TRANSITIONS, CandidateStage

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Finite State Machine pour le pipeline candidat."""

    async def transition(
        self,
        candidate_id: str,
        tenant_id: str,
        new_stage: str,
        triggered_by: str,
        reason: str = ""
    ) -> dict:
        """Exécute une transition de stage avec validation."""
        # Récupérer le stage actuel
        res = supabase_admin.table("candidates").select("pipeline_stage").eq(
            "id", candidate_id).execute()
        candidates = get_data(res) or []
        if not candidates:
            raise ValueError(f"Candidat {candidate_id} introuvable")

        current = candidates[0]["pipeline_stage"]
        allowed = CANDIDATE_TRANSITIONS.get(current, [])

        if new_stage not in allowed:
            raise ValueError(
                f"Transition invalide: {current} → {new_stage}. "
                f"Transitions autorisées: {allowed}"
            )

        # Mettre à jour le candidat
        supabase_admin.table("candidates").update(
            {"pipeline_stage": new_stage}
        ).eq("id", candidate_id).execute()

        # Enregistrer dans workflow_states
        supabase_admin.table("workflow_states").insert({
            "tenant_id": tenant_id,
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "current_state": new_stage,
            "previous_state": current,
            "triggered_by": triggered_by,
            "event_name": f"{current}_to_{new_stage}",
            "metadata": {"reason": reason}
        }).execute()

        logger.info(f"[Workflow] {candidate_id}: {current} → {new_stage}")
        return {"previous": current, "current": new_stage, "candidate_id": candidate_id}

    async def get_history(self, candidate_id: str, tenant_id: str) -> list:
        """Retourne l'historique des transitions d'un candidat."""
        res = supabase_admin.table("workflow_states").select("*").eq(
            "entity_id", candidate_id
        ).eq("tenant_id", tenant_id).order("created_at").execute()
        return get_data(res) or []

    def get_allowed_transitions(self, current_stage: str) -> list:
        return CANDIDATE_TRANSITIONS.get(current_stage, [])


workflow_engine = WorkflowEngine()
