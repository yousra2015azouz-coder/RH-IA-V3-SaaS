"""
utils/pdf_generator.py — Génération de PDF (Doc 5.1 & 5.2)
"""
import io
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm

logger = logging.getLogger(__name__)

def generate_interview_report(data: dict) -> bytes:
    """Génère le document 5.1 : Compte rendu d'entretien."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    elements.append(Paragraph("<b>COMPTE RENDU D'ENTRETIEN</b>", ParagraphStyle('Title', parent=styles['Heading1'], alignment=1)))
    elements.append(Spacer(1, 1*cm))

    # --- Section Candidat & Poste ---
    elements.append(Paragraph("<b>Informations du Candidat</b>", styles['Heading2']))
    c_data = [
        ["Candidat:", data.get("candidate_name", "N/A")],
        ["Poste:", data.get("job_title", "N/A")],
        ["Date de l'entretien:", data.get("date", "N/A")]
    ]
    t1 = Table(c_data, colWidths=[5*cm, 11*cm])
    t1.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold')]))
    elements.append(t1)
    elements.append(Spacer(1, 1*cm))

    # --- Section Évaluation (Notation 1-5) ---
    elements.append(Paragraph("<b>Critères d'Évaluation</b>", styles['Heading2']))
    eval_data = [["Critère", "Notation (1-5)", "Commentaires"]]
    for k, v in data.get("criteria", {}).items():
        eval_data.append([k, str(v.get("score", "-")), v.get("comment", "")])
    
    t2 = Table(eval_data, colWidths=[5*cm, 3*cm, 8*cm])
    t2.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (1,1), (1,-1), 'CENTER')
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 1*cm))

    # --- Synthèse ---
    elements.append(Paragraph(f"<b>Score Global:</b> {data.get('global_score', '0')}/5", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"<b>Avis Final:</b> {data.get('final_opinion', 'N/A')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"<b>Commentaires:</b><br/>{data.get('comments', 'Aucun')}", styles['Normal']))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_approval_pdf(data: dict) -> bytes:
    """Génère le document 5.2 : Demande d'approbation RH (Copie Conforme au modèle)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # --- COULEURS EXACTES DU MODÈLE ---
    SECTION_BG = colors.HexColor("#2C3E50")  # Bleu marine section
    LABEL_BG = colors.HexColor("#D5D8DC")    # Gris entête
    VALUE_BG = colors.HexColor("#E9F7EF")    # Vert pâle données
    TEXT_BLUE = colors.HexColor("#2E86C1")   # Bleu pour les chiffres
    
    # --- STYLES ---
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=18, spaceAfter=10)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey, spaceAfter=15)
    section_style = ParagraphStyle('Sec', parent=styles['Normal'], fontSize=9, textColor=colors.white, backColor=SECTION_BG, leftIndent=5, leading=14)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7)
    value_style = ParagraphStyle('Val', parent=styles['Normal'], fontSize=7, textColor=TEXT_BLUE, alignment=1)
    
    # --- HEADER ---
    elements.append(Paragraph("Demande d'Approbation RH", title_style))
    elements.append(Paragraph("Merci de renseigner tous les champs en couleur grise", subtitle_style))
    
    # --- BARRE TOP ---
    top_data = [[
        Paragraph("Nature de la demande RH", cell_style), Paragraph(f"<b>{str(data.get('nature', 'Recrutement'))}</b>", value_style),
        Paragraph("Budgétisation RH", cell_style), Paragraph("<b>Oui</b>" if data.get("is_budgeted") else "<b>Non</b>", value_style),
        Paragraph("Date d'application", cell_style), Paragraph(f"<b>{str(data.get('date_application', '16/03/2026'))}</b>", value_style)
    ]]
    t_top = Table(top_data, colWidths=[4*cm, 2.5*cm, 3.5*cm, 2*cm, 4*cm, 3*cm])
    t_top.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,0), SECTION_BG), ('TEXTCOLOR', (0,0), (0,0), colors.white),
        ('BACKGROUND', (2,0), (2,0), SECTION_BG), ('TEXTCOLOR', (2,0), (2,0), colors.white),
        ('BACKGROUND', (4,0), (4,0), SECTION_BG), ('TEXTCOLOR', (4,0), (4,0), colors.white),
        ('BACKGROUND', (1,0), (1,0), VALUE_BG),
        ('BACKGROUND', (3,0), (3,0), VALUE_BG),
        ('BACKGROUND', (5,0), (5,0), VALUE_BG),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    elements.append(t_top)
    elements.append(Spacer(1, 0.2*cm))

    # --- SECTION 1 : INFOS GÉNÉRALES ---
    elements.append(Paragraph("Informations générales", section_style))
    gen_data = [
        [Paragraph("Nom du collaborateur", cell_style), Paragraph(f"<b>{str(data.get('nom_collaborateur', 'N/A'))}</b>", value_style), "", ""],
        [Paragraph("Date d'embauche", cell_style), Paragraph(str(data.get("date_embauche", "N/A")), value_style), Paragraph("Personnes à charge", cell_style), Paragraph(str(data.get("personnes_a_charge", 0)), value_style)],
        [Paragraph("Date de naissance", cell_style), Paragraph(str(data.get("date_naissance", "N/A")), value_style), Paragraph("Situation Familiale", cell_style), Paragraph(str(data.get("situation_familiale", "Célibataire")), value_style)]
    ]
    t_gen = Table(gen_data, colWidths=[5*cm, 5*cm, 4.5*cm, 4.5*cm])
    t_gen.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), LABEL_BG),
        ('BACKGROUND', (2,1), (2,-1), LABEL_BG),
        ('BACKGROUND', (1,0), (3,0), VALUE_BG), ('SPAN', (1,0), (3,0)),
        ('BACKGROUND', (1,1), (1,-1), VALUE_BG),
        ('BACKGROUND', (3,1), (3,-1), VALUE_BG),
    ]))
    elements.append(t_gen)

    # --- SECTION 2 : INFOS ORGANISATIONNELLES ---
    elements.append(Paragraph("Informations organisationnelles", section_style))
    org_data = [
        [Paragraph("Site (Succursale)", cell_style), Paragraph(str(data.get("site", "Siège")), value_style)],
        [Paragraph("Entité Organisationnelle", cell_style), Paragraph(str(data.get("entity", "N/A")), value_style)],
        [Paragraph("Fonction", cell_style), Paragraph(str(data.get("job_title", "N/A")), value_style)],
        [Paragraph("Emploi de référence", cell_style), Paragraph(str(data.get("ref_job", "N/A")), value_style)],
        [Paragraph("Type de rémunération", cell_style), Paragraph("Indirect", value_style)],
        [Paragraph("Grade", cell_style), Paragraph("53", value_style)]
    ]
    t_org = Table(org_data, colWidths=[5*cm, 14*cm])
    t_org.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), LABEL_BG),
        ('BACKGROUND', (1,0), (1,-1), VALUE_BG),
    ]))
    elements.append(t_org)

    # --- SECTION 3 : SITUATION SALARIALE (DÉTAILLÉE) ---
    elements.append(Paragraph("Situation salariale", section_style))
    rubrics = [
        ("Salaire de base", data.get("salaire_base", 0)),
        ("Prime d'ancienneté", 0),
        ("Indemnité Représentation", 0),
        ("Indemnité Panier", data.get("indemnite_panier", 550)),
        ("Indemnité GSM", 0),
        ("Indemnité Transport", data.get("indemnite_transport", 550)),
        ("Indemnité Caisse Recettes", 0),
        ("Indemnité Caisse Dépenses", 0),
        ("Indemnité Spéciale", 0),
        ("Prime Loyer", 150),
        ("Prime d'encadrement", 0),
        ("Prime Spéciale", 0),
        ("<b>Salaire mensuel brut</b>", data.get("salaire_mensuel_brut", 0)),
        ("<b>Salaire mensuel net</b>", data.get("salaire_mensuel_net", 0)),
    ]
    sal_rows = [[Paragraph("Rubrique", cell_style), "", Paragraph("Situation Proposée", cell_style)]]
    for label, val in rubrics:
        sal_rows.append([Paragraph(label, cell_style), "", Paragraph(f"{val:,.2f} MAD", value_style)])
    
    t_sal = Table(sal_rows, colWidths=[6*cm, 6.5*cm, 6.5*cm])
    t_sal.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), LABEL_BG),
        ('BACKGROUND', (2,1), (2,-1), VALUE_BG),
        ('SPAN', (0,0), (1,0)),
        ('SPAN', (0,1), (1,1)), ('SPAN', (0,2), (1,2)), ('SPAN', (0,3), (1,3)), ('SPAN', (0,4), (1,4)),
        ('SPAN', (0,5), (1,5)), ('SPAN', (0,6), (1,6)), ('SPAN', (0,7), (1,7)), ('SPAN', (0,8), (1,8)),
        ('SPAN', (0,9), (1,9)), ('SPAN', (0,10), (1,10)), ('SPAN', (0,11), (1,11)), ('SPAN', (0,12), (1,12)),
        ('SPAN', (0,13), (1,13)), ('SPAN', (0,14), (1,14)),
    ]))
    elements.append(t_sal)

    # --- SECTION 4 : AVANTAGES ---
    elements.append(Paragraph("Avantages", section_style))
    adv_data = [
        [Paragraph("Rubrique", cell_style), "", Paragraph("Situation Proposée", cell_style)],
        [Paragraph("Primes Aïd", cell_style), "", Paragraph("2 100,00 MAD", value_style)],
        [Paragraph("Taux CIMR", cell_style), "", Paragraph("6.00 %", value_style)]
    ]
    t_adv = Table(adv_data, colWidths=[6*cm, 6.5*cm, 6.5*cm])
    t_adv.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), LABEL_BG),
        ('BACKGROUND', (2,1), (2,-1), VALUE_BG),
        ('SPAN', (0,0), (1,0)), ('SPAN', (0,1), (1,1)), ('SPAN', (0,2), (1,2))
    ]))
    elements.append(t_adv)

    # --- APPROBATIONS (FORMAT MODÈLE) ---
    elements.append(Spacer(1, 0.5*cm))
    app_titles = [
        Paragraph("<b>Directeur Hiérarchique</b>", cell_style),
        Paragraph("<b>Directeur Fonctionnel</b>", cell_style),
        Paragraph("<b>Directeur RH</b>", cell_style),
        Paragraph("<b>Directeur Général</b>", cell_style)
    ]
    app_boxes = [
        [Paragraph("Nom:<br/>Date:", cell_style), Paragraph("Nom:<br/>Date:", cell_style), Paragraph("Nom:<br/>Date:", cell_style), Paragraph("Nom:<br/>Date:", cell_style)]
    ]
    
    t_app_h = Table([app_titles], colWidths=[4.75*cm]*4)
    t_app_h.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,0), LABEL_BG), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    elements.append(t_app_h)
    
    t_app_b = Table(app_boxes, colWidths=[4.75*cm]*4, rowHeights=[1.5*cm])
    t_app_b.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('VALIGN', (0,0), (-1,-1), 'BOTTOM')]))
    elements.append(t_app_b)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
