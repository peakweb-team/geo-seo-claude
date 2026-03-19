#!/usr/bin/env python3
"""
Branded GEO Visibility Audit PDF for Denver Sprinkler Services
Prepared by Peakweb – follows Peakweb Brand Guidelines v1.0
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import textwrap

# ─── BRAND COLORS ───
DEEP_BLUE = HexColor("#0A2C49")
AQUAMARINE = HexColor("#01EFA0")
LIGHT_GREEN = HexColor("#BCFF8A")
MIDNIGHT_GREEN = HexColor("#0A3E3C")
LILAC = HexColor("#9892B5")
STONE = HexColor("#FCF7E6")
WHITE = HexColor("#FFFFFF")
AMBER = HexColor("#F5A623")
LIGHT_BLUE_BG = HexColor("#1a4a6e")
MUTED_BLUE = HexColor("#94b8cc")
SOFT_RED_BG = HexColor("#FFF0F0")
SOFT_GREEN_BG = HexColor("#EFFFEF")
WARN_BG = HexColor("#FFF8E6")

# ─── FONT ───
pdfmetrics.registerFont(TTFont('Outfit', '/sessions/youthful-laughing-lamport/fonts/Outfit-Variable.ttf'))

# ─── LOGO PNGs (converted from SVG) ───
LOGO_LG = "/sessions/youthful-laughing-lamport/logo_large.png"
LOGO_SM = "/sessions/youthful-laughing-lamport/logo_small.png"

# ─── OUTPUT ───
OUTPUT = "/sessions/youthful-laughing-lamport/mnt/Peakweb/Sales/Denver Sprinkler Services/geo-audit/PeakwebGEOProposal-DenverSprinklerServices.pdf"

PW, PH = letter
M = 54
CW = PW - 2 * M


class PDF:
    def __init__(self):
        self.c = canvas.Canvas(OUTPUT, pagesize=letter)
        self.c.setTitle("GEO Visibility Audit - Denver Sprinkler & Landscape")
        self.c.setAuthor("Peakweb")
        self.pn = 0
        self.y = PH - M
        self._cover_done = False

    # ── LOGO (PNG image) ──
    def logo_img(self, x, y, width=120):
        """Draw PNG logo at position. y is bottom of image."""
        try:
            self.c.drawImage(LOGO_LG, x, y, width=width, preserveAspectRatio=True, mask='auto')
        except:
            # Fallback text
            self.c.setFillColor(AQUAMARINE)
            self.c.setFont('Outfit', 16)
            self.c.drawString(x, y + 4, "Peakweb")

    def logo_img_sm(self, x, y, width=80, height=None):
        """Small logo for header bar with explicit dimensions."""
        if height is None:
            height = width / 5  # 5:1 aspect ratio
        try:
            self.c.drawImage(LOGO_SM, x, y, width=width, height=height, mask='auto')
        except:
            self.c.setFillColor(AQUAMARINE)
            self.c.setFont('Outfit', 12)
            self.c.drawString(x, y + 2, "Peakweb")

    def w_icon(self, x, y, size=200):
        """Draw the actual Peakweb W icon mark extracted from the brand SVG.
        x, y = bottom-left of bounding box. size = desired width."""
        # Original SVG coordinates for the 3 parallelograms (from PeakWeb-Green-RGB.svg)
        # Bounding box in SVG: x 1033.79..1296.92, y 476.84..686.38
        # SVG y-axis is inverted vs PDF, so we flip vertically
        orig_w = 263.13
        orig_h = 209.54
        scale = size / orig_w
        sh = orig_h * scale  # scaled height

        # Three shapes as absolute SVG coords: [(x,y), ...]
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
        self.c.setFillColor(AQUAMARINE)
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

    def w_icon_staggered(self, start_x, start_y, shape_h=320, x_gap=30, y_drop=80):
        """Draw three parallelograms in a staggered diagonal cascade like the
        brand guidelines back page.  Each shape is a copy of the tallest W
        parallelogram, positioned so they cascade down-right with the last
        shape bleeding off the right edge of the page.
        start_x, start_y = top-left of the first (leftmost) shape.
        shape_h = height of each parallelogram.
        x_gap = horizontal gap between shapes.
        y_drop = vertical drop between successive shapes.
        """
        # The tallest parallelogram from the SVG, normalised to a unit shape
        # SVG coords: (1296.92,520.02) (1197.34,686.38) (1171.29,643.13) (1270.92,476.84)
        # Width ≈ 125.63, height ≈ 209.54
        svg_w = 125.63
        svg_h = 209.54
        scale = shape_h / svg_h
        sw = svg_w * scale  # scaled width of one shape

        # Unit shape relative to its own bounding box (0,0 = top-left in SVG space)
        # Normalised from the tallest parallelogram
        unit = [
            (125.63,  43.18),  # top-right
            ( 26.05, 209.54),  # bottom-right
            (  0.00, 166.29),  # bottom-left
            ( 99.63,   0.00),  # top-left
        ]

        self.c.saveState()
        self.c.setFillColor(AQUAMARINE)
        for i in range(3):
            ox = start_x + i * (sw + x_gap)
            oy = start_y - i * y_drop  # drop down each time
            p = self.c.beginPath()
            for j, (ux, uy) in enumerate(unit):
                px = ox + ux * scale
                py = oy - uy * scale  # flip y for PDF
                if j == 0:
                    p.moveTo(px, py)
                else:
                    p.lineTo(px, py)
            p.close()
            self.c.drawPath(p, fill=1, stroke=0)
        self.c.restoreState()

    def accent(self, x, y, w, h=3):
        self.c.setFillColor(AQUAMARINE)
        self.c.rect(x, y, w, h, fill=1, stroke=0)

    # ── SEMI-BOLD TEXT via fill+stroke rendering ──
    def _semibold_text(self, x, y, text, font_size, color=DEEP_BLUE):
        """Simulate semi-bold by rendering text with fill + thin stroke."""
        self.c.saveState()
        self.c.setFillColor(color)
        self.c.setStrokeColor(color)
        self.c.setLineWidth(font_size * 0.028)
        self.c.setFont('Outfit', font_size)
        self.c._textRenderMode = 2  # fill + stroke
        self.c.drawString(x, y, text)
        self.c._textRenderMode = 0
        self.c.restoreState()

    def _semibold_centered(self, x, y, text, font_size, color=DEEP_BLUE):
        self.c.saveState()
        self.c.setFillColor(color)
        self.c.setStrokeColor(color)
        self.c.setLineWidth(font_size * 0.028)
        self.c.setFont('Outfit', font_size)
        self.c._textRenderMode = 2
        self.c.drawCentredString(x, y, text)
        self.c._textRenderMode = 0
        self.c.restoreState()

    # ── PAGE MANAGEMENT ──
    def page(self):
        if self._cover_done or self.pn > 0:
            self.c.showPage()
        self._cover_done = False
        self.pn += 1
        # Header bar
        hdr_h = 42
        self.c.setFillColor(DEEP_BLUE)
        self.c.rect(0, PH - hdr_h, PW, hdr_h, fill=1, stroke=0)
        # Logo image – explicit size, vertically centred in bar
        logo_w = 82
        logo_h = 16
        logo_y = PH - hdr_h + (hdr_h - logo_h) / 2
        self.logo_img_sm(M, logo_y, width=logo_w, height=logo_h)
        self.accent(0, PH - hdr_h - 3, PW, 3)
        # Footer
        self.accent(M, 42, CW, 1)
        self.c.setFillColor(DEEP_BLUE)
        self.c.setFont('Outfit', 8)
        self.c.drawString(M, 28, "Peakweb  |  peakweb.io")
        self.c.drawRightString(PW - M, 28, f"Page {self.pn}")
        self.y = PH - M - 55

    def need(self, h):
        if self.y - h < 65:
            self.page()

    # ── TEXT PRIMITIVES ──
    def h1(self, text):
        self.need(50)
        self.y -= 18
        self._semibold_text(M, self.y, text, 22)
        self.y -= 9
        self.accent(M, self.y, 60, 3)
        self.y -= 18

    def h2(self, text, color=DEEP_BLUE):
        self.need(36)
        self.y -= 14
        self._semibold_text(M, self.y, text, 14, color)
        self.y -= 18

    def h3(self, text, color=MIDNIGHT_GREEN):
        self.need(28)
        self.y -= 10
        self._semibold_text(M, self.y, text, 11, color)
        self.y -= 14

    def body(self, text, indent=0, size=10, color=DEEP_BLUE):
        self.c.setFillColor(color)
        self.c.setFont('Outfit', size)
        cpl = int((CW - indent) / (size * 0.475))
        lh = size + 4
        for para in text.split('\n'):
            if not para.strip():
                self.y -= lh * 0.5
                continue
            for ln in textwrap.wrap(para, width=cpl):
                self.need(lh + 8)
                self.c.drawString(M + indent, self.y, ln)
                self.y -= lh

    def bullet(self, text, indent=15, size=9.5):
        self.need(18)
        self.c.setFillColor(AQUAMARINE)
        self.c.setFont('Outfit', size)
        self.c.drawString(M + indent, self.y, "\u2022")
        self.c.setFillColor(DEEP_BLUE)
        cpl = int((CW - indent - 12) / (size * 0.475))
        lh = size + 4
        for ln in textwrap.wrap(text, width=cpl):
            self.c.drawString(M + indent + 12, self.y, ln)
            self.y -= lh

    def gap(self, h=8):
        self.y -= h

    def callout(self, text, bg=STONE, border=AQUAMARINE, size=9.5):
        """Callout box with text vertically centred."""
        self.c.setFont('Outfit', size)
        cpl = int((CW - 30) / (size * 0.475))
        lines = textwrap.wrap(text, width=cpl)
        lh = size + 4
        text_block_h = len(lines) * lh
        padding = 12
        bh = text_block_h + padding * 2
        if bh < 36:
            bh = 36
        self.need(bh + 6)
        # Box background
        box_bottom = self.y - bh + 8
        self.c.setFillColor(bg)
        self.c.roundRect(M, box_bottom, CW, bh, 4, fill=1, stroke=0)
        # Left accent border
        self.c.setFillColor(border)
        self.c.rect(M, box_bottom, 4, bh, fill=1, stroke=0)
        # Vertically centred text (accounting for ascender/descender)
        box_centre_y = box_bottom + bh / 2
        baseline_span = (len(lines) - 1) * lh
        text_start_y = box_centre_y + baseline_span / 2 - size * 0.2
        self.c.setFillColor(DEEP_BLUE)
        self.c.setFont('Outfit', size)
        ty = text_start_y
        for ln in lines:
            self.c.drawString(M + 16, ty, ln)
            ty -= lh
        self.y -= bh + 4

    def numbered(self, num, title, desc):
        self.need(40)
        r = 11
        cx = M + r
        cy = self.y
        self.c.setFillColor(AQUAMARINE)
        self.c.circle(cx, cy, r, fill=1, stroke=0)
        self.c.setFillColor(DEEP_BLUE)
        self.c.setFont('Outfit', 10)
        self.c.drawCentredString(cx, cy - 4, str(num))
        self._semibold_text(M + 28, self.y - 2, title, 11)
        self.y -= 15
        if desc:
            self.c.setFont('Outfit', 9)
            cpl = int((CW - 28) / (9 * 0.475))
            self.c.setFillColor(DEEP_BLUE)
            for ln in textwrap.wrap(desc, width=cpl):
                self.c.drawString(M + 28, self.y, ln)
                self.y -= 12
        self.y -= 4

    def score_bar(self, score, mx=100):
        self.need(55)
        gw = CW * 0.65
        gh = 22
        gx = M
        gy = self.y - 6
        self.c.setFillColor(HexColor("#E8ECF0"))
        self.c.roundRect(gx, gy, gw, gh, 11, fill=1, stroke=0)
        fill_w = gw * (score / mx)
        col = AMBER if score < 60 else AQUAMARINE
        self.c.setFillColor(col)
        self.c.roundRect(gx, gy, fill_w, gh, 11, fill=1, stroke=0)
        self.c.setFillColor(DEEP_BLUE)
        self.c.setFont('Outfit', 28)
        self.c.drawString(gx + gw + 14, gy - 4, str(score))
        self.c.setFont('Outfit', 14)
        self.c.drawString(gx + gw + 50, gy, f"/ {mx}")
        self.y -= 42

    def stats_row(self, items):
        self.need(55)
        w = CW / len(items)
        for i, (val, lab) in enumerate(items):
            cx = M + i * w + w / 2
            self._semibold_text(cx - self.c.stringWidth(val, 'Outfit', 24) / 2, self.y, val, 24, AQUAMARINE)
            self.c.setFillColor(DEEP_BLUE)
            self.c.setFont('Outfit', 8.5)
            self.c.drawCentredString(cx, self.y - 16, lab)
        self.y -= 42

    def option_card(self, title, desc):
        self.c.setFont('Outfit', 9)
        cpl = int((CW - 28) / (9 * 0.475))
        lines = textwrap.wrap(desc, width=cpl)
        ch = 18 + len(lines) * 12 + 10
        self.need(ch + 6)
        self.c.setFillColor(STONE)
        self.c.roundRect(M, self.y - ch + 8, CW, ch, 4, fill=1, stroke=0)
        self.c.setFillColor(AQUAMARINE)
        self.c.rect(M, self.y - ch + 8, 4, ch, fill=1, stroke=0)
        self._semibold_text(M + 14, self.y, title, 11)
        self.c.setFillColor(DEEP_BLUE)
        self.c.setFont('Outfit', 9)
        ty = self.y - 14
        for ln in lines:
            self.c.drawString(M + 14, ty, ln)
            ty -= 12
        self.y -= ch + 4

    def table(self, hdrs, rows):
        ncol = len(hdrs)
        rh = 24
        total_h = (1 + len(rows)) * rh
        self.need(total_h + 10)
        cw = CW / ncol
        x0 = M
        self.c.setFillColor(DEEP_BLUE)
        self.c.rect(x0, self.y - rh, CW, rh, fill=1, stroke=0)
        self.c.setFillColor(WHITE)
        self.c.setFont('Outfit', 9)
        for i, h in enumerate(hdrs):
            self.c.drawString(x0 + i * cw + 8, self.y - rh + 8, h)
        self.y -= rh
        for r, row in enumerate(rows):
            bg = STONE if r % 2 == 0 else WHITE
            self.c.setFillColor(bg)
            self.c.rect(x0, self.y - rh, CW, rh, fill=1, stroke=0)
            self.c.setFillColor(DEEP_BLUE)
            self.c.setFont('Outfit', 9)
            for i, cell in enumerate(row):
                self.c.drawString(x0 + i * cw + 8, self.y - rh + 8, cell)
            self.y -= rh
        self.y -= 8

    def timeline(self, week, title, hours, items, score):
        self.need(28 + len(items) * 14)
        bw, bh = 54, 20
        self.c.setFillColor(DEEP_BLUE)
        self.c.roundRect(M, self.y - bh + 6, bw, bh, 3, fill=1, stroke=0)
        self.c.setFillColor(AQUAMARINE)
        self.c.setFont('Outfit', 9)
        self.c.drawCentredString(M + bw / 2, self.y - 7, week)
        self._semibold_text(M + bw + 8, self.y - 4, title, 11)
        self.c.setFillColor(LILAC)
        self.c.setFont('Outfit', 8)
        self.c.drawString(M + bw + 8, self.y - 16, f"Led by: {hours}  |  Expected Score: {score}")
        self.y -= 28
        for item in items:
            self.bullet(item, indent=18, size=9)
        self.gap(4)

    # ═══ PAGES ═══

    def cover(self):
        self.pn += 1
        c = self.c
        c.setFillColor(DEEP_BLUE)
        c.rect(0, 0, PW, PH, fill=1, stroke=0)
        self.accent(0, PH - 3, PW, 3)
        # Logo (PNG)
        self.logo_img(M, PH - 85, width=160)
        # Title
        self._semibold_text(M, PH - 200, "Website Visibility", 38, WHITE)
        self._semibold_text(M, PH - 248, "Audit", 38, WHITE)
        self.accent(M, PH - 266, 80, 4)
        c.setFillColor(AQUAMARINE)
        c.setFont('Outfit', 16)
        c.drawString(M, PH - 296, "GEO Analysis & Implementation Proposal")
        # Client info box
        iy = PH - 370
        bh = 110
        c.setFillColor(LIGHT_BLUE_BG)
        c.roundRect(M, iy - bh, CW, bh, 6, fill=1, stroke=0)
        c.setFillColor(AQUAMARINE)
        c.rect(M, iy - bh, 4, bh, fill=1, stroke=0)
        c.setFillColor(MUTED_BLUE)
        c.setFont('Outfit', 8)
        c.drawString(M + 18, iy - 18, "PREPARED FOR")
        c.drawString(M + CW / 2 + 10, iy - 18, "WEBSITE")
        c.drawString(M + 18, iy - 72, "DATE")
        c.setFillColor(WHITE)
        c.setFont('Outfit', 13)
        c.drawString(M + 18, iy - 35, "Ramon Robles, Owner")
        c.setFont('Outfit', 11)
        c.drawString(M + 18, iy - 52, "Denver Sprinkler & Landscape")
        c.drawString(M + CW / 2 + 10, iy - 35, "denversprinklerservices.com")
        c.drawString(M + 18, iy - 88, "March 17, 2026")
        # W icon mark shifted right so it partially bleeds off the page edge,
        # matching the brand guidelines back page treatment.
        self.w_icon(PW - 235, 50, size=260)
        c.setFillColor(AQUAMARINE)
        c.setFont('Outfit', 9)
        c.drawString(M, 30, "peakweb.io")
        c.setFillColor(MUTED_BLUE)
        c.drawRightString(PW - M, 30, "Confidential")
        # Mark cover as done (no extra showPage; page() will handle it)
        self._cover_done = True

    def p_exec_summary(self):
        self.page()
        self.h1("Executive Summary")
        self.body(
            "When someone asks ChatGPT, Google AI, or Perplexity a question like "
            "\"Who does sprinkler repair in Denver?\" your business is rarely mentioned "
            "\u2013 even though you have 25 years of experience and an A+ BBB rating."
        )
        self.gap(6)
        self.callout(
            "This audit identifies the specific gaps holding you back and outlines what "
            "needs to change. Every issue has a proven solution \u2013 Peakweb can guide "
            "implementation to ensure it\u2019s done right the first time."
        )
        self.gap(4)
        self.h2("The New Reality: AI Search")
        self.body(
            "The way people find local businesses is changing rapidly. Traditional Google Search "
            "still matters \u2013 customers search and get a list of links. But AI Search is growing "
            "fast: customers ask ChatGPT or Perplexity a question and get 2\u20133 direct recommendations. "
            "Those recommended businesses get the calls."
        )
        self.gap(4)
        self.body(
            "Right now, AI systems answering questions about Denver landscaping or sprinkler "
            "services rarely mention your business. Not because you're not qualified, but "
            "because your website doesn't communicate effectively with AI systems yet."
        )
        self.gap(6)
        self.h2("What Is GEO?")
        self.body("GEO stands for Generative Engine Optimization. Think of it this way:")
        self.gap(3)
        self.bullet("SEO (Search Engine Optimization) = Making your website show up in Google search results")
        self.bullet("GEO (Generative Engine Optimization) = Making your website get recommended by ChatGPT, Claude, Google AI, and Perplexity")
        self.gap(4)
        self.body(
            "Studies show that 30\u2013115% more people discover businesses optimized for AI search "
            "compared to those that aren't. Your competitors who figure this out first will "
            "capture those leads. It's like having a Yellow Pages ad in 1990 vs. not having one."
        )
        self.gap(6)
        self.h2("Why GEO Matters Now")
        self.body(
            "You need both SEO and GEO. Traditional SEO gets you found in Google. GEO gets you "
            "recommended by AI. Most SEO services don't include GEO yet \u2013 it's too new. "
            "That's why early movers have a huge advantage right now."
        )

    def p_score(self):
        self.page()
        self.h1("Your Current Score")
        self.gap(4)
        self.score_bar(53)
        self.callout(
            "FAIR \u2013 Your website is functional but not optimized for AI systems. "
            "AI search engines can access your site but rarely cite or recommend it. "
            "You're not invisible, but you're not competing effectively.",
            bg=WARN_BG, border=AMBER
        )
        self.gap(6)
        self.h2("What\u2019s Working Well")
        for item in [
            "Your website is accessible \u2013 AI systems can read your content (many businesses block them accidentally)",
            "Strong reputation \u2013 BBB A+ rating, Trees.com #6 in Denver, 20+ testimonials",
            "Complete contact info \u2013 address, phone, hours, service area clearly listed",
            "Professional website \u2013 clean design, mobile-friendly, secure (HTTPS)",
            "Real experience \u2013 25+ years in the industry, established business",
        ]:
            self.bullet(item)
        self.gap(6)
        self.callout("The foundation is solid. Peakweb\u2019s job is to make AI systems notice it.")
        self.gap(8)
        self.h2("What This Means For Your Business")
        self.body(
            "When AI systems answer questions about Denver landscaping or sprinkler services, "
            "they rarely mention your business. This means:"
        )
        self.gap(3)
        self.bullet("Lost phone calls from potential customers who never hear your name")
        self.bullet("Competitors who optimize for AI get recommended instead of you")
        self.bullet("Your 25 years of experience and A+ rating are invisible to these systems")

    def p_issues1(self):
        self.page()
        self.h1("The 6 Key Issues Identified")
        self.gap(3)

        self.h2("1. AI Systems Don\u2019t Know Who You Are")
        self.body(
            "Your business has no \"identity\" in AI databases \u2013 no Wikipedia page, no LinkedIn "
            "company page, minimal online presence beyond your website. When someone asks ChatGPT "
            "\"Who does sprinkler repair in Denver?\" the AI doesn't recognize you as a legitimate "
            "business entity."
        )
        self.gap(3)
        self.callout(
            "Impact: Lost leads from the 30\u201340% of people now using AI to research local services.",
            bg=WARN_BG, border=AMBER
        )
        self.gap(6)

        self.h2("2. Your Website Has No Dates On Anything")
        self.body(
            "Not a single page shows when it was published or last updated. Your testimonials have "
            "no dates. AI systems assume undated content is stale and won't cite it. When someone "
            "asks about 2026 sprinkler prices, your pages are skipped as potentially outdated."
        )
        self.gap(3)
        self.body(
            "Real example: Customer asks \"What does sprinkler winterization cost in Denver in 2026?\" "
            "AI cites your competitor's blog from 2025 with dates, and ignores your page with no date.",
            size=9, color=MIDNIGHT_GREEN
        )
        self.gap(6)

        self.h2("3. 20+ Testimonials Are Hidden From AI")
        self.body(
            "You have 20+ customer testimonials but they're not marked up in a way AI systems "
            "can understand. No star ratings show up in Google results. AI systems can't verify "
            "your reputation because they can't \"see\" your reviews."
        )
        self.gap(3)
        self.callout(
            "This is a solvable problem. With the right technical implementation, your "
            "reviews can start showing star ratings in search results immediately."
        )

    def p_issues2(self):
        self.page()

        self.h2("4. Content Is Generic Marketing Copy")
        self.body(
            "Your service pages use generic phrases like \"professional sprinkler repair services\" but "
            "lack the specific, verifiable data that AI systems look for when deciding which "
            "businesses to recommend. AI systems cite websites with concrete data \u2013 not marketing "
            "language. Your 25 years of experience and deep Denver expertise exist but aren\u2019t "
            "documented in a format AI can parse and verify."
        )
        self.gap(3)
        self.callout(
            "Peakweb\u2019s content strategy transforms your real-world expertise into the data-rich, "
            "AI-friendly format that earns citations and recommendations."
        )
        self.gap(6)

        self.h2("5. Missing Technical Files AI Systems Look For")
        self.body(
            "Your site is missing critical configuration files that AI systems rely on to "
            "understand and index your business. Without them, it\u2019s like having a store "
            "with no sign out front and the lights off. AI systems have to guess what "
            "you do \u2013 many give up and cite competitors instead."
        )
        self.gap(2)
        self.callout(
            "These files require precise formatting and placement. Misconfigured files "
            "can actually hurt visibility. Peakweb handles this as part of every GEO engagement."
        )
        self.gap(6)

        self.h2("6. Business Age Inconsistency Hurts Trust")
        self.body(
            "Your website says \"25+ years in business\" but BBB shows the business started in "
            "2011 (14 years ago). AI systems fact-check claims. When they find conflicting "
            "information, they either skip citing you entirely, cite competitors with consistent "
            "information, or mention the discrepancy (hurting credibility)."
        )
        self.gap(3)
        self.callout(
            "Resolving this requires a coordinated update across your website, directory listings, "
            "and business profiles. Peakweb ensures consistency across every platform AI checks."
        )
        self.gap(8)

        self.h2("What Happens If You Do Nothing?")
        self.gap(2)
        self.h3("Short-term (Next 6 months):")
        self.bullet("Competitors who optimize for AI will get recommended more often")
        self.bullet("You\u2019ll continue missing leads from the growing AI search audience (30\u201340% of searches)")
        self.bullet("The gap between you and optimized competitors widens")
        self.gap(3)
        self.h3("Long-term (1\u20132 years):")
        self.bullet("AI search becomes the dominant way people find local services")
        self.bullet("Businesses without AI visibility become increasingly invisible")
        self.bullet("Playing catch-up gets harder as competitors build content libraries and authority")

    def p_quick_wins(self):
        self.page()
        self.h1("The Opportunity")
        self.body(
            "Our audit identified issues across four key areas that are preventing AI systems "
            "from recommending your business. The good news: every one of them is fixable, and "
            "the projected impact is significant."
        )
        self.gap(6)
        self.h2("Your Score Improvement Potential")
        self.gap(4)
        self.stats_row([
            ("53", "Current Score"),
            ("\u2192", ""),
            ("79+", "Projected Score"),
        ])
        self.gap(4)
        self.h3("Areas Requiring Attention:")
        self.gap(2)
        self.numbered(1, "Technical Configuration",
            "Your site is missing key files and data formats that AI systems "
            "rely on to discover, understand, and recommend local businesses.")
        self.numbered(2, "Content & Authority Signals",
            "AI systems need verifiable data, not marketing copy. Your 25 years of "
            "experience isn\u2019t documented in a way AI can parse and cite.")
        self.numbered(3, "Trust & Consistency",
            "Conflicting information across your online presence causes AI systems "
            "to question your credibility and skip you in favor of competitors.")
        self.numbered(4, "Freshness & Relevance",
            "Without timestamps, update signals, and current content, AI treats "
            "your site as potentially outdated and deprioritizes it.")
        self.gap(6)
        self.callout(
            "Each of these areas involves multiple coordinated changes that must be implemented "
            "correctly and in the right sequence. Peakweb\u2019s GEO methodology addresses all four "
            "areas in a structured 30-day engagement \u2013 validated across every major AI platform."
        )

    def p_plan(self):
        self.page()
        self.h1("How Peakweb Gets You There")
        self.gap(3)
        self.body(
            "Our GEO methodology follows a proven 4-week rollout, sequenced so each phase "
            "builds on the last. You stay focused on running your business while we handle "
            "the technical implementation and platform validation."
        )
        self.gap(4)
        self.timeline("Week 1", "Technical Foundation", "Peakweb-led", [
            "Deploy all critical AI configuration and discovery signals",
            "Resolve trust and consistency issues across your online presence",
        ], "70\u201375")
        self.gap(3)
        self.timeline("Week 2", "Authority & Identity", "Collaborative", [
            "Build your verified presence on key AI-indexed platforms",
            "You provide business content; we structure it for AI consumption",
        ], "78\u201382")
        self.gap(3)
        self.timeline("Week 3", "Content Depth", "Collaborative", [
            "Publish AI-optimized content that positions you as the Denver authority",
            "Enrich your site with the verifiable data AI systems cite",
        ], "82\u201386")
        self.gap(3)
        self.timeline("Week 4", "Validation & Launch", "Peakweb-led", [
            "QA across all major AI platforms (ChatGPT, Perplexity, Claude, Google AI)",
            "Deliver monitoring dashboard and ongoing content strategy",
        ], "85\u201390")

    def p_investment(self):
        self.page()
        self.h1("Working With Peakweb")
        self.gap(3)
        self.body(
            "GEO optimization involves specialized technical work \u2013 structured data formats, "
            "AI crawler protocols, and platform-specific configurations that change frequently. "
            "A general web developer can update your content, but the AI-specific implementation "
            "requires expertise in how each AI platform indexes and ranks local businesses."
        )
        self.gap(4)
        self.option_card(
            "GEO Essentials \u2013 Guided Implementation ($1,000)",
            "Peakweb handles all 7 priority technical fixes, deploys AI configuration files, "
            "implements structured data, and validates your site across all major AI platforms. "
            "You provide business content (photos, testimonials, project details); we handle the rest. "
            "Includes 30-day post-launch monitoring."
        )
        self.option_card(
            "GEO Growth \u2013 Full 30-Day Engagement ($2,000\u2013$3,000)",
            "Everything in Essentials plus: authority-building across AI-indexed platforms, "
            "AI-optimized content creation (guides, FAQs, case studies), video channel repair, "
            "and a 90-day monitoring dashboard. Best for maximum visibility in the shortest time."
        )
        self.option_card(
            "GEO Partner \u2013 Ongoing Optimization ($500/month)",
            "After initial implementation, Peakweb monitors your AI visibility monthly, "
            "publishes fresh content to maintain relevance signals, and adapts your strategy "
            "as AI platforms evolve. Ensures you stay ahead of competitors long-term."
        )
        self.gap(8)
        self.h2("Expected Return on Investment")
        self.gap(4)
        self.stats_row([
            ("7\u20138", "Additional Leads/Mo"),
            ("2\u20133", "New Customers/Mo"),
            ("$1K\u20136K", "Add'l Monthly Rev"),
            ("$12\u201372K", "Annual Impact"),
        ])
        self.gap(2)
        self.callout(
            "Break-even: Implementation pays for itself in the first month. Unlike one-time "
            "marketing, these improvements keep working 24/7 with compounding returns."
        )
        self.gap(6)
        self.h2("The Compounding Effect")
        self.gap(2)
        self.bullet("Month 1\u20133: Initial boost as AI systems discover updated content")
        self.bullet("Month 4\u20136: Momentum builds as you add more content (blog, videos)")
        self.bullet("Month 7\u201312: You become a recognized authority; AI systems cite you regularly")
        self.bullet("Year 2+: Competitors struggle to catch up; you're the established AI-visible brand")

    def p_comparison(self):
        self.page()
        self.h1("Traditional SEO vs. GEO")
        self.body(
            "You might be thinking: \"I already paid for SEO. Isn't this the same thing?\" "
            "The short answer is no. Here's how they compare:"
        )
        self.gap(6)
        self.table(
            ["Traditional SEO", "GEO (AI Optimization)"],
            [
                ["Goal: Rank in Google's 10 blue links", "Goal: Get mentioned by ChatGPT / AI"],
                ["Optimizes for keywords", "Optimizes for natural language questions"],
                ["Success = page 1 ranking", "Success = AI recommendation"],
                ["Works for Google search", "Works for ChatGPT, Perplexity, Google AI, Claude"],
                ["Established practice (20+ years)", "Emerging practice (critical now)"],
            ]
        )
        self.gap(4)
        self.callout(
            "You need BOTH. Traditional SEO gets you found in Google. GEO gets you recommended "
            "by AI. The catch: most SEO services don't include GEO yet. Early movers win."
        )
        self.gap(8)

        self.h2("Even If AI Search Stalls, You Still Win")
        self.body("Every optimization in this audit also improves your traditional Google SEO:")
        self.gap(3)
        self.bullet("Star ratings increase click-through rates in Google results")
        self.bullet("Fresh content with dates ranks better in Google search")
        self.bullet("Case studies with data build authority and attract backlinks")
        self.bullet("FAQ pages answer user questions and capture featured snippets")
        self.bullet("Complete structured data helps Google understand your business")
        self.gap(4)
        self.callout(
            "These are best practices regardless of AI. You literally can't lose."
        )

    def p_before_after(self):
        self.page()
        self.h1("What This Looks Like in Practice")
        self.gap(3)
        self.body("Here's what happens when a potential customer asks an AI assistant for help:")
        self.gap(8)

        # BEFORE
        lines_before = [
            'Customer: "Who should I call for sprinkler winterization in Denver?"',
            '',
            'AI Response: "Here are some well-reviewed options:',
            '  \u2013 GreenCo Irrigation (mentioned in multiple sources)',
            '  \u2013 Colorado Sprinkler Pros (4.8 stars, established since 2010)',
            '  \u2013 Mountain View Landscaping (EPA WaterSense partner)"',
            '',
            'Your business: Not mentioned.',
        ]
        bh = len(lines_before) * 12 + 30
        self.need(bh + 8)
        self.c.setFillColor(SOFT_RED_BG)
        self.c.roundRect(M, self.y - bh, CW, bh, 5, fill=1, stroke=0)
        self._semibold_text(M + 14, self.y - 16, "BEFORE Optimization", 11, HexColor("#CC4444"))
        self.c.setFillColor(DEEP_BLUE)
        self.c.setFont('Outfit', 9)
        ty = self.y - 32
        for ln in lines_before:
            self.c.drawString(M + 14, ty, ln)
            ty -= 12
        self.y -= bh + 10

        # AFTER
        lines_after = [
            'Customer: "Who should I call for sprinkler winterization in Denver?"',
            '',
            'AI Response: "Here are some well-reviewed options:',
            '  \u2013 Denver Sprinkler and Landscape (25+ years experience, BBB A+,',
            '    serving Denver since 2011. Winterization typically $85\u2013150)',
            '  \u2013 GreenCo Irrigation (mentioned in multiple sources)',
            '  \u2013 Colorado Sprinkler Pros (4.8 stars)"',
            '',
            'Your business: Mentioned FIRST with specific details and contact info.',
        ]
        bh = len(lines_after) * 12 + 30
        self.need(bh + 8)
        self.c.setFillColor(SOFT_GREEN_BG)
        self.c.roundRect(M, self.y - bh, CW, bh, 5, fill=1, stroke=0)
        self.c.setFillColor(AQUAMARINE)
        self.c.rect(M, self.y - bh, 4, bh, fill=1, stroke=0)
        self._semibold_text(M + 14, self.y - 16, "AFTER Optimization", 11, MIDNIGHT_GREEN)
        self.c.setFillColor(DEEP_BLUE)
        self.c.setFont('Outfit', 9)
        ty = self.y - 32
        for ln in lines_after:
            self.c.drawString(M + 14, ty, ln)
            ty -= 12
        self.y -= bh + 8

        self.callout(
            "Same customer, same question. One scenario: they never hear about you. "
            "The other: you're recommended first with supporting details. "
            "How many customers asked this question last month and never heard your name?"
        )

        self.gap(8)
        self.h2("Frequently Asked Questions")
        self.gap(3)
        self.h3("\"Is this really necessary? My business is doing fine.\"")
        self.body(
            "Your business IS doing fine \u2013 25 years of success proves that. But consider: "
            "in 2005, businesses said \"I don't need a website.\" In 2010, \"I don't need Google reviews.\" "
            "In 2015, \"I don't need social media.\" Those who adapted early dominated their markets. "
            "AI search is the next shift.",
            size=9.5
        )
        self.gap(4)
        self.h3("\"How long will these changes stay relevant?\"")
        self.body(
            "The technical foundation we build is permanent \u2013 it doesn\u2019t expire or need replacing. "
            "Content assets (guides, FAQs, case studies) appreciate over time and keep driving leads "
            "for years. That said, AI platforms evolve quickly, which is why ongoing monitoring matters. "
            "Peakweb\u2019s GEO Partner plan keeps you current as the landscape shifts.",
            size=9.5
        )

    def p_next_steps(self):
        self.page()
        self.h1("Next Steps")
        self.gap(3)
        steps = [
            ("Schedule a 30-Minute Strategy Call with Peakweb",
             "We\u2019ll walk through this audit together, answer your questions, and "
             "recommend the right engagement level for your goals and budget."),
            ("Choose Your Implementation Package",
             "GEO Essentials ($1,000) for priority technical fixes, GEO Growth "
             "($2,000\u2013$3,000) for the full 30-day roadmap, or GEO Partner ($500/mo) for ongoing optimization."),
            ("Gather Your Business Content",
             "While Peakweb handles the technical side, you\u2019ll want to have project photos, "
             "customer stories, and service details ready. We\u2019ll send you a simple content checklist."),
            ("Implementation Begins",
             "Peakweb deploys changes in the sequence outlined in our 30-day roadmap, "
             "with check-ins at each milestone so you always know what\u2019s happening."),
            ("Track Results Together",
             "We\u2019ll monitor your visibility across ChatGPT, Perplexity, Google AI, and Claude \u2013 "
             "and provide monthly reports showing your score improvement and lead impact."),
        ]
        for i, (t, d) in enumerate(steps, 1):
            self.numbered(i, t, d)

        self.gap(10)

        bh = 85
        self.need(bh + 10)
        self.c.setFillColor(DEEP_BLUE)
        self.c.roundRect(M, self.y - bh, CW, bh, 6, fill=1, stroke=0)
        self._semibold_centered(PW / 2, self.y - 22, "The Bottom Line", 16, AQUAMARINE)
        self.c.setFillColor(WHITE)
        self.c.setFont('Outfit', 10)
        self.c.drawCentredString(PW / 2, self.y - 42,
            "You\u2019ve built an excellent business over 25 years. The only thing holding")
        self.c.drawCentredString(PW / 2, self.y - 56,
            "you back is that AI systems don\u2019t know about it yet.")
        self.c.setFillColor(AQUAMARINE)
        self.c.setFont('Outfit', 10)
        self.c.drawCentredString(PW / 2, self.y - 74,
            "The businesses that dominate Denver sprinkler services in 2027\u20132030")
        self.y -= bh + 6

        self.gap(8)
        self.body(
            "Ready to get started? Reach out to Peakweb to schedule your strategy call. "
            "We\u2019ll map out the fastest path to getting your business recommended by AI \u2013 "
            "and make sure every dollar you invest delivers measurable returns."
        )

    def back_cover(self):
        self.c.showPage()
        self.pn += 1
        c = self.c
        c.setFillColor(DEEP_BLUE)
        c.rect(0, 0, PW, PH, fill=1, stroke=0)
        self.accent(0, PH - 6, PW, 6)
        # Logo (PNG, centred)
        logo_w = 180
        self.logo_img(PW / 2 - logo_w / 2, PH - 150, width=logo_w)
        self._semibold_centered(PW / 2, PH - 240, "Ready to Get Started?", 24, WHITE)
        self.accent(PW / 2 - 30, PH - 256, 60, 3)
        c.setFillColor(MUTED_BLUE)
        c.setFont('Outfit', 11)
        c.drawCentredString(PW / 2, PH - 290,
            "Schedule your free strategy call and we\u2019ll walk")
        c.drawCentredString(PW / 2, PH - 306,
            "through every finding in this audit together.")
        c.drawCentredString(PW / 2, PH - 336,
            "Your business deserves to be seen. Let\u2019s make it happen.")
        c.setFillColor(AQUAMARINE)
        c.setFont('Outfit', 14)
        c.drawCentredString(PW / 2, PH - 380, "peakweb.io")
        self.w_icon(PW / 2 - 80, 60, size=160)
        c.setFillColor(HexColor("#4a7a94"))
        c.setFont('Outfit', 7.5)
        c.drawCentredString(PW / 2, 32,
            "This report was prepared March 17, 2026, for Denver Sprinkler and Landscape Inc.")
        c.drawCentredString(PW / 2, 22,
            "Results and timelines are based on current AI search landscape. Individual results may vary.")

    def build(self):
        self.cover()
        self.p_exec_summary()
        self.p_score()
        self.p_issues1()
        self.p_issues2()
        self.p_quick_wins()
        self.p_plan()
        self.p_investment()
        self.p_comparison()
        self.p_before_after()
        self.p_next_steps()
        self.back_cover()
        self.c.save()
        print(f"PDF saved: {OUTPUT}")
        print(f"Total pages: {self.pn}")


if __name__ == '__main__':
    PDF().build()
