#!/usr/bin/env python3
"""
Peakweb GEO Pitch Deck Generator
Generates a 12-page Peakweb-branded pitch deck PDF from GEO audit data.

Usage:
    python generate_pitch_deck.py <json_data_file> [output_file.pdf]

The JSON data file should contain the audit results structured as documented
in skills/geo-pitch-deck/SKILL.md.
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, white, black, lightgrey
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether, Image as RLImage, ListFlowable, ListItem
    )
    from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
    from reportlab.graphics.charts.barcharts import VerticalBarChart
except ImportError:
    print("ERROR: ReportLab not installed. Run: pip install reportlab")
    sys.exit(1)


# ============================================================
# PEAKWEB COLOR PALETTE
# ============================================================
DEEP_BLUE = HexColor("#0A2C49")       # Primary dark, headers
AQUAMARINE = HexColor("#01EFA0")       # Bright accent, CTAs
LIGHT_GREEN = HexColor("#BCFF8A")      # Secondary accent
MIDNIGHT_GREEN = HexColor("#0A3E3C")   # Dark teal accent
LILAC = HexColor("#9892B5")            # Subtle accent
STONE = HexColor("#FCF7E6")            # Light background

# Semantic colors
PRIMARY = DEEP_BLUE
ACCENT = AQUAMARINE
SUCCESS = HexColor("#00b894")
WARNING = HexColor("#fdcb6e")
DANGER = HexColor("#d63031")
INFO = HexColor("#0984e3")
TEXT_PRIMARY = DEEP_BLUE
TEXT_SECONDARY = HexColor("#636e72")
LIGHT_BG = STONE
WHITE = white
BLACK = black


def get_score_color(score):
    """Return color based on score value."""
    if score >= 80:
        return SUCCESS
    elif score >= 60:
        return INFO
    elif score >= 40:
        return WARNING
    else:
        return DANGER


def get_score_label(score):
    """Return label based on score value."""
    if score >= 85:
        return "EXCELLENT"
    elif score >= 70:
        return "GOOD"
    elif score >= 55:
        return "FAIR"
    elif score >= 40:
        return "BELOW AVERAGE"
    else:
        return "NEEDS ATTENTION"


def create_score_gauge(score, width=150, height=150):
    """Create a visual score gauge with Peakweb styling."""
    d = Drawing(width, height)

    # Background circle
    d.add(Circle(width/2, height/2, 60, fillColor=LIGHT_BG, strokeColor=DEEP_BLUE, strokeWidth=3))

    # Score arc (simplified as colored circle)
    color = get_score_color(score)
    d.add(Circle(width/2, height/2, 52, fillColor=color, strokeColor=None))

    # Inner white circle
    d.add(Circle(width/2, height/2, 40, fillColor=WHITE, strokeColor=None))

    # Score text
    d.add(String(width/2, height/2 + 8, str(score),
                 fontSize=28, fontName='Helvetica-Bold',
                 fillColor=DEEP_BLUE, textAnchor='middle'))

    # Label
    d.add(String(width/2, height/2 - 12, "/ 100",
                 fontSize=12, fontName='Helvetica',
                 fillColor=TEXT_SECONDARY, textAnchor='middle'))

    return d


def create_progress_bar(current, projected, width=400, height=60):
    """Create a progress bar showing current vs projected score."""
    d = Drawing(width, height)

    bar_y = height / 2
    bar_height = 20
    bar_width = width - 100

    # Background bar
    d.add(Rect(50, bar_y - bar_height/2, bar_width, bar_height,
               fillColor=LIGHT_BG, strokeColor=DEEP_BLUE, strokeWidth=1))

    # Current score bar
    current_width = (current / 100) * bar_width
    d.add(Rect(50, bar_y - bar_height/2, current_width, bar_height,
               fillColor=get_score_color(current), strokeColor=None))

    # Projected line
    projected_x = 50 + (projected / 100) * bar_width
    d.add(Line(projected_x, bar_y - bar_height/2 - 5, projected_x, bar_y + bar_height/2 + 5,
               strokeColor=AQUAMARINE, strokeWidth=3))

    # Labels
    d.add(String(50 + current_width/2, bar_y + 2, str(current),
                 fontSize=12, fontName='Helvetica-Bold',
                 fillColor=WHITE, textAnchor='middle'))

    d.add(String(projected_x, bar_y + bar_height/2 + 15, str(projected),
                 fontSize=10, fontName='Helvetica-Bold',
                 fillColor=AQUAMARINE, textAnchor='middle'))

    # Legend
    d.add(String(10, bar_y, "Current",
                 fontSize=8, fontName='Helvetica',
                 fillColor=TEXT_SECONDARY, textAnchor='start'))

    d.add(String(width - 10, bar_y, "Projected",
                 fontSize=8, fontName='Helvetica',
                 fillColor=AQUAMARINE, textAnchor='end'))

    return d


def build_styles():
    """Create Peakweb-branded paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='PeakTitle',
        fontName='Helvetica-Bold',
        fontSize=28,
        textColor=DEEP_BLUE,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='PeakSubtitle',
        fontName='Helvetica',
        fontSize=14,
        textColor=TEXT_SECONDARY,
        spaceAfter=20,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='PeakH1',
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=DEEP_BLUE,
        spaceBefore=20,
        spaceAfter=12,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='PeakH2',
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=DEEP_BLUE,
        spaceBefore=16,
        spaceAfter=8,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='PeakH3',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=MIDNIGHT_GREEN,
        spaceBefore=12,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='PeakBody',
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        spaceBefore=4,
        spaceAfter=4,
        leading=14,
        alignment=TA_JUSTIFY,
    ))

    styles.add(ParagraphStyle(
        name='PeakBodyLeft',
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        spaceBefore=4,
        spaceAfter=4,
        leading=14,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='PeakSmall',
        fontName='Helvetica',
        fontSize=8,
        textColor=TEXT_SECONDARY,
        spaceBefore=2,
        spaceAfter=2,
    ))

    styles.add(ParagraphStyle(
        name='PeakBullet',
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        leftIndent=20,
        spaceBefore=3,
        spaceAfter=3,
        bulletIndent=10,
        leading=14,
    ))

    styles.add(ParagraphStyle(
        name='PeakIssueTitle',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=DANGER,
        spaceBefore=12,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name='PeakCallout',
        fontName='Helvetica-Oblique',
        fontSize=9,
        textColor=TEXT_SECONDARY,
        leftIndent=10,
        spaceBefore=4,
        spaceAfter=8,
        leading=12,
    ))

    styles.add(ParagraphStyle(
        name='PeakCTA',
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=AQUAMARINE,
        alignment=TA_CENTER,
        spaceBefore=20,
        spaceAfter=10,
    ))

    styles.add(ParagraphStyle(
        name='PeakFooter',
        fontName='Helvetica',
        fontSize=8,
        textColor=TEXT_SECONDARY,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='PeakCenter',
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=4,
    ))

    return styles


def peakweb_header_footer(canvas, doc):
    """Add Peakweb header and footer to each page."""
    canvas.saveState()

    # Header line with Peakweb green
    canvas.setStrokeColor(AQUAMARINE)
    canvas.setLineWidth(2)
    canvas.line(50, letter[1] - 40, letter[0] - 50, letter[1] - 40)

    # Footer
    canvas.setStrokeColor(lightgrey)
    canvas.setLineWidth(0.5)
    canvas.line(50, 40, letter[0] - 50, 40)

    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(TEXT_SECONDARY)
    canvas.drawString(50, 28, "Peakweb | peakweb.io")
    canvas.drawRightString(letter[0] - 50, 28, f"Page {doc.page}")
    canvas.drawCentredString(letter[0] / 2, 28, "Confidential")

    canvas.restoreState()


def make_peakweb_table_style(header_color=DEEP_BLUE):
    """Create a Peakweb-branded table style."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, lightgrey),
        ('BACKGROUND', (0, 1), (-1, -1), WHITE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, STONE]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ])


def generate_pitch_deck(data, output_path="PeakwebGEOProposal.pdf"):
    """Generate the full Peakweb pitch deck PDF."""

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=55,
        bottomMargin=55,
        leftMargin=50,
        rightMargin=50,
    )

    styles = build_styles()
    elements = []

    # Extract data with defaults
    client_name = data.get("client_name", "Client")
    contact_name = data.get("contact_name", "")
    contact_title = data.get("contact_title", "")
    client_website = data.get("client_website", "")
    report_date = data.get("report_date", datetime.now().strftime("%B %d, %Y"))

    geo_score = data.get("geo_score", 50)
    score_label = data.get("score_label", get_score_label(geo_score))
    score_description = data.get("score_description", "")
    projected_score = data.get("projected_score", min(geo_score + 30, 95))

    sample_query = data.get("sample_query", "")
    years = data.get("years", "")
    bbb_rating = data.get("bbb_rating", "")
    city = data.get("city", "")
    industry = data.get("industry", "")
    service_type = data.get("service_type", "")

    working = data.get("working", [])
    means = data.get("means", [])
    issues = data.get("issues", [])
    nothing_short = data.get("nothing_short", [])
    nothing_long = data.get("nothing_long", [])
    opportunities = data.get("opportunities", [])
    week_scores = data.get("week_scores", [65, 72, 80, 85])
    roi = data.get("roi", {})
    before_lines = data.get("before_lines", [])
    after_lines = data.get("after_lines", [])
    faqs = data.get("faqs", [])
    bottom_line = data.get("bottom_line", [])

    # ============================================================
    # PAGE 1: COVER
    # ============================================================
    elements.append(Spacer(1, 80))

    # Try to load logo
    logo_paths = [
        "assets/PeakWeb-Green-RGB.jpg",
        "../assets/PeakWeb-Green-RGB.jpg",
        os.path.expanduser("~/.claude/skills/geo/assets/PeakWeb-Green-RGB.jpg"),
    ]
    logo_loaded = False
    for logo_path in logo_paths:
        if os.path.exists(logo_path):
            try:
                logo = RLImage(logo_path, width=150, height=50)
                elements.append(logo)
                logo_loaded = True
                break
            except Exception:
                pass

    if not logo_loaded:
        elements.append(Paragraph("PEAKWEB", styles['PeakTitle']))

    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Website Visibility", styles['PeakTitle']))
    elements.append(Paragraph("Audit", styles['PeakTitle']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("GEO Analysis &amp; Implementation Proposal", styles['PeakSubtitle']))

    elements.append(Spacer(1, 40))
    elements.append(HRFlowable(width="100%", thickness=2, color=AQUAMARINE, spaceAfter=20))

    # Client details table
    contact_display = f"{contact_name}, {contact_title}" if contact_name and contact_title else contact_name or ""
    details_data = [
        ["PREPARED FOR", contact_display],
        ["", client_name],
        ["WEBSITE", client_website],
        ["DATE", report_date],
    ]

    details_table = Table(details_data, colWidths=[100, 350])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SECONDARY),
        ('TEXTCOLOR', (1, 0), (1, -1), DEEP_BLUE),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(details_table)

    elements.append(PageBreak())

    # ============================================================
    # PAGE 2: EXECUTIVE SUMMARY
    # ============================================================
    elements.append(Paragraph("Executive Summary", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    if sample_query and years and bbb_rating:
        exec_text = (
            f'When someone asks ChatGPT, Google AI, or Perplexity a question like '
            f'<i>"{sample_query}"</i> your business is rarely mentioned – even though you have '
            f'{years} years of experience and an {bbb_rating} BBB rating.'
        )
    else:
        exec_text = (
            'When potential customers ask AI assistants about services like yours, '
            'your business is rarely mentioned – not because you\'re not qualified, '
            'but because your website doesn\'t communicate effectively with AI systems yet.'
        )
    elements.append(Paragraph(exec_text, styles['PeakBody']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "This audit identifies the specific gaps holding you back and outlines what needs to change. "
        "Every issue has a proven solution – Peakweb can guide implementation to ensure it's done right the first time.",
        styles['PeakBody']
    ))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("The New Reality: AI Search", styles['PeakH2']))
    elements.append(Paragraph(
        "The way people find local businesses is changing rapidly. Traditional Google Search still matters – "
        "customers search and get a list of links. But <b>AI Search is growing fast</b>: customers ask ChatGPT or "
        "Perplexity a question and get 2–3 direct recommendations. Those recommended businesses get the calls.",
        styles['PeakBody']
    ))

    if city and industry:
        elements.append(Paragraph(
            f"Right now, AI systems answering questions about {city} {industry} or {service_type} services rarely "
            "mention your business. Not because you're not qualified, but because your website doesn't communicate "
            "effectively with AI systems yet.",
            styles['PeakBody']
        ))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("What Is GEO?", styles['PeakH2']))
    elements.append(Paragraph(
        "<b>GEO = Generative Engine Optimization</b>",
        styles['PeakBodyLeft']
    ))
    elements.append(Paragraph("• <b>SEO</b> = Making your website show up in Google search results", styles['PeakBullet']))
    elements.append(Paragraph("• <b>GEO</b> = Making your website get recommended by ChatGPT, Claude, Google AI, and Perplexity", styles['PeakBullet']))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "Studies show that <b>30–115% more people</b> discover businesses optimized for AI search compared to those that "
        "aren't. Your competitors who figure this out first will capture those leads.",
        styles['PeakBody']
    ))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 3: YOUR CURRENT SCORE
    # ============================================================
    elements.append(Paragraph("Your Current Score", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    # Score gauge
    gauge = create_score_gauge(geo_score)
    elements.append(gauge)

    score_color = get_score_color(geo_score)
    elements.append(Paragraph(
        f'<font color="{score_color.hexval()}"><b>{score_label}</b></font> – {score_description}',
        styles['PeakCenter']
    ))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("What's Working Well", styles['PeakH2']))

    for item in working[:5]:
        elements.append(Paragraph(f"• {item}", styles['PeakBullet']))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "<b>The foundation is solid.</b> Peakweb's job is to make AI systems <i>notice</i> it.",
        styles['PeakBody']
    ))

    if means:
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("What This Means For Your Business", styles['PeakH2']))
        if city and industry:
            elements.append(Paragraph(
                f"When AI systems answer questions about {city} {industry} or {service_type} services, "
                "they rarely mention your business. This means:",
                styles['PeakBody']
            ))
        for item in means[:3]:
            elements.append(Paragraph(f"• {item}", styles['PeakBullet']))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 4: THE 6 KEY ISSUES (Part 1)
    # ============================================================
    elements.append(Paragraph("The 6 Key Issues Identified", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    for i, issue in enumerate(issues[:3], 1):
        title = issue.get("title", f"Issue {i}")
        body = issue.get("body", "")
        callout = issue.get("callout", issue.get("example", ""))

        elements.append(Paragraph(f"<b>{i}. {title}</b>", styles['PeakIssueTitle']))
        elements.append(Paragraph(body, styles['PeakBody']))
        if callout:
            elements.append(Paragraph(callout, styles['PeakCallout']))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 5: THE 6 KEY ISSUES (Part 2)
    # ============================================================
    for i, issue in enumerate(issues[3:6], 4):
        title = issue.get("title", f"Issue {i}")
        body = issue.get("body", "")
        callout = issue.get("callout", issue.get("example", ""))

        elements.append(Paragraph(f"<b>{i}. {title}</b>", styles['PeakIssueTitle']))
        elements.append(Paragraph(body, styles['PeakBody']))
        if callout:
            elements.append(Paragraph(callout, styles['PeakCallout']))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 6: WHAT HAPPENS IF YOU DO NOTHING
    # ============================================================
    elements.append(Paragraph("What Happens If You Do Nothing?", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    elements.append(Paragraph("<b>Short-term (Next 6 months):</b>", styles['PeakH3']))
    for item in nothing_short[:3]:
        elements.append(Paragraph(f"• {item}", styles['PeakBullet']))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>Long-term (1–2 years):</b>", styles['PeakH3']))
    for item in nothing_long[:3]:
        elements.append(Paragraph(f"• {item}", styles['PeakBullet']))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "<b>Think of it like websites in 2005:</b> Early adopters who built websites got a huge advantage. "
        "Those who waited until 2010 had to catch up in a crowded market. We're at that same inflection point "
        "with AI search right now.",
        styles['PeakBody']
    ))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 7: THE OPPORTUNITY
    # ============================================================
    elements.append(Paragraph("The Opportunity", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    elements.append(Paragraph(
        "Our audit identified issues across four key areas that are preventing AI systems from recommending your "
        "business. The good news: every one of them is fixable, and the projected impact is significant.",
        styles['PeakBody']
    ))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Your Score Improvement Potential", styles['PeakH2']))

    # Progress bar
    progress = create_progress_bar(geo_score, projected_score)
    elements.append(progress)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Areas Requiring Attention:</b>", styles['PeakH3']))

    if opportunities:
        opp_data = [["#", "Area", "Description"]]
        for i, opp in enumerate(opportunities[:4], 1):
            opp_data.append([str(i), opp.get("area", ""), opp.get("desc", "")])

        opp_table = Table(opp_data, colWidths=[30, 150, 280])
        opp_table.setStyle(make_peakweb_table_style())
        elements.append(opp_table)

    elements.append(Spacer(1, 15))
    elements.append(Paragraph(
        "Each of these areas involves multiple coordinated changes that must be implemented correctly and in the "
        "right sequence. Peakweb's GEO methodology addresses all four areas in a structured 30-day engagement – "
        "validated across every major AI platform.",
        styles['PeakBody']
    ))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 8: HOW PEAKWEB GETS YOU THERE
    # ============================================================
    elements.append(Paragraph("How Peakweb Gets You There", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    elements.append(Paragraph(
        "Our GEO methodology follows a proven 4-week rollout, sequenced so each phase builds on the last. "
        "You stay focused on running your business while we handle the technical implementation.",
        styles['PeakBody']
    ))

    elements.append(Spacer(1, 15))

    weeks = [
        ("Week 1", "Technical Foundation", "Peakweb-led",
         "Deploy all critical AI configuration and discovery signals. Resolve trust and consistency issues."),
        ("Week 2", "Authority & Identity", "Collaborative",
         "Build your verified presence on key AI-indexed platforms. Structure content for AI consumption."),
        ("Week 3", "Content Depth", "Collaborative",
         f"Publish AI-optimized content that positions you as the {city} authority. Enrich with verifiable data."),
        ("Week 4", "Validation & Launch", "Peakweb-led",
         "QA across all major AI platforms. Deliver monitoring dashboard and ongoing content strategy."),
    ]

    for i, (week, title, led_by, desc) in enumerate(weeks):
        score_target = week_scores[i] if i < len(week_scores) else projected_score
        elements.append(Paragraph(f"<b>{week}: {title}</b>", styles['PeakH3']))
        elements.append(Paragraph(f"<i>Led by: {led_by} | Expected Score: {score_target}/100</i>", styles['PeakSmall']))
        elements.append(Paragraph(desc, styles['PeakBody']))
        elements.append(Spacer(1, 8))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 9: WORKING WITH PEAKWEB (Pricing)
    # ============================================================
    elements.append(Paragraph("Working With Peakweb", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    elements.append(Paragraph(
        "GEO optimization involves specialized technical work – structured data formats, AI crawler protocols, and "
        "platform-specific configurations that change frequently. A general web developer can update your content, "
        "but the AI-specific implementation requires expertise in how each AI platform indexes and ranks local businesses.",
        styles['PeakBody']
    ))

    elements.append(Spacer(1, 15))

    # Package 1
    elements.append(Paragraph("<b>GEO Essentials – Guided Implementation ($1,000)</b>", styles['PeakH3']))
    elements.append(Paragraph(
        "Peakweb handles all priority technical fixes, deploys AI configuration files, implements structured data, and "
        "validates your site across all major AI platforms. You provide business content; we handle the rest. "
        "Includes 30-day post-launch monitoring.",
        styles['PeakBody']
    ))

    elements.append(Spacer(1, 10))

    # Package 2
    elements.append(Paragraph("<b>GEO Growth – Full 30-Day Engagement ($2,000–$3,000)</b>", styles['PeakH3']))
    elements.append(Paragraph(
        "Everything in Essentials plus: authority-building across AI-indexed platforms, AI-optimized content creation "
        "(guides, FAQs, case studies), video channel repair, and a 90-day monitoring dashboard. Best for maximum "
        "visibility in the shortest time.",
        styles['PeakBody']
    ))

    elements.append(Spacer(1, 10))

    # Package 3
    elements.append(Paragraph("<b>GEO Partner – Ongoing Optimization ($500/month)</b>", styles['PeakH3']))
    elements.append(Paragraph(
        "After initial implementation, Peakweb monitors your AI visibility monthly, publishes fresh content to maintain "
        "relevance signals, and adapts your strategy as AI platforms evolve. Ensures you stay ahead of competitors long-term.",
        styles['PeakBody']
    ))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 10: ROI & SEO vs GEO
    # ============================================================
    elements.append(Paragraph("Expected Return on Investment", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    if roi:
        roi_data = [
            [roi.get("leads_per_month", "5-8"), roi.get("customers_per_month", "2-3"),
             roi.get("monthly_rev", "$1,000-3,000"), roi.get("annual_impact", "$12,000-36,000")],
            ["Additional Leads/Mo", "New Customers/Mo", "Add'l Monthly Rev", "Annual Impact"],
        ]

        roi_table = Table(roi_data, colWidths=[115, 115, 115, 115])
        roi_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 16),
            ('TEXTCOLOR', (0, 0), (-1, 0), AQUAMARINE),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, 1), 8),
            ('TEXTCOLOR', (0, 1), (-1, 1), TEXT_SECONDARY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(roi_table)

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "<b>Break-even:</b> Implementation pays for itself in the first month. Unlike one-time marketing, these "
        "improvements keep working 24/7 with compounding returns.",
        styles['PeakBody']
    ))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Traditional SEO vs. GEO", styles['PeakH2']))

    comparison_data = [
        ["Traditional SEO", "GEO (AI Optimization)"],
        ["Goal: Rank in Google's 10 blue links", "Goal: Get mentioned by ChatGPT / AI"],
        ["Optimizes for keywords", "Optimizes for natural language questions"],
        ["Success = page 1 ranking", "Success = AI recommendation"],
        ["Established practice (20+ years)", "Emerging practice (critical now)"],
    ]

    comp_table = Table(comparison_data, colWidths=[230, 230])
    comp_table.setStyle(make_peakweb_table_style())
    elements.append(comp_table)

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "<b>You need BOTH.</b> Traditional SEO gets you found in Google. GEO gets you recommended by AI. "
        "The catch: most SEO services don't include GEO yet. Early movers win.",
        styles['PeakBody']
    ))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 11: BEFORE/AFTER + FAQs
    # ============================================================
    elements.append(Paragraph("What This Looks Like in Practice", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    if before_lines:
        elements.append(Paragraph("<b>BEFORE Optimization</b>", styles['PeakH3']))
        for line in before_lines[:5]:
            elements.append(Paragraph(line, styles['PeakSmall']))
        elements.append(Spacer(1, 10))

    if after_lines:
        elements.append(Paragraph("<b>AFTER Optimization</b>", styles['PeakH3']))
        for line in after_lines[:6]:
            elements.append(Paragraph(line, styles['PeakSmall']))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "<b>Same customer, same question.</b> One scenario: they never hear about you. "
        "The other: you're recommended first with supporting details.",
        styles['PeakBody']
    ))

    if faqs:
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("Frequently Asked Questions", styles['PeakH2']))
        for faq in faqs[:2]:
            elements.append(Paragraph(f"<b>\"{faq.get('q', '')}\"</b>", styles['PeakH3']))
            elements.append(Paragraph(faq.get('a', ''), styles['PeakBody']))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 12: NEXT STEPS / CTA
    # ============================================================
    elements.append(Paragraph("Next Steps", styles['PeakH1']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AQUAMARINE, spaceAfter=12))

    steps = [
        ("1", "Schedule a 30-Minute Strategy Call with Peakweb",
         "We'll walk through this audit together, answer your questions, and recommend the right engagement level."),
        ("2", "Choose Your Implementation Package",
         "GEO Essentials ($1,000) for priority technical fixes, GEO Growth ($2,000–$3,000) for the full 30-day roadmap, "
         "or GEO Partner ($500/mo) for ongoing optimization."),
        ("3", "Gather Your Business Content",
         "While Peakweb handles the technical side, you'll want to have project photos, customer stories, and service details ready."),
        ("4", "Implementation Begins",
         "Peakweb deploys changes in the sequence outlined in our 30-day roadmap, with check-ins at each milestone."),
        ("5", "Track Results Together",
         "We'll monitor your visibility across ChatGPT, Perplexity, Google AI, and Claude – and provide monthly reports."),
    ]

    for num, title, desc in steps:
        elements.append(Paragraph(f"<b>{num}. {title}</b>", styles['PeakH3']))
        elements.append(Paragraph(desc, styles['PeakBody']))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("The Bottom Line", styles['PeakH2']))

    for line in bottom_line[:2]:
        elements.append(Paragraph(line, styles['PeakBody']))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph(
        "Ready to get started? Reach out to Peakweb to schedule your strategy call. "
        "We'll map out the fastest path to getting your business recommended by AI.",
        styles['PeakBody']
    ))

    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=2, color=AQUAMARINE, spaceAfter=15))

    elements.append(Paragraph("Ready to Get Started?", styles['PeakCTA']))
    elements.append(Paragraph(
        "Schedule your free strategy call and we'll walk through every finding together.",
        styles['PeakCenter']
    ))
    elements.append(Paragraph(
        "<b>Your business deserves to be seen. Let's make it happen.</b>",
        styles['PeakCenter']
    ))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("peakweb.io", styles['PeakCTA']))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"<i>This report was prepared {report_date} for {client_name}. "
        "Results and timelines are based on current AI search landscape. Individual results may vary.</i>",
        styles['PeakSmall']
    ))

    # ============================================================
    # BUILD PDF
    # ============================================================
    doc.build(elements, onFirstPage=peakweb_header_footer, onLaterPages=peakweb_header_footer)
    return output_path


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Generate a sample for demonstration
        sample_data = {
            "client_name": "Denver Sprinkler & Landscape",
            "contact_name": "Ramon Robles",
            "contact_title": "Owner",
            "client_website": "denversprinklerservices.com",
            "report_date": "March 17, 2026",

            "geo_score": 53,
            "score_label": "FAIR",
            "score_description": "Your website is functional but not optimized for AI systems. AI search engines can access your site but rarely cite or recommend it.",
            "projected_score": 85,

            "sample_query": "Who does sprinkler repair in Denver?",
            "years": "25",
            "bbb_rating": "A+",
            "city": "Denver",
            "industry": "landscaping",
            "service_type": "sprinkler",

            "working": [
                "Your website is accessible - AI systems can read your content",
                "Strong reputation - BBB A+ rating, Trees.com #6 in Denver, 20+ testimonials",
                "Complete contact info - address, phone, hours clearly listed",
                "Professional website - clean design, mobile-friendly, secure (HTTPS)",
                "Real experience - 25+ years in the industry, established business"
            ],

            "means": [
                "Lost phone calls from potential customers who never hear your name",
                "Competitors who optimize for AI get recommended instead of you",
                "Your 25 years of experience and A+ rating are invisible to these systems"
            ],

            "issues": [
                {
                    "title": "AI Systems Don't Know Who You Are",
                    "body": "Your business has no 'identity' in AI databases - no Wikipedia page, no LinkedIn company page, minimal online presence beyond your website.",
                    "callout": "Impact: Lost leads from the 30-40% of people now using AI to research local services."
                },
                {
                    "title": "Your Website Has No Dates On Anything",
                    "body": "Not a single page shows when it was published or last updated. AI systems assume undated content is stale and won't cite it.",
                    "callout": "Real example: Customer asks about 2026 prices - AI cites competitor's dated blog, ignores your undated page."
                },
                {
                    "title": "20+ Testimonials Are Hidden From AI",
                    "body": "You have 20+ customer testimonials but they're not marked up in a way AI systems can understand. No star ratings show up in Google results.",
                    "callout": "This is solvable in under an hour with the right technical implementation."
                },
                {
                    "title": "Content Is Generic Marketing Copy",
                    "body": "Your service pages use generic phrases like 'professional sprinkler repair services' but lack specific, verifiable data that AI systems look for.",
                    "callout": "AI systems cite websites with concrete data - not marketing language."
                },
                {
                    "title": "Missing Technical Files AI Systems Look For",
                    "body": "Your site is missing critical configuration files that AI systems rely on to understand and index your business.",
                    "callout": "It's like having a store with no sign out front and the lights off."
                },
                {
                    "title": "Business Age Inconsistency Hurts Trust",
                    "body": "Your website says '25+ years in business' but BBB shows business started in 2011 (14 years ago). AI systems fact-check claims.",
                    "callout": "When they find conflicting information, they either skip citing you or mention the discrepancy."
                }
            ],

            "nothing_short": [
                "Competitors who optimize for AI will get recommended more often",
                "You'll continue missing leads from the growing AI search audience (30-40% of searches)",
                "The gap between you and optimized competitors widens"
            ],

            "nothing_long": [
                "AI search becomes the dominant way people find local services",
                "Businesses without AI visibility become increasingly invisible",
                "Playing catch-up gets harder as competitors build content libraries and authority"
            ],

            "opportunities": [
                {"area": "Technical Configuration", "desc": "Deploy all critical AI configuration and discovery signals"},
                {"area": "Content & Authority Signals", "desc": "Build verified presence on key AI-indexed platforms"},
                {"area": "Trust & Consistency", "desc": "Resolve conflicting information across platforms"},
                {"area": "Freshness & Relevance", "desc": "Add dates and current data to all content"}
            ],

            "week_scores": [65, 72, 80, 85],

            "roi": {
                "leads_per_month": "7-8",
                "customers_per_month": "2-3",
                "monthly_rev": "$1,000-6,000",
                "annual_impact": "$12,000-72,000"
            },

            "before_lines": [
                "Customer: 'Hey ChatGPT, who should I call for sprinkler repair in Denver?'",
                "ChatGPT: 'Here are some well-reviewed options:'",
                "- GreenCo Irrigation (mentioned in multiple sources)",
                "- Colorado Sprinkler Pros (4.8 stars)",
                "Your business: Not mentioned"
            ],

            "after_lines": [
                "Customer: 'Hey ChatGPT, who should I call for sprinkler repair in Denver?'",
                "ChatGPT: 'Here are some well-reviewed options:'",
                "- Denver Sprinkler and Landscape (25+ years, BBB A+, since 2011)",
                "- GreenCo Irrigation",
                "Your business: Mentioned FIRST with specific details"
            ],

            "faqs": [
                {
                    "q": "Is this really necessary? My business is doing fine.",
                    "a": "Your business IS doing fine. But consider: in 2005, many businesses said 'I don't need a website.' In 2010, they said 'I don't need Google reviews.' Those who adapted early dominated. AI search is the next shift."
                },
                {
                    "q": "How long will these changes stay relevant?",
                    "a": "The technical fixes are permanent foundations. The content strategies are ongoing assets that appreciate over time. These are solid business practices that happen to also optimize for AI."
                }
            ],

            "bottom_line": [
                "You've built an excellent business over 25 years. You have the experience, the reputation, and the satisfied customers to prove it.",
                "The only thing holding you back is that AI systems don't know about it yet."
            ]
        }

        output_file = "PeakwebGEOProposal-Sample.pdf"
        result = generate_pitch_deck(sample_data, output_file)
        print(f"Sample pitch deck generated: {result}")

    else:
        # Load data from file
        input_path = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "PeakwebGEOProposal.pdf"

        if input_path == "-":
            data = json.loads(sys.stdin.read())
        else:
            with open(input_path) as f:
                data = json.load(f)

        result = generate_pitch_deck(data, output_file)
        print(f"Pitch deck generated: {result}")
