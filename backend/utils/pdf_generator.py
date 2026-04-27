"""
utils/pdf_generator.py — Génération de PDF (Doc 5.1 & 5.2) — Design Premium
"""
import io
import logging
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing, Line
from decimal import Decimal

logger = logging.getLogger(__name__)

def get_branding(data):
    """Récupère les couleurs et logo du tenant."""
    PRIMARY = colors.HexColor("#1e40af") # Blue par défaut
    SECONDARY = colors.HexColor("#f59e0b") # Amber par défaut
    if data.get("primary_color") and data.get("primary_color").startswith("#"):
        PRIMARY = colors.HexColor(data["primary_color"])
    if data.get("secondary_color") and data.get("secondary_color").startswith("#"):
        SECONDARY = colors.HexColor(data["secondary_color"])
    return PRIMARY, SECONDARY

def add_header_footer(canvas, doc, data):
    """Ajoute un header et footer sur chaque page."""
    canvas.saveState()
    PRIMARY, _ = get_branding(data)
    
    # Header line
    canvas.setStrokeColor(PRIMARY)
    canvas.setLineWidth(2)
    canvas.line(1*cm, A4[1]-1.5*cm, A4[0]-1*cm, A4[1]-1.5*cm)
    
    # Footer
    canvas.setFont('Helvetica', 8)
    canvas.setStrokeColor(colors.lightgrey)
    canvas.line(1*cm, 1.5*cm, A4[0]-1*cm, 1.5*cm)
    canvas.drawString(1*cm, 1.2*cm, f"Document généré par RH-IA V3 — Confidentiel")
    canvas.drawRightString(A4[0]-1*cm, 1.2*cm, f"Page {doc.page}")
    canvas.restoreState()

def generate_interview_report(data: dict) -> bytes:
    """Génère le document 5.1 : Compte rendu d'entretien (Design Premium)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    PRIMARY, SECONDARY = get_branding(data)

    # Styles personnalisés
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=22, textColor=PRIMARY, alignment=0, spaceAfter=20)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=12, textColor=colors.white, backColor=PRIMARY, leftIndent=5, borderPadding=5, borderRadius=3, spaceBefore=15, spaceAfter=10)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=10)

    # --- Header avec Logo ---
    logo_path = data.get("logo_url")
    app_name = data.get("app_name", "RH-IA Platform")
    
    header_table_data = []
    if logo_path and os.path.exists(logo_path):
        try:
            img = RLImage(logo_path, width=2.5*cm, height=2.5*cm)
            header_table_data = [[img, Paragraph(f"<b>{app_name}</b><br/><font size=9 color=grey>Expertise & Recrutement IA</font>", styles['Normal'])]]
        except:
            header_table_data = [[Paragraph(f"<b>{app_name}</b>", title_style)]]
    else:
        header_table_data = [[Paragraph(f"<b>{app_name}</b>", title_style)]]

    t_header = Table(header_table_data, colWidths=[3*cm, 15*cm])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(t_header)
    elements.append(Spacer(1, 0.5*cm))

    elements.append(Paragraph("COMPTE RENDU D'ENTRETIEN", title_style))
    
    # --- Infos Candidat ---
    elements.append(Paragraph("INFORMATIONS CANDIDAT", section_style))
    info_data = [
        [Paragraph("Candidat", label_style), Paragraph(data.get("candidate_name", "N/A"), value_style), Paragraph("Date", label_style), Paragraph(data.get("date", "N/A"), value_style)],
        [Paragraph("Poste", label_style), Paragraph(data.get("job_title", "N/A"), value_style), Paragraph("Évaluateur", label_style), Paragraph(data.get("interviewer_name", "N/A"), value_style)],
    ]
    t_info = Table(info_data, colWidths=[4*cm, 5*cm, 4*cm, 5*cm])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('BACKGROUND', (2,0), (2,-1), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(t_info)

    # --- Évaluation ---
    elements.append(Paragraph("ÉVALUATION DES COMPÉTENCES", section_style))
    eval_data = [[Paragraph("Critère d'évaluation", label_style), Paragraph("Score", label_style), Paragraph("Commentaires & Observations", label_style)]]
    
    for k, v in data.get("criteria", {}).items():
        score = v.get("score", 0)
        if score > 5: score = score / 20
        # Etoiles ou barre de score
        stars = "★" * int(score) + "☆" * (5 - int(score))
        eval_data.append([
            Paragraph(k.capitalize(), value_style),
            Paragraph(f"<font color={SECONDARY}><b>{stars}</b></font> ({score}/5)", value_style),
            Paragraph(v.get("comment", "-"), value_style)
        ])
    
    t_eval = Table(eval_data, colWidths=[5*cm, 4*cm, 9*cm])
    t_eval.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8)
    ]))
    elements.append(t_eval)

    # --- IA Summary ---
    if data.get("ai_summary"):
        elements.append(Paragraph("SYNTHÈSE DE L'INTELLIGENCE ARTIFICIELLE", section_style))
        elements.append(Paragraph(data["ai_summary"], ParagraphStyle('IA', parent=styles['Normal'], backColor=colors.HexColor("#f0fdf4"), borderPadding=10, borderRadius=5, leading=14)))
        elements.append(Spacer(1, 0.5*cm))

    # --- Conclusion ---
    elements.append(Paragraph("CONCLUSION & DÉCISION", section_style))
    opinion = data.get("final_opinion", "Avis réservé")
    opinion_color = colors.green if "FAVORABLE" in opinion.upper() else colors.red
    
    conc_data = [
        [Paragraph("Score Global", label_style), Paragraph(f"<b>{data.get('global_score', '0')}/5</b>", ParagraphStyle('GS', parent=value_style, fontSize=14, textColor=PRIMARY))],
        [Paragraph("Avis Final", label_style), Paragraph(f"<b>{opinion}</b>", ParagraphStyle('OP', parent=value_style, fontSize=12, textColor=opinion_color))],
        [Paragraph("Observations", label_style), Paragraph(data.get("comments", "-"), value_style)]
    ]
    t_conc = Table(conc_data, colWidths=[4*cm, 14*cm])
    t_conc.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    elements.append(t_conc)

    doc.build(elements, onFirstPage=lambda c, d: add_header_footer(c, d, data), onLaterPages=lambda c, d: add_header_footer(c, d, data))
    return buffer.getvalue()

def generate_approval_pdf(data: dict) -> bytes:
    """Génère le document 5.2 : Demande d'Approbation RH (Modèle Premium Dynamique)."""
    buffer = io.BytesIO()
    # Marges plus étroites pour maximiser l'espace
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.8*cm, leftMargin=0.8*cm, topMargin=0.8*cm, bottomMargin=0.8*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # --- PALETTE DE COULEURS ---
    PRIMARY = colors.HexColor("#1e3a8a") # Bleu Marine Profond
    SECONDARY = colors.HexColor("#f8fafc") # Blanc Cassé
    ACCENT = colors.HexColor("#e2e8f0") # Gris Clair Bordure
    SUCCESS = colors.HexColor("#059669") # Vert Approbation
    
    # --- STYLES PERSONNALISÉS ---
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=18, textColor=PRIMARY, spaceAfter=15)
    section_style = ParagraphStyle('Sec', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=colors.white, backColor=PRIMARY, leftIndent=5, leading=16, spaceBefore=5, spaceAfter=5)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.black)
    value_style = ParagraphStyle('Val', parent=styles['Normal'], fontSize=8.5, textColor=colors.darkgrey)
    sig_title_style = ParagraphStyle('SigTitle', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', alignment=1)
    sig_info_style = ParagraphStyle('SigInfo', parent=styles['Normal'], fontSize=7.5, alignment=1, leading=10)

    # --- EN-TÊTE : LOGO & TITRE ---
    logo_path = data.get("logo_url")
    header_data = []
    if logo_path and os.path.exists(logo_path):
        try:
            img = RLImage(logo_path, width=3.5*cm, height=1.2*cm)
            header_data.append([img, Paragraph("DEMANDE D'APPROBATION RH", title_style)])
        except:
            header_data.append(["", Paragraph("DEMANDE D'APPROBATION RH", title_style)])
    else:
        header_data.append(["", Paragraph("DEMANDE D'APPROBATION RH", title_style)])

    t_head = Table(header_data, colWidths=[6*cm, 13*cm])
    t_head.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(t_head)
    elements.append(Spacer(1, 0.2*cm))

    # --- INFOS GÉNÉRALES ---
    elements.append(Paragraph("1. INFORMATIONS GÉNÉRALES", section_style))
    gen_data = [
        [Paragraph("Nom du collaborateur", label_style), Paragraph(f"<b>{data.get('nom_collaborateur') or 'N/A'}</b>", value_style), Paragraph("Nature", label_style), Paragraph(data.get("nature") or "Recrutement", value_style)],
        [Paragraph("Date d'embauche", label_style), Paragraph(data.get("date_embauche") or "N/A", value_style), Paragraph("Budget", label_style), Paragraph("Oui" if data.get("is_budgeted") else "Non", value_style)],
        [Paragraph("Date de naissance", label_style), Paragraph(data.get("date_naissance") or "N/A", value_style), Paragraph("Email", label_style), Paragraph(data.get("email") or "N/A", value_style)],
        [Paragraph("Situation Familiale", label_style), Paragraph(data.get("situation_familiale") or "N/A", value_style), Paragraph("Personnes à charge", label_style), Paragraph(str(data.get("personnes_a_charge") or 0), value_style)]
    ]
    t_gen = Table(gen_data, colWidths=[4.5*cm, 5*cm, 4.5*cm, 5*cm])
    t_gen.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, ACCENT),
        ('BACKGROUND', (0,0), (0,-1), SECONDARY), ('BACKGROUND', (2,0), (2,-1), SECONDARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(t_gen)

    # --- INFOS ORGANISATIONNELLES ---
    elements.append(Paragraph("2. INFORMATIONS ORGANISATIONNELLES", section_style))
    job = data.get("job_offers") or {}
    org_data = [
        [Paragraph("Site (Succursale)", label_style), Paragraph(data.get("site") or job.get("site") or "N/A", value_style), Paragraph("Entité Organisationnelle", label_style), Paragraph(data.get("entity") or job.get("entity_organisationnelle") or "N/A", value_style)],
        [Paragraph("Fonction / Poste", label_style), Paragraph(data.get("job_title") or job.get("title") or "N/A", value_style), Paragraph("Emploi de référence", label_style), Paragraph(data.get("ref_job") or job.get("reference") or "N/A", value_style)],
        [Paragraph("Type de rémunération", label_style), Paragraph(data.get("type_remuneration") or "Direct", value_style), Paragraph("Grade / Niveau", label_style), Paragraph(str(data.get("grade") or job.get("grade") or "N/A"), value_style)]
    ]
    t_org = Table(org_data, colWidths=[4.5*cm, 5*cm, 4.5*cm, 5*cm])
    t_org.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, ACCENT),
        ('BACKGROUND', (0,0), (0,-1), SECONDARY), ('BACKGROUND', (2,0), (2,-1), SECONDARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(t_org)

    # --- SITUATION SALARIALE ---
    elements.append(Paragraph("3. SITUATION SALARIALE PROPOSÉE (MAD)", section_style))
    sal_rubrics = [
        ("Salaire de base", data.get("salaire_base") or 0),
        ("Prime d'ancienneté", 0),
        ("Indemnité Représentation", 0),
        ("Indemnité Panier", data.get("indemnite_panier") or job.get("indemnite_panier") or 550),
        ("Indemnité GSM", data.get("indemnite_gsm") or job.get("indemnite_gsm") or 0),
        ("Indemnité Transport", data.get("indemnite_transport") or job.get("indemnite_transport") or 550),
        ("Indemnité Caisse", 0),
        ("Indemnité Spéciale", 0),
        ("Prime de Performance (Mensuelle)", 0),
        ("<b>SALAIRE MENSUEL BRUT</b>", data.get("salaire_mensuel_brut") or 0),
        ("<b>SALAIRE MENSUEL NET</b>", data.get("salaire_mensuel_net") or 0)
    ]
    
    sal_rows = []
    # Split en 2 colonnes pour économiser de l'espace
    mid = (len(sal_rubrics) + 1) // 2
    for i in range(mid):
        r1 = sal_rubrics[i]
        r2 = sal_rubrics[i+mid] if i+mid < len(sal_rubrics) else ("", "")
        
        row = [
            Paragraph(r1[0], label_style), Paragraph(f"{r1[1]:,.2f}" if isinstance(r1[1], (int,float,Decimal)) else str(r1[1]), value_style),
            Paragraph(r2[0], label_style) if r2[0] else "", Paragraph(f"{r2[1]:,.2f}" if isinstance(r2[1], (int,float,Decimal)) else str(r2[1]), value_style) if r2[0] else ""
        ]
        sal_rows.append(row)

    t_sal = Table(sal_rows, colWidths=[4.5*cm, 5*cm, 4.5*cm, 5*cm])
    t_sal.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, ACCENT),
        ('BACKGROUND', (0,0), (0,-1), SECONDARY), ('BACKGROUND', (2,0), (2,-1), SECONDARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (1, -1), (1, -1), colors.HexColor("#f0f9ff")), # Highlight Net
        ('BACKGROUND', (3, -1), (3, -1), colors.HexColor("#f0f9ff"))
    ]))
    elements.append(t_sal)

    # --- AVANTAGES & POSITIONNEMENT ---
    elements.append(Paragraph("4. AVANTAGES & POSITIONNEMENT", section_style))
    adv_data = [
        [Paragraph("Primes Aïd / Scolarité", label_style), Paragraph(f"{data.get('prime_aid') or 2100:,.2f} MAD", value_style), Paragraph("Transport / Véhicule", label_style), Paragraph("Inclus (Panier/Transport)", value_style)],
        [Paragraph("Carte Carburant", label_style), Paragraph("Selon politique", value_style), Paragraph("Taux CIMR", label_style), Paragraph(f"{data.get('taux_cimr') or 6:.2f}%", value_style)],
        [Paragraph("<b>Salaire Annuel Garanti (SAG)</b>", label_style), Paragraph(f"<b>{data.get('salaire_annuel_garanti') or 0:,.2f} MAD</b>", value_style), Paragraph("<b>Salaire Annuel Total (SAT)</b>", label_style), Paragraph(f"<b>{data.get('salaire_annuel_total') or 0:,.2f} MAD</b>", value_style)]
    ]
    t_adv = Table(adv_data, colWidths=[4.5*cm, 5*cm, 4.5*cm, 5*cm])
    t_adv.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, ACCENT),
        ('BACKGROUND', (0,0), (0,-1), SECONDARY), ('BACKGROUND', (2,0), (2,-1), SECONDARY),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(t_adv)

    # --- COMMENTAIRES ---
    elements.append(Paragraph("5. COMMENTAIRES & JUSTIFICATIONS", section_style))
    comm = data.get("comments") or "Recrutement validé suite à l'évaluation positive de l'IA et des entretiens opérationnels."
    t_comm = Table([[Paragraph(comm, value_style)]], colWidths=[19*cm], rowHeights=[1.5*cm])
    t_comm.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, ACCENT),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 8)
    ]))
    elements.append(t_comm)

    # --- APPROBATIONS & SIGNATURES ---
    elements.append(Paragraph("6. CIRCUIT D'APPROBATION ET SIGNATURES", section_style))
    
    sigs = data.get("signatures") or {}
    def get_sig_block(role, title):
        s = sigs.get(role) or {}
        if s.get('signed'):
            content = [
                Paragraph(f"<b>{title}</b>", sig_title_style),
                Paragraph(f"<font color=green><b>APPROUVÉ</b></font>", sig_info_style),
                Paragraph(f"Nom: {s.get('name')}", sig_info_style),
                Paragraph(f"Date: {s.get('date')}", sig_info_style),
                Paragraph("<i>Signature Digitale Valide</i>", ParagraphStyle('Digital', parent=sig_info_style, textColor=PRIMARY, fontSize=6))
            ]
        else:
            content = [
                Paragraph(f"<b>{title}</b>", sig_title_style),
                Paragraph("<br/><br/>Nom: ____________", sig_info_style),
                Paragraph("Date: ____________", sig_info_style),
                Paragraph("Signature: _________", sig_info_style)
            ]
        return content

    sig_table_data = [[
        get_sig_block("hierarchic", "Directeur Hiérarchique"),
        get_sig_block("functional", "Directeur Fonctionnel"),
        get_sig_block("hr", "Directeur RH"),
        get_sig_block("dg", "Directeur Général")
    ]]
    
    t_sig = Table(sig_table_data, colWidths=[4.75*cm]*4, rowHeights=[3*cm])
    t_sig.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, ACCENT),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    elements.append(t_sig)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


