#!/usr/bin/env python3
"""
Peakweb GEO Snapshot — Slim 3-Page Pitch Deck Generator

Generates a concise, infographic-style 3-page PDF designed for cold outreach
to small business owners. Complements (but does not replace) the full 12-page
pitch deck — use this first, then follow up with the full deck after engagement.

Usage:
    python3 generate_slim_deck.py                      # Sample Denver Sprinkler data
    python3 generate_slim_deck.py data.json            # Custom client data
    python3 generate_slim_deck.py data.json out.pdf    # Custom output filename

JSON input schema:
    {
      "client_name": "Denver Sprinkler & Landscape",
      "client_website": "denversprinklerservices.com",
      "report_date": "March 23, 2026",
      "contact_name": "Ramon Robles",
      "geo_score": 52,
      "score_label": "Fair",
      "projected_score": 85,
      "working": ["item 1", "item 2", "item 3"],
      "improvements": ["item 1", "item 2", "item 3"],
      "onsite_tasks": 6,
      "offsite_tasks": 4
    }
"""

import json
import math
import os
import re
import sys
import textwrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
FONTS_DIR = os.path.join(PROJECT_DIR, "assets/fonts")
LOGO_PATH = os.path.join(PROJECT_DIR, "assets/PeakWeb-Green-RGB.png")
LOGO_STONE_BLUE_PATH = os.path.join(PROJECT_DIR, "assets/Stone-Blue.png")
W_CHEVRON_PATH = os.path.join(PROJECT_DIR, "assets/PeakWeb-W-Chevron.png")

# ─── Page dimensions ──────────────────────────────────────────────────────────
PAGE_WIDTH, PAGE_HEIGHT = letter   # 612 × 792 pts
MARGIN = 54                         # 0.75 in
CW = PAGE_WIDTH - 2 * MARGIN       # 504 pts content width

# ─── Brand colours (RGB 0–1) ──────────────────────────────────────────────────
DEEP_BLUE      = (10/255,  44/255,  73/255)    # #0A2C49
AQUAMARINE     = (1/255,  239/255, 160/255)    # #01EFA0
LIGHT_GREEN    = (188/255, 255/255, 138/255)   # #BCFF8A
MIDNIGHT_GREEN = (10/255,  62/255,  60/255)    # #0A3E3C
LILAC          = (152/255, 146/255, 181/255)   # #9892B5
STONE          = (252/255, 247/255, 230/255)   # #FCF7E6
WHITE          = (1, 1, 1)
AMBER          = (245/255, 166/255,  35/255)   # #F5A623
SCORE_BG       = (232/255, 236/255, 240/255)   # #E8ECF0
WARN_BG        = (255/255, 248/255, 230/255)   # #FFF8E6
LIGHT_BLUE_BG  = (26/255,  74/255, 110/255)    # #1a4a6e

# ─── Font name globals (overridden by register_fonts if Outfit is available) ──
FONT_THIN     = 'Helvetica'
FONT_LIGHT    = 'Helvetica'
FONT_REGULAR  = 'Helvetica'
FONT_SEMIBOLD = 'Helvetica-Bold'


def register_fonts():
    """Try to register Outfit fonts; fall back to Helvetica."""
    global FONT_THIN, FONT_LIGHT, FONT_REGULAR, FONT_SEMIBOLD
    font_files = [
        ('Outfit-Thin',     'Outfit-Thin.ttf'),
        ('Outfit-Light',    'Outfit-Light.ttf'),
        ('Outfit-Regular',  'Outfit-Regular.ttf'),
        ('Outfit-SemiBold', 'Outfit-SemiBold.ttf'),
    ]
    loaded = 0
    for name, fname in font_files:
        path = os.path.join(FONTS_DIR, fname)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                loaded += 1
            except Exception as e:
                print(f"Warning: could not load {name}: {e}")
    if loaded >= 4:
        FONT_THIN     = 'Outfit-Thin'
        FONT_LIGHT    = 'Outfit-Light'
        FONT_REGULAR  = 'Outfit-Regular'
        FONT_SEMIBOLD = 'Outfit-SemiBold'
        print("Using Outfit fonts")
    else:
        print("Using Helvetica fallback fonts")


# ─── Default sample data (Denver Sprinkler) ───────────────────────────────────
DEFAULT_DATA = {
    "client_name":    "Denver Sprinkler & Landscape",
    "client_website": "denversprinklerservices.com",
    "report_date":    "March 23, 2026",
    "contact_name":   "Ramon Robles",
    "geo_score":      52,
    "score_label":    "Fair",
    "projected_score": 85,
    "working": [
        "AI crawlers can access your site (GPTBot, ClaudeBot allowed)",
        "Strong technical foundation — WordPress, HTTPS, mobile-ready",
        "LocalBusiness schema & Google Business Profile exist",
    ],
    "improvements": [
        "No llms.txt — AI systems lack structured guidance about you",
        "Missing FAQ schema on service pages (key citation opportunity)",
        "Limited presence on AI-indexed third-party platforms",
    ],
    "onsite_tasks":  6,
    "offsite_tasks": 4,
}


def normalize(data):
    """Return a copy of data with sensible defaults for missing fields."""
    d = dict(DEFAULT_DATA)
    d.update(data)
    # Ensure lists are lists, cap at 3 items
    for key in ("working", "improvements"):
        if not isinstance(d.get(key), list):
            d[key] = []
        d[key] = d[key][:3]
    d["onsite_tasks"]  = int(d.get("onsite_tasks",  0))
    d["offsite_tasks"] = int(d.get("offsite_tasks", 0))
    d["geo_score"]     = int(d.get("geo_score", 0))
    d["projected_score"] = int(d.get("projected_score", 85))
    return d


# ─── Generator ────────────────────────────────────────────────────────────────

class SlimDeckGenerator:
    def __init__(self, data, output_path):
        self.d = normalize(data)
        self.output_path = output_path
        self.c = None
        self._page_num = 0

    # ── public ────────────────────────────────────────────────────────────────

    def generate(self):
        register_fonts()
        self.c = canvas.Canvas(self.output_path, pagesize=letter)
        self._page_1()
        self._page_2()
        self._page_3()
        self.c.save()
        print(f"Generated: {self.output_path}")

    # ── low-level canvas helpers ──────────────────────────────────────────────

    def _new_page(self, bg=WHITE):
        if self._page_num > 0:
            self.c.showPage()
        self._page_num += 1
        self.c.setFillColorRGB(*bg)
        self.c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

    def _draw_header(self, dark_bg=False, logo_path=None):
        """Deep Blue header bar with logo + client info."""
        hdr_h = 42
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.rect(0, PAGE_HEIGHT - hdr_h, PAGE_WIDTH, hdr_h, fill=1, stroke=0)

        chosen_logo = logo_path or LOGO_PATH
        if os.path.exists(chosen_logo):
            logo_w = 90
            # Stone-Blue.jpg is square (4500×4500), Green-RGB.png is 8000×4500
            is_square = chosen_logo == LOGO_STONE_BLUE_PATH
            logo_h = logo_w if is_square else logo_w * (4500 / 8000)
            logo_y = PAGE_HEIGHT - hdr_h + (hdr_h - logo_h) / 2
            self.c.drawImage(chosen_logo, MARGIN, logo_y,
                             width=logo_w, height=logo_h, mask='auto')

        # Client name + domain right-aligned
        client = self.d["client_name"]
        domain = self.d["client_website"]
        cy_top = PAGE_HEIGHT - 14
        cy_bot = PAGE_HEIGHT - 28
        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_SEMIBOLD, 9)
        self.c.drawRightString(PAGE_WIDTH - MARGIN, cy_top, client)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawRightString(PAGE_WIDTH - MARGIN, cy_bot, domain)

        # Aquamarine accent stripe
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(0, PAGE_HEIGHT - hdr_h - 3, PAGE_WIDTH, 3, fill=1, stroke=0)

    def _draw_footer(self, text_color=DEEP_BLUE, line_color=AQUAMARINE):
        """Footer with brand name and page number."""
        self.c.setFillColorRGB(*line_color)
        self.c.rect(MARGIN, 42, CW, 1, fill=1, stroke=0)
        self.c.setFillColorRGB(*text_color)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(MARGIN, 28, "Peakweb  |  peakweb.io")
        self.c.drawRightString(PAGE_WIDTH - MARGIN, 28,
                                f"{self._page_num} / 3")

    def _sb(self, x, y, text, size, color):
        """Semibold text via fill+stroke trick (preserves brand weight)."""
        self.c.saveState()
        self.c.setFillColorRGB(*color)
        self.c.setStrokeColorRGB(*color)
        self.c.setLineWidth(size * 0.028)
        self.c.setFont(FONT_SEMIBOLD if FONT_SEMIBOLD != 'Helvetica-Bold'
                       else FONT_LIGHT, size)
        self.c._code.append('2 Tr')
        self.c.drawString(x, y, text)
        self.c._code.append('0 Tr')
        self.c.restoreState()

    def _sb_centered(self, cx, y, text, size, color):
        self.c.saveState()
        self.c.setFont(FONT_SEMIBOLD, size)
        w = self.c.stringWidth(text, FONT_SEMIBOLD, size)
        self.c.restoreState()
        self._sb(cx - w / 2, y, text, size, color)

    def _text(self, x, y, text, size, color, font=None):
        f = font or FONT_LIGHT
        self.c.setFillColorRGB(*color)
        self.c.setFont(f, size)
        self.c.drawString(x, y, text)

    def _text_centered(self, cx, y, text, size, color, font=None):
        f = font or FONT_LIGHT
        self.c.setFillColorRGB(*color)
        self.c.setFont(f, size)
        self.c.drawCentredString(cx, y, text)

    def _sb_centered_with_emoji(self, cx, y, emoji, text, size, color):
        """Draw centred semibold text preceded by an emoji image, both centred together."""
        from PIL import Image, ImageDraw, ImageFont as PILFont
        import tempfile

        EMOJI_FONT = '/System/Library/Fonts/Apple Color Emoji.ttc'
        px_size = int(size * 5)          # render at 5× for sharpness
        pt_h = size * 1.35               # visual height in PDF pts
        gap = size * 0.55                # gap between emoji and text

        # Measure text width
        self.c.setFont(FONT_SEMIBOLD, size)
        text_w = self.c.stringWidth(text, FONT_SEMIBOLD, size)

        if os.path.exists(EMOJI_FONT):
            try:
                img = Image.new('RGBA', (px_size, px_size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                efont = PILFont.truetype(EMOJI_FONT, px_size - 4)
                draw.text((0, 0), emoji, font=efont, embedded_color=True)
                # Crop to bounding box of non-transparent pixels
                bbox = img.getbbox()
                if bbox:
                    img = img.crop(bbox)
                aspect = img.width / img.height
                pt_w = pt_h * aspect
                total_w = pt_w + gap + text_w
                ex = cx - total_w / 2
                # Save to temp PNG and embed in PDF
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
                    img.save(tf.name)
                    self.c.drawImage(tf.name, ex, y - 1,
                                     width=pt_w, height=pt_h, mask='auto')
                os.unlink(tf.name)
                self._sb(ex + pt_w + gap, y, text, size, color)
                return
            except Exception:
                pass

        # Fallback: centred text only (no emoji)
        self._sb_centered(cx, y, text, size, color)

    def _italic(self, x, y, text, size, color):
        """Simulate italic via a horizontal shear transform. Returns glyph width."""
        skew = math.tan(math.radians(13))
        self.c.saveState()
        self.c.setFillColorRGB(*color)
        self.c.setFont(FONT_LIGHT, size)
        self.c.transform(1, 0, skew, 1, 0, 0)
        self.c.drawString(x - skew * y, y, text)
        self.c.restoreState()
        return self.c.stringWidth(text, FONT_LIGHT, size)

    def _render_segments(self, x, y, segments, base_size, base_color):
        """Render a list of (text, style, color_override) tuples inline.

        style: 'normal' | 'bold' | 'italic'
        color_override: RGB tuple or None to use base_color
        Returns x after the last segment.
        """
        px = x
        for text, style, color_override in segments:
            color = color_override or base_color
            if style == 'bold':
                self._sb(px, y, text, base_size, color)
                self.c.setFont(FONT_SEMIBOLD, base_size)
                px += self.c.stringWidth(text, FONT_SEMIBOLD, base_size)
            elif style == 'italic':
                px += self._italic(px, y, text, base_size, color)
            else:
                self.c.setFillColorRGB(*color)
                self.c.setFont(FONT_LIGHT, base_size)
                self.c.drawString(px, y, text)
                px += self.c.stringWidth(text, FONT_LIGHT, base_size)
        return px

    def _wrap(self, text, font, size, max_w):
        """Word-wrap text to fit max_w; returns list of lines."""
        words = text.split()
        lines, cur = [], []
        for w in words:
            test = ' '.join(cur + [w])
            if self.c.stringWidth(test, font, size) <= max_w:
                cur.append(w)
            else:
                if cur:
                    lines.append(' '.join(cur))
                cur = [w]
        if cur:
            lines.append(' '.join(cur))
        return lines or ['']

    def _draw_wrapped(self, x, y, text, size, color, max_w, leading=None,
                      font=None, centered=False, center_x=None):
        """Draw wrapped text, return y after last line."""
        f = font or FONT_LIGHT
        lh = leading or (size * 1.4)
        lines = self._wrap(text, f, size, max_w)
        self.c.setFillColorRGB(*color)
        self.c.setFont(f, size)
        for ln in lines:
            if centered and center_x:
                self.c.drawCentredString(center_x, y, ln)
            else:
                self.c.drawString(x, y, ln)
            y -= lh
        return y

    # ── compound drawing helpers ──────────────────────────────────────────────

    def _section_title_band(self, title, y_top=747, band_h=50):
        """Stone background section title bar just below the header."""
        self.c.setFillColorRGB(*STONE)
        self.c.rect(0, y_top - band_h, PAGE_WIDTH, band_h, fill=1, stroke=0)
        text_y = y_top - band_h + (band_h - 18) / 2 + 8
        self._sb(MARGIN, text_y, title, 18, DEEP_BLUE)
        # Short aquamarine underline
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, text_y - 8, 50, 3, fill=1, stroke=0)
        return y_top - band_h  # bottom of band

    def _col_header(self, x, y, w, h, label, bg, text_color):
        """Filled rectangle column header."""
        self.c.setFillColorRGB(*bg)
        self.c.rect(x, y, w, h, fill=1, stroke=0)
        # Vertically center text
        text_y = y + (h - 10) / 2 + 2
        self.c.setFillColorRGB(*text_color)
        self.c.setFont(FONT_SEMIBOLD, 10)
        self.c.drawCentredString(x + w / 2, text_y, label)

    def _col_body(self, x, y, w, h, lines, bg, text_color, text_size=9):
        """Filled content box with wrapped text lines."""
        self.c.setFillColorRGB(*bg)
        self.c.rect(x, y, w, h, fill=1, stroke=0)
        ty = y + h - 18
        pad = 10
        lh = text_size * 1.45
        for line in lines:
            wrapped = self._wrap(line, FONT_LIGHT, text_size, w - pad * 2)
            for wl in wrapped:
                if ty > y + 4:
                    self.c.setFillColorRGB(*text_color)
                    self.c.setFont(FONT_LIGHT, text_size)
                    self.c.drawString(x + pad, ty, wl)
                    ty -= lh

    def _stat_badge(self, x, y, w, h, big_val, label, val_color=AQUAMARINE):
        """A large stat number with label below, in a Stone rounded rect."""
        self.c.setFillColorRGB(*STONE)
        self.c.roundRect(x, y, w, h, 6, fill=1, stroke=0)
        # Big value centred
        self._sb_centered(x + w / 2, y + h * 0.52, big_val, 30, val_color)
        # Label wrapped below
        lh = 11
        lines = self._wrap(label, FONT_LIGHT, 8.5, w - 20)
        ty = y + h * 0.52 - 22
        for ln in lines:
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_LIGHT, 8.5)
            self.c.drawCentredString(x + w / 2, ty, ln)
            ty -= lh

    def _icon_card(self, x, y, w, h, icon, title, desc,
                   bg, icon_bg, icon_fg, text_color=DEEP_BLUE, border_color=None):
        """Infographic card with coloured background, icon circle, title, desc."""
        r = 6
        self.c.setFillColorRGB(*bg)
        self.c.roundRect(x, y, w, h, r, fill=1, stroke=0)
        # Optional left border accent
        if border_color:
            self.c.setFillColorRGB(*border_color)
            self.c.rect(x, y, 4, h, fill=1, stroke=0)
        # Icon circle (centred horizontally, near top)
        cx = x + w / 2
        circle_cy = y + h - 22
        cr = 12
        self.c.setFillColorRGB(*icon_bg)
        self.c.circle(cx, circle_cy, cr, fill=1, stroke=0)
        self.c.setFillColorRGB(*icon_fg)
        self.c.setFont(FONT_SEMIBOLD, 14)
        self.c.drawCentredString(cx, circle_cy - 5, icon)
        # Title
        title_y = y + h - 46
        self.c.setFillColorRGB(*text_color)
        self.c.setFont(FONT_SEMIBOLD, 10)
        title_lines = self._wrap(title, FONT_SEMIBOLD, 10, w - 16)
        for tl in title_lines:
            self.c.drawCentredString(cx, title_y, tl)
            title_y -= 14
        # Desc
        desc_y = title_y - 4
        desc_lines = self._wrap(desc, FONT_LIGHT, 8, w - 16)
        for dl in desc_lines[:3]:
            self.c.setFillColorRGB(*text_color)
            self.c.setFont(FONT_LIGHT, 8)
            self.c.drawCentredString(cx, desc_y, dl)
            desc_y -= 11

    def _bullet_col(self, items, x, y, w, bullet_color, text_color=DEEP_BLUE,
                    bg=None, bg_h=None, text_size=9):
        """Bulleted list in a (optionally backed) column."""
        pad = 12
        lh = text_size * 1.5
        if bg and bg_h:
            self.c.setFillColorRGB(*bg)
            self.c.roundRect(x, y, w, bg_h, 5, fill=1, stroke=0)
        ty = y + (bg_h or 0) - 18 if bg else y
        for item in items:
            # Bullet circle
            self.c.setFillColorRGB(*bullet_color)
            self.c.circle(x + pad, ty + 3, 4, fill=1, stroke=0)
            # Text
            wrapped = self._wrap(item, FONT_LIGHT, text_size,
                                 w - pad * 2 - 10)
            for i, wl in enumerate(wrapped):
                self.c.setFillColorRGB(*text_color)
                self.c.setFont(FONT_LIGHT, text_size)
                self.c.drawString(x + pad + 10, ty, wl)
                ty -= lh
            ty -= 4

    def _score_arc(self, cx, cy, radius, score, score_label):
        """Draw a thick-stroke semicircle gauge for the GEO score."""
        lw = 18
        x1, y1 = cx - radius, cy - radius
        x2, y2 = cx + radius, cy + radius

        # Background arc (full 180°)
        self.c.saveState()
        self.c.setLineWidth(lw)
        self.c.setStrokeColorRGB(*SCORE_BG)
        p = self.c.beginPath()
        p.arc(x1, y1, x2, y2, startAng=0, extent=180)
        self.c.drawPath(p, stroke=1, fill=0)

        # Score arc (proportional)
        arc_color = AMBER if score < 60 else (
            LIGHT_GREEN if score >= 80 else AQUAMARINE)
        self.c.setStrokeColorRGB(*arc_color)
        extent = score / 100 * 180
        p2 = self.c.beginPath()
        p2.arc(x1, y1, x2, y2, startAng=0, extent=extent)
        self.c.drawPath(p2, stroke=1, fill=0)
        self.c.restoreState()

        # Score number
        self._sb_centered(cx, cy - 10, str(score), 36, DEEP_BLUE)
        # "/ 100" right of score
        self.c.setFont(FONT_LIGHT, 13)
        score_w = self.c.stringWidth(str(score), FONT_SEMIBOLD, 36)
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.drawString(cx + score_w / 2 + 4, cy - 10, "/ 100")
        # Label below
        label_color = AMBER if score < 60 else (
            LIGHT_GREEN if score >= 80 else AQUAMARINE)
        self._sb_centered(cx, cy - 30, score_label.upper(), 11, label_color)
        # "GEO SCORE" subtitle
        self.c.setFillColorRGB(*LILAC)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawCentredString(cx, cy - 44, "GEO VISIBILITY SCORE")

    def _step_card(self, x, y, w, h, number, title, desc):
        """Service step card (used on page 3)."""
        self.c.setFillColorRGB(*LIGHT_BLUE_BG)
        self.c.roundRect(x, y, w, h, 6, fill=1, stroke=0)
        cx = x + w / 2
        # Number circle
        circle_y = y + h - 20
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.circle(cx, circle_y, 12, fill=1, stroke=0)
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 11)
        self.c.drawCentredString(cx, circle_y - 4, str(number))
        # Title
        title_y = y + h - 44
        title_lines = self._wrap(title, FONT_SEMIBOLD, 10, w - 12)
        for tl in title_lines:
            self.c.setFillColorRGB(*AQUAMARINE)
            self.c.setFont(FONT_SEMIBOLD, 10)
            self.c.drawCentredString(cx, title_y, tl)
            title_y -= 14
        # Desc
        desc_y = title_y - 4
        desc_lines = self._wrap(desc, FONT_LIGHT, 8, w - 12)
        for dl in desc_lines[:3]:
            self.c.setFillColorRGB(*STONE)
            self.c.setFont(FONT_LIGHT, 8)
            self.c.drawCentredString(cx, desc_y, dl)
            desc_y -= 11

    # ── Page 1: The Changing Search Landscape ─────────────────────────────────

    def _page_1(self):
        self._new_page(WHITE)
        self._draw_header()
        self._draw_footer()

        # Title band
        band_bottom = self._section_title_band(
            "The Changing Search Landscape", y_top=747, band_h=50)

        # ── SEO vs GEO two-column compare ──────────────────────────────────
        col_w = (CW - 6) / 2   # ~249
        col_x_l = MARGIN
        col_x_r = MARGIN + col_w + 6

        hdr_h = 26
        body_h = 120
        hdr_y = band_bottom - 10 - hdr_h   # top of header rect (bottom coord)
        body_y = hdr_y - body_h

        # Left column header: Deep Blue
        self._col_header(col_x_l, hdr_y, col_w, hdr_h,
                         "TRADITIONAL SEO", DEEP_BLUE, WHITE)
        # Left column body: Stone
        self._col_body(col_x_l, body_y, col_w, body_h, [
            "Google / Bing",
            "→  User clicks a link",
            "→  Visits your website",
            "→  You answer their question",
            "",
            "You control the click.",
        ], STONE, DEEP_BLUE, text_size=9.5)

        # Right column header: Midnight Green with Aquamarine text
        self._col_header(col_x_r, hdr_y, col_w, hdr_h,
                         "GEO  —  AI SEARCH", MIDNIGHT_GREEN, AQUAMARINE)
        # Right column body: Midnight Green
        self._col_body(col_x_r, body_y, col_w, body_h, [
            "ChatGPT / Perplexity / Gemini",
            "→  AI answers the question",
            "→  Cites sources it trusts",
            "→  User may never visit Google",
            "",
            "You must earn the citation.",
        ], MIDNIGHT_GREEN, STONE, text_size=9.5)

        # Thin Lilac divider between columns
        div_x = MARGIN + col_w + 2
        self.c.setFillColorRGB(*LILAC)
        self.c.rect(div_x, body_y, 2, hdr_h + body_h, fill=1, stroke=0)

        y_after_cols = body_y - 14

        # ── Stat badges ────────────────────────────────────────────────────
        badge_w = (CW - 14) / 2
        badge_h = 82
        badge_y = y_after_cols - badge_h

        self._stat_badge(MARGIN, badge_y, badge_w, badge_h,
                         "527%",
                         "growth in AI-referred web sessions (Jan–May 2025)")
        self._stat_badge(MARGIN + badge_w + 14, badge_y, badge_w, badge_h,
                         "50%",
                         "of all search traffic expected to shift to AI by 2028  (Gartner)")

        # Thin divider between badges
        self.c.setFillColorRGB(*LILAC)
        self.c.rect(MARGIN + badge_w + 6, badge_y + 10, 2, badge_h - 20,
                    fill=1, stroke=0)

        y_after_badges = badge_y - 12

        # ── "THE OPPORTUNITY" band ─────────────────────────────────────────
        opp_band_h = 28
        opp_band_y = y_after_badges - opp_band_h
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.rect(0, opp_band_y, PAGE_WIDTH, opp_band_h, fill=1, stroke=0)
        self._sb_centered(PAGE_WIDTH / 2, opp_band_y + 9,
                          "THE OPPORTUNITY", 11, AQUAMARINE)

        y_after_band = opp_band_y - 6

        # ── Three opportunity icon cards ────────────────────────────────────
        card_h = 145
        card_w = (CW - 2 * 6) / 3   # ~164 pt
        card_y = y_after_band - card_h

        cards = [
            {
                "icon": "+", "title": "New Leads Channel",
                "desc": "AI assistants now refer customers directly to businesses they trust — bypassing Google entirely.",
                "bg": AQUAMARINE, "icon_bg": DEEP_BLUE,
                "icon_fg": AQUAMARINE, "text": DEEP_BLUE, "border": None,
            },
            {
                "icon": "$", "title": "Optimize Now While Cost is Low",
                "desc": "Early adopters get established at a fraction of the cost. As demand grows, so do prices.",
                "bg": LIGHT_GREEN, "icon_bg": MIDNIGHT_GREEN,
                "icon_fg": AQUAMARINE, "text": DEEP_BLUE, "border": None,
            },
            {
                "icon": ">", "title": "Leapfrog Competitors",
                "desc": "Most local businesses haven't started. First to optimize owns the AI recommendation slot.",
                "bg": STONE, "icon_bg": AQUAMARINE,
                "icon_fg": DEEP_BLUE, "text": DEEP_BLUE,
                "border": MIDNIGHT_GREEN,
            },
        ]
        for i, card in enumerate(cards):
            cx = MARGIN + i * (card_w + 6)
            self._icon_card(
                cx, card_y, card_w, card_h,
                card["icon"], card["title"], card["desc"],
                card["bg"], card["icon_bg"], card["icon_fg"],
                text_color=card["text"],
                border_color=card["border"],
            )

        y_after_cards = card_y - 12

        # ── "Key insight" personalised callout ─────────────────────────────
        # Only show if there's room above the footer (y=65)
        callout_h = 48
        if y_after_cards - callout_h > 70:
            callout_y = y_after_cards - callout_h
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.roundRect(MARGIN, callout_y, CW, callout_h, 6,
                             fill=1, stroke=0)
            self.c.setFillColorRGB(*AQUAMARINE)
            self.c.rect(MARGIN, callout_y, 4, callout_h, fill=1, stroke=0)
            insight = (
                f"Right now, {self.d['client_name']} ranks well on Google — "
                "but doesn't appear when customers ask AI assistants the same question."
            )
            lines = self._wrap(insight, FONT_LIGHT, 9, CW - 24)
            line_h = 13
            n = min(len(lines), 3)
            # Start so the whole text block is vertically centred in the box
            ty = callout_y + callout_h / 2 + (n - 1) * line_h / 2
            for ln in lines[:n]:
                self.c.setFillColorRGB(*STONE)
                self.c.setFont(FONT_LIGHT, 9)
                self.c.drawString(MARGIN + 14, ty, ln)
                ty -= line_h

    # ── Page 2: Your GEO Snapshot + The Risk ──────────────────────────────────

    def _page_2(self):
        self._new_page(WHITE)
        self._draw_header()
        self._draw_footer()

        band_bottom = self._section_title_band(
            "Your GEO Snapshot", y_top=747, band_h=50)

        # ── Score arc gauge ────────────────────────────────────────────────
        gauge_radius = 58
        gauge_cy = band_bottom - 20 - gauge_radius
        gauge_cx = PAGE_WIDTH / 2
        self._score_arc(gauge_cx, gauge_cy, gauge_radius,
                        self.d["geo_score"], self.d["score_label"])

        y_after_gauge = gauge_cy - gauge_radius - 20

        # ── Two-column: What's Working / Needs Attention ──────────────────
        col_w2 = (CW - 12) / 2
        col_x_l = MARGIN
        col_x_r = MARGIN + col_w2 + 12

        # Column header labels
        hdr2_y = y_after_gauge - 22
        self._sb(col_x_l, hdr2_y, "✓  What's Working", 11, DEEP_BLUE)
        self._sb(col_x_r, hdr2_y, "⚠  Needs Attention", 11, AMBER)

        # Column content boxes
        items_per_col = max(len(self.d["working"]),
                            len(self.d["improvements"]))
        col_body2_h = max(90, items_per_col * 35 + 16)
        col_body2_y = hdr2_y - col_body2_h - 6

        self._bullet_col(
            self.d["working"], col_x_l, col_body2_y, col_w2,
            bullet_color=AQUAMARINE, text_color=DEEP_BLUE,
            bg=STONE, bg_h=col_body2_h, text_size=9,
        )
        self._bullet_col(
            self.d["improvements"], col_x_r, col_body2_y, col_w2,
            bullet_color=AMBER, text_color=DEEP_BLUE,
            bg=WARN_BG, bg_h=col_body2_h, text_size=9,
        )

        y_after_cols2 = col_body2_y - 12

        # ── On-site vs Off-site bar ────────────────────────────────────────
        bar_h = 58
        bar_y = y_after_cols2 - bar_h
        self.c.setFillColorRGB(*MIDNIGHT_GREEN)
        self.c.roundRect(MARGIN, bar_y, CW, bar_h, 6, fill=1, stroke=0)

        half = CW / 2
        # Left half: on-site
        onsite_cx = MARGIN + half / 2
        self._sb_centered(onsite_cx, bar_y + bar_h - 16,
                          "ON-SITE", 9, AQUAMARINE)
        self.c.setFillColorRGB(*STONE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawCentredString(onsite_cx, bar_y + bar_h - 30,
                                 "schema · llms.txt · FAQ · technical fixes")
        # Task count badge
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.circle(onsite_cx, bar_y + 14, 10, fill=1, stroke=0)
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 9)
        self.c.drawCentredString(onsite_cx, bar_y + 10,
                                 str(self.d["onsite_tasks"]))

        # Right half: off-site
        offsite_cx = MARGIN + half + half / 2
        self._sb_centered(offsite_cx, bar_y + bar_h - 16,
                          "OFF-SITE", 9, LIGHT_GREEN)
        self.c.setFillColorRGB(*STONE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawCentredString(offsite_cx, bar_y + bar_h - 30,
                                 "new platforms · citations · brand mentions")
        self.c.setFillColorRGB(*LIGHT_GREEN)
        self.c.circle(offsite_cx, bar_y + 14, 10, fill=1, stroke=0)
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 9)
        self.c.drawCentredString(offsite_cx, bar_y + 10,
                                 str(self.d["offsite_tasks"]))

        # Divider
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN + half - 1, bar_y + 8, 2, bar_h - 16,
                    fill=1, stroke=0)

        y_after_bar = bar_y - 10

        # ── Risk section ───────────────────────────────────────────────────
        risk_hdr_h = 28
        risk_hdr_y = y_after_bar - risk_hdr_h
        # Amber header band
        self.c.setFillColorRGB(*AMBER)
        self.c.rect(0, risk_hdr_y, PAGE_WIDTH, risk_hdr_h, fill=1, stroke=0)
        self._sb_centered_with_emoji(
            PAGE_WIDTH / 2, risk_hdr_y + 9,
            "\U0001f680",
            f"Position {self.d['client_name']} for Growth",
            10, DEEP_BLUE,
        )

        # Expand body to fill remaining space above the footer line (y=42)
        footer_clearance = 55
        risk_body_h = max(110, risk_hdr_y - footer_clearance)
        risk_body_y = risk_hdr_y - risk_body_h
        # WARN_BG body box
        self.c.setFillColorRGB(*WARN_BG)
        self.c.roundRect(MARGIN, risk_body_y, CW, risk_body_h, 5,
                         fill=1, stroke=0)
        # Amber left border
        self.c.setFillColorRGB(*AMBER)
        self.c.rect(MARGIN, risk_body_y, 4, risk_body_h, fill=1, stroke=0)

        # Each line is a list of (text, style, color_override) segments.
        # Styles: 'normal' | 'bold' | 'italic'
        risk_lines = [
            [
                ("As competitors optimize, AI embeds them in responses\u00a0\u2014\u00a0", "normal", None),
                ("permanently", "italic", None),
                (".", "normal", None),
            ],
            [
                ("Catching up costs\u00a0", "normal", None),
                ("3\u20135\u00d7", "bold", AMBER),
                (" more and takes\u00a0", "normal", None),
                ("6+ months", "italic", None),
                (" once the field is crowded.", "normal", None),
            ],
            [
                ("First-mover advantage", "bold", None),
                (" compounds: early presence becomes a lasting\u00a0", "normal", None),
                ("citation signal", "italic", None),
                (".", "normal", None),
            ],
        ]

        # Space bullets evenly across the full body height
        n_lines = len(risk_lines)
        v_pad = 14
        usable_h = risk_body_h - 2 * v_pad
        slot_h = usable_h / n_lines

        for i, segments in enumerate(risk_lines):
            # Vertically centre each item in its slot (top slot = i=0)
            ty = risk_body_y + risk_body_h - v_pad - (i + 0.5) * slot_h

            self.c.setFillColorRGB(*AMBER)
            self.c.circle(MARGIN + 18, ty + 3, 4, fill=1, stroke=0)

            self._render_segments(MARGIN + 30, ty, segments, 8.5, DEEP_BLUE)

    # ── Page 3: Peakweb GEO Services + CTA ────────────────────────────────────

    def _page_3(self):
        self._new_page(bg=DEEP_BLUE)
        self._draw_header(dark_bg=True)
        self._draw_footer(text_color=AQUAMARINE, line_color=AQUAMARINE)

        # Title (no Stone band — dark page)
        title_y = 726
        self._sb(MARGIN, title_y, "Peakweb GEO Services", 22, AQUAMARINE)
        # Light green underline
        self.c.setFillColorRGB(*LIGHT_GREEN)
        self.c.rect(MARGIN, title_y - 8, 56, 3, fill=1, stroke=0)

        # ── Service step cards — Row 1 (3 cards) ──────────────────────────
        card_w = (CW - 2 * 8) / 3     # ~162 pt
        card_h = 115
        row1_y = title_y - 26 - card_h  # bottom of row 1 cards

        steps = [
            (1, "Audit",              "Full GEO visibility assessment across all AI platforms"),
            (2, "Prompt Analysis",    "Real queries your customers already use to find services like yours"),
            (3, "Competitor Analysis","See exactly who AI recommends instead of you — and why"),
            (4, "On-site Optimizations", "llms.txt · schema markup · robots.txt · FAQ & content fixes"),
            (5, "Off-site Recommendations", "New platform presence · revised listings · citation building"),
            (6, "GA4 Monitoring",     "Track AI-referred traffic and measure GEO impact month over month"),
        ]
        for i, (num, title, desc) in enumerate(steps[:3]):
            cx = MARGIN + i * (card_w + 8)
            self._step_card(cx, row1_y, card_w, card_h, num, title, desc)

        # ── Row 2 (3 cards) ────────────────────────────────────────────────
        row2_y = row1_y - 10 - card_h
        for i, (num, title, desc) in enumerate(steps[3:]):
            cx = MARGIN + i * (card_w + 8)
            self._step_card(cx, row2_y, card_w, card_h, num, title, desc)

        y_after_cards = row2_y - 14

        # ── Pricing line ───────────────────────────────────────────────────
        pricing_h = 48
        pricing_y = y_after_cards - pricing_h
        self.c.setFillColorRGB(*STONE)
        self.c.roundRect(MARGIN, pricing_y, CW, pricing_h, 5, fill=1, stroke=0)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, pricing_y, 4, pricing_h, fill=1, stroke=0)

        line1 = "Peakweb GEO Essentials  \u00b7  Audit  \u00b7  Technical fixes  \u00b7  Schema  \u00b7  AI config files  \u00b7  30-day monitoring"
        line2 = "Starting at $999"
        line_h = 14
        cx = MARGIN + CW / 2
        # Vertically centre the two-line block
        pty = pricing_y + pricing_h / 2 + line_h / 2
        self._text_centered(cx, pty, line1, 8.5, DEEP_BLUE)
        self._sb_centered(cx, pty - line_h, line2, 10, DEEP_BLUE)

        y_after_pricing = pricing_y - 12

        # ── CTA box ────────────────────────────────────────────────────────
        # Fill remaining space above footer
        cta_h = y_after_pricing - 65
        if cta_h < 80:
            cta_h = 80
        cta_y = y_after_pricing - cta_h

        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.roundRect(MARGIN, cta_y, CW, cta_h, 8, fill=1, stroke=0)

        # Stone-Blue logo in lower-right of CTA box (transparent PNG)
        if os.path.exists(LOGO_STONE_BLUE_PATH):
            chev_size = min(cta_h * 0.7, 90)
            chev_x = MARGIN + CW - chev_size - 8
            chev_y = cta_y + 6
            self.c.drawImage(LOGO_STONE_BLUE_PATH,
                             chev_x, chev_y,
                             width=chev_size, height=chev_size,
                             mask='auto')

        # CTA text — vertically centred
        vcenter = cta_y + cta_h / 2
        self._sb_centered(PAGE_WIDTH / 2, vcenter + 22,
                          "Ready to be found by AI?", 20, DEEP_BLUE)
        self._text_centered(PAGE_WIDTH / 2, vcenter + 2,
                            "Schedule a free 30-minute strategy call with Peakweb",
                            10, MIDNIGHT_GREEN)
        self._sb_centered(PAGE_WIDTH / 2, vcenter - 18,
                          "peakweb.io   ·   hello@peakweb.io",
                          11, MIDNIGHT_GREEN)


# ─── CLI entry point ──────────────────────────────────────────────────────────

def main():
    data = DEFAULT_DATA
    output = None

    if len(sys.argv) >= 2 and sys.argv[1] != '-':
        json_path = sys.argv[1]
        try:
            with open(json_path) as f:
                data = json.load(f)
            print(f"Loaded data from {json_path}")
        except FileNotFoundError:
            print(f"Error: {json_path} not found", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in {json_path}: {e}", file=sys.stderr)
            sys.exit(1)

    if len(sys.argv) >= 3:
        output = sys.argv[2]

    if output is None:
        slug = re.sub(r'[^A-Za-z0-9]', '',
                      data.get('client_name', 'Client'))
        output = f"PeakwebGEOSnapshot-{slug}.pdf"

    SlimDeckGenerator(data, output).generate()


if __name__ == '__main__':
    main()
