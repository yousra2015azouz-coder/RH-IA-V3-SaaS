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
    salaire_base_drh: float,
    taux_cimr: float = 6.00,
    nb_enfants: int = 0
) -> dict:
    """
    Calcul paie marocaine (Brut Fixe -> Net Variable).
    Le salaire de base est fixé par le DRH.
    Les indemnités sont ajoutées.
    Le Net est calculé selon la situation familiale.
    """
    SB = Decimal(str(salaire_base_drh)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    # --- 1. Indemnités Fixes (Standard Entreprise) ---
    ind_panier = Decimal("660.00")    # 30 MAD * 22j (Exonéré)
    ind_transport = Decimal("500.00") # Standard (Exonéré)
    prime_loyer = (SB * Decimal("0.05")).quantize(Decimal("0.01"), ROUND_HALF_UP) # 5% du base
    
    # Salaire Brut Global
    brut_global = SB + ind_panier + ind_transport + prime_loyer

    # --- 2. Cotisations Sociales ---
    # La CNSS est plafonnée à 6000 MAD de brut
    cnss_base = min(brut_global, Decimal("6000"))
    cnss = (cnss_base * Decimal("0.0448")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    amo = (brut_global * Decimal("0.0226")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    cimr = (brut_global * Decimal(str(taux_cimr)) / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # --- 3. Impôt sur le Revenu (IR) ---
    # Frais pro (20% plafonné à 2500 MAD/mois) sur le brut taxable (hors panier/transport)
    brut_taxable = SB + prime_loyer
    frais_pro = min(brut_taxable * Decimal("0.20"), Decimal("2500"))
    
    # Revenu Net Imposable (RNI)
    rni_mensuel = brut_taxable - cnss - amo - cimr - frais_pro
    rni_annuel = rni_mensuel * 12

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

    # Déductions famille (30 MAD par personne à charge)
    deduction_famille = Decimal("30") * min(Decimal(str(nb_enfants)), Decimal("6"))
    ir_mensuel = max((ir_annuel / 12) - deduction_famille, Decimal("0")).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # --- 4. Résultats ---
    salaire_net = brut_global - cnss - amo - cimr - ir_mensuel

    return {
        "salaire_base": float(SB),
        "indemnite_panier": float(ind_panier),
        "indemnite_transport": float(ind_transport),
        "prime_loyer": float(prime_loyer),
        "salaire_mensuel_brut": float(brut_global),
        "cnss": float(cnss),
        "amo": float(amo),
        "cimr": float(cimr),
        "ir_mensuel": float(ir_mensuel),
        "salaire_net": float(salaire_net.quantize(Decimal("1"), ROUND_HALF_UP)),
        "salaire_annuel_garanti": float(salaire_net * 12),
        "taux_cimr": taux_cimr
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
                "title": "✒️ Signature requise (Doc 5.2)",
                "message": f"Le document d'approbation RH est prêt pour votre signature.",
                "type": "approval",
                "link": f"/dashboards/approvals/{approval_id}"
            }).execute()
            logger.info(f"🔔 Notification envoyée à {user['id']}")
        except Exception as e:
            logger.error(f"Failed to send notification to {user['id']}: {e}")
