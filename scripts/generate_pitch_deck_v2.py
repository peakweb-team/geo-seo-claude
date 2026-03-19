#!/usr/bin/env python3
"""
Peakweb Pitch Deck Generator v2 - Fully Programmatic

Generates a 12-page branded PDF from scratch using ReportLab.
Follows Peakweb brand guidelines exactly.
"""

import json
import math
import os
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
        bh = 110
        box_x = MARGIN
        box_width = PAGE_WIDTH - 2 * MARGIN

        # Light blue background - #1a4a6e from reference
        self.c.setFillColorRGB(*LIGHT_BLUE_BG)
        self.c.roundRect(box_x, iy - bh, box_width, bh, 6, fill=1, stroke=0)

        # Green left border - 4px wide
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(box_x, iy - bh, 4, bh, fill=1, stroke=0)

        # Labels use MUTED_BLUE color (from reference)
        left_pad = 18
        right_col = box_x + box_width / 2 + 10

        # PREPARED FOR
        self.c.setFillColorRGB(*MUTED_BLUE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(box_x + left_pad, iy - 18, "PREPARED FOR")

        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 13)
        self.c.drawString(box_x + left_pad, iy - 35, self.data.get('CONTACT_NAME, TITLE', ''))
        self.c.setFont(FONT_LIGHT, 11)
        self.c.drawString(box_x + left_pad, iy - 52, self.data.get('CLIENT_NAME', ''))

        # WEBSITE (right side)
        self.c.setFillColorRGB(*MUTED_BLUE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(right_col, iy - 18, "WEBSITE")

        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 11)
        self.c.drawString(right_col, iy - 35, self.data.get('CLIENT_WEBSITE', ''))

        # DATE
        self.c.setFillColorRGB(*MUTED_BLUE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(box_x + left_pad, iy - 72, "DATE")

        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 11)
        self.c.drawString(box_x + left_pad, iy - 88, self.data.get('REPORT_DATE', ''))

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
        """Issues 1-3 page."""
        self._new_page()
        self._draw_header()
        self._draw_footer()

        y = PAGE_HEIGHT - 100

        # Title
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 24)
        self.c.drawString(MARGIN, y, "The 6 Key Issues Identified")
        y -= 40

        # Issues 1-3
        for i in range(1, 4):
            title = self.data.get(f'ISSUE_{i}_TITLE', '')
            body = self.data.get(f'ISSUE_{i}_BODY', '')
            callout = self.data.get(f'ISSUE_{i}_CALLOUT', '') or self.data.get(f'ISSUE_{i}_EXAMPLE', '')

            if not title:
                continue

            # Issue number and title
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_SEMIBOLD, 14)
            self.c.drawString(MARGIN, y, f"{i}. {title}")
            y -= 20

            # Body
            y = self._draw_text(body, MARGIN, y, max_width=500)
            y -= 5

            # Callout
            if callout:
                self.c.setFillColorRGB(*MIDNIGHT_GREEN)
                self.c.setFont(FONT_LIGHT, 9)
                y = self._draw_text(callout, MARGIN + 15, y, color=MIDNIGHT_GREEN, max_width=485, size=9)

            y -= 25

    def _page_5_issues_4_to_6(self):
        """Issues 4-6 + What Happens page."""
        self._new_page()
        self._draw_header()
        self._draw_footer()

        y = PAGE_HEIGHT - 100

        # Issues 4-6
        for i in range(4, 7):
            title = self.data.get(f'ISSUE_{i}_TITLE', '')
            body = self.data.get(f'ISSUE_{i}_BODY', '')
            callout = self.data.get(f'ISSUE_{i}_CALLOUT', '') or self.data.get(f'ISSUE_{i}_EXAMPLE', '')

            if not title:
                continue

            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_SEMIBOLD, 14)
            self.c.drawString(MARGIN, y, f"{i}. {title}")
            y -= 20

            y = self._draw_text(body, MARGIN, y, max_width=500)
            y -= 5

            if callout:
                self.c.setFillColorRGB(*MIDNIGHT_GREEN)
                y = self._draw_text(callout, MARGIN + 15, y, color=MIDNIGHT_GREEN, max_width=485, size=9)

            y -= 25

        # What Happens If You Do Nothing
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 16)
        self.c.drawString(MARGIN, y, "What Happens If You Do Nothing?")
        y -= 25

        # Short-term
        self.c.setFont(FONT_SEMIBOLD, 11)
        self.c.drawString(MARGIN, y, "Short-term (Next 6 months):")
        y -= 15

        short_term = [
            self.data.get('NOTHING_SHORT_1', ''),
            self.data.get('NOTHING_SHORT_2', ''),
            self.data.get('NOTHING_SHORT_3', ''),
        ]
        short_term = [s for s in short_term if s]
        y = self._draw_bullet_list(short_term, MARGIN, y, max_width=490)
        y -= 15

        # Long-term
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 11)
        self.c.drawString(MARGIN, y, "Long-term (1–2 years):")
        y -= 15

        long_term = [
            self.data.get('NOTHING_LONG_1', ''),
            self.data.get('NOTHING_LONG_2', ''),
            self.data.get('NOTHING_LONG_3', ''),
        ]
        long_term = [l for l in long_term if l]
        self._draw_bullet_list(long_term, MARGIN, y, max_width=490)

    def _page_6_opportunity(self):
        """The Opportunity page."""
        self._new_page()
        self._draw_header()
        self._draw_footer()

        y = PAGE_HEIGHT - 100

        # Title
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 24)
        self.c.drawString(MARGIN, y, "The Opportunity")
        y -= 30

        intro = "Our audit identified issues across four key areas that are preventing AI systems from recommending your business. The good news: every one of them is fixable, and the projected impact is significant."
        y = self._draw_text(intro, MARGIN, y, max_width=500)
        y -= 30

        # Score improvement box
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 14)
        self.c.drawString(MARGIN, y, "Your Score Improvement Potential")
        y -= 40

        score = self.data.get('GEO_SCORE', 53)
        projected = self.data.get('PROJECTED', '85/100')

        # Current score
        self.c.setFont(FONT_SEMIBOLD, 28)
        self.c.drawString(MARGIN + 50, y, str(score))
        self.c.setFont(FONT_LIGHT, 10)
        self.c.drawString(MARGIN + 50, y - 20, "Current Score")

        # Arrow
        self.c.setFont(FONT_LIGHT, 24)
        self.c.drawString(MARGIN + 150, y, "→")

        # Projected score
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_SEMIBOLD, 28)
        self.c.drawString(MARGIN + 250, y, projected.replace('/100', '+'))
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_LIGHT, 10)
        self.c.drawString(MARGIN + 250, y - 20, "Projected Score")

        y -= 60

        # Areas
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 14)
        self.c.drawString(MARGIN, y, "Areas Requiring Attention:")
        y -= 25

        areas = [
            ("1", "Technical Configuration", self.data.get('OPP_1_DESC', '')),
            ("2", "Content & Authority Signals", self.data.get('OPP_2_DESC', '')),
            ("3", "Trust & Consistency", self.data.get('OPP_3_DESC', '')),
            ("4", "Freshness & Relevance", self.data.get('OPP_4_DESC', '')),
        ]

        for num, title, desc in areas:
            # Number circle
            self.c.setFillColorRGB(*AQUAMARINE)
            self.c.circle(MARGIN + 10, y + 5, 10, fill=1, stroke=0)
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_SEMIBOLD, 10)
            self.c.drawCentredString(MARGIN + 10, y + 2, num)

            # Title
            self.c.setFont(FONT_SEMIBOLD, 11)
            self.c.drawString(MARGIN + 30, y + 5, title)

            # Description
            self.c.setFont(FONT_LIGHT, 9)
            y = self._draw_text(desc, MARGIN + 30, y - 10, max_width=470, size=9)
            y -= 15

    def _page_7_roadmap(self):
        """4-Week Roadmap page."""
        self._new_page()
        self._draw_header()
        self._draw_footer()

        y = PAGE_HEIGHT - 100

        # Title
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 24)
        self.c.drawString(MARGIN, y, "How Peakweb Gets You There")
        y -= 30

        intro = "Our GEO methodology follows a proven 4-week rollout, sequenced so each phase builds on the last. You stay focused on running your business while we handle the technical implementation and platform validation."
        y = self._draw_text(intro, MARGIN, y, max_width=500)
        y -= 30

        weeks = [
            ("Week 1", "Technical Foundation", self.data.get('W1_SCORE', '65/100'), "Peakweb-led", [
                "Deploy all critical AI configuration and discovery signals",
                "Resolve trust and consistency issues across your online presence"
            ]),
            ("Week 2", "Authority & Identity", self.data.get('W2_SCORE', '72/100'), "Collaborative", [
                "Build your verified presence on key AI-indexed platforms",
                "You provide business content; we structure it for AI consumption"
            ]),
            ("Week 3", "Content Depth", self.data.get('W3_SCORE', '80/100'), "Collaborative", [
                f"Publish AI-optimized content that positions you as the {self.data.get('CITY', 'local')} authority",
                "Enrich your site with the verifiable data AI systems cite"
            ]),
            ("Week 4", "Validation & Launch", self.data.get('W4_SCORE', '85/100'), "Peakweb-led", [
                "QA across all major AI platforms (ChatGPT, Perplexity, Claude, Google AI)",
                "Deliver monitoring dashboard and ongoing content strategy"
            ]),
        ]

        for week, title, score, led_by, bullets in weeks:
            # Week header
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_SEMIBOLD, 12)
            self.c.drawString(MARGIN, y, f"{week}")

            self.c.setFont(FONT_SEMIBOLD, 12)
            self.c.drawString(MARGIN + 60, y, title)

            # Led by and score
            self.c.setFillColorRGB(*LILAC)
            self.c.setFont(FONT_LIGHT, 8)
            self.c.drawString(MARGIN + 60, y - 12, f"Led by: {led_by}  |  Expected Score: {score}")

            y -= 30

            # Bullets
            self.c.setFillColorRGB(*DEEP_BLUE)
            y = self._draw_bullet_list(bullets, MARGIN + 20, y, max_width=470, spacing=10)
            y -= 15

    def _page_8_pricing(self):
        """Pricing and ROI page."""
        self._new_page()
        self._draw_header()
        self._draw_footer()

        y = PAGE_HEIGHT - 100

        # Title
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 24)
        self.c.drawString(MARGIN, y, "Working With Peakweb")
        y -= 30

        intro = "GEO optimization involves specialized technical work – structured data formats, AI crawler protocols, and platform-specific configurations that change frequently."
        y = self._draw_text(intro, MARGIN, y, max_width=500)
        y -= 25

        # Pricing packages
        packages = [
            ("GEO Essentials – $1,000", "Peakweb handles all priority technical fixes, deploys AI configuration files, implements structured data, and validates your site across all major AI platforms. Includes 30-day post-launch monitoring."),
            ("GEO Growth – $2,000–$3,000", "Everything in Essentials plus: authority-building across AI-indexed platforms, AI-optimized content creation, and a 90-day monitoring dashboard. Best for maximum visibility in the shortest time."),
            ("GEO Partner – $500/month", "After initial implementation, Peakweb monitors your AI visibility monthly, publishes fresh content to maintain relevance signals, and adapts your strategy as AI platforms evolve."),
        ]

        for title, desc in packages:
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_SEMIBOLD, 11)
            self.c.drawString(MARGIN, y, title)
            y -= 15
            y = self._draw_text(desc, MARGIN, y, max_width=500, size=9)
            y -= 20

        # ROI Section
        y -= 10
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 16)
        self.c.drawString(MARGIN, y, "Expected Return on Investment")
        y -= 35

        # ROI metrics
        metrics = [
            (self.data.get('LEADS_PER_MONTH', '7-8'), "Additional Leads/Mo"),
            (self.data.get('CUSTOMERS_PER_MONTH', '2-3'), "New Customers/Mo"),
            (self.data.get('MONTHLY_REV', '$1K-6K'), "Add'l Monthly Rev"),
            (self.data.get('ANNUAL_IMPACT', '$12-72K'), "Annual Impact"),
        ]

        x = MARGIN
        for value, label in metrics:
            self.c.setFillColorRGB(*AQUAMARINE)
            self.c.setFont(FONT_SEMIBOLD, 20)
            self.c.drawString(x, y, value)

            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_LIGHT, 8)
            self.c.drawString(x, y - 15, label)

            x += 125

    def _page_9_seo_vs_geo(self):
        """SEO vs GEO comparison page."""
        self._new_page()
        self._draw_header()
        self._draw_footer()

        y = PAGE_HEIGHT - 100

        # Title
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 24)
        self.c.drawString(MARGIN, y, "Traditional SEO vs. GEO")
        y -= 30

        intro = 'You might be thinking: "I already paid for SEO. Isn\'t this the same thing?" The short answer is no. Here\'s how they compare:'
        y = self._draw_text(intro, MARGIN, y, max_width=500)
        y -= 30

        # Comparison table
        comparisons = [
            ("Goal: Rank in Google's 10 blue links", "Goal: Get mentioned by ChatGPT / AI"),
            ("Optimizes for keywords", "Optimizes for natural language questions"),
            ("Success = page 1 ranking", "Success = AI recommendation"),
            ("Works for Google search", "Works for ChatGPT, Perplexity, Google AI, Claude"),
            ("Established practice (20+ years)", "Emerging practice (critical now)"),
        ]

        # Headers
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 11)
        self.c.drawString(MARGIN, y, "Traditional SEO")
        self.c.drawString(MARGIN + 260, y, "GEO (AI Optimization)")
        y -= 20

        for seo, geo in comparisons:
            self.c.setFont(FONT_LIGHT, 9)
            self.c.drawString(MARGIN, y, seo)
            self.c.drawString(MARGIN + 260, y, geo)
            y -= 15

        y -= 20

        conclusion = "You need BOTH. Traditional SEO gets you found in Google. GEO gets you recommended by AI. The catch: most SEO services don't include GEO yet. Early movers win."
        self._draw_callout_box(conclusion, MARGIN, y - 20, 500)
        y -= 70

        # Even If AI Stalls section
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 14)
        self.c.drawString(MARGIN, y, "Even If AI Search Stalls, You Still Win")
        y -= 20

        still_win = "Every optimization in this audit also improves your traditional Google SEO:"
        y = self._draw_text(still_win, MARGIN, y, max_width=500)
        y -= 5

        benefits = [
            "Star ratings increase click-through rates in Google results",
            "Fresh content with dates ranks better in Google search",
            "Case studies with data build authority and attract backlinks",
            "FAQ pages answer user questions and capture featured snippets",
            "Complete structured data helps Google understand your business"
        ]
        y = self._draw_bullet_list(benefits, MARGIN, y, max_width=490)

        y -= 10
        self._draw_text("These are best practices regardless of AI. You literally can't lose.", MARGIN, y,
                       font=FONT_SEMIBOLD, size=10)

    def _page_10_before_after(self):
        """Before/After + FAQ page."""
        self._new_page()
        self._draw_header()
        self._draw_footer()

        y = PAGE_HEIGHT - 100

        # Title
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 24)
        self.c.drawString(MARGIN, y, "What This Looks Like in Practice")
        y -= 30

        intro = "Here's what happens when a potential customer asks an AI assistant for help:"
        y = self._draw_text(intro, MARGIN, y, max_width=500)
        y -= 25

        # BEFORE box
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 12)
        self.c.drawString(MARGIN, y, "BEFORE Optimization")
        y -= 20

        before_lines = [
            self.data.get('BEFORE_LINE_1', ''),
            self.data.get('BEFORE_LINE_2', ''),
            self.data.get('BEFORE_LINE_3', ''),
            self.data.get('BEFORE_LINE_4', ''),
            self.data.get('BEFORE_LINE_5', ''),
        ]

        self.c.setFont(FONT_LIGHT, 9)
        for line in before_lines:
            if line:
                self.c.drawString(MARGIN + 15, y, line)
                y -= 12

        y -= 20

        # AFTER box
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 12)
        self.c.drawString(MARGIN, y, "AFTER Optimization")
        y -= 20

        after_lines = [
            self.data.get('AFTER_LINE_1', ''),
            self.data.get('AFTER_LINE_2', ''),
            self.data.get('AFTER_LINE_3', ''),
            self.data.get('AFTER_LINE_4', ''),
            self.data.get('AFTER_LINE_5', ''),
            self.data.get('AFTER_LINE_6', ''),
        ]

        self.c.setFont(FONT_LIGHT, 9)
        for line in after_lines:
            if line:
                self.c.drawString(MARGIN + 15, y, line)
                y -= 12

        y -= 30

        # FAQs
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 16)
        self.c.drawString(MARGIN, y, "Frequently Asked Questions")
        y -= 25

        # FAQ 1
        q1 = self.data.get('FAQ_1_Q', '')
        a1 = self.data.get('FAQ_1_A', '')
        if q1:
            self.c.setFillColorRGB(*MIDNIGHT_GREEN)
            self.c.setFont(FONT_SEMIBOLD, 10)
            self.c.drawString(MARGIN, y, f'"{q1}"')
            y -= 15
            self.c.setFillColorRGB(*DEEP_BLUE)
            y = self._draw_text(a1, MARGIN, y, max_width=500, size=9)
            y -= 15

        # FAQ 2
        q2 = self.data.get('FAQ_2_Q', '')
        a2 = self.data.get('FAQ_2_A', '')
        if q2:
            self.c.setFillColorRGB(*MIDNIGHT_GREEN)
            self.c.setFont(FONT_SEMIBOLD, 10)
            self.c.drawString(MARGIN, y, f'"{q2}"')
            y -= 15
            self.c.setFillColorRGB(*DEEP_BLUE)
            self._draw_text(a2, MARGIN, y, max_width=500, size=9)

    def _page_11_next_steps(self):
        """Next Steps + Bottom Line page."""
        self._new_page()
        self._draw_header()
        self._draw_footer()

        y = PAGE_HEIGHT - 100

        # Title
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 24)
        self.c.drawString(MARGIN, y, "Next Steps")
        y -= 35

        steps = [
            ("1", "Schedule a 30-Minute Strategy Call", "We'll walk through this audit together, answer your questions, and recommend the right engagement level for your goals and budget."),
            ("2", "Choose Your Implementation Package", "GEO Essentials ($1,000) for priority technical fixes, GEO Growth ($2,000–$3,000) for the full 30-day roadmap, or GEO Partner ($500/mo) for ongoing optimization."),
            ("3", "Gather Your Business Content", "While Peakweb handles the technical side, you'll want to have project photos, customer stories, and service details ready."),
            ("4", "Implementation Begins", "Peakweb deploys changes in the sequence outlined in our 30-day roadmap, with check-ins at each milestone."),
            ("5", "Track Results Together", "We'll monitor your visibility across ChatGPT, Perplexity, Google AI, and Claude – and provide monthly reports."),
        ]

        for num, title, desc in steps:
            # Number
            self.c.setFillColorRGB(*AQUAMARINE)
            self.c.circle(MARGIN + 10, y + 5, 12, fill=1, stroke=0)
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_SEMIBOLD, 11)
            self.c.drawCentredString(MARGIN + 10, y + 1, num)

            # Title
            self.c.setFont(FONT_SEMIBOLD, 11)
            self.c.drawString(MARGIN + 35, y + 5, title)

            # Description
            y = self._draw_text(desc, MARGIN + 35, y - 10, max_width=460, size=9)
            y -= 20

        y -= 20

        # The Bottom Line
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 18)
        self.c.drawString(MARGIN, y, "The Bottom Line")
        y -= 25

        line1 = self.data.get('BOTTOM_LINE_1', "You've built an excellent business.")
        line2 = self.data.get('BOTTOM_LINE_2', "The only thing holding you back is that AI systems don't know about it yet.")

        self.c.setFont(FONT_LIGHT, 11)
        self.c.drawString(MARGIN, y, line1)
        y -= 16
        self.c.drawString(MARGIN, y, line2)
        y -= 25

        closer = self.data.get('BOTTOM_LINE_CLOSER', "Let's fix that.")
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_SEMIBOLD, 14)
        self.c.drawString(MARGIN, y, closer)

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
    "ISSUE_1_CALLOUT": "Impact: AI systems may see a blank page instead of your 23 years of expertise",

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
    "NOTHING_SHORT_3": "Your 23 years of expertise remain invisible to 30-40% of potential customers",

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

    "BOTTOM_LINE_1": "You've built a stellar reputation over 23 years.",
    "BOTTOM_LINE_2": "AI systems just don't know about it yet.",
    "BOTTOM_LINE_CLOSER": "Let's change that.",
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Using sample data for testing...")
        data = SAMPLE_DATA
        output = "PeakwebGEOProposal-WildReflections-v2.pdf"
    elif len(sys.argv) == 2:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
        client = data.get('CLIENT_NAME', 'Output').replace(' ', '')
        output = f"PeakwebGEOProposal-{client}.pdf"
    else:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
        output = sys.argv[2]

    generator = PitchDeckGenerator(data, output)
    generator.generate()
