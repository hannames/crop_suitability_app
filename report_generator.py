"""
report_generator.py
Generate a styled PDF methodology and results report.
Uses ReportLab — no external LaTeX or LibreOffice needed.
"""

import io
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Colour palette ───────────────────────────────────────────────────────────
GREEN1 = colors.HexColor('#1A5C30')
GREEN2 = colors.HexColor('#2E7D46')
GREEN3 = colors.HexColor('#EAF5EE')
BLUE1  = colors.HexColor('#1F4E79')
BLUE2  = colors.HexColor('#E8F1FB')
AMBER  = colors.HexColor('#FFF3CD')
RED2   = colors.HexColor('#FDECEA')
GREY   = colors.HexColor('#F5F5F5')
WHITE  = colors.white
BLACK  = colors.HexColor('#222222')


def generate_report(parcel_info: dict,
                    results: dict,
                    crop_name: str,
                    map_image_bytes: Optional[bytes] = None) -> bytes:
    """
    Build a PDF report and return as bytes.

    Args:
        parcel_info: output from kml_utils.parse_uploaded_file()
        results: output from gee_analysis.run_analysis()
        crop_name: display name of the crop
        map_image_bytes: PNG bytes of the map screenshot (optional)

    Returns:
        PDF as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f'Crop Suitability Report — {parcel_info["name"]}',
        author='Crop Suitability App'
    )

    styles = _build_styles()
    story = []

    # ── Cover block ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('RAPPORT D\'APTITUDE AGRICOLE', styles['cover_title']))
    story.append(Paragraph('Crop Suitability Analysis Report', styles['cover_sub']))
    story.append(HRFlowable(width='100%', thickness=3, color=GREEN2, spaceAfter=10))

    meta = [
        ['Parcelle', parcel_info.get('name', 'N/A')],
        ['Culture analysée', crop_name],
        ['Superficie totale', f"{parcel_info.get('area_ha', 0):,.1f} ha"],
        ['Zone d\'analyse', f"Parcelle + {results.get('buffer_m', 0)/1000:.0f} km buffer"],
        ['Centroïde', _fmt_coord(parcel_info.get('centroid', (0, 0)))],
        ['Date d\'analyse', datetime.now().strftime('%d %B %Y')],
        ['Plateforme', 'Google Earth Engine (cloud)'],
        ['Résolution', '30 m/pixel (SRTM, Hansen, ESA)'],
    ]
    story.append(_data_table(meta, col_widths=[5*cm, 12*cm], shaded=True))
    story.append(Spacer(1, 0.5*cm))

    # ── Section 1: Zone summary ──────────────────────────────────────────────
    story.append(_section_header('1. Résultats — Zones d\'aptitude', styles))

    zone_labels = {
        '4': ('Zone 4 — PRIME', GREEN1, WHITE, 'Développer en priorité — meilleur rapport coût/rendement'),
        '3': ('Zone 3 — BONNE', GREEN2, WHITE, 'Phase 2 — bonnes conditions avec contraintes gérables'),
        '2': ('Zone 2 — MARGINALE', colors.HexColor('#E65100'), WHITE, 'Investissement ciblé requis pour lever les contraintes'),
        '1': ('Zone 1 — ÉVITER', colors.HexColor('#C62828'), WHITE, 'Pente forte, eau trop loin, forêt dense'),
        '0': ('Zone 0 — COURS D\'EAU', BLUE1, WHITE, 'Source d\'irrigation — non cultivable'),
    }

    zone_areas = results.get('zone_areas', {})
    total_area = sum(zone_areas.values()) or 1

    zone_data = [['Zone', 'Superficie (ha)', '% de la zone', 'Recommandation']]
    for key in ['4', '3', '2', '1', '0']:
        lbl, bg, fg, rec = zone_labels[key]
        ha = zone_areas.get(key, 0)
        pct = ha / total_area * 100
        zone_data.append([lbl, f'{ha:,.1f}', f'{pct:.1f}%', rec])

    t = Table(zone_data, colWidths=[4*cm, 3*cm, 2.5*cm, 7.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), GREEN1),
        ('TEXTCOLOR',   (0,0), (-1,0), WHITE),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [GREEN3, WHITE]),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING',   (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    # Target area summary
    target_ha = results.get('target_ha', 5000)
    best_zone = (zone_areas.get('4', 0) + zone_areas.get('3', 0))
    story.append(Paragraph(
        f'<b>Superficie potentielle (Zones 3+4) :</b> {best_zone:,.1f} ha '
        f'sur un objectif de <b>{target_ha:,} ha</b>.',
        styles['body']
    ))

    # ── Score thresholds ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('Superficie disponible par seuil de score', styles['h3']))
    thresh_data = [['Seuil de score', 'Superficie (ha)', 'Commentaire']]
    for item in results.get('score_thresholds', []):
        t_val = item['threshold']
        ha = item['area_ha']
        comment = ''
        if abs(ha - target_ha) < target_ha * 0.15:
            comment = f'← proche de l\'objectif {target_ha:,} ha'
        thresh_data.append([f'>= {t_val}', f'{ha:,.1f}', comment])

    t2 = Table(thresh_data, colWidths=[4*cm, 4*cm, 9*cm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLUE1),
        ('TEXTCOLOR',  (0,0), (-1,0), WHITE),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLUE2, WHITE]),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    story.append(t2)

    # ── Section 2: Component scores ───────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(_section_header('2. Scores moyens par critère', styles))

    comp = results.get('component_means', {})
    cfg  = results.get('crop_config', {})
    weights = cfg.get('weights', {})

    comp_data = [['Critère', 'Poids', 'Score moyen (0-10)', 'Barre']]
    criteria_labels = {
        'slope_score':    'Pente (topographie)',
        'water_score':    'Distance à l\'eau',
        'elec_score':     'Proximité électrique',
        'wetness_score':  'Humidité terrain',
        'clearing_score': 'Coût de défrichage',
        'flood_score':    'Risque d\'inondation',
    }
    weight_keys = {
        'slope_score': 'slope', 'water_score': 'water',
        'elec_score': 'elec', 'wetness_score': 'wetness',
        'clearing_score': 'clearing', 'flood_score': 'flood',
    }
    for key, label in criteria_labels.items():
        score = comp.get(key, 0)
        w = weights.get(weight_keys.get(key, ''), 0)
        bar = '█' * int(score) + '░' * (10 - int(score))
        comp_data.append([label, f'{w*100:.0f}%', f'{score:.1f}', bar])

    t3 = Table(comp_data, colWidths=[5.5*cm, 2*cm, 3.5*cm, 6*cm])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), GREEN1),
        ('TEXTCOLOR',  (0,0), (-1,0), WHITE),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('FONTNAME',   (3,1), (3,-1), 'Courier'),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [GREEN3, WHITE]),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    story.append(t3)

    # ── Section 3: Key statistics ─────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(_section_header('3. Statistiques clés', styles))

    slope_s = results.get('slope_stats', {})
    water_s = results.get('water_stats', {})
    elec_s  = results.get('elec_stats', {})

    key_stats = [
        ['Pente moyenne', f"{slope_s.get('slope_mean', 0):.2f}°"],
        ['Pente max', f"{slope_s.get('slope_max', 0):.1f}°"],
        ['Pente médiane (p50)', f"{slope_s.get('slope_p50', 0):.2f}°"],
        ['Distance min à l\'eau', f"{water_s.get('dist_water_min', 0):.0f} m"],
        ['Distance moy à l\'eau', f"{water_s.get('dist_water_mean', 0):.0f} m"],
        ['Distance min à l\'électricité', f"{elec_s.get('dist_grid_min', 0)/1000:.1f} km"],
        ['Score moyen global', f"{results.get('suit_stats', {}).get('suitability_mean', 0):.2f} / 10"],
        ['Score max global', f"{results.get('suit_stats', {}).get('suitability_max', 0):.2f} / 10"],
    ]
    story.append(_data_table(key_stats, col_widths=[8*cm, 9*cm], shaded=True))

    # ── Section 4: Methodology ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(_section_header('4. Méthodologie', styles))
    story.append(Paragraph(
        'Cette analyse utilise une approche de notation multicritère (0–10 par critère) '
        'combinée dans un score composite pondéré. Chaque pixel de 30×30 m est noté '
        'indépendamment. Les sources de données sont exclusivement publiques et '
        'accessibles via Google Earth Engine.',
        styles['body']
    ))
    story.append(Spacer(1, 0.3*cm))

    dataset_data = [
        ['Jeu de données', 'Identifiant GEE', 'Résolution', 'Utilisation'],
        ['SRTM DEM', 'USGS/SRTMGL1_003', '30 m', 'Pente, élévation relative'],
        ['HydroSHEDS', 'WWF/HydroSHEDS/15ACC', '~500 m', 'Réseau hydrographique'],
        ['Hansen GFC 2023', 'UMD/hansen/global_forest_change_2023_v1_11', '30 m', 'Couvert arboré (coût défrichage)'],
        ['ESA WorldCover 2021', 'ESA/WorldCover/v200', '10 m', 'Occupation du sol'],
        ['VIIRS mensuel', 'NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG', '~500 m', 'Lumières nocturnes (électricité)'],
    ]
    t4 = Table(dataset_data, colWidths=[4*cm, 5.5*cm, 2*cm, 5.5*cm])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLUE1),
        ('TEXTCOLOR',  (0,0), (-1,0), WHITE),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLUE2, WHITE]),
        ('LEFTPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    story.append(t4)

    # ── Section 5: Caveats ────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(_section_header('5. Limites et vérifications terrain requises', styles))

    caveats = [
        ('Précision topographique',
         'Le MNT SRTM a une erreur verticale de ±6–10 m. Les zones bien notées sur la pente '
         'doivent être re-levées par GNSS différentiel ou MNT Copernicus 10 m avant tout dimensionnement.'),
        ('Permanence des cours d\'eau',
         'HydroSHEDS identifie les chenaux de drainage mais ne confirme pas le débit en saison sèche. '
         'Une visite terrain en saison sèche est indispensable pour valider la disponibilité en eau.'),
        ('Sol et drainage',
         'Aucune donnée pédologique n\'est utilisée dans cette analyse. La texture, la perméabilité '
         'et la capacité de rétention d\'eau doivent être mesurées in situ par sondage.'),
        ('Occupation foncière',
         'Les pixels de déforestation (Hansen) indiquent une activité humaine existante. '
         'Un diagnostic foncier terrain est nécessaire avant toute mise en valeur.'),
        ('Électricité',
         'VIIRS mesure la luminosité nocturne, non la puissance ou la capacité du réseau. '
         'Vérifier auprès de l\'opérateur national (ENEO) le point de raccordement le plus proche.'),
    ]

    for title, text in caveats:
        story.append(Paragraph(f'<b>{title} :</b> {text}', styles['caveat']))
        story.append(Spacer(1, 0.15*cm))

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width='100%', thickness=1, color=GREEN2))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f'Rapport généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")} | '
        'Analyse de présélection par télédétection — ne pas utiliser pour dimensionnement d\'ingénierie.',
        styles['footer']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles['cover_title'] = ParagraphStyle('cover_title', fontSize=22, textColor=GREEN1,
        fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=6)
    styles['cover_sub'] = ParagraphStyle('cover_sub', fontSize=13, textColor=GREEN2,
        fontName='Helvetica', alignment=TA_CENTER, spaceAfter=14)
    styles['section_hdr'] = ParagraphStyle('section_hdr', fontSize=12, textColor=WHITE,
        fontName='Helvetica-Bold', backColor=GREEN1,
        leftIndent=6, rightIndent=6, spaceBefore=12, spaceAfter=8,
        leading=18, borderPadding=4)
    styles['h3'] = ParagraphStyle('h3', fontSize=10, textColor=BLUE1,
        fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=4)
    styles['body'] = ParagraphStyle('body', fontSize=9, textColor=BLACK,
        fontName='Helvetica', spaceAfter=6, leading=14)
    styles['caveat'] = ParagraphStyle('caveat', fontSize=9, textColor=BLACK,
        fontName='Helvetica', spaceAfter=4, leading=13,
        leftIndent=10, borderPadding=(4,6,4,6),
        backColor=AMBER, borderColor=colors.HexColor('#E65100'), borderWidth=0)
    styles['footer'] = ParagraphStyle('footer', fontSize=7, textColor=colors.grey,
        fontName='Helvetica', alignment=TA_CENTER)
    return styles


def _section_header(title: str, styles: dict):
    return Paragraph(title, styles['section_hdr'])


def _data_table(rows, col_widths=None, shaded=False):
    col_widths = col_widths or [6*cm, 11*cm]
    t = Table(rows, colWidths=col_widths)
    style = [
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('FONTNAME',    (0,0), (0,-1), 'Helvetica-Bold'),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
    ]
    if shaded:
        style.append(('ROWBACKGROUNDS', (0,0), (-1,-1), [GREY, WHITE]))
    t.setStyle(TableStyle(style))
    return t


def _fmt_coord(centroid):
    if not centroid or len(centroid) < 2:
        return 'N/A'
    return f"{centroid[1]:.5f}°N, {centroid[0]:.5f}°E"
