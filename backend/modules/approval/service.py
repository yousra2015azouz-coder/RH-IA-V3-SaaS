"""
modules/approval/service.py — Calculs fiscaux marocains + workflow 4 signatures
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from backend.config import supabase_admin, get_data
from backend.workflow.states import ApprovalStatus, APPROVAL_TRANSITIONS, APPROVAL_ROLE_MAP
from backend.modules.error_tracker.service import log_error

logger = logging.getLogger(__name__)


def calculate_moroccan_salary(
    salaire_brut: float,
    taux_cimr: float = 6.00,
    nb_enfants: int = 0,
    anciennete_years: int = 0
) -> dict:
    """
    Calcul net marocain complet :
    CNSS = min(brut, 6000) × 4.48%
    AMO  = brut × 2.26%
    CIMR = brut × taux_cimr%
    Revenu imposable = brut - CNSS - AMO - CIMR - frais_pro(20%, max 30000/an)
    IR   = tranches progressives
    Déductions IR : 360 MAD/enfant/an (max 6)
    Net  = brut - CNSS - AMO - CIMR - IR
    """
    B = Decimal(str(salaire_brut))

    # Cotisations sociales
    cnss_base = min(B, Decimal("6000"))
    cnss = (cnss_base * Decimal("0.0448")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    amo = (B * Decimal("0.0226")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    cimr = (B * Decimal(str(taux_cimr)) / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # Frais professionnels (20% plafonné à 2500/mois)
    frais_pro = min(B * Decimal("0.20"), Decimal("2500"))

    # Revenu net imposable mensuel
    rni_mensuel = B - cnss - amo - cimr - frais_pro
    rni_annuel = rni_mensuel * 12

    # IR annuel — tranches 2024
    if rni_annuel <= 30000:
        ir_annuel = Decimal("0")
    elif rni_annuel <= 50000:
        ir_annuel = (rni_annuel - 30000) * Decimal("0.10")
    elif rni_annuel <= 60000:
        ir_annuel = Decimal("2000") + (rni_annuel - 50000) * Decimal("0.20")
    elif rni_annuel <= 80000:
        ir_annuel = Decimal("4000") + (rni_annuel - 60000) * Decimal("0.30")
    elif rni_annuel <= 180000:
        ir_annuel = Decimal("10000") + (rni_annuel - 80000) * Decimal("0.34")
    else:
        ir_annuel = Decimal("44000") + (rni_annuel - 180000) * Decimal("0.37")

    # Déductions pour charges de famille
    nb_enfants_deductibles = min(nb_enfants, 6)
    deduction_famille = Decimal("30") * nb_enfants_deductibles  # 30 MAD/mois/enfant

    ir_mensuel = ((ir_annuel / 12) - deduction_famille).quantize(Decimal("0.01"), ROUND_HALF_UP)
    ir_mensuel = max(ir_mensuel, Decimal("0"))

    # Salaire Net
    salaire_net = (B - cnss - amo - cimr - ir_mensuel).quantize(Decimal("0.01"), ROUND_HALF_UP)

    return {
        "salaire_brut": float(B),
        "cnss": float(cnss),
        "amo": float(amo),
        "cimr": float(cimr),
        "ir_mensuel": float(ir_mensuel),
        "salaire_net": float(salaire_net),
        "salaire_annuel_garanti": float(salaire_net * 12),
        "taux_cimr": taux_cimr,
    }


async def get_next_approval_status(current_status: str) -> str | None:
    """Retourne le prochain statut dans la chaîne d'approbation."""
    return APPROVAL_TRANSITIONS.get(current_status)


async def notify_next_approver(tenant_id: str, approval_id: str, next_status: str):
    """Notifie le prochain approbateur."""
    required_role = APPROVAL_ROLE_MAP.get(next_status)
    if not required_role:
        return

    users_res = supabase_admin.table("users").select("id").eq(
        "tenant_id", tenant_id).eq("role", required_role).execute()

    for user in (users_res.data or []):
        try:
            supabase_admin.table("notifications").insert({
                "user_id": user["id"],
                "tenant_id": tenant_id,
                "title": "Demande d'approbation en attente",
                "message": f"Une demande d'approbation RH requiert votre signature.",
                "type": "approval"
            }).execute()
        except Exception as e:
            logger.error(f"Failed to send notification to {user['id']}: {e}")
