#!/usr/bin/env python3
"""
GEO Roadmap PDF Generator
=========================
Generates a clean, branded PDF roadmap from action plan JSON.
Follows the same ReportLab canvas pattern as generate_pitch_deck.py.

Usage:
    python3 generate_roadmap_pdf.py                          # uses sample data
    python3 generate_roadmap_pdf.py data.json                # reads JSON file
    python3 generate_roadmap_pdf.py data.json output.pdf     # custom output name

JSON input: the output of action_plan_generator.py (or /tmp/roadmap-data.json)
"""

import json
import math
import os
import sys
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
FONTS_DIR = os.path.join(PROJECT_DIR, "assets/fonts")
LOGO_PATH = os.path.join(PROJECT_DIR, "assets/PeakWeb-Green-RGB.png")
W_CHEVRON_PATH = os.path.join(PROJECT_DIR, "assets/PeakWeb-W-Chevron.png")

# ---------------------------------------------------------------------------
# Page dimensions
# ---------------------------------------------------------------------------
PAGE_WIDTH, PAGE_HEIGHT = letter   # 612 x 792 points
MARGIN = 54                        # 0.75 inch

# ---------------------------------------------------------------------------
# Brand colours (RGB tuples 0-1) — same palette as generate_pitch_deck.py
# ---------------------------------------------------------------------------
DEEP_BLUE      = (10/255, 44/255, 73/255)        # #0A2C49
AQUAMARINE     = (1/255, 239/255, 160/255)       # #01EFA0
LIGHT_GREEN    = (188/255, 255/255, 138/255)     # #BCFF8A
MIDNIGHT_GREEN = (10/255, 62/255, 60/255)        # #0A3E3C
STONE          = (252/255, 247/255, 230/255)     # #FCF7E6
WHITE          = (1, 1, 1)
AMBER          = (245/255, 166/255, 35/255)      # #F5A623 — warning / low scores
MUTED_BLUE     = (148/255, 184/255, 204/255)     # #94B8CC — labels
SCORE_BAR_BG   = (232/255, 236/255, 240/255)     # #E8ECF0
SOFT_RED_BG    = (255/255, 240/255, 240/255)     # #FFF0F0
SOFT_GREEN_BG  = (239/255, 255/255, 239/255)     # #EFFFEF

# ReportLab colour objects
C_DEEP_BLUE      = colors.Color(*DEEP_BLUE)
C_AQUAMARINE     = colors.Color(*AQUAMARINE)
C_LIGHT_GREEN    = colors.Color(*LIGHT_GREEN)
C_MIDNIGHT_GREEN = colors.Color(*MIDNIGHT_GREEN)
C_STONE          = colors.Color(*STONE)
C_WHITE          = colors.white
C_AMBER          = colors.Color(*AMBER)
C_MUTED_BLUE     = colors.Color(*MUTED_BLUE)
C_SCORE_BAR_BG   = colors.Color(*SCORE_BAR_BG)

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_REGULAR  = 'Helvetica'
FONT_BOLD     = 'Helvetica-Bold'
FONT_ITALIC   = 'Helvetica-Oblique'


def register_fonts():
    """Try to register Outfit fonts, fall back to Helvetica if not available."""
    global FONT_REGULAR, FONT_BOLD
    try:
        pdfmetrics.registerFont(TTFont("Outfit-Regular",   os.path.join(FONTS_DIR, "Outfit-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Outfit-Bold",      os.path.join(FONTS_DIR, "Outfit-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("Outfit-SemiBold",  os.path.join(FONTS_DIR, "Outfit-SemiBold.ttf")))
        FONT_REGULAR = "Outfit-Regular"
        FONT_BOLD    = "Outfit-Bold"
    except Exception:
        pass  # Helvetica fallback is fine


# ---------------------------------------------------------------------------
# Score colour helpers
# ---------------------------------------------------------------------------

def _score_colour(score: int):
    """Traffic-light colour for a 0-100 score."""
    if score >= 75:
        return colors.Color(0, 0.6, 0.3)    # green
    elif score >= 60:
        return colors.Color(0.06, 0.47, 0.71)  # blue
    elif score >= 40:
        return C_AMBER                         # amber
    return colors.Color(0.8, 0.1, 0.1)        # red


def _score_label(score: int) -> str:
    if score >= 90: return "Excellent"
    if score >= 75: return "Good"
    if score >= 60: return "Fair"
    if score >= 40: return "Poor"
    return "Critical"


def _impact_colour(level: str):
    return {
        "very_high": colors.Color(0.8, 0.1, 0.1),
        "high":      colors.Color(0.85, 0.45, 0.1),
        "medium":    colors.Color(0.7, 0.6, 0.0),
        "low":       colors.Color(0.4, 0.4, 0.4),
    }.get(level, colors.Color(0.4, 0.4, 0.4))


def _difficulty_colour(level: str):
    return {
        "low":      colors.Color(0, 0.55, 0.3),
        "medium":   colors.Color(0.7, 0.6, 0),
        "high":     colors.Color(0.85, 0.45, 0.1),
        "very_high": colors.Color(0.8, 0.1, 0.1),
    }.get(level, colors.Color(0.4, 0.4, 0.4))


def _horizon_colour(h: str):
    return {
        "immediate": colors.Color(0.8, 0.1, 0.1),
        "near_term": colors.Color(0.7, 0.6, 0),
        "long_term": colors.Color(0.4, 0.4, 0.4),
    }.get(h, colors.Color(0.4, 0.4, 0.4))


# ---------------------------------------------------------------------------
# Common drawing helpers
# ---------------------------------------------------------------------------

def _draw_header(c: canvas.Canvas, page_num: int, brand: str):
    """Top accent bar + page number + confidential label."""
    c.setFillColorRGB(*DEEP_BLUE)
    c.rect(0, PAGE_HEIGHT - 8, PAGE_WIDTH, 8, fill=1, stroke=0)
    c.setFillColorRGB(*MUTED_BLUE)
    c.setFont(FONT_REGULAR, 8)
    c.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 22, f"Confidential — {brand}")
    c.setFillColorRGB(*MUTED_BLUE)
    c.drawRightString(PAGE_WIDTH - MARGIN, 18, f"Page {page_num}")


def _draw_logo(c: canvas.Canvas, x: float, y: float, w: float = 100):
    """Draw Peakweb logo if available."""
    if os.path.exists(LOGO_PATH):
        ratio = 1
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(LOGO_PATH)
            iw, ih = img.getSize()
            ratio = ih / iw
        except Exception:
            ratio = 0.25
        c.drawImage(LOGO_PATH, x, y, width=w, height=w * ratio,
                    preserveAspectRatio=True, mask="auto")


def _draw_section_heading(c: canvas.Canvas, text: str, y: float, bg_colour=None) -> float:
    """Draw a section heading bar. Returns y position after the bar."""
    bg = bg_colour or DEEP_BLUE
    c.setFillColorRGB(*bg)
    c.rect(MARGIN, y - 4, PAGE_WIDTH - 2 * MARGIN, 22, fill=1, stroke=0)
    c.setFillColorRGB(*AQUAMARINE)
    c.setFont(FONT_BOLD, 11)
    c.drawString(MARGIN + 8, y + 4, text.upper())
    return y - 30


def _badge(c: canvas.Canvas, text: str, x: float, y: float, colour, width: float = 80):
    """Draw a small coloured badge pill."""
    h = 14
    r = h / 2
    # Draw rounded rect via arc + lines approximation using a simple rect with rounded corners
    c.setFillColor(colour)
    c.roundRect(x, y, width, h, r, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont(FONT_BOLD, 7)
    c.drawCentredString(x + width / 2, y + 3, text.upper())


def _fmt_impact(i: str) -> str:
    return {"very_high": "Very High", "high": "High", "medium": "Medium", "low": "Low"}.get(i, i.title())


def _fmt_diff(d: str) -> str:
    return {"very_high": "Very Hard", "high": "Hard", "medium": "Medium", "low": "Easy"}.get(d, d.title())


def _fmt_horizon(h: str) -> str:
    return {"immediate": "Immediate", "near_term": "Near-term", "long_term": "Long-term"}.get(h, h.title())


def _fmt_peakweb(p: str) -> str:
    return {"direct_service": "Peakweb", "partner_referral": "Partner", "advisory_only": "Client/Team"}.get(p, p)


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def _page_cover(c: canvas.Canvas, data: dict, page_num: list):
    """Cover page."""
    page_num[0] += 1
    brand = data.get("brand_name") or "Your Business"
    url = data.get("url") or ""
    geo_score = data.get("geo_score", 0)
    today = date.today().strftime("%B %d, %Y")

    # Background
    c.setFillColorRGB(*DEEP_BLUE)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

    # Aquamarine accent strip
    c.setFillColorRGB(*AQUAMARINE)
    c.rect(0, PAGE_HEIGHT - 6, PAGE_WIDTH, 6, fill=1, stroke=0)

    # Logo
    _draw_logo(c, MARGIN, PAGE_HEIGHT - 70, w=120)

    # Title
    c.setFillColor(C_WHITE)
    c.setFont(FONT_BOLD, 28)
    c.drawString(MARGIN, PAGE_HEIGHT - 180, "AI Visibility Roadmap")

    c.setFont(FONT_REGULAR, 16)
    c.setFillColorRGB(*AQUAMARINE)
    c.drawString(MARGIN, PAGE_HEIGHT - 210, brand)

    c.setFont(FONT_REGULAR, 11)
    c.setFillColor(C_MUTED_BLUE)
    if url:
        c.drawString(MARGIN, PAGE_HEIGHT - 232, url)
    c.drawString(MARGIN, PAGE_HEIGHT - 250, f"Generated {today}")

    # Score gauge area
    cx = PAGE_WIDTH - MARGIN - 100
    cy = PAGE_HEIGHT - 200
    radius = 72
    score_col = _score_colour(geo_score)
    label = _score_label(geo_score)

    # Background circle
    c.setFillColor(C_MUTED_BLUE)
    c.circle(cx, cy, radius + 4, fill=1, stroke=0)

    # Score arc (simplified: filled circle with score colour)
    c.setFillColor(score_col)
    c.circle(cx, cy, radius, fill=1, stroke=0)

    # Inner white circle
    c.setFillColor(C_WHITE)
    c.circle(cx, cy, radius * 0.65, fill=1, stroke=0)

    # Score number
    c.setFillColorRGB(*DEEP_BLUE)
    c.setFont(FONT_BOLD, 28)
    c.drawCentredString(cx, cy - 4, str(geo_score))
    c.setFont(FONT_REGULAR, 9)
    c.setFillColor(colors.Color(0.4, 0.4, 0.4))
    c.drawCentredString(cx, cy - 18, "/100")

    c.setFillColor(score_col)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(cx, cy - 90, label.upper())
    c.setFont(FONT_REGULAR, 8)
    c.setFillColor(C_MUTED_BLUE)
    c.drawCentredString(cx, cy - 102, "GEO Score")

    # Summary stats
    summary = data.get("summary", {})
    y_stats = PAGE_HEIGHT - 360
    stats = [
        (str(summary.get("total_actions", 0)), "Total Actions"),
        (str(summary.get("immediate_actions", 0)), "Immediate"),
        (str(summary.get("quick_wins", 0)), "Quick Wins"),
        (str(summary.get("peakweb_deliverable", 0)), "Peakweb Can Do"),
    ]
    box_w = (PAGE_WIDTH - 2 * MARGIN - 30) / 4
    for i, (val, label) in enumerate(stats):
        bx = MARGIN + i * (box_w + 10)
        c.setFillColorRGB(*MIDNIGHT_GREEN)
        c.roundRect(bx, y_stats, box_w, 52, 6, fill=1, stroke=0)
        c.setFillColorRGB(*AQUAMARINE)
        c.setFont(FONT_BOLD, 22)
        c.drawCentredString(bx + box_w / 2, y_stats + 26, val)
        c.setFillColor(C_MUTED_BLUE)
        c.setFont(FONT_REGULAR, 8)
        c.drawCentredString(bx + box_w / 2, y_stats + 12, label)

    # Business type / platform
    y_info = y_stats - 40
    info_parts = []
    if data.get("business_type") and data["business_type"] != "unknown":
        info_parts.append(f"Business type: {data['business_type'].replace('_', ' ').title()}")
    if data.get("platform") and data["platform"] != "unknown":
        info_parts.append(f"Platform: {data['platform'].title()}")
    if info_parts:
        c.setFillColor(C_MUTED_BLUE)
        c.setFont(FONT_REGULAR, 10)
        c.drawString(MARGIN, y_info, "  ·  ".join(info_parts))

    # Footer
    c.setFillColor(C_MUTED_BLUE)
    c.setFont(FONT_REGULAR, 8)
    c.drawString(MARGIN, 24, "Prepared by Peakweb  ·  peakweb.co  ·  Confidential")

    c.showPage()


def _page_executive_summary(c: canvas.Canvas, data: dict, page_num: list):
    """Executive summary page."""
    page_num[0] += 1
    brand = data.get("brand_name") or "Your Business"
    geo_score = data.get("geo_score", 0)
    summary = data.get("summary", {})
    exec_summary = data.get("executive_summary", "")
    action_items = data.get("action_items", [])

    _draw_header(c, page_num[0], brand)

    y = PAGE_HEIGHT - 50
    c.setFillColorRGB(*DEEP_BLUE)
    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN, y, "Executive Summary")
    y -= 30

    # Score band row
    c.setFillColorRGB(*SCORE_BAR_BG)
    c.rect(MARGIN, y - 8, PAGE_WIDTH - 2 * MARGIN, 34, fill=1, stroke=0)
    score_col = _score_colour(geo_score)
    c.setFillColor(score_col)
    c.setFont(FONT_BOLD, 14)
    c.drawString(MARGIN + 12, y + 8, f"GEO Score: {geo_score}/100 — {_score_label(geo_score)}")
    y -= 52

    # Executive summary text
    if exec_summary:
        style = ParagraphStyle("body", fontName=FONT_REGULAR, fontSize=10, leading=15,
                               textColor=colors.Color(0.15, 0.15, 0.15))
        p = Paragraph(exec_summary.replace("\n", "<br/>"), style)
        w, h = p.wrap(PAGE_WIDTH - 2 * MARGIN, 200)
        p.drawOn(c, MARGIN, y - h)
        y -= h + 20

    # How to read framing
    c.setFillColorRGB(*MIDNIGHT_GREEN)
    c.rect(MARGIN, y - 50, PAGE_WIDTH - 2 * MARGIN, 58, fill=1, stroke=0)
    c.setFillColorRGB(*AQUAMARINE)
    c.setFont(FONT_BOLD, 9)
    c.drawString(MARGIN + 10, y + 0, "HOW TO READ THIS ROADMAP")
    framing = (
        "This roadmap identifies the signals AI systems rely on when deciding whether to cite or "
        "recommend a business. Each action is scored by expected impact, your level of control, "
        "and implementation speed. This roadmap is designed to complement your existing SEO provider."
    )
    style2 = ParagraphStyle("sm", fontName=FONT_REGULAR, fontSize=9, leading=13,
                             textColor=C_MUTED_BLUE)
    p2 = Paragraph(framing, style2)
    w2, h2 = p2.wrap(PAGE_WIDTH - 2 * MARGIN - 20, 60)
    p2.drawOn(c, MARGIN + 10, y - h2 - 4)
    y -= 80

    # Top action callout
    if action_items:
        top = action_items[0]
        why_text = top.get("whyItMatters", "")
        callout_w = PAGE_WIDTH - 2 * MARGIN - 20
        style_callout = ParagraphStyle("callout", fontName=FONT_REGULAR, fontSize=9, leading=13,
                                       textColor=colors.Color(0.3, 0.3, 0.3))
        p_callout = Paragraph(why_text, style_callout)
        _, h_callout = p_callout.wrap(callout_w, 200)
        # box: label(14) + title(18) + why_text + badges(20) + padding(16)
        box_h = 14 + 18 + h_callout + 6 + 20 + 16
        c.setFillColorRGB(*STONE)
        c.rect(MARGIN, y - box_h + 8, PAGE_WIDTH - 2 * MARGIN, box_h, fill=1, stroke=0)
        inner_y = y + 2
        c.setFillColorRGB(*DEEP_BLUE)
        c.setFont(FONT_BOLD, 9)
        c.drawString(MARGIN + 10, inner_y, "TOP PRIORITY ACTION")
        inner_y -= 16
        c.setFont(FONT_BOLD, 11)
        c.drawString(MARGIN + 10, inner_y, top.get("title", ""))
        inner_y -= 6
        p_callout.drawOn(c, MARGIN + 10, inner_y - h_callout)
        inner_y -= h_callout + 8
        # Badges
        bx = MARGIN + 10
        _badge(c, _fmt_impact(top.get("estimatedScoreImpact", "")),
               bx, inner_y - 14, _impact_colour(top.get("estimatedScoreImpact", "")), 62)
        bx += 70
        _badge(c, _fmt_diff(top.get("difficultyLevel", "")),
               bx, inner_y - 14, _difficulty_colour(top.get("difficultyLevel", "")), 56)
        bx += 64
        _badge(c, _fmt_horizon(top.get("timeHorizon", "")),
               bx, inner_y - 14, _horizon_colour(top.get("timeHorizon", "")), 68)
        y -= box_h + 10

    # Category scores table
    cat_scores = data.get("category_scores", {})
    if cat_scores:
        y = _draw_section_heading(c, "Score Breakdown", y, DEEP_BLUE)
        categories = [
            ("AI Citability", "ai_citability", "25%"),
            ("Brand Authority", "brand_authority", "20%"),
            ("Content E-E-A-T", "content_eeat", "20%"),
            ("Technical", "technical", "15%"),
            ("Schema", "schema", "10%"),
            ("Platform Opt.", "platform_optimization", "10%"),
        ]
        bar_area_w = PAGE_WIDTH - 2 * MARGIN - 200
        for name, key, weight in categories:
            score = cat_scores.get(key, 0)
            if not isinstance(score, int):
                score = 0
            # Label
            c.setFillColorRGB(*DEEP_BLUE)
            c.setFont(FONT_REGULAR, 9)
            c.drawString(MARGIN, y, f"{name} ({weight})")
            # Bar background
            bx = MARGIN + 120
            c.setFillColor(C_SCORE_BAR_BG)
            c.rect(bx, y - 2, bar_area_w, 11, fill=1, stroke=0)
            # Bar fill
            c.setFillColor(_score_colour(score))
            c.rect(bx, y - 2, bar_area_w * score / 100, 11, fill=1, stroke=0)
            # Score label
            c.setFillColorRGB(*DEEP_BLUE)
            c.setFont(FONT_BOLD, 9)
            c.drawString(bx + bar_area_w + 6, y, f"{score}/100")
            y -= 18

    _draw_logo(c, PAGE_WIDTH - MARGIN - 80, MARGIN, w=70)
    c.showPage()


def _page_top_priorities(c: canvas.Canvas, data: dict, page_num: list):
    """Top 5 priorities as cards."""
    page_num[0] += 1
    brand = data.get("brand_name") or "Your Business"
    action_items = data.get("action_items", [])
    top_5 = action_items[:5]

    _draw_header(c, page_num[0], brand)

    y = PAGE_HEIGHT - 50
    c.setFillColorRGB(*DEEP_BLUE)
    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN, y, "Top Priorities")
    y -= 14
    c.setFillColor(C_MUTED_BLUE)
    c.setFont(FONT_REGULAR, 9)
    c.drawString(MARGIN, y, "Highest combined score impact, feasibility, and urgency")
    y -= 22

    card_gap = 8
    content_w = PAGE_WIDTH - 2 * MARGIN
    text_w = content_w - 50  # left indent (10) + rank circle area (40)

    style_why = ParagraphStyle("why", fontName=FONT_REGULAR, fontSize=8, leading=11,
                               textColor=colors.Color(0.2, 0.2, 0.2))
    style_rec = ParagraphStyle("rec", fontName=FONT_ITALIC, fontSize=8, leading=11,
                               textColor=colors.Color(0.1, 0.1, 0.1))
    style_evi = ParagraphStyle("evi", fontName=FONT_REGULAR, fontSize=7, leading=10,
                               textColor=C_MUTED_BLUE)

    HEADER_H = 50   # space reserved for title + badges before text blocks
    TEXT_GAP = 5    # vertical gap between text blocks
    BOTTOM_PAD = 10

    for i, item in enumerate(top_5):
        why_text = item.get("whyItMatters", "")
        rec_text = item.get("customerSpecificRecommendation") or item.get("implementationNotes", "")
        evi_text = item.get("evidence", "")

        p_why = Paragraph(why_text, style_why) if why_text else None
        p_rec = Paragraph(f"Next step: {rec_text}", style_rec) if rec_text else None
        p_evi = Paragraph(f"Audit evidence: {evi_text}", style_evi) if evi_text else None

        _, h_why = p_why.wrap(text_w, 400) if p_why else (0, 0)
        _, h_rec = p_rec.wrap(text_w, 400) if p_rec else (0, 0)
        _, h_evi = p_evi.wrap(text_w, 400) if p_evi else (0, 0)

        text_total = (h_why
                      + (TEXT_GAP + h_rec if p_rec else 0)
                      + (TEXT_GAP + h_evi if p_evi else 0))
        card_h = max(HEADER_H + text_total + BOTTOM_PAD, 90)

        if y - card_h < MARGIN + 20:
            break

        # Card background
        c.setFillColorRGB(*STONE)
        c.roundRect(MARGIN, y - card_h, content_w, card_h, 5, fill=1, stroke=0)

        # Rank badge
        c.setFillColorRGB(*DEEP_BLUE)
        c.circle(MARGIN + 18, y - 20, 13, fill=1, stroke=0)
        c.setFillColor(C_AQUAMARINE)
        c.setFont(FONT_BOLD, 12)
        c.drawCentredString(MARGIN + 18, y - 24, str(i + 1))

        # Title
        c.setFillColorRGB(*DEEP_BLUE)
        c.setFont(FONT_BOLD, 11)
        c.drawString(MARGIN + 38, y - 14, item.get("title", ""))

        # Priority score
        pscore = item.get("priorityScore", 0)
        c.setFillColor(_score_colour(pscore))
        c.setFont(FONT_BOLD, 9)
        c.drawRightString(PAGE_WIDTH - MARGIN - 6, y - 14, f"Priority {pscore}/100")

        # Badges row
        bx = MARGIN + 38
        by = y - 30
        for badge_text, badge_col, badge_w in [
            (_fmt_impact(item.get("estimatedScoreImpact", "")),
             _impact_colour(item.get("estimatedScoreImpact", "")), 60),
            (_fmt_diff(item.get("difficultyLevel", "")),
             _difficulty_colour(item.get("difficultyLevel", "")), 54),
            (_fmt_horizon(item.get("timeHorizon", "")),
             _horizon_colour(item.get("timeHorizon", "")), 66),
            (_fmt_peakweb(item.get("peakwebFit", "")),
             C_DEEP_BLUE, 72),
        ]:
            _badge(c, badge_text, bx, by, badge_col, badge_w)
            bx += badge_w + 6

        # Text content — stacked Paragraphs
        text_y = y - HEADER_H
        if p_why:
            text_y -= h_why
            p_why.drawOn(c, MARGIN + 10, text_y)
            text_y -= TEXT_GAP
        if p_rec:
            text_y -= h_rec
            p_rec.drawOn(c, MARGIN + 10, text_y)
            text_y -= TEXT_GAP
        if p_evi:
            text_y -= h_evi
            p_evi.drawOn(c, MARGIN + 10, text_y)

        y -= card_h + card_gap

    _draw_logo(c, PAGE_WIDTH - MARGIN - 80, MARGIN, w=70)
    c.showPage()


def _page_full_action_plan(c: canvas.Canvas, data: dict, page_num: list):
    """Full ranked action plan as a table, may span multiple pages."""
    brand = data.get("brand_name") or "Your Business"
    action_items = data.get("action_items", [])

    page_num[0] += 1
    _draw_header(c, page_num[0], brand)
    y = PAGE_HEIGHT - 50

    c.setFillColorRGB(*DEEP_BLUE)
    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN, y, "Full Ranked Action Plan")
    y -= 14
    c.setFillColor(C_MUTED_BLUE)
    c.setFont(FONT_REGULAR, 9)
    c.drawString(MARGIN, y, f"All {len(action_items)} identified actions ranked by priority score")
    y -= 22

    # Build table data
    # Available width = PAGE_WIDTH - 2*MARGIN = 504pt; Action column gets the remainder
    fixed_cols = [24, 52, 52, 64, 60, 38]   # #, Impact, Difficulty, Timeline, Peakweb, Score
    action_col_w = (PAGE_WIDTH - 2 * MARGIN) - sum(fixed_cols)  # ~214pt
    col_widths = [24, action_col_w, 52, 52, 64, 60, 38]

    style_cell = ParagraphStyle("cell", fontName=FONT_REGULAR, fontSize=8, leading=11,
                                textColor=colors.Color(0.1, 0.1, 0.1))
    style_hdr  = ParagraphStyle("hdr",  fontName=FONT_BOLD,    fontSize=8, leading=11,
                                textColor=colors.white)

    header = ["#", Paragraph("Action", style_hdr), "Impact", "Difficulty", "Timeline", "Peakweb Fit", "Score"]
    table_data = [header]

    for i, item in enumerate(action_items, 1):
        table_data.append([
            str(i),
            Paragraph(item.get("title", ""), style_cell),
            _fmt_impact(item.get("estimatedScoreImpact", "")),
            _fmt_diff(item.get("difficultyLevel", "")),
            _fmt_horizon(item.get("timeHorizon", "")),
            _fmt_peakweb(item.get("peakwebFit", "")),
            str(item.get("priorityScore", 0)),
        ])

    row_h = 20  # slightly taller to allow wrapping room
    rows_per_page = int((y - MARGIN - 30) / row_h)
    chunks = [table_data[i:i + rows_per_page] for i in range(0, len(table_data), rows_per_page)]

    def _render_chunk(chunk, y_start, page_first: bool):
        if not page_first:
            page_num[0] += 1
            _draw_header(c, page_num[0], brand)
            y_start = PAGE_HEIGHT - 50

        rows = [header] + chunk if not page_first else chunk
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), C_DEEP_BLUE),
            ("TEXTCOLOR",  (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_SCORE_BAR_BG]),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (6, 0), (6, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.8, 0.8, 0.8)),
        ]
        t = Table(rows, colWidths=col_widths,
                  style=TableStyle(style))
        t_w, t_h = t.wrap(sum(col_widths), y_start - MARGIN)
        t.drawOn(c, MARGIN, y_start - t_h)
        return y_start - t_h

    # First chunk includes header
    first_chunk = chunks[0] if chunks else []
    _render_chunk(first_chunk, y, True)

    for chunk in chunks[1:]:
        c.showPage()
        page_num[0] += 1
        _draw_header(c, page_num[0], brand)
        c.setFillColorRGB(*DEEP_BLUE)
        c.setFont(FONT_BOLD, 12)
        c.drawString(MARGIN, PAGE_HEIGHT - 44, "Full Ranked Action Plan (continued)")
        _render_chunk(chunk, PAGE_HEIGHT - 60, True)

    _draw_logo(c, PAGE_WIDTH - MARGIN - 80, MARGIN, w=70)
    c.showPage()


def _page_peakweb_services(c: canvas.Canvas, data: dict, page_num: list):
    """Peakweb services + partner items split page."""
    page_num[0] += 1
    brand = data.get("brand_name") or "Your Business"
    action_items = data.get("action_items", [])
    peakweb_items = [a for a in action_items if a.get("peakwebFit") == "direct_service"]
    partner_items = [a for a in action_items if a.get("peakwebFit") == "partner_referral"]
    client_items  = [a for a in action_items if a.get("peakwebFit") == "advisory_only"]

    _draw_header(c, page_num[0], brand)
    y = PAGE_HEIGHT - 50

    c.setFillColorRGB(*DEEP_BLUE)
    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN, y, "Who Does What")
    y -= 30

    style_note = ParagraphStyle("note", fontName=FONT_REGULAR, fontSize=8, leading=11,
                                textColor=colors.Color(0.25, 0.25, 0.25))

    def _render_group(title: str, items: list, bg_colour, y_pos: float) -> float:
        if not items:
            return y_pos
        y_pos = _draw_section_heading(c, title, y_pos, bg_colour)
        note_w = PAGE_WIDTH - 2 * MARGIN - 10
        for item in items:
            c.setFillColorRGB(*DEEP_BLUE)
            c.setFont(FONT_BOLD, 9)
            c.drawString(MARGIN, y_pos, f"• {item.get('title', '')}")
            y_pos -= 6
            note_text = item.get("customerSpecificRecommendation") or item.get("implementationNotes", "")
            if note_text:
                p_note = Paragraph(note_text, style_note)
                _, h_note = p_note.wrap(note_w, 200)
                y_pos -= h_note
                p_note.drawOn(c, MARGIN + 10, y_pos)
                y_pos -= 18  # generous gap after note to visually separate from next title
            else:
                y_pos -= 10
            if y_pos < MARGIN + 40:
                break
        return y_pos

    y = _render_group("Peakweb Can Implement Directly", peakweb_items, MIDNIGHT_GREEN, y)
    y -= 10
    y = _render_group("Partner / Specialist Recommended", partner_items, (70/255, 100/255, 130/255), y)
    y -= 10
    y = _render_group("Client Team or Advisory", client_items, (80/255, 80/255, 80/255), y)

    _draw_logo(c, PAGE_WIDTH - MARGIN - 80, MARGIN, w=70)
    c.showPage()


def _page_quick_wins(c: canvas.Canvas, data: dict, page_num: list):
    """Quick wins + appendix on one page."""
    page_num[0] += 1
    brand = data.get("brand_name") or "Your Business"
    action_items = data.get("action_items", [])
    quick_wins = [a for a in action_items
                  if a.get("controlLevel") == "direct"
                  and a.get("difficultyLevel") in ("low", "medium")]

    _draw_header(c, page_num[0], brand)
    y = PAGE_HEIGHT - 50

    c.setFillColorRGB(*DEEP_BLUE)
    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN, y, "Quick Wins")
    y -= 14
    c.setFillColor(C_MUTED_BLUE)
    c.setFont(FONT_REGULAR, 9)
    c.drawString(MARGIN, y, "Direct control · low-to-medium difficulty · can start this week")
    y -= 22

    if quick_wins:
        fixed_qw = [55, 55, 85, 90]   # Impact, Difficulty, Timeline, Peakweb Fit
        action_qw_w = (PAGE_WIDTH - 2 * MARGIN) - sum(fixed_qw)  # ~219pt
        col_widths_qw = [action_qw_w] + fixed_qw
        style_qw_cell = ParagraphStyle("qwcell", fontName=FONT_REGULAR, fontSize=8, leading=11,
                                       textColor=colors.Color(0.1, 0.1, 0.1))
        style_qw_hdr  = ParagraphStyle("qwhdr",  fontName=FONT_BOLD,    fontSize=8, leading=11,
                                       textColor=colors.white)
        header_qw = [Paragraph("Action", style_qw_hdr), "Impact", "Difficulty", "Timeline", "Peakweb Fit"]
        rows_qw = [header_qw]
        for item in quick_wins[:12]:
            rows_qw.append([
                Paragraph(item.get("title", ""), style_qw_cell),
                _fmt_impact(item.get("estimatedScoreImpact", "")),
                _fmt_diff(item.get("difficultyLevel", "")),
                _fmt_horizon(item.get("timeHorizon", "")),
                _fmt_peakweb(item.get("peakwebFit", "")),
            ])
        style = [
            ("BACKGROUND",    (0, 0), (-1, 0), C_DEEP_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_SCORE_BAR_BG]),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.8, 0.8, 0.8)),
        ]
        t = Table(rows_qw, colWidths=col_widths_qw, style=TableStyle(style))
        t_w, t_h = t.wrap(sum(col_widths_qw), y - MARGIN - 150)
        t.drawOn(c, MARGIN, y - t_h)
        y -= t_h + 30
    else:
        c.setFillColor(C_MUTED_BLUE)
        c.setFont(FONT_ITALIC, 10)
        c.drawString(MARGIN, y, "No quick wins identified — all improvements require moderate or higher effort.")
        y -= 30

    # Appendix: scoring weights
    y = _draw_section_heading(c, "Appendix: GEO Score Components", y - 10, DEEP_BLUE)

    cat_data = [
        ["Component", "Weight", "Your Score", "Benchmark"],
        ["AI Citability & Visibility", "25%",
         f"{data.get('category_scores', {}).get('ai_citability', 'N/A')}/100", "75+"],
        ["Brand Authority Signals", "20%",
         f"{data.get('category_scores', {}).get('brand_authority', 'N/A')}/100", "70+"],
        ["Content Quality & E-E-A-T", "20%",
         f"{data.get('category_scores', {}).get('content_eeat', 'N/A')}/100", "70+"],
        ["Technical Foundations", "15%",
         f"{data.get('category_scores', {}).get('technical', 'N/A')}/100", "70+"],
        ["Structured Data", "10%",
         f"{data.get('category_scores', {}).get('schema', 'N/A')}/100", "70+"],
        ["Platform Optimisation", "10%",
         f"{data.get('category_scores', {}).get('platform_optimization', 'N/A')}/100", "70+"],
    ]
    style_app = [
        ("BACKGROUND",    (0, 0), (-1, 0), C_DEEP_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_SCORE_BAR_BG]),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.8, 0.8, 0.8)),
    ]
    t_app = Table(cat_data, colWidths=[200, 60, 80, 80], style=TableStyle(style_app))
    t_w, t_h = t_app.wrap(420, y - MARGIN - 10)
    t_app.drawOn(c, MARGIN, y - t_h)

    c.setFillColor(C_MUTED_BLUE)
    c.setFont(FONT_REGULAR, 7)
    c.drawString(MARGIN, MARGIN + 20,
                 "GEO scoring methodology: scoring.md — peakweb.co — Confidential")

    _draw_logo(c, PAGE_WIDTH - MARGIN - 80, MARGIN, w=70)
    c.showPage()


# ---------------------------------------------------------------------------
# Main PDF builder
# ---------------------------------------------------------------------------

def generate_pdf(data: dict, output_path: str):
    """Build the full roadmap PDF and write to output_path."""
    register_fonts()
    c = canvas.Canvas(output_path, pagesize=letter)
    c.setTitle(f"GEO Roadmap — {data.get('brand_name', 'Report')}")
    c.setAuthor("Peakweb")
    c.setSubject("AI Visibility Roadmap")

    page_num = [0]  # mutable counter passed to page builders

    _page_cover(c, data, page_num)
    _page_executive_summary(c, data, page_num)
    _page_top_priorities(c, data, page_num)
    _page_full_action_plan(c, data, page_num)
    _page_peakweb_services(c, data, page_num)
    _page_quick_wins(c, data, page_num)

    c.save()
    return output_path


# ---------------------------------------------------------------------------
# Sample data (used when run without arguments)
# ---------------------------------------------------------------------------

SAMPLE_DATA = {
    "brand_name": "Resilient Martial Arts",
    "url": "https://resilientmartialarts.com",
    "date": date.today().isoformat(),
    "geo_score": 42,
    "business_type": "local",
    "platform": "wordpress",
    "executive_summary": (
        "Resilient Martial Arts has a functional online presence but is currently "
        "largely invisible to AI systems like ChatGPT, Google AI Overviews, and Perplexity. "
        "The most urgent issue is that AI crawlers are blocked from indexing the site at all. "
        "Combined with missing structured data and no llms.txt file, the business is absent "
        "from AI-powered recommendations — a growing channel for local service discovery. "
        "The good news is that the highest-impact fixes are technical and can be implemented quickly."
    ),
    "category_scores": {
        "ai_citability": 38,
        "brand_authority": 35,
        "content_eeat": 45,
        "technical": 52,
        "schema": 20,
        "platform_optimization": 40,
    },
    "action_items": [
        {
            "id": "unblock_ai_crawlers",
            "title": "Unblock AI Crawlers in robots.txt",
            "category": "technical",
            "scoreComponent": "technical",
            "controlLevel": "direct",
            "difficultyLevel": "low",
            "estimatedScoreImpact": "very_high",
            "timeHorizon": "immediate",
            "peakwebFit": "direct_service",
            "isFoundational": True,
            "affectedPlatforms": ["ChatGPT", "Perplexity", "Claude", "Gemini", "Bing Copilot"],
            "whyItMatters": "AI systems can only cite content they can access. If crawlers are blocked, the site is invisible regardless of content quality.",
            "evidence": "GPTBot and ClaudeBot blocked in robots.txt",
            "customerSpecificRecommendation": "Remove Disallow rules for GPTBot, ClaudeBot, PerplexityBot, CCBot from robots.txt. 5-minute edit with very high impact.",
            "implementationNotes": "Edit robots.txt. Remove Disallow rules for AI bots.",
            "platformSpecificNotes": "In WordPress, edit via FTP or a robots.txt plugin. Do not use All in One SEO's robots.txt if it has blanket Disallow rules.",
            "priorityScore": 97,
            "status": "not_started",
        },
        {
            "id": "add_local_business_schema",
            "title": "Add LocalBusiness Schema (JSON-LD)",
            "category": "schema",
            "scoreComponent": "schema",
            "controlLevel": "direct",
            "difficultyLevel": "low",
            "estimatedScoreImpact": "high",
            "timeHorizon": "immediate",
            "peakwebFit": "direct_service",
            "isFoundational": False,
            "affectedPlatforms": ["Google AI Overviews", "ChatGPT", "Gemini", "Bing Copilot"],
            "whyItMatters": "Local AI queries rely heavily on structured location data. Without LocalBusiness schema, AI systems often skip local service providers in conversational recommendations.",
            "evidence": "No LocalBusiness schema detected on any crawled pages.",
            "customerSpecificRecommendation": "Add LocalBusiness schema immediately. Specify your service area, opening hours, address, and phone. As a martial arts school, use SportsActivityLocation as the sub-type.",
            "implementationNotes": "Use the most specific sub-type. Include address, phone, openingHours, geo coordinates, areaServed.",
            "platformSpecificNotes": "Use Rank Math Pro's Local SEO module to generate this automatically from your location settings.",
            "priorityScore": 84,
            "status": "not_started",
        },
        {
            "id": "publish_llms_txt",
            "title": "Publish an llms.txt File",
            "category": "technical",
            "scoreComponent": "ai_citability",
            "controlLevel": "direct",
            "difficultyLevel": "low",
            "estimatedScoreImpact": "high",
            "timeHorizon": "immediate",
            "peakwebFit": "direct_service",
            "isFoundational": False,
            "affectedPlatforms": ["Claude", "Perplexity", "ChatGPT"],
            "whyItMatters": "AI tools read llms.txt as a structured site index. It gives AI systems an authoritative, compact overview of who you are and what you offer.",
            "evidence": "No llms.txt file found at site root.",
            "customerSpecificRecommendation": "Create llms.txt in under an hour. Include your school name, location, martial arts styles taught, class schedule URL, and instructor bios.",
            "implementationNotes": "Follow llmstxt.org standard. Keep under 2KB.",
            "platformSpecificNotes": "Upload via FTP or cPanel File Manager to the WordPress root directory.",
            "priorityScore": 78,
            "status": "not_started",
        },
        {
            "id": "claim_google_business_profile",
            "title": "Claim and Optimise Google Business Profile",
            "category": "brand",
            "scoreComponent": "brand_authority",
            "controlLevel": "direct",
            "difficultyLevel": "low",
            "estimatedScoreImpact": "high",
            "timeHorizon": "immediate",
            "peakwebFit": "direct_service",
            "isFoundational": False,
            "affectedPlatforms": ["Google AI Overviews", "Gemini", "Bing Copilot"],
            "whyItMatters": "Google Business Profile is a primary trust signal for Google AI Overviews and Gemini for local queries.",
            "evidence": "Google Business Profile not detected or not fully claimed.",
            "customerSpecificRecommendation": "Verify your Google Business Profile. Add all martial arts styles, class photos, instructor profiles, and your full schedule. Respond to all reviews.",
            "implementationNotes": "Verify at business.google.com. Complete all fields including description, categories, attributes, hours.",
            "priorityScore": 74,
            "status": "not_started",
        },
        {
            "id": "restructure_content_answer_blocks",
            "title": "Restructure Key Pages with Direct Answer Blocks",
            "category": "content",
            "scoreComponent": "ai_citability",
            "controlLevel": "direct",
            "difficultyLevel": "medium",
            "estimatedScoreImpact": "high",
            "timeHorizon": "immediate",
            "peakwebFit": "direct_service",
            "isFoundational": False,
            "affectedPlatforms": ["ChatGPT", "Perplexity", "Google AI Overviews", "Gemini"],
            "whyItMatters": "AI systems extract passage-level content. They look for direct answers within self-contained blocks. Poorly structured pages rarely get cited.",
            "evidence": "Answer block quality rated 'weak'. Content not structured for AI passage extraction.",
            "customerSpecificRecommendation": "Rewrite your class pages to directly answer: What is this martial art? Who is it for? What age groups do you accept? How much does it cost? What should I expect at my first class?",
            "implementationNotes": "Each key question gets its own H2/H3 and a 100-200 word direct answer paragraph.",
            "priorityScore": 68,
            "status": "not_started",
        },
        {
            "id": "add_faq_schema",
            "title": "Add FAQPage Schema to Key Pages",
            "category": "schema",
            "scoreComponent": "schema",
            "controlLevel": "direct",
            "difficultyLevel": "low",
            "estimatedScoreImpact": "high",
            "timeHorizon": "immediate",
            "peakwebFit": "direct_service",
            "isFoundational": False,
            "affectedPlatforms": ["Google AI Overviews", "ChatGPT", "Perplexity", "Gemini"],
            "whyItMatters": "FAQ schema makes answers directly machine-readable. AI systems that generate answers actively prefer sources with clean Q&A pairs.",
            "evidence": "No FAQPage schema detected.",
            "customerSpecificRecommendation": "Add an FAQ block to your homepage and class pages. Common questions: What martial arts do you teach? What age groups do you accept? Do you offer trial classes? How much do classes cost?",
            "implementationNotes": "Add FAQPage JSON-LD to any page with 3+ Q&A pairs.",
            "platformSpecificNotes": "Rank Math auto-generates FAQPage schema when using its FAQ block in Gutenberg.",
            "priorityScore": 63,
            "status": "not_started",
        },
        {
            "id": "build_wikidata_entity",
            "title": "Create a Wikidata Entity",
            "category": "brand",
            "scoreComponent": "brand_authority",
            "controlLevel": "indirect",
            "difficultyLevel": "medium",
            "estimatedScoreImpact": "high",
            "timeHorizon": "near_term",
            "peakwebFit": "direct_service",
            "isFoundational": False,
            "affectedPlatforms": ["ChatGPT", "Google AI Overviews", "Gemini"],
            "whyItMatters": "Wikidata is a primary structured knowledge source for AI entity resolution. An entry significantly improves how accurately AI systems identify and describe your business.",
            "evidence": "No Wikidata entity found for this business.",
            "customerSpecificRecommendation": "Create a Wikidata entry for Resilient Martial Arts. Include founding year, location, sports offered, and official website URL.",
            "implementationNotes": "Create at wikidata.org/wiki/Special:NewItem. Add: instance of (sports organisation), name, website, location, founded date.",
            "priorityScore": 44,
            "status": "not_started",
        },
        {
            "id": "build_wikipedia_presence",
            "title": "Establish Wikipedia Presence",
            "category": "brand",
            "scoreComponent": "brand_authority",
            "controlLevel": "indirect",
            "difficultyLevel": "very_high",
            "estimatedScoreImpact": "very_high",
            "timeHorizon": "long_term",
            "peakwebFit": "advisory_only",
            "isFoundational": False,
            "affectedPlatforms": ["ChatGPT", "Google AI Overviews", "Gemini", "Perplexity"],
            "whyItMatters": "Wikipedia is the single strongest trust signal for AI entity recognition. Businesses with Wikipedia articles are dramatically more likely to be cited accurately.",
            "evidence": "No Wikipedia presence found.",
            "customerSpecificRecommendation": "Focus first on earning press coverage and building brand citations. Revisit Wikipedia once you have significant independent coverage. Do not attempt this prematurely.",
            "implementationNotes": "Prerequisites: significant third-party press coverage in recognised publications.",
            "priorityScore": 21,
            "status": "not_started",
        },
    ],
    "summary": {
        "total_actions": 8,
        "immediate_actions": 5,
        "quick_wins": 5,
        "peakweb_deliverable": 6,
        "top_priority": "Unblock AI Crawlers in robots.txt",
    }
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if input_file:
        with open(input_file, "r") as f:
            data = json.load(f)
    else:
        print("No input file provided — using sample data.", file=sys.stderr)
        data = SAMPLE_DATA

    if not output_file:
        brand_slug = (data.get("brand_name") or "report").replace(" ", "")
        output_file = f"GEO-ROADMAP-{brand_slug}.pdf"

    print(f"Generating PDF: {output_file} ...", file=sys.stderr)
    generate_pdf(data, output_file)

    size = os.path.getsize(output_file)
    print(f"Done. {output_file} ({size:,} bytes)", file=sys.stderr)
    print(output_file)  # stdout: the path (for scripting)
