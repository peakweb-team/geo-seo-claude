#!/usr/bin/env python3
"""
Peakweb Pitch Deck Generator

Generates a 12-page branded PDF from scratch using ReportLab.
Follows Peakweb brand guidelines exactly.

Usage:
    python3 generate_pitch_deck.py                     # Uses sample data for testing
    python3 generate_pitch_deck.py data.json           # Uses JSON file
    python3 generate_pitch_deck.py data.json out.pdf   # Custom output filename

JSON input accepts both formats:
    - UPPER_SNAKE_CASE: {"CLIENT_NAME": "...", "GEO_SCORE": 53}
    - snake_case: {"client_name": "...", "geo_score": 53}
"""

import json
import math
import os
import re
import sys
import textwrap
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
FONTS_DIR = os.path.join(PROJECT_DIR, "assets/fonts")
LOGO_PATH = os.path.join(PROJECT_DIR, "assets/PeakWeb-Green-RGB.png")
W_CHEVRON_PATH = os.path.join(PROJECT_DIR, "assets/PeakWeb-W-Chevron.png")

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792 points
MARGIN = 54  # 0.75 inch

# Brand Colors (RGB tuples 0-1) - from build_pdf3.py reference
DEEP_BLUE = (10/255, 44/255, 73/255)         # #0A2C49
AQUAMARINE = (1/255, 239/255, 160/255)       # #01EFA0
LIGHT_GREEN = (188/255, 255/255, 138/255)    # #BCFF8A
MIDNIGHT_GREEN = (10/255, 62/255, 60/255)    # #0A3E3C
LILAC = (152/255, 146/255, 181/255)          # #9892B5
STONE = (252/255, 247/255, 230/255)          # #FCF7E6
WHITE = (1, 1, 1)
AMBER = (245/255, 166/255, 35/255)           # #F5A623 - warning/low scores
SCORE_BAR_BG = (232/255, 236/255, 240/255)   # #E8ECF0 - score bar background
WARN_BG = (255/255, 248/255, 230/255)        # #FFF8E6 - warning callout background
SOFT_RED_BG = (255/255, 240/255, 240/255)    # #FFF0F0 - before box background
SOFT_GREEN_BG = (239/255, 255/255, 239/255)  # #EFFFEF - after box background
LIGHT_BLUE_BG = (26/255, 74/255, 110/255)    # #1a4a6e - info box background
MUTED_BLUE = (148/255, 184/255, 204/255)     # #94b8cc - labels and "Confidential"

# ReportLab color objects
C_DEEP_BLUE = colors.Color(*DEEP_BLUE)
C_AQUAMARINE = colors.Color(*AQUAMARINE)
C_LIGHT_GREEN = colors.Color(*LIGHT_GREEN)
C_MIDNIGHT_GREEN = colors.Color(*MIDNIGHT_GREEN)
C_LILAC = colors.Color(*LILAC)
C_STONE = colors.Color(*STONE)
C_WHITE = colors.white

# Font name constants - use Helvetica fallbacks since Outfit fonts are not available
FONT_THIN = 'Helvetica'
FONT_LIGHT = 'Helvetica'
FONT_REGULAR = 'Helvetica'
FONT_SEMIBOLD = 'Helvetica-Bold'


def register_fonts():
    """Try to register Outfit fonts, fall back to Helvetica if not available."""
    global FONT_THIN, FONT_LIGHT, FONT_REGULAR, FONT_SEMIBOLD

    font_files = [
        ('Outfit-Thin', 'Outfit-Thin.ttf'),
        ('Outfit-Light', 'Outfit-Light.ttf'),
        ('Outfit-Regular', 'Outfit-Regular.ttf'),
        ('Outfit-SemiBold', 'Outfit-SemiBold.ttf'),
    ]

    fonts_loaded = 0
    for font_name, filename in font_files:
        path = os.path.join(FONTS_DIR, filename)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                fonts_loaded += 1
            except Exception as e:
                print(f"Warning: Could not load font {font_name}: {e}")

    if fonts_loaded >= 4:
        # All fonts loaded successfully, use Outfit
        FONT_THIN = 'Outfit-Thin'
        FONT_LIGHT = 'Outfit-Light'
        FONT_REGULAR = 'Outfit-Regular'
        FONT_SEMIBOLD = 'Outfit-SemiBold'
        print("Using Outfit fonts")
    else:
        print("Using Helvetica fallback fonts")


def normalize_data(data):
    """
    Normalize input data to accept both snake_case and UPPER_SNAKE_CASE keys.
    Also handles nested structures like issues[], working[], etc.
    Returns data with UPPER_SNAKE_CASE keys as expected by the generator.
    """
    # Mapping from snake_case to expected UPPER_SNAKE_CASE
    key_mapping = {
        # Client info
        'client_name': 'CLIENT_NAME',
        'client_name_full': 'CLIENT_NAME_FULL',
        'contact_name': 'CONTACT_NAME, TITLE',
        'contact_title': 'CONTACT_NAME, TITLE',  # Combined field
        'client_website': 'CLIENT_WEBSITE',
        'report_date': 'REPORT_DATE',

        # Scores
        'geo_score': 'GEO_SCORE',
        'score_label': 'SCORE_LABEL',
        'score_description': 'SCORE_DESCRIPTION',
        'projected_score': 'PROJECTED',
        'projected': 'PROJECTED',

        # Business context
        'sample_query': 'SAMPLE_QUERY',
        'years': 'YEARS',
        'bbb_rating': 'BBB_RATING',
        'city': 'CITY',
        'industry': 'INDUSTRY',
        'service_type': 'SERVICE_TYPE',
        'service_type_plural': 'SERVICE_TYPE_PLURAL',

        # ROI
        'leads_per_month': 'LEADS_PER_MONTH',
        'customers_per_month': 'CUSTOMERS_PER_MONTH',
        'monthly_rev': 'MONTHLY_REV',
        'annual_impact': 'ANNUAL_IMPACT',

        # Week scores
        'w1_score': 'W1_SCORE',
        'w2_score': 'W2_SCORE',
        'w3_score': 'W3_SCORE',
        'w4_score': 'W4_SCORE',

        # Bottom line
        'bottom_line_1': 'BOTTOM_LINE_1',
        'bottom_line_2': 'BOTTOM_LINE_2',
        'bottom_line_closer': 'BOTTOM_LINE_CLOSER',
    }

    normalized = {}

    for key, value in data.items():
        # Check if key is already UPPER_SNAKE_CASE
        if key.isupper() or key in ['CONTACT_NAME, TITLE']:
            normalized[key] = value
        # Check if we have a mapping for this snake_case key
        elif key.lower() in key_mapping:
            normalized[key_mapping[key.lower()]] = value
        # Convert snake_case to UPPER_SNAKE_CASE
        else:
            upper_key = key.upper()
            normalized[upper_key] = value

    # Handle combined contact_name + contact_title
    if 'contact_name' in data and 'contact_title' in data:
        name = data.get('contact_name', '')
        title = data.get('contact_title', '')
        if name and title:
            normalized['CONTACT_NAME, TITLE'] = f"{name}, {title}"
        elif name:
            normalized['CONTACT_NAME, TITLE'] = name

    # Handle 'working' array -> WORKING_1, WORKING_2, etc.
    if 'working' in data and isinstance(data['working'], list):
        for i, item in enumerate(data['working'][:5], 1):
            normalized[f'WORKING_{i}'] = item

    # Handle 'means' array -> MEANS_1, MEANS_2, etc.
    if 'means' in data and isinstance(data['means'], list):
        for i, item in enumerate(data['means'][:3], 1):
            normalized[f'MEANS_{i}'] = item

    # Handle 'issues' array -> ISSUE_1_TITLE, ISSUE_1_BODY, etc.
    if 'issues' in data and isinstance(data['issues'], list):
        for i, issue in enumerate(data['issues'][:6], 1):
            if isinstance(issue, dict):
                normalized[f'ISSUE_{i}_TITLE'] = issue.get('title', '')
                normalized[f'ISSUE_{i}_BODY'] = issue.get('body', '')
                normalized[f'ISSUE_{i}_CALLOUT'] = issue.get('callout', issue.get('example', ''))

    # Handle 'nothing_short' array -> NOTHING_SHORT_1, etc.
    if 'nothing_short' in data and isinstance(data['nothing_short'], list):
        for i, item in enumerate(data['nothing_short'][:3], 1):
            normalized[f'NOTHING_SHORT_{i}'] = item

    # Handle 'nothing_long' array -> NOTHING_LONG_1, etc.
    if 'nothing_long' in data and isinstance(data['nothing_long'], list):
        for i, item in enumerate(data['nothing_long'][:3], 1):
            normalized[f'NOTHING_LONG_{i}'] = item

    # Handle 'opportunities' array -> OPP_1_DESC, etc.
    if 'opportunities' in data and isinstance(data['opportunities'], list):
        for i, opp in enumerate(data['opportunities'][:4], 1):
            if isinstance(opp, dict):
                normalized[f'OPP_{i}_DESC'] = opp.get('desc', opp.get('description', ''))

    # Handle 'roi' nested object
    if 'roi' in data and isinstance(data['roi'], dict):
        roi = data['roi']
        if 'leads_per_month' in roi:
            normalized['LEADS_PER_MONTH'] = roi['leads_per_month']
        if 'customers_per_month' in roi:
            normalized['CUSTOMERS_PER_MONTH'] = roi['customers_per_month']
        if 'monthly_rev' in roi:
            normalized['MONTHLY_REV'] = roi['monthly_rev']
        if 'annual_impact' in roi:
            normalized['ANNUAL_IMPACT'] = roi['annual_impact']

    # Handle 'week_scores' array -> W1_SCORE, etc.
    if 'week_scores' in data and isinstance(data['week_scores'], list):
        scores = data['week_scores']
        for i, score in enumerate(scores[:4], 1):
            normalized[f'W{i}_SCORE'] = str(score)

    # Handle 'bottom_line' array -> BOTTOM_LINE_1, BOTTOM_LINE_2
    if 'bottom_line' in data and isinstance(data['bottom_line'], list):
        lines = data['bottom_line']
        if len(lines) >= 1:
            normalized['BOTTOM_LINE_1'] = lines[0]
        if len(lines) >= 2:
            normalized['BOTTOM_LINE_2'] = lines[1]

    return normalized


class PitchDeckGenerator:
    def __init__(self, data, output_path):
        self.data = data
        self.output_path = output_path
        self.c = None
        self.page_num = 0
        self.y = PAGE_HEIGHT - MARGIN  # Current y position for content

    def generate(self):
        """Generate the complete pitch deck."""
        register_fonts()

        self.c = canvas.Canvas(self.output_path, pagesize=letter)

        self._page_1_cover()
        self._page_2_executive_summary()
        self._page_3_current_score()
        self._page_4_issues_1_to_3()
        self._page_5_issues_4_to_6()
        self._page_6_opportunity()
        self._page_7_roadmap()
        self._page_8_pricing()
        self._page_9_seo_vs_geo()
        self._page_10_before_after()
        self._page_11_next_steps()
        self._page_12_cta()

        self.c.save()
        print(f"Generated: {self.output_path}")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _new_page(self, bg_color=WHITE):
        """Start a new page with background color."""
        if self.page_num > 0:
            self.c.showPage()
        self.page_num += 1

        # Fill background
        self.c.setFillColorRGB(*bg_color)
        self.c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

    def _draw_header(self, show_logo=True):
        """Draw page header with logo - matches build_pdf3.py page() method."""
        # Header bar - 42pt high (from reference)
        hdr_h = 42
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.rect(0, PAGE_HEIGHT - hdr_h, PAGE_WIDTH, hdr_h, fill=1, stroke=0)

        # Logo - small version in header
        # Our PNG is 8000x4500 (1.78:1 ratio) - taller than the reference's 5:1 logo
        # Center it vertically in header bar; overflow will be clipped
        if show_logo and os.path.exists(LOGO_PATH):
            logo_w = 100
            logo_h = logo_w * (4500 / 8000)  # ≈ 56
            # Center vertically in header bar
            logo_y = PAGE_HEIGHT - hdr_h + (hdr_h - logo_h) / 2
            self.c.drawImage(LOGO_PATH, MARGIN, logo_y,
                           width=logo_w, height=logo_h, mask='auto')

        # Green accent line below header (3pt)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(0, PAGE_HEIGHT - hdr_h - 3, PAGE_WIDTH, 3, fill=1, stroke=0)

    def _draw_footer(self):
        """Draw page footer - matches build_pdf3.py page() method."""
        # Accent line above footer text (1pt, spans content width)
        CW = PAGE_WIDTH - 2 * MARGIN
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, 42, CW, 1, fill=1, stroke=0)

        # Footer text
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(MARGIN, 28, "Peakweb  |  peakweb.io")
        self.c.drawRightString(PAGE_WIDTH - MARGIN, 28, f"Page {self.page_num}")

    def _start_content_page(self):
        """Start a new content page with header, footer, and proper y position."""
        # Reference uses white background for content pages (no explicit fill)
        self._new_page(bg_color=WHITE)
        self._draw_header()
        self._draw_footer()
        # Content starts below header (42pt bar + 3pt accent + margin)
        self.y = PAGE_HEIGHT - MARGIN - 55

    def _need(self, h):
        """Check if we need a new page for content of height h."""
        if self.y - h < 65:  # Footer area
            self._start_content_page()

    def _h1(self, text):
        """Draw H1 heading with accent line - matches build_pdf3.py h1()."""
        self._need(50)
        self.y -= 18
        self._draw_semibold_text(MARGIN, self.y, text, 22, DEEP_BLUE)
        self.y -= 9
        # Accent line
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, self.y, 60, 3, fill=1, stroke=0)
        self.y -= 18

    def _h2(self, text, color=DEEP_BLUE):
        """Draw H2 heading - matches build_pdf3.py h2()."""
        self._need(36)
        self.y -= 14
        self._draw_semibold_text(MARGIN, self.y, text, 14, color)
        self.y -= 18

    def _h3(self, text, color=MIDNIGHT_GREEN):
        """Draw H3 heading - matches build_pdf3.py h3()."""
        self._need(28)
        self.y -= 10
        self._draw_semibold_text(MARGIN, self.y, text, 11, color)
        self.y -= 14

    def _body(self, text, indent=0, size=10, color=DEEP_BLUE):
        """Draw body text with wrapping - matches build_pdf3.py body()."""
        CW = PAGE_WIDTH - 2 * MARGIN
        self.c.setFillColorRGB(*color)
        self.c.setFont(FONT_LIGHT, size)
        cpl = int((CW - indent) / (size * 0.475))  # chars per line
        lh = size + 4  # line height
        for para in text.split('\n'):
            if not para.strip():
                self.y -= lh * 0.5
                continue
            for ln in textwrap.wrap(para, width=cpl):
                self._need(lh + 8)
                self.c.drawString(MARGIN + indent, self.y, ln)
                self.y -= lh

    def _bullet(self, text, indent=15, size=9.5):
        """Draw bullet point - matches build_pdf3.py bullet()."""
        CW = PAGE_WIDTH - 2 * MARGIN
        self._need(18)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_LIGHT, size)
        self.c.drawString(MARGIN + indent, self.y, "\u2022")
        self.c.setFillColorRGB(*DEEP_BLUE)
        cpl = int((CW - indent - 12) / (size * 0.475))
        lh = size + 4
        for ln in textwrap.wrap(text, width=cpl):
            self.c.drawString(MARGIN + indent + 12, self.y, ln)
            self.y -= lh

    def _callout(self, text, bg=STONE, border=AQUAMARINE, size=9.5):
        """Draw callout box - matches build_pdf3.py callout()."""
        CW = PAGE_WIDTH - 2 * MARGIN
        self.c.setFont(FONT_LIGHT, size)
        cpl = int((CW - 30) / (size * 0.475))
        lines = textwrap.wrap(text, width=cpl)
        lh = size + 4
        text_block_h = len(lines) * lh
        padding = 12
        bh = text_block_h + padding * 2
        if bh < 36:
            bh = 36
        self._need(bh + 6)
        # Box background
        box_bottom = self.y - bh + 8
        self.c.setFillColorRGB(*bg)
        self.c.roundRect(MARGIN, box_bottom, CW, bh, 4, fill=1, stroke=0)
        # Left accent border
        self.c.setFillColorRGB(*border)
        self.c.rect(MARGIN, box_bottom, 4, bh, fill=1, stroke=0)
        # Vertically centred text
        box_centre_y = box_bottom + bh / 2
        baseline_span = (len(lines) - 1) * lh
        text_start_y = box_centre_y + baseline_span / 2 - size * 0.2
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_LIGHT, size)
        ty = text_start_y
        for ln in lines:
            self.c.drawString(MARGIN + 16, ty, ln)
            ty -= lh
        self.y -= bh + 4

    def _gap(self, h=8):
        """Add vertical gap."""
        self.y -= h

    def _truncate_text(self, text, font, size, max_width):
        """Truncate text with ellipsis if it exceeds max_width."""
        if not text:
            return text
        self.c.setFont(font, size)
        if self.c.stringWidth(text, font, size) <= max_width:
            return text
        # Truncate and add ellipsis
        while len(text) > 0 and self.c.stringWidth(text + "…", font, size) > max_width:
            text = text[:-1]
        return text.rstrip() + "…"

    def _numbered(self, num, title, desc):
        """Draw numbered item with circle - matches build_pdf3.py numbered()."""
        self._need(40)
        r = 11
        cx = MARGIN + r
        cy = self.y
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.circle(cx, cy, r, fill=1, stroke=0)
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_REGULAR, 10)
        self.c.drawCentredString(cx, cy - 4, str(num))
        self._draw_semibold_text(MARGIN + 28, self.y - 2, title, 11, DEEP_BLUE)
        self.y -= 15
        if desc:
            CW = PAGE_WIDTH - 2 * MARGIN
            self.c.setFont(FONT_LIGHT, 9)
            cpl = int((CW - 28) / (9 * 0.475))
            self.c.setFillColorRGB(*DEEP_BLUE)
            for ln in textwrap.wrap(desc, width=cpl):
                self.c.drawString(MARGIN + 28, self.y, ln)
                self.y -= 12
        self.y -= 4

    def _stats_row(self, items):
        """Draw stats row with large values and labels - matches build_pdf3.py stats_row()."""
        self._need(55)
        CW = PAGE_WIDTH - 2 * MARGIN

        # Calculate actual widths needed at font size 24
        font_size = 24
        label_font_size = 8.5
        padding = 12  # minimum padding between items

        # Calculate widths for both values and labels, use max of each pair
        val_widths = [self.c.stringWidth(str(val), FONT_SEMIBOLD, font_size) for val, lab in items]
        lab_widths = [self.c.stringWidth(lab, FONT_LIGHT, label_font_size) for val, lab in items]
        col_widths = [max(vw, lw) for vw, lw in zip(val_widths, lab_widths)]
        total_needed = sum(col_widths) + padding * (len(items) - 1)

        # If content is too wide, reduce font size
        while total_needed > CW and font_size > 14:
            font_size -= 2
            val_widths = [self.c.stringWidth(str(val), FONT_SEMIBOLD, font_size) for val, lab in items]
            col_widths = [max(vw, lw) for vw, lw in zip(val_widths, lab_widths)]
            total_needed = sum(col_widths) + padding * (len(items) - 1)

        # Calculate positions - distribute extra space evenly
        extra_space = CW - total_needed
        gap = extra_space / (len(items) + 1)  # space at edges and between items

        x = MARGIN + gap
        for i, (val, lab) in enumerate(items):
            col_w = col_widths[i]
            cx = x + col_w / 2
            # Center the value within the column
            val_w = val_widths[i]
            self._draw_semibold_text(cx - val_w / 2, self.y, str(val), font_size, AQUAMARINE)
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_LIGHT, label_font_size)
            self.c.drawCentredString(cx, self.y - 16, lab)
            x += col_w + gap + padding
        self.y -= 42

    def _option_card(self, title, desc):
        """Draw option card with left accent - matches build_pdf3.py option_card()."""
        CW = PAGE_WIDTH - 2 * MARGIN
        self.c.setFont(FONT_LIGHT, 9)
        cpl = int((CW - 28) / (9 * 0.475))
        lines = textwrap.wrap(desc, width=cpl)
        ch = 18 + len(lines) * 12 + 10
        self._need(ch + 6)
        self.c.setFillColorRGB(*STONE)
        self.c.roundRect(MARGIN, self.y - ch + 8, CW, ch, 4, fill=1, stroke=0)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, self.y - ch + 8, 4, ch, fill=1, stroke=0)
        self._draw_semibold_text(MARGIN + 14, self.y, title, 11, DEEP_BLUE)
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_LIGHT, 9)
        ty = self.y - 14
        for ln in lines:
            self.c.drawString(MARGIN + 14, ty, ln)
            ty -= 12
        self.y -= ch + 4

    def _table(self, hdrs, rows):
        """Draw comparison table - matches build_pdf3.py table()."""
        CW = PAGE_WIDTH - 2 * MARGIN
        ncol = len(hdrs)
        rh = 24
        total_h = (1 + len(rows)) * rh
        self._need(total_h + 10)
        cw = CW / ncol
        x0 = MARGIN
        # Header row
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.rect(x0, self.y - rh, CW, rh, fill=1, stroke=0)
        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 9)
        for i, h in enumerate(hdrs):
            self.c.drawString(x0 + i * cw + 8, self.y - rh + 8, h)
        self.y -= rh
        # Data rows
        for r, row in enumerate(rows):
            bg = STONE if r % 2 == 0 else WHITE
            self.c.setFillColorRGB(*bg)
            self.c.rect(x0, self.y - rh, CW, rh, fill=1, stroke=0)
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_LIGHT, 9)
            for i, cell in enumerate(row):
                self.c.drawString(x0 + i * cw + 8, self.y - rh + 8, cell)
            self.y -= rh
        self.y -= 8

    def _timeline(self, week, title, led_by, items, score):
        """Draw timeline entry - matches build_pdf3.py timeline()."""
        self._need(28 + len(items) * 14)
        bw, bh = 54, 20
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.roundRect(MARGIN, self.y - bh + 6, bw, bh, 3, fill=1, stroke=0)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_LIGHT, 9)
        self.c.drawCentredString(MARGIN + bw / 2, self.y - 7, week)
        self._draw_semibold_text(MARGIN + bw + 8, self.y - 4, title, 11, DEEP_BLUE)
        self.c.setFillColorRGB(*LILAC)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(MARGIN + bw + 8, self.y - 16, f"Led by: {led_by}  |  Expected Score: {score}")
        self.y -= 28
        for item in items:
            self._bullet(item, indent=18, size=9)

    def _draw_text(self, text, x, y, font=None, size=10, color=DEEP_BLUE,
                   max_width=None, leading=None):
        """Draw text, optionally with wrapping."""
        if font is None:
            font = FONT_LIGHT
        self.c.setFillColorRGB(*color)
        self.c.setFont(font, size)

        if not leading:
            leading = size * 1.4

        if max_width and len(text) * size * 0.5 > max_width:
            # Wrap text
            lines = self._wrap_text(text, font, size, max_width)
            for line in lines:
                self.c.drawString(x, y, line)
                y -= leading
            return y
        else:
            self.c.drawString(x, y, text)
            return y - leading

    def _wrap_text(self, text, font, size, max_width):
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            width = self.c.stringWidth(test_line, font, size)

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def _draw_bullet_list(self, items, x, y, font=None, size=9.5,
                          color=DEEP_BLUE, max_width=450, spacing=14):
        """Draw a bulleted list."""
        if font is None:
            font = FONT_LIGHT
        self.c.setFillColorRGB(*color)

        for item in items:
            if not item:
                continue
            # Draw bullet
            self.c.setFont(font, size)
            self.c.drawString(x, y, "•")

            # Draw text (with wrapping)
            lines = self._wrap_text(item, font, size, max_width - 15)
            text_x = x + 15
            for line in lines:
                self.c.drawString(text_x, y, line)
                y -= size * 1.3

            y -= spacing - size * 1.3  # Additional spacing between items

        return y

    def _draw_progress_bar(self, score, x, y, width=200, height=22):
        """Draw a horizontal progress bar with rounded corners - matches build_pdf3.py score_bar()."""
        # Background - rounded rectangle
        self.c.setFillColorRGB(*SCORE_BAR_BG)
        self.c.roundRect(x, y, width, height, 11, fill=1, stroke=0)

        # Fill based on score - AMBER for < 60, AQUAMARINE for >= 60
        fill_color = AMBER if score < 60 else AQUAMARINE
        fill_width = width * (score / 100)
        self.c.setFillColorRGB(*fill_color)
        self.c.roundRect(x, y, fill_width, height, 11, fill=1, stroke=0)

    def _draw_callout_box(self, text, x, y, width, bg=STONE, border=AQUAMARINE):
        """Draw a callout box with background and left border - matches build_pdf3.py callout()."""
        size = 9.5
        self.c.setFont(FONT_LIGHT, size)
        cpl = int((width - 30) / (size * 0.475))
        lines = textwrap.wrap(text, width=cpl)
        lh = size + 4
        text_block_h = len(lines) * lh
        padding = 12
        bh = text_block_h + padding * 2
        if bh < 36:
            bh = 36

        # Box background with rounded corners
        box_bottom = y - bh + 8
        self.c.setFillColorRGB(*bg)
        self.c.roundRect(x, box_bottom, width, bh, 4, fill=1, stroke=0)

        # Left accent border
        self.c.setFillColorRGB(*border)
        self.c.rect(x, box_bottom, 4, bh, fill=1, stroke=0)

        # Vertically centered text
        box_centre_y = box_bottom + bh / 2
        baseline_span = (len(lines) - 1) * lh
        text_start_y = box_centre_y + baseline_span / 2 - size * 0.2
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_LIGHT, size)
        ty = text_start_y
        for ln in lines:
            self.c.drawString(x + 16, ty, ln)
            ty -= lh

    # =========================================================================
    # Page Rendering Methods
    # =========================================================================

    def _page_1_cover(self):
        """Cover page - matches examples/peakweb/PeakwebGEOProposal-DenverSprinklerServices.pdf
        Reference: build_pdf3.py cover() method
        """
        self._new_page(bg_color=DEEP_BLUE)

        # Green bar at top - 3pt thick (from reference: self.accent(0, PH - 3, PW, 3))
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(0, PAGE_HEIGHT - 3, PAGE_WIDTH, 3, fill=1, stroke=0)

        # Logo at top left
        # Reference uses 5:1 aspect ratio logo at (M, PH - 85, width=160)
        # Our PNG is 8000x4500 (1.78:1), so we need to position it carefully
        # y parameter is BOTTOM of image, so we need to account for image height
        if os.path.exists(LOGO_PATH):
            logo_width = 175
            # PNG is 8000x4500, so height = width / (8000/4500) = width * 0.5625
            logo_height = logo_width * (4500 / 8000)  # ≈ 98
            # Position so top of logo is just below the green bar
            # PNG has internal padding, so move it up to compensate (but leave small gap)
            logo_y = PAGE_HEIGHT + 25 - logo_height
            self.c.drawImage(LOGO_PATH, MARGIN, logo_y,
                           width=logo_width, height=logo_height, mask='auto')

        # Main title - semibold simulation (fill + stroke)
        self._draw_semibold_text(MARGIN, PAGE_HEIGHT - 200, "Website Visibility", 38, WHITE)
        self._draw_semibold_text(MARGIN, PAGE_HEIGHT - 248, "Audit", 38, WHITE)

        # Decorative line under "Audit" - 4pt thick, 80px wide (from reference)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, PAGE_HEIGHT - 266, 80, 4, fill=1, stroke=0)

        # Subtitle (below the line)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_LIGHT, 16)
        self.c.drawString(MARGIN, PAGE_HEIGHT - 296, "GEO Analysis & Implementation Proposal")

        # Client info box - from reference: iy = PH - 370, bh = 110
        iy = PAGE_HEIGHT - 370
        box_x = MARGIN
        box_width = PAGE_WIDTH - 2 * MARGIN
        left_pad = 18
        right_col = box_x + box_width / 2 + 10
        left_col_width = box_width / 2 - left_pad - 10

        # Check if contact name needs wrapping (before drawing box)
        contact_name = self.data.get('CONTACT_NAME, TITLE', '')
        self.c.setFont(FONT_LIGHT, 13)
        wrapped = self.c.stringWidth(contact_name, FONT_LIGHT, 13) > left_col_width

        # Adjust box height if wrapped
        bh = 125 if wrapped else 110

        # Light blue background - #1a4a6e from reference
        self.c.setFillColorRGB(*LIGHT_BLUE_BG)
        self.c.roundRect(box_x, iy - bh, box_width, bh, 6, fill=1, stroke=0)

        # Green left border - 4px wide
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(box_x, iy - bh, 4, bh, fill=1, stroke=0)

        # PREPARED FOR
        self.c.setFillColorRGB(*MUTED_BLUE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(box_x + left_pad, iy - 18, "PREPARED FOR")

        # Contact name (already have contact_name and wrapped from above)
        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 13)

        if wrapped:
            # Wrap to 2 lines
            cpl = int(left_col_width / (13 * 0.5))  # chars per line estimate
            lines = textwrap.wrap(contact_name, width=cpl)
            self.c.drawString(box_x + left_pad, iy - 32, lines[0] if lines else '')
            if len(lines) > 1:
                self.c.drawString(box_x + left_pad, iy - 47, lines[1])
            # Client name shifts down
            self.c.setFont(FONT_LIGHT, 11)
            self.c.drawString(box_x + left_pad, iy - 64, self.data.get('CLIENT_NAME', ''))
        else:
            self.c.drawString(box_x + left_pad, iy - 35, contact_name)
            self.c.setFont(FONT_LIGHT, 11)
            self.c.drawString(box_x + left_pad, iy - 52, self.data.get('CLIENT_NAME', ''))

        # WEBSITE (right side)
        self.c.setFillColorRGB(*MUTED_BLUE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(right_col, iy - 18, "WEBSITE")

        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 11)
        self.c.drawString(right_col, iy - 35, self.data.get('CLIENT_WEBSITE', ''))

        # DATE - add extra padding when contact name wrapped
        date_y = iy - 85 if wrapped else iy - 72
        self.c.setFillColorRGB(*MUTED_BLUE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(box_x + left_pad, date_y, "DATE")

        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 11)
        self.c.drawString(box_x + left_pad, date_y - 16, self.data.get('REPORT_DATE', ''))

        # W icon - from reference: self.w_icon(PW - 235, 50, size=260)
        self._draw_w_icon(PAGE_WIDTH - 235, 50, size=260)

        # Footer
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_LIGHT, 9)
        self.c.drawString(MARGIN, 30, "peakweb.io")

        # "Confidential" uses MUTED_BLUE (from reference)
        self.c.setFillColorRGB(*MUTED_BLUE)
        self.c.drawRightString(PAGE_WIDTH - MARGIN, 30, "Confidential")

    def _draw_semibold_text(self, x, y, text, font_size, color):
        """Simulate semi-bold by rendering text with fill + thin stroke (from build_pdf3.py)."""
        self.c.saveState()
        self.c.setFillColorRGB(*color)
        self.c.setStrokeColorRGB(*color)
        self.c.setLineWidth(font_size * 0.028)
        self.c.setFont(FONT_LIGHT, font_size)
        # Set text render mode to fill+stroke
        self.c._code.append('2 Tr')  # 2 = fill and stroke
        self.c.drawString(x, y, text)
        self.c._code.append('0 Tr')  # Reset to fill only
        self.c.restoreState()

    def _draw_w_icon(self, x, y, size=200):
        """Draw the Peakweb W icon mark (from build_pdf3.py w_icon method).
        x, y = bottom-left of bounding box. size = desired width.
        """
        # Original SVG coordinates for the 3 parallelograms
        # Bounding box in SVG: x 1033.79..1296.92, y 476.84..686.38
        orig_w = 263.13
        orig_h = 209.54
        scale = size / orig_w
        sh = orig_h * scale  # scaled height

        # Three shapes as absolute SVG coords
        shapes = [
            # Rightmost, tallest
            [(1296.92, 520.02), (1197.34, 686.38), (1171.29, 643.13), (1270.92, 476.84)],
            # Middle
            [(1178.03, 476.89), (1079.63, 641.13), (1105.65, 684.33), (1204.01, 520.02)],
            # Leftmost, shortest
            [(1085.86, 478.13), (1033.79, 565.04), (1059.79, 608.20), (1111.83, 521.26)],
        ]
        ox = 1033.79  # SVG origin x
        oy = 476.84   # SVG origin y (top in SVG)

        self.c.saveState()
        self.c.setFillColorRGB(*AQUAMARINE)
        for shape in shapes:
            p = self.c.beginPath()
            for i, (sx, sy) in enumerate(shape):
                # Transform: shift to origin, scale, flip y, position at (x, y)
                px = x + (sx - ox) * scale
                py = y + sh - (sy - oy) * scale  # flip y
                if i == 0:
                    p.moveTo(px, py)
                else:
                    p.lineTo(px, py)
            p.close()
            self.c.drawPath(p, fill=1, stroke=0)
        self.c.restoreState()

    def _draw_w_chevron(self, x, y, scale=1.0):
        """Draw the W chevron using the PNG image."""
        if os.path.exists(W_CHEVRON_PATH):
            width = 250 * scale
            height = 240 * scale
            self.c.drawImage(W_CHEVRON_PATH, x, y,
                           width=width, height=height,
                           preserveAspectRatio=True, mask='auto')

    def _page_2_executive_summary(self):
        """Executive Summary page - matches build_pdf3.py p_exec_summary()."""
        self._start_content_page()

        self._h1("Executive Summary")

        # Intro paragraph
        sample_query = self.data.get('SAMPLE_QUERY', 'your services')
        years = self.data.get('YEARS', '')
        bbb = self.data.get('BBB_RATING', '')

        intro = f'When someone asks ChatGPT, Google AI, or Perplexity a question like "{sample_query}" your business is rarely mentioned'
        if years and bbb:
            intro += f' – even though you have {years} years of experience and an {bbb} BBB rating.'
        else:
            intro += '.'

        self._body(intro)
        self._gap(6)

        # Callout box
        self._callout(
            "This audit identifies the specific gaps holding you back and outlines what "
            "needs to change. Every issue has a proven solution – Peakweb can guide "
            "implementation to ensure it's done right the first time."
        )
        self._gap(4)

        # The New Reality: AI Search
        self._h2("The New Reality: AI Search")
        self._body(
            "The way people find local businesses is changing rapidly. Traditional Google Search "
            "still matters – customers search and get a list of links. But AI Search is growing "
            "fast: customers ask ChatGPT or Perplexity a question and get 2–3 direct recommendations. "
            "Those recommended businesses get the calls."
        )
        self._gap(4)

        city = self.data.get('CITY', 'your area')
        industry = self.data.get('INDUSTRY', 'your industry')
        service = self.data.get('SERVICE_TYPE', 'services')

        self._body(
            f"Right now, AI systems answering questions about {city} {industry} or {service} "
            "services rarely mention your business. Not because you're not qualified, but "
            "because your website doesn't communicate effectively with AI systems yet."
        )
        self._gap(6)

        # What Is GEO?
        self._h2("What Is GEO?")
        self._body("GEO stands for Generative Engine Optimization. Think of it this way:")
        self._gap(3)
        self._bullet("SEO (Search Engine Optimization) = Making your website show up in Google search results")
        self._bullet("GEO (Generative Engine Optimization) = Making your website get recommended by ChatGPT, Claude, Google AI, and Perplexity")
        self._gap(4)

        self._body(
            "Studies show that 30–115% more people discover businesses optimized for AI search "
            "compared to those that aren't. Your competitors who figure this out first will "
            "capture those leads. It's like having a Yellow Pages ad in 1990 vs. not having one."
        )
        self._gap(6)

        # Why GEO Matters Now
        self._h2("Why GEO Matters Now")
        self._body(
            "You need both SEO and GEO. Traditional SEO gets you found in Google. GEO gets you "
            "recommended by AI. Most SEO services don't include GEO yet – it's too new. "
            "That's why early movers have a huge advantage right now."
        )

    def _page_3_current_score(self):
        """Your Current Score page - matches build_pdf3.py p_score()."""
        self._start_content_page()

        self._h1("Your Current Score")
        self._gap(4)

        # Score bar and number - matches build_pdf3.py score_bar()
        score = self.data.get('GEO_SCORE', 53)
        if isinstance(score, str):
            try:
                score = int(score)
            except:
                score = 53

        CW = PAGE_WIDTH - 2 * MARGIN
        gw = CW * 0.65
        gh = 22
        gx = MARGIN
        gy = self.y - 6
        # Draw the progress bar
        self._draw_progress_bar(score, gx, gy, width=gw, height=gh)
        # Score number to the right
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 28)
        self.c.drawString(gx + gw + 14, gy - 4, str(score))
        self.c.setFont(FONT_LIGHT, 14)
        self.c.drawString(gx + gw + 50, gy, "/ 100")
        self.y -= 42

        # Score label callout with warning styling
        score_label = self.data.get('SCORE_LABEL', 'FAIR')
        score_desc = self.data.get('SCORE_DESCRIPTION',
            "Your website is functional but not optimized for AI systems. "
            "AI search engines can access your site but rarely cite or recommend it. "
            "You're not invisible, but you're not competing effectively.")
        self._callout(f"{score_label} – {score_desc}", bg=WARN_BG, border=AMBER)
        self._gap(6)

        # What's Working Well
        self._h2("What's Working Well")
        working = [
            self.data.get('WORKING_1', ''),
            self.data.get('WORKING_2', ''),
            self.data.get('WORKING_3', ''),
            self.data.get('WORKING_4', ''),
            self.data.get('WORKING_5', ''),
        ]
        for w in working:
            if w:
                self._bullet(w)
        self._gap(6)

        # Foundation callout
        self._callout("The foundation is solid. Peakweb's job is to make AI systems notice it.")
        self._gap(8)

        # What This Means For Your Business
        self._h2("What This Means For Your Business")
        city = self.data.get('CITY', 'your area')
        industry = self.data.get('INDUSTRY', 'your industry')
        service_plural = self.data.get('SERVICE_TYPE_PLURAL', 'services')
        self._body(
            f"When AI systems answer questions about {city} {industry} or {service_plural}, "
            "they rarely mention your business. This means:"
        )
        self._gap(3)

        means = [
            self.data.get('MEANS_1', ''),
            self.data.get('MEANS_2', ''),
            self.data.get('MEANS_3', ''),
        ]
        for m in means:
            if m:
                self._bullet(m)

    def _page_4_issues_1_to_3(self):
        """Issues 1-3 page - matches build_pdf3.py p_issues1()."""
        self._start_content_page()

        self._h1("The 6 Key Issues Identified")
        self._gap(3)

        # Issue 1
        title1 = self.data.get('ISSUE_1_TITLE', "AI Systems Don't Know Who You Are")
        body1 = self.data.get('ISSUE_1_BODY',
            'Your business has no "identity" in AI databases – no Wikipedia page, no LinkedIn '
            'company page, minimal online presence beyond your website.')
        callout1 = self.data.get('ISSUE_1_CALLOUT', 'Impact: Lost leads from the 30–40% of people now using AI to research local services.')

        self._h2(f"1. {title1}")
        self._body(body1)
        self._gap(3)
        if callout1:
            self._callout(callout1, bg=WARN_BG, border=AMBER)
        self._gap(6)

        # Issue 2
        title2 = self.data.get('ISSUE_2_TITLE', "Your Website Has No Dates On Anything")
        body2 = self.data.get('ISSUE_2_BODY',
            'Not a single page shows when it was published or last updated. Your testimonials have '
            'no dates. AI systems assume undated content is stale and won\'t cite it.')
        example2 = self.data.get('ISSUE_2_EXAMPLE', '')

        self._h2(f"2. {title2}")
        self._body(body2)
        self._gap(3)
        if example2:
            self._body(example2, size=9, color=MIDNIGHT_GREEN)
        self._gap(6)

        # Issue 3
        title3 = self.data.get('ISSUE_3_TITLE', "Testimonials Are Hidden From AI")
        body3 = self.data.get('ISSUE_3_BODY',
            'You have customer testimonials but they\'re not marked up in a way AI systems '
            'can understand. No star ratings show up in Google results.')
        callout3 = self.data.get('ISSUE_3_CALLOUT',
            'This is a solvable problem. With the right technical implementation, your '
            'reviews can start showing star ratings in search results immediately.')

        self._h2(f"3. {title3}")
        self._body(body3)
        self._gap(3)
        if callout3:
            self._callout(callout3)

    def _page_5_issues_4_to_6(self):
        """Issues 4-6 + What Happens page - matches build_pdf3.py p_issues2()."""
        self._start_content_page()

        # Issue 4
        title4 = self.data.get('ISSUE_4_TITLE', "Content Is Generic Marketing Copy")
        body4 = self.data.get('ISSUE_4_BODY',
            'Your service pages use generic phrases but lack the specific, verifiable data that '
            'AI systems look for when deciding which businesses to recommend.')
        callout4 = self.data.get('ISSUE_4_CALLOUT',
            "Peakweb's content strategy transforms your real-world expertise into the data-rich, "
            "AI-friendly format that earns citations and recommendations.")

        self._h2(f"4. {title4}")
        self._body(body4)
        self._gap(3)
        if callout4:
            self._callout(callout4)
        self._gap(6)

        # Issue 5
        title5 = self.data.get('ISSUE_5_TITLE', "Missing Technical Files AI Systems Look For")
        body5 = self.data.get('ISSUE_5_BODY',
            "Your site is missing critical configuration files that AI systems rely on to "
            "understand and index your business. Without them, AI systems have to guess what "
            "you do – many give up and cite competitors instead.")
        callout5 = self.data.get('ISSUE_5_CALLOUT',
            "These files require precise formatting and placement. Misconfigured files "
            "can actually hurt visibility. Peakweb handles this as part of every GEO engagement.")

        self._h2(f"5. {title5}")
        self._body(body5)
        self._gap(2)
        if callout5:
            self._callout(callout5)
        self._gap(6)

        # Issue 6
        title6 = self.data.get('ISSUE_6_TITLE', "Business Information Inconsistency")
        body6 = self.data.get('ISSUE_6_BODY',
            "AI systems fact-check claims. When they find conflicting information across "
            "your online presence, they either skip citing you entirely or cite competitors "
            "with consistent information.")
        callout6 = self.data.get('ISSUE_6_CALLOUT',
            "Resolving this requires a coordinated update across your website, directory listings, "
            "and business profiles. Peakweb ensures consistency across every platform AI checks.")

        self._h2(f"6. {title6}")
        self._body(body6)
        self._gap(3)
        if callout6:
            self._callout(callout6)
        self._gap(8)

        # What Happens If You Do Nothing
        self._h2("What Happens If You Do Nothing?")
        self._gap(2)

        self._h3("Short-term (Next 6 months):")
        short_term = [
            self.data.get('NOTHING_SHORT_1', 'Competitors who optimize for AI will get recommended more often'),
            self.data.get('NOTHING_SHORT_2', "You'll continue missing leads from the growing AI search audience (30–40% of searches)"),
            self.data.get('NOTHING_SHORT_3', 'The gap between you and optimized competitors widens'),
        ]
        for s in short_term:
            if s:
                self._bullet(s)
        self._gap(3)

        self._h3("Long-term (1–2 years):")
        long_term = [
            self.data.get('NOTHING_LONG_1', 'AI search becomes the dominant way people find local services'),
            self.data.get('NOTHING_LONG_2', 'Businesses without AI visibility become increasingly invisible'),
            self.data.get('NOTHING_LONG_3', 'Playing catch-up gets harder as competitors build content libraries and authority'),
        ]
        for l in long_term:
            if l:
                self._bullet(l)

    def _page_6_opportunity(self):
        """The Opportunity page - matches build_pdf3.py p_quick_wins()."""
        self._start_content_page()

        self._h1("The Opportunity")
        self._body(
            "Our audit identified issues across four key areas that are preventing AI systems "
            "from recommending your business. The good news: every one of them is fixable, and "
            "the projected impact is significant."
        )
        self._gap(6)

        self._h2("Your Score Improvement Potential")
        self._gap(4)

        score = self.data.get('GEO_SCORE', 53)
        projected = str(self.data.get('PROJECTED', '79+'))
        if '/' in projected:
            projected = projected.replace('/100', '+')
        if projected.isdigit():
            projected = projected + "+"

        self._stats_row([
            (str(score), "Current Score"),
            ("→", ""),
            (projected, "Projected Score"),
        ])
        self._gap(4)

        self._h3("Areas Requiring Attention:")
        self._gap(2)

        self._numbered(1, "Technical Configuration",
            self.data.get('OPP_1_DESC',
                "Your site is missing key files and data formats that AI systems "
                "rely on to discover, understand, and recommend local businesses."))
        self._numbered(2, "Content & Authority Signals",
            self.data.get('OPP_2_DESC',
                "AI systems need verifiable data, not marketing copy. Your experience "
                "isn't documented in a way AI can parse and cite."))
        self._numbered(3, "Trust & Consistency",
            self.data.get('OPP_3_DESC',
                "Conflicting information across your online presence causes AI systems "
                "to question your credibility and skip you in favor of competitors."))
        self._numbered(4, "Freshness & Relevance",
            self.data.get('OPP_4_DESC',
                "Without timestamps, update signals, and current content, AI treats "
                "your site as potentially outdated and deprioritizes it."))
        self._gap(6)

        self._callout(
            "Each of these areas involves multiple coordinated changes that must be implemented "
            "correctly and in the right sequence. Peakweb's GEO methodology addresses all four "
            "areas in a structured 30-day engagement – validated across every major AI platform."
        )

    def _page_7_roadmap(self):
        """4-Week Roadmap page - matches build_pdf3.py p_plan()."""
        self._start_content_page()

        self._h1("How Peakweb Gets You There")
        self._gap(3)
        self._body(
            "Our GEO methodology follows a proven 4-week rollout, sequenced so each phase "
            "builds on the last. You stay focused on running your business while we handle "
            "the technical implementation and platform validation."
        )
        self._gap(4)

        city = self.data.get('CITY', 'local')

        self._timeline("Week 1", "Technical Foundation", "Peakweb-led", [
            "Deploy all critical AI configuration and discovery signals",
            "Resolve trust and consistency issues across your online presence",
        ], self.data.get('W1_SCORE', '70–75'))
        self._gap(3)

        self._timeline("Week 2", "Authority & Identity", "Collaborative", [
            "Build your verified presence on key AI-indexed platforms",
            "You provide business content; we structure it for AI consumption",
        ], self.data.get('W2_SCORE', '78–82'))
        self._gap(3)

        self._timeline("Week 3", "Content Depth", "Collaborative", [
            f"Publish AI-optimized content that positions you as the {city} authority",
            "Enrich your site with the verifiable data AI systems cite",
        ], self.data.get('W3_SCORE', '82–86'))
        self._gap(3)

        self._timeline("Week 4", "Validation & Launch", "Peakweb-led", [
            "QA across all major AI platforms (ChatGPT, Perplexity, Claude, Google AI)",
            "Set up GA4 AI/GEO traffic channel group for ongoing tracking",
        ], self.data.get('W4_SCORE', '85–90'))

    def _page_8_pricing(self):
        """Pricing and ROI page - matches build_pdf3.py p_investment()."""
        self._start_content_page()

        self._h1("Working With Peakweb")
        self._gap(3)
        self._body(
            "GEO optimization involves specialized technical work – structured data formats, "
            "AI crawler protocols, and platform-specific configurations that change frequently. "
            "A general web developer can update your content, but the AI-specific implementation "
            "requires expertise in how each AI platform indexes and ranks local businesses."
        )
        self._gap(4)

        self._option_card(
            "GEO Essentials – Guided Implementation ($1,000)",
            "Peakweb handles all 7 priority technical fixes, deploys AI configuration files, "
            "implements structured data, and validates your site across all major AI platforms. "
            "You provide business content (photos, testimonials, project details); we handle the rest. "
            "Includes GA4 AI traffic channel setup for ongoing tracking."
        )
        self._option_card(
            "GEO Growth – Full 30-Day Engagement ($2,000–$3,000)",
            "Everything in Essentials plus: authority-building across AI-indexed platforms, "
            "AI-optimized content creation (guides, FAQs, case studies), and video channel repair. "
            "Includes 3 monthly follow-up reports to track progress and refine strategy."
        )
        self._option_card(
            "GEO Partner – Ongoing Optimization ($500/month)",
            "After initial implementation, Peakweb publishes fresh content to maintain relevance "
            "signals, adapts your strategy as AI platforms evolve, and provides monthly progress "
            "reports. Automated monitoring dashboard coming soon."
        )
        self._gap(8)

        self._h2("Expected Return on Investment")
        self._gap(4)

        self._stats_row([
            (self.data.get('LEADS_PER_MONTH', '7–8'), "Additional Leads/Mo"),
            (self.data.get('CUSTOMERS_PER_MONTH', '2–3'), "New Customers/Mo"),
            (self.data.get('MONTHLY_REV', '$1K–6K'), "Add'l Monthly Rev"),
            (self.data.get('ANNUAL_IMPACT', '$12–72K'), "Annual Impact"),
        ])
        self._gap(2)

        self._callout(
            "Break-even: Implementation pays for itself in the first month. Unlike one-time "
            "marketing, these improvements keep working 24/7 with compounding returns."
        )
        self._gap(6)

        self._h2("The Compounding Effect")
        self._gap(2)
        self._bullet("Month 1–3: Initial boost as AI systems discover updated content")
        self._bullet("Month 4–6: Momentum builds as you add more content (blog, videos)")
        self._bullet("Month 7–12: You become a recognized authority; AI systems cite you regularly")
        self._bullet("Year 2+: Competitors struggle to catch up; you're the established AI-visible brand")

    def _page_9_seo_vs_geo(self):
        """SEO vs GEO comparison page - matches build_pdf3.py p_comparison()."""
        self._start_content_page()

        self._h1("Traditional SEO vs. GEO")
        self._body(
            'You might be thinking: "I already paid for SEO. Isn\'t this the same thing?" '
            "The short answer is no. Here's how they compare:"
        )
        self._gap(6)

        self._table(
            ["Traditional SEO", "GEO (AI Optimization)"],
            [
                ["Goal: Rank in Google's 10 blue links", "Goal: Get mentioned by ChatGPT / AI"],
                ["Optimizes for keywords", "Optimizes for natural language questions"],
                ["Success = page 1 ranking", "Success = AI recommendation"],
                ["Works for Google search", "Works for ChatGPT, Perplexity, Google AI, Claude"],
                ["Established practice (20+ years)", "Emerging practice (critical now)"],
            ]
        )
        self._gap(4)

        self._callout(
            "You need BOTH. Traditional SEO gets you found in Google. GEO gets you recommended "
            "by AI. The catch: most SEO services don't include GEO yet. Early movers win."
        )
        self._gap(8)

        self._h2("Even If AI Search Stalls, You Still Win")
        self._body("Every optimization in this audit also improves your traditional Google SEO:")
        self._gap(3)
        self._bullet("Star ratings increase click-through rates in Google results")
        self._bullet("Fresh content with dates ranks better in Google search")
        self._bullet("Case studies with data build authority and attract backlinks")
        self._bullet("FAQ pages answer user questions and capture featured snippets")
        self._bullet("Complete structured data helps Google understand your business")
        self._gap(4)

        self._callout("These are best practices regardless of AI. You literally can't lose.")

    def _page_10_before_after(self):
        """Before/After + FAQ page - matches build_pdf3.py p_before_after()."""
        self._start_content_page()
        CW = PAGE_WIDTH - 2 * MARGIN

        self._h1("What This Looks Like in Practice")
        self._gap(3)
        self._body("Here's what happens when a potential customer asks an AI assistant for help:")
        self._gap(8)

        # BEFORE box - red background
        service = self.data.get('SERVICE_TYPE', 'services')
        city = self.data.get('CITY', 'your area')
        lines_before = [
            f'Customer: "Who should I call for {service} in {city}?"',
            '',
            'AI Response: "Here are some well-reviewed options:',
            '  – GreenCo Services (mentioned in multiple sources)',
            '  – ProTech Solutions (4.8 stars, established since 2010)',
            '  – Mountain View Pros (industry certified)"',
            '',
            'Your business: Not mentioned.',
        ]
        bh = len(lines_before) * 12 + 30
        self._need(bh + 8)
        self.c.setFillColorRGB(*SOFT_RED_BG)
        self.c.roundRect(MARGIN, self.y - bh, CW, bh, 5, fill=1, stroke=0)
        self._draw_semibold_text(MARGIN + 14, self.y - 16, "BEFORE Optimization", 11, (0.8, 0.27, 0.27))
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_LIGHT, 9)
        ty = self.y - 32
        for ln in lines_before:
            self.c.drawString(MARGIN + 14, ty, ln)
            ty -= 12
        self.y -= bh + 10

        # AFTER box - green background
        client_name = self.data.get('CLIENT_NAME', 'Your Business')
        years = self.data.get('YEARS', '25+')
        lines_after = [
            f'Customer: "Who should I call for {service} in {city}?"',
            '',
            'AI Response: "Here are some well-reviewed options:',
            f'  – {client_name} ({years} years experience, BBB A+,',
            f'    serving {city}. Typical pricing $85–150)',
            '  – GreenCo Services (mentioned in multiple sources)',
            '  – ProTech Solutions (4.8 stars)"',
            '',
            'Your business: Mentioned FIRST with specific details and contact info.',
        ]
        bh = len(lines_after) * 12 + 30
        self._need(bh + 8)
        self.c.setFillColorRGB(*SOFT_GREEN_BG)
        self.c.roundRect(MARGIN, self.y - bh, CW, bh, 5, fill=1, stroke=0)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, self.y - bh, 4, bh, fill=1, stroke=0)
        self._draw_semibold_text(MARGIN + 14, self.y - 16, "AFTER Optimization", 11, MIDNIGHT_GREEN)
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_LIGHT, 9)
        ty = self.y - 32
        for ln in lines_after:
            self.c.drawString(MARGIN + 14, ty, ln)
            ty -= 12
        self.y -= bh + 8

        self._callout(
            "Same customer, same question. One scenario: they never hear about you. "
            "The other: you're recommended first with supporting details. "
            "How many customers asked this question last month and never heard your name?"
        )
        self._gap(8)

        # FAQs
        self._h2("Frequently Asked Questions")
        self._gap(3)

        self._h3('"Is this really necessary? My business is doing fine."')
        self._body(
            "Your business IS doing fine – years of success proves that. But consider: "
            "in 2005, businesses said \"I don't need a website.\" In 2010, \"I don't need Google reviews.\" "
            "In 2015, \"I don't need social media.\" Those who adapted early dominated their markets. "
            "AI search is the next shift.",
            size=9.5
        )
        self._gap(4)

        self._h3('"How long will these changes stay relevant?"')
        self._body(
            "The technical foundation we build is permanent – it doesn't expire or need replacing. "
            "Content assets (guides, FAQs, case studies) appreciate over time and keep driving leads "
            "for years. That said, AI platforms evolve quickly, which is why ongoing monitoring matters. "
            "Peakweb's GEO Partner plan keeps you current as the landscape shifts.",
            size=9.5
        )

    def _page_11_next_steps(self):
        """Next Steps + Bottom Line page - matches build_pdf3.py p_next_steps()."""
        self._start_content_page()
        CW = PAGE_WIDTH - 2 * MARGIN

        self._h1("Next Steps")
        self._gap(3)

        self._numbered(1, "Schedule a 30-Minute Strategy Call with Peakweb",
            "We'll walk through this audit together, answer your questions, and "
            "recommend the right engagement level for your goals and budget.")
        self._numbered(2, "Choose Your Implementation Package",
            self.data.get('NEXT_STEP_2',
            "We offer packages tailored to your site complexity and goals. "
            "See the pricing options in this report, or ask us for a custom quote."))
        self._numbered(3, "Gather Your Business Content",
            "While Peakweb handles the technical side, you'll want to have project photos, "
            "customer stories, and service details ready. We'll send you a simple content checklist.")
        self._numbered(4, "Implementation Begins",
            "Peakweb deploys changes in the sequence outlined in our 30-day roadmap, "
            "with check-ins at each milestone so you always know what's happening.")
        self._numbered(5, "Validate and Launch",
            self.data.get('NEXT_STEP_5',
            "We validate changes across all AI platforms, provide a final score report, "
            "and document everything for your team. Ongoing monitoring available separately."))

        self._gap(10)

        # The Bottom Line box
        bh = 85
        self._need(bh + 10)
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.roundRect(MARGIN, self.y - bh, CW, bh, 6, fill=1, stroke=0)

        # Centered title
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_SEMIBOLD, 16)
        self.c.drawCentredString(PAGE_WIDTH / 2, self.y - 22, "The Bottom Line")

        # Centered text
        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 10)
        line1 = self.data.get('BOTTOM_LINE_1', "You've built an excellent business.")
        line2 = self.data.get('BOTTOM_LINE_2', "The only thing holding you back is that AI systems don't know about it yet.")
        self.c.drawCentredString(PAGE_WIDTH / 2, self.y - 42, line1)
        self.c.drawCentredString(PAGE_WIDTH / 2, self.y - 56, line2)

        # Closer
        closer = self.data.get('BOTTOM_LINE_CLOSER', "Let's fix that.")
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_SEMIBOLD, 12)
        self.c.drawCentredString(PAGE_WIDTH / 2, self.y - 74, closer)

    def _page_12_cta(self):
        """Final CTA page."""
        self._new_page(bg_color=DEEP_BLUE)

        y = PAGE_HEIGHT - 200

        # Main CTA
        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_SEMIBOLD, 28)
        self.c.drawCentredString(PAGE_WIDTH / 2, y, "Ready to Get Started?")
        y -= 40

        self.c.setFont(FONT_LIGHT, 14)
        self.c.drawCentredString(PAGE_WIDTH / 2, y, "Schedule your free strategy call and we'll walk")
        y -= 20
        self.c.drawCentredString(PAGE_WIDTH / 2, y, "through every finding in this audit together.")
        y -= 50

        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_SEMIBOLD, 16)
        self.c.drawCentredString(PAGE_WIDTH / 2, y, "Your business deserves to be seen. Let's make it happen.")
        y -= 60

        # Website
        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 18)
        self.c.drawCentredString(PAGE_WIDTH / 2, y, "peakweb.io")

        # W icon (centered) - from reference: self.w_icon(PW / 2 - 80, 60, size=160)
        self._draw_w_icon(PAGE_WIDTH / 2 - 80, 60, size=160)

        # Footer
        client_name = self.data.get('CLIENT_NAME_FULL', self.data.get('CLIENT_NAME', ''))
        report_date = self.data.get('REPORT_DATE', '')

        self.c.setFillColorRGB(*LILAC)
        self.c.setFont(FONT_LIGHT, 7.5)
        footer_text = f"This report was prepared {report_date}, for {client_name}."
        self.c.drawCentredString(PAGE_WIDTH / 2, 40, footer_text)
        self.c.drawCentredString(PAGE_WIDTH / 2, 28, "Results and timelines are based on current AI search landscape. Individual results may vary.")


# =============================================================================
# Sample Data
# =============================================================================

SAMPLE_DATA = {
    "CONTACT_NAME, TITLE": "Grant Gullicks, Owner & Master Taxidermist",
    "CLIENT_NAME": "Wild Reflections Studio",
    "CLIENT_WEBSITE": "wildreflectionsstudio.com",
    "REPORT_DATE": "March 18, 2026",
    "CLIENT_NAME_FULL": "Wild Reflections Studio",

    "SAMPLE_QUERY": "Who does taxidermy in Anchorage?",
    "YEARS": "23",
    "BBB_RATING": "A+",
    "CITY": "Anchorage",
    "INDUSTRY": "taxidermy",
    "SERVICE_TYPE": "taxidermy",
    "SERVICE_TYPE_PLURAL": "taxidermy services",

    "GEO_SCORE": 38,
    "SCORE_LABEL": "POOR",
    "SCORE_DESCRIPTION": "Your website is functional but invisible to AI systems. Wix's JavaScript rendering and lack of structured data make it hard for AI to understand your business.",

    "WORKING_1": "AI crawlers are allowed - your robots.txt doesn't block ChatGPT, Claude, or others",
    "WORKING_2": "Exceptional credentials - 23+ years experience, trained at world-famous Animal Artistry",
    "WORKING_3": "Industry recognition - quoted as expert in Hunt Alaska Magazine",
    "WORKING_4": "Sheep specialization - a genuine differentiator few competitors can claim",

    "MEANS_1": "Lost projects from hunters who never hear your name when asking AI for recommendations",
    "MEANS_2": "Competitors with inferior work get recommended instead of you",
    "MEANS_3": "Your Animal Artistry training and sheep specialization are invisible to AI systems",

    "ISSUE_1_TITLE": "Wix Sites Are Nearly Invisible to AI",
    "ISSUE_1_BODY": "Wix uses JavaScript rendering which many AI crawlers can't process. Your content may be invisible to ChatGPT, Claude, and others.",
    "ISSUE_1_CALLOUT": "Impact: AI systems may see a blank page instead of your years of expertise",

    "ISSUE_2_TITLE": "No Structured Data for AI to Parse",
    "ISSUE_2_BODY": "Your site has zero schema markup. AI systems don't know you're a LocalBusiness, what services you offer, or your specializations.",
    "ISSUE_2_CALLOUT": "Adding schema takes 2 hours and immediately helps AI understand your business",

    "ISSUE_3_TITLE": "Your Expert Credentials Aren't Discoverable",
    "ISSUE_3_BODY": "You trained at Animal Artistry (one of the most prestigious programs). This isn't structured for AI to find and cite.",
    "ISSUE_3_CALLOUT": "This credential alone should make you a top recommendation",

    "ISSUE_4_TITLE": "No Instructions for AI Systems",
    "ISSUE_4_BODY": "Your website has no llms.txt file telling AI systems what your business does and what makes you unique.",
    "ISSUE_4_CALLOUT": "Adding this takes 30 minutes and immediately helps AI understand you",

    "ISSUE_5_TITLE": "Sheep Specialization Not Highlighted",
    "ISSUE_5_BODY": "You specialize in sheep mounts - a rare expertise. But this isn't prominently structured for AI discovery.",
    "ISSUE_5_CALLOUT": "Hunters specifically asking about sheep taxidermy won't find you",

    "ISSUE_6_TITLE": "Limited Online Presence Beyond Website",
    "ISSUE_6_BODY": "AI systems build recommendations from multiple sources. A single website isn't enough to build authority signals.",
    "ISSUE_6_CALLOUT": "LinkedIn, Google Business Profile, and industry directories all help",

    "NOTHING_SHORT_1": "Hunters asking AI for taxidermist recommendations won't hear your name",
    "NOTHING_SHORT_2": "Competitors who optimize will capture the growing AI search market",
    "NOTHING_SHORT_3": "Your years of expertise remain invisible to 30-40% of potential customers",

    "NOTHING_LONG_1": "AI search becomes the primary way hunters find taxidermists",
    "NOTHING_LONG_2": "The gap between you and AI-optimized competitors becomes insurmountable",
    "NOTHING_LONG_3": "Your Animal Artistry training and reputation fade from digital discovery",

    "PROJECTED": "78/100",

    "OPP_1_DESC": "Fix Wix rendering issues or deploy AI-friendly landing pages",
    "OPP_2_DESC": "Add comprehensive LocalBusiness and Service schema markup",
    "OPP_3_DESC": "Structure your credentials (Animal Artistry, sheep expertise) for AI",
    "OPP_4_DESC": "Build presence on platforms AI trusts (LinkedIn, Google Business)",

    "W1_SCORE": "52/100",
    "W2_SCORE": "62/100",
    "W3_SCORE": "70/100",
    "W4_SCORE": "78/100",

    "LEADS_PER_MONTH": "3-5",
    "CUSTOMERS_PER_MONTH": "1-2",
    "MONTHLY_REV": "$500-2K",
    "ANNUAL_IMPACT": "$6-24K",

    "BEFORE_LINE_1": "Hunter: 'Who does quality taxidermy in Anchorage?'",
    "BEFORE_LINE_2": "ChatGPT: 'Here are some options in the Anchorage area:'",
    "BEFORE_LINE_3": "- Northland Taxidermy (mentioned on hunting forums)",
    "BEFORE_LINE_4": "- Alaska Wildlife Creations (has Google reviews)",
    "BEFORE_LINE_5": "Your business: Not mentioned",

    "AFTER_LINE_1": "Hunter: 'Who does quality taxidermy in Anchorage?'",
    "AFTER_LINE_2": "ChatGPT: 'Here are some highly regarded options:'",
    "AFTER_LINE_3": "- Wild Reflections Studio (23+ years, Animal Artistry trained)",
    "AFTER_LINE_4": "- Northland Taxidermy",
    "AFTER_LINE_5": "- Alaska Wildlife Creations",
    "AFTER_LINE_6": "Your business: Mentioned FIRST with credentials",

    "FAQ_1_Q": "Can Wix sites really be optimized for AI?",
    "FAQ_1_A": "Yes, but it requires workarounds. We can add schema via Wix's custom code feature, create an llms.txt, and potentially deploy AI-optimized landing pages that complement your main site.",

    "FAQ_2_Q": "How long until I see results?",
    "FAQ_2_A": "Technical fixes show impact in 2-4 weeks. Building authority takes 2-3 months. Full optimization typically reaches target score in 90 days.",

    "BOTTOM_LINE_1": "You've built a stellar reputation as a master taxidermist.",
    "BOTTOM_LINE_2": "AI systems just don't know about it yet.",
    "BOTTOM_LINE_CLOSER": "Let's change that.",
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Using sample data for testing...")
        data = SAMPLE_DATA
        output = "PeakwebGEOProposal-Sample.pdf"
    elif len(sys.argv) == 2:
        with open(sys.argv[1], 'r') as f:
            raw_data = json.load(f)
        data = normalize_data(raw_data)
        # Handle both CLIENT_NAME and client_name for filename
        client = data.get('CLIENT_NAME', raw_data.get('client_name', 'Output'))
        client = client.replace(' ', '').replace('&', 'And')
        output = f"PeakwebGEOProposal-{client}.pdf"
    else:
        with open(sys.argv[1], 'r') as f:
            raw_data = json.load(f)
        data = normalize_data(raw_data)
        output = sys.argv[2]

    generator = PitchDeckGenerator(data, output)
    generator.generate()
