#!/usr/bin/env python3
"""
Peakweb Statement of Work Generator

Generates an 8-page branded SOW PDF from JSON input using ReportLab.
Follows Peakweb brand guidelines.

Usage:
    python3 generate_sow.py                     # Uses sample data for testing
    python3 generate_sow.py data.json           # Uses JSON file
    python3 generate_sow.py data.json out.pdf   # Custom output filename

JSON input structure documented in skills/geo-sow/SKILL.md
"""

import json
import os
import sys
import textwrap
from datetime import datetime, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
FONTS_DIR = os.path.join(PROJECT_DIR, "assets/fonts")
LOGO_PATH = os.path.join(PROJECT_DIR, "assets/PeakWeb-Green-RGB.png")

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792 points
MARGIN = 54  # 0.75 inch

# Brand Colors (RGB tuples 0-1)
DEEP_BLUE = (10/255, 44/255, 73/255)         # #0A2C49
AQUAMARINE = (1/255, 239/255, 160/255)       # #01EFA0
LIGHT_GREEN = (188/255, 255/255, 138/255)    # #BCFF8A
MIDNIGHT_GREEN = (10/255, 62/255, 60/255)    # #0A3E3C
STONE = (252/255, 247/255, 230/255)          # #FCF7E6
WARNING_ORANGE = (255/255, 165/255, 0/255)   # #FFA500
WARNING_BG = (255/255, 248/255, 230/255)     # Light orange background
WHITE = (1, 1, 1)
LIGHT_GRAY = (0.95, 0.95, 0.95)
TABLE_HEADER_BG = (0.12, 0.17, 0.29)         # Darker blue for table headers
TABLE_ALT_BG = (0.97, 0.97, 0.98)            # Alternating row background

# Font name constants - use Helvetica fallbacks
FONT_LIGHT = 'Helvetica'
FONT_REGULAR = 'Helvetica'
FONT_SEMIBOLD = 'Helvetica-Bold'


def register_fonts():
    """Try to register Outfit fonts, fall back to Helvetica if not available."""
    global FONT_LIGHT, FONT_REGULAR, FONT_SEMIBOLD

    font_files = [
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

    if fonts_loaded >= 3:
        FONT_LIGHT = 'Outfit-Light'
        FONT_REGULAR = 'Outfit-Regular'
        FONT_SEMIBOLD = 'Outfit-SemiBold'
        print("Using Outfit fonts")
    else:
        print("Using Helvetica fallback fonts")


class SOWGenerator:
    def __init__(self, data, output_path):
        self.data = data
        self.output_path = output_path
        self.c = None
        self.page_num = 0
        self.y = PAGE_HEIGHT - MARGIN

    def generate(self):
        """Generate the complete SOW document."""
        register_fonts()

        self.c = canvas.Canvas(self.output_path, pagesize=letter)

        self._page_1_cover()
        self._page_2_overview()
        self._page_3_scope()
        self._page_4_deliverables()
        self._page_5_resources()
        self._page_6_pricing()
        self._page_7_terms()
        self._page_8_signatures()

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

        self.c.setFillColorRGB(*bg_color)
        self.c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

    def _draw_header(self, show_logo=True):
        """Draw page header with logo."""
        hdr_h = 42
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.rect(0, PAGE_HEIGHT - hdr_h, PAGE_WIDTH, hdr_h, fill=1, stroke=0)

        if show_logo and os.path.exists(LOGO_PATH):
            logo_w = 100
            logo_h = logo_w * (4500 / 8000)
            logo_y = PAGE_HEIGHT - hdr_h + (hdr_h - logo_h) / 2
            self.c.drawImage(LOGO_PATH, MARGIN, logo_y,
                           width=logo_w, height=logo_h, mask='auto')

        # Green accent line below header
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(0, PAGE_HEIGHT - hdr_h - 3, PAGE_WIDTH, 3, fill=1, stroke=0)

    def _draw_footer(self, confidential=True):
        """Draw page footer."""
        CW = PAGE_WIDTH - 2 * MARGIN

        # Accent line above footer
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, 42, CW, 1, fill=1, stroke=0)

        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(MARGIN, 28, "Peakweb Inc.  |  peakweb.io")

        if confidential:
            self.c.drawCentredString(PAGE_WIDTH / 2, 28, "Confidential")

        self.c.drawRightString(PAGE_WIDTH - MARGIN, 28, f"Page {self.page_num}")

    def _start_content_page(self):
        """Start a new content page with header and footer."""
        self._new_page(bg_color=WHITE)
        self._draw_header()
        self._draw_footer()
        self.y = PAGE_HEIGHT - MARGIN - 55

    def _need(self, h):
        """Check if we need a new page for content of height h."""
        if self.y - h < 65:
            self._start_content_page()

    def _draw_text(self, x, y, text, font, size, color):
        """Draw text at position."""
        self.c.setFillColorRGB(*color)
        self.c.setFont(font, size)
        self.c.drawString(x, y, text)

    def _draw_semibold_text(self, x, y, text, size, color):
        """Draw semibold text."""
        self._draw_text(x, y, text, FONT_SEMIBOLD, size, color)

    def _h1(self, text):
        """Draw H1 heading with accent line."""
        self._need(50)
        self.y -= 18
        self._draw_semibold_text(MARGIN, self.y, text, 22, DEEP_BLUE)
        self.y -= 9
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, self.y, 60, 3, fill=1, stroke=0)
        self.y -= 18

    def _h2(self, text, color=DEEP_BLUE):
        """Draw H2 heading."""
        self._need(36)
        self.y -= 14
        self._draw_semibold_text(MARGIN, self.y, text, 14, color)
        self.y -= 18

    def _h3(self, text, color=MIDNIGHT_GREEN):
        """Draw H3 heading."""
        self._need(28)
        self.y -= 10
        self._draw_semibold_text(MARGIN, self.y, text, 11, color)
        self.y -= 14

    def _body(self, text, indent=0, size=10, color=DEEP_BLUE):
        """Draw body text with wrapping."""
        CW = PAGE_WIDTH - 2 * MARGIN
        self.c.setFillColorRGB(*color)
        self.c.setFont(FONT_LIGHT, size)
        cpl = int((CW - indent) / (size * 0.475))
        lh = size + 4
        for para in text.split('\n'):
            if not para.strip():
                self.y -= lh * 0.5
                continue
            for ln in textwrap.wrap(para, width=cpl):
                self._need(lh + 8)
                self.c.drawString(MARGIN + indent, self.y, ln)
                self.y -= lh

    def _bullet(self, text, indent=15, size=9.5):
        """Draw bullet point."""
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
        """Draw callout box."""
        CW = PAGE_WIDTH - 2 * MARGIN
        self.c.setFont(FONT_LIGHT, size)
        cpl = int((CW - 30) / (size * 0.475))
        lines = textwrap.wrap(text, width=cpl)
        lh = size + 4
        text_block_h = len(lines) * lh
        padding = 12
        bh = max(text_block_h + padding * 2, 36)
        self._need(bh + 6)

        box_bottom = self.y - bh + 8
        self.c.setFillColorRGB(*bg)
        self.c.roundRect(MARGIN, box_bottom, CW, bh, 4, fill=1, stroke=0)
        self.c.setFillColorRGB(*border)
        self.c.rect(MARGIN, box_bottom, 4, bh, fill=1, stroke=0)

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

    def _draw_table(self, headers, rows, col_widths=None):
        """Draw a simple table with headers and rows, wrapping text as needed."""
        CW = PAGE_WIDTH - 2 * MARGIN
        if col_widths is None:
            col_widths = [CW / len(headers)] * len(headers)

        header_height = 26
        line_height = 12
        cell_padding = 8

        # Calculate row heights based on wrapped text
        row_heights = []
        wrapped_rows = []
        for row in rows:
            max_lines = 1
            wrapped_row = []
            for i, cell in enumerate(row):
                text = str(cell) if cell else ""
                max_w = col_widths[i] - 16
                # Wrap text
                lines = []
                words = text.split()
                current_line = ""
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    if self.c.stringWidth(test_line, FONT_LIGHT, 9) <= max_w:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                if not lines:
                    lines = [""]
                wrapped_row.append(lines)
                max_lines = max(max_lines, len(lines))
            wrapped_rows.append(wrapped_row)
            row_heights.append(max(22, max_lines * line_height + cell_padding * 2))

        total_height = header_height + sum(row_heights) + 10
        self._need(total_height)

        x = MARGIN
        y = self.y

        # Header row
        self.c.setFillColorRGB(*TABLE_HEADER_BG)
        self.c.rect(x, y - header_height, CW, header_height, fill=1, stroke=0)

        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_SEMIBOLD, 9)
        col_x = x + 8
        for i, header in enumerate(headers):
            self.c.drawString(col_x, y - 17, header)
            col_x += col_widths[i]

        y -= header_height

        # Data rows
        for row_idx, (wrapped_row, row_height) in enumerate(zip(wrapped_rows, row_heights)):
            # Alternating background
            if row_idx % 2 == 1:
                self.c.setFillColorRGB(*TABLE_ALT_BG)
                self.c.rect(x, y - row_height, CW, row_height, fill=1, stroke=0)

            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_LIGHT, 9)
            col_x = x + 8
            for i, lines in enumerate(wrapped_row):
                text_y = y - cell_padding - 9
                for line in lines:
                    self.c.drawString(col_x, text_y, line)
                    text_y -= line_height
                col_x += col_widths[i]
            y -= row_height

        self.y = y - 10

    def _info_box(self, label, value, width, x=None):
        """Draw a labeled info box."""
        if x is None:
            x = MARGIN

        self.c.setFillColorRGB(*LIGHT_GRAY)
        self.c.roundRect(x, self.y - 40, width, 40, 4, fill=1, stroke=0)

        self.c.setFillColorRGB(*MIDNIGHT_GREEN)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(x + 10, self.y - 15, label)

        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 12)
        self.c.drawString(x + 10, self.y - 32, str(value))

    def _signature_block(self, x, y, party_name, width):
        """Draw a signature block for one party."""
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 11)
        self.c.drawString(x, y, f"For {party_name}")

        y -= 30
        # Signature line
        self.c.setStrokeColorRGB(*DEEP_BLUE)
        self.c.setLineWidth(0.5)
        self.c.line(x, y, x + width - 20, y)
        self.c.setFont(FONT_LIGHT, 8)
        self.c.drawString(x, y - 12, "Signature")

        y -= 40
        # Name line
        self.c.line(x, y, x + width - 20, y)
        self.c.drawString(x, y - 12, "Name")

        y -= 40
        # Title line
        self.c.line(x, y, x + width - 20, y)
        self.c.drawString(x, y - 12, "Title")

        y -= 40
        # Date line
        self.c.line(x, y, x + width - 20, y)
        self.c.drawString(x, y - 12, "Date")

    # =========================================================================
    # Page Methods
    # =========================================================================

    def _page_1_cover(self):
        """Page 1: Cover page."""
        self._new_page(bg_color=DEEP_BLUE)

        # Logo at top
        if os.path.exists(LOGO_PATH):
            logo_w = 180
            logo_h = logo_w * (4500 / 8000)
            self.c.drawImage(LOGO_PATH, MARGIN, PAGE_HEIGHT - 100,
                           width=logo_w, height=logo_h, mask='auto')

        # Main title
        self.y = PAGE_HEIGHT - 200
        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_SEMIBOLD, 36)
        self.c.drawString(MARGIN, self.y, "Statement of Work")

        # Subtitle
        self.y -= 35
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_LIGHT, 14)
        self.c.drawString(MARGIN, self.y, "GEO Optimization Engagement")

        # Divider line
        self.y -= 30
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, self.y, 100, 3, fill=1, stroke=0)

        # Client info
        self.y -= 50
        client = self.data.get('client', {})

        self.c.setFillColorRGB(*WHITE)
        self.c.setFont(FONT_LIGHT, 11)

        info_items = [
            ("Client:", client.get('company_name', 'Client Name')),
            ("Project:", self.data.get('project', {}).get('name', 'GEO Optimization')),
            ("SOW Reference:", self.data.get('sow_ref', 'SOW-2026-XXXX')),
            ("Effective Date:", self.data.get('effective_date', 'TBD')),
        ]

        for label, value in info_items:
            self.c.setFillColorRGB(*AQUAMARINE)
            self.c.setFont(FONT_LIGHT, 10)
            self.c.drawString(MARGIN, self.y, label)
            self.c.setFillColorRGB(*WHITE)
            self.c.setFont(FONT_REGULAR, 11)
            self.c.drawString(MARGIN + 100, self.y, value)
            self.y -= 22

        # Footer info
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.setFont(FONT_LIGHT, 9)
        self.c.drawString(MARGIN, 50, "peakweb.io")

        expires = self.data.get('expiration_date', '')
        if expires:
            self.c.drawRightString(PAGE_WIDTH - MARGIN, 50, f"Valid until: {expires}")

    def _page_2_overview(self):
        """Page 2: Overview."""
        self._start_content_page()

        self._h1("1. Overview")

        # Purpose
        self._h3("Purpose")
        overview_text = (
            f"This Statement of Work (\"SOW\") establishes the terms for "
            f"Generative Engine Optimization (GEO) services to be provided by "
            f"Peakweb Inc. (\"Peakweb\") to {self.data.get('client', {}).get('company_name', 'Client')} "
            f"(\"Client\"). The engagement focuses on improving the Client's visibility "
            f"in AI-powered search systems including ChatGPT, Google AI Overviews, and Perplexity."
        )
        self._body(overview_text)
        self._gap(15)

        # Project summary box
        CW = PAGE_WIDTH - 2 * MARGIN
        box_h = 90
        self._need(box_h + 20)

        self.c.setFillColorRGB(*STONE)
        self.c.roundRect(MARGIN, self.y - box_h, CW, box_h, 6, fill=1, stroke=0)
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(MARGIN, self.y - box_h, 4, box_h, fill=1, stroke=0)

        # Box content
        project = self.data.get('project', {})
        engagement = self.data.get('engagement', {})
        pricing = self.data.get('pricing', {})

        box_y = self.y - 20
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.setFont(FONT_SEMIBOLD, 12)
        self.c.drawString(MARGIN + 16, box_y, "Project Summary")

        box_y -= 25
        self.c.setFont(FONT_LIGHT, 10)

        summary_items = [
            ("Package:", project.get('package_display', 'GEO Services')),
            ("Duration:", engagement.get('duration', 'TBD')),
            ("Investment:", pricing.get('total', 'TBD')),
        ]

        for label, value in summary_items:
            self.c.setFillColorRGB(*MIDNIGHT_GREEN)
            self.c.drawString(MARGIN + 16, box_y, label)
            self.c.setFillColorRGB(*DEEP_BLUE)
            self.c.setFont(FONT_SEMIBOLD, 10)
            self.c.drawString(MARGIN + 100, box_y, value)
            self.c.setFont(FONT_LIGHT, 10)
            box_y -= 18

        self.y -= box_h + 15

        # Audit context (if available)
        context = self.data.get('context', {})
        if context.get('geo_score'):
            self._gap(10)
            self._h3("Current State")
            score = context.get('geo_score', 0)
            label = context.get('score_label', 'Fair')
            self._body(f"Based on our GEO audit, the Client's current GEO Score is {score}/100 ({label}).")
            self._gap(5)

            # Key issues
            issues = context.get('key_issues', [])
            if issues:
                self._body("Key issues identified:")
                for issue in issues[:3]:
                    self._bullet(issue)

    def _page_3_scope(self):
        """Page 3: Scope of Services."""
        self._start_content_page()

        self._h1("2. Scope of Services")

        # Objectives
        self._h2("2.1 Objectives")
        objectives = self.data.get('objectives', [
            "Improve AI search visibility across major platforms",
            "Deploy technical GEO optimizations",
            "Establish ongoing monitoring and reporting"
        ])
        for obj in objectives:
            self._bullet(obj)

        self._gap(15)

        # In Scope
        self._h2("2.2 In Scope")
        scope = self.data.get('scope', {})
        in_scope = scope.get('in_scope', [
            "Technical GEO audit and implementation",
            "AI configuration file deployment",
            "Schema.org markup implementation"
        ])
        for item in in_scope:
            self._bullet(item)

        self._gap(15)

        # Out of Scope
        self._h2("2.3 Out of Scope")
        out_scope = scope.get('out_of_scope', [
            "Website redesign or development",
            "Traditional SEO services",
            "Content creation beyond specified limits"
        ])
        for item in out_scope:
            self._bullet(item)

    def _page_4_deliverables(self):
        """Page 4: Deliverables & Timeline."""
        self._start_content_page()

        self._h1("3. Deliverables & Timeline")

        # Deliverables table
        self._h2("3.1 Deliverables")

        deliverables = self.data.get('deliverables', [
            {"number": 1, "name": "Technical Foundation", "description": "AI configuration files", "due": "Week 1-2"},
            {"number": 2, "name": "Implementation", "description": "Schema and optimizations", "due": "Week 3-4"},
            {"number": 3, "name": "Validation", "description": "Testing and monitoring", "due": "Week 5-6"},
        ])

        # Check if any deliverables have due dates
        has_due_dates = any(d.get('due', '').strip() for d in deliverables)

        if has_due_dates:
            headers = ["#", "Deliverable", "Description", "Due"]
            rows = []
            for d in deliverables:
                rows.append([
                    str(d.get('number', '')),
                    d.get('name', ''),
                    d.get('description', ''),
                    d.get('due', '')
                ])
            col_widths = [30, 130, 250, 80]
        else:
            headers = ["#", "Deliverable", "Description"]
            rows = []
            for d in deliverables:
                rows.append([
                    str(d.get('number', '')),
                    d.get('name', ''),
                    d.get('description', '')
                ])
            col_widths = [30, 150, 310]

        self._draw_table(headers, rows, col_widths)

        self._gap(20)

        # Milestones
        milestones = self.data.get('milestones', [])
        if milestones:
            self._h2("3.2 Milestones")
            for m in milestones:
                week = m.get('week', '')
                milestone = m.get('milestone', '')
                target = m.get('score_target', '')
                text = f"{week}: {milestone}"
                if target:
                    text += f" (Target: {target}/100)"
                self._bullet(text)

        # Score dependency note (warning style)
        score_note = self.data.get('score_dependency_note', '')
        if score_note:
            self._gap(10)
            self._callout(score_note, bg=WARNING_BG, border=WARNING_ORANGE)

        # Engagement timeline
        self._gap(15)
        engagement = self.data.get('engagement', {})
        start = engagement.get('start_date', '')
        end = engagement.get('end_date', '')
        if start and end:
            self._callout(f"Engagement Period: {start} to {end}")

    def _page_5_resources(self):
        """Page 5: Resource Requirements."""
        self._start_content_page()

        self._h1("4. Resource Requirements")

        # Peakweb Resources
        self._h2("4.1 Peakweb Resources")
        peakweb_resources = self.data.get('resources', {}).get('peakweb', [
            "GEO Specialist (primary contact)",
            "Technical implementation team",
            "Content strategist (Growth/Partner packages)"
        ])
        for resource in peakweb_resources:
            self._bullet(resource)

        self._gap(20)

        # Client Responsibilities
        self._h2("4.2 Client Responsibilities")
        self._body(
            "To ensure successful engagement, the Client agrees to provide the following:"
        )
        self._gap(8)

        client_resources = self.data.get('resources', {}).get('client', [
            "CMS access credentials (read/write) within 5 business days of signing",
            "Google Analytics access (read) for baseline metrics",
            "Google Search Console access (read) for search performance data",
            "Brand assets and photography as needed for content",
            "Timely feedback on content drafts (within 48 business hours)",
            "Designated point of contact for approvals and decisions"
        ])
        for resource in client_resources:
            self._bullet(resource)

        self._gap(20)

        # Important callout
        self._callout(
            "Note: Delays in providing required access or feedback may impact the "
            "project timeline and deliverable dates."
        )

    def _page_6_pricing(self):
        """Page 6: Pricing & Payment."""
        self._start_content_page()

        self._h1("5. Pricing & Payment")

        pricing = self.data.get('pricing', {})

        # Total Fee
        self._h2("5.1 Fees")
        total = pricing.get('total', '$0')
        pricing_type = pricing.get('type', 'one-time')

        if pricing_type == 'ongoing':
            self._body(f"Monthly retainer: {total}")
        else:
            self._body(f"Total engagement fee: {total}")

        # Fee breakdown
        breakdown = pricing.get('breakdown', [])
        if breakdown:
            self._gap(10)
            self._h3("Fee Breakdown")
            headers = ["Item", "Amount"]
            rows = [[b.get('item', ''), b.get('amount', '')] for b in breakdown]
            col_widths = [350, 140]
            self._draw_table(headers, rows, col_widths)

        self._gap(20)

        # Payment Schedule
        self._h2("5.2 Payment Schedule")
        schedule = pricing.get('payment_schedule', [
            {"milestone": "Upon signing", "percentage": "100%", "amount": total}
        ])

        headers = ["Milestone", "Percentage", "Amount"]
        rows = []
        for s in schedule:
            rows.append([
                s.get('milestone', ''),
                s.get('percentage', ''),
                s.get('amount', '')
            ])
        col_widths = [250, 120, 120]
        self._draw_table(headers, rows, col_widths)

        self._gap(20)

        # Payment terms
        self._h2("5.3 Payment Terms")
        self._body("Invoices will be sent separately via Mercury and are due within 15 days of receipt.")
        self._gap(5)
        self._body("Accepted payment methods:")
        self._bullet("Credit card")
        self._bullet("Apple Pay / Google Pay")
        self._bullet("ACH transfer")
        self._bullet("Wire transfer")

        self._gap(10)

        # Expenses
        expenses = pricing.get('expenses', '')
        if expenses:
            self._h3("Expenses")
            self._body(expenses)

    def _page_7_terms(self):
        """Page 7: Terms & Conditions."""
        self._start_content_page()

        self._h1("6. Terms & Conditions")

        # Change Management
        self._h2("6.1 Change Management")
        change_mgmt = self.data.get('change_management',
            "Changes to scope must be submitted in writing. Peakweb will provide "
            "a change order with revised timeline and pricing within 48 hours. "
            "No work on changes begins until written approval is received."
        )
        self._body(change_mgmt)

        self._gap(15)

        # Assumptions
        self._h2("6.2 Assumptions & Dependencies")
        assumptions = self.data.get('assumptions', [
            "Client will provide CMS access within 5 business days of signing",
            "Client feedback on deliverables within 48 business hours",
            "No major website redesign during engagement period",
            "Current hosting and domain remain stable"
        ])
        for assumption in assumptions:
            self._bullet(assumption)

        self._gap(15)

        # Acceptance
        self._h2("6.3 Acceptance Criteria")
        acceptance = self.data.get('acceptance_criteria',
            "Deliverables are considered accepted if no written objections are received "
            "within 5 business days of delivery. Final acceptance is confirmed by "
            "documented GEO score improvement as measured against the baseline audit."
        )
        self._body(acceptance)

        self._gap(15)

        # Term & Termination
        self._h2("6.4 Term & Termination")
        term = self.data.get('term', {})
        duration = term.get('duration', 'As specified in the engagement details')
        notice = term.get('termination_notice', '14 days written notice')

        self._body(f"Duration: {duration}")
        self._gap(5)
        self._body(f"Termination: Either party may terminate with {notice}. "
                  f"Payment for completed work through the termination date is due immediately.")

        self._gap(15)

        # Liability & Risk
        self._h2("6.5 Liability & Technical Modifications")
        self._body(
            "GEO implementation involves modifications to website code, configuration files, "
            "structured data, and third-party platform settings. By signing this agreement, "
            "Client acknowledges the inherent risks associated with such modifications."
        )
        self._gap(5)
        self._bullet("Peakweb maintains professional liability insurance covering our services")
        self._bullet("All modifications will be coordinated with Client's designated technical contact")
        self._bullet("Peakweb will document all changes and provide rollback procedures where applicable")
        self._bullet("Client is responsible for maintaining current backups of website and data")

    def _page_8_signatures(self):
        """Page 8: Signature blocks."""
        self._start_content_page()

        self._h1("7. Agreement")

        self._body(
            "By signing below, both parties agree to the terms and conditions "
            "outlined in this Statement of Work."
        )

        self._gap(30)

        # Two-column signature blocks
        CW = PAGE_WIDTH - 2 * MARGIN
        col_width = (CW - 40) / 2

        sig_y = self.y - 20

        # Peakweb signature
        self._signature_block(MARGIN, sig_y, "Peakweb Inc.", col_width)

        # Client signature
        client_name = self.data.get('client', {}).get('company_name', 'Client')
        self._signature_block(MARGIN + col_width + 40, sig_y, client_name, col_width)

        # SOW reference at bottom
        self.y = 100
        self._gap(20)
        sow_ref = self.data.get('sow_ref', '')
        if sow_ref:
            self.c.setFillColorRGB(*MIDNIGHT_GREEN)
            self.c.setFont(FONT_LIGHT, 9)
            self.c.drawCentredString(PAGE_WIDTH / 2, 80, f"SOW Reference: {sow_ref}")


# =============================================================================
# Sample Data for Testing
# =============================================================================

SAMPLE_DATA = {
    "sow_ref": "SOW-2026-0323-SIGSAUER",
    "effective_date": "March 30, 2026",
    "expiration_date": "April 30, 2026",

    "client": {
        "company_name": "SIG SAUER Inc.",
        "contact_name": "Jack Morris",
        "contact_title": "Sr. Manager, Web / Email",
        "website": "sigsauer.com"
    },

    "provider": {
        "company_name": "Peakweb Inc.",
        "contact_name": "Nathan Perry",
        "contact_email": "nathan@peakweb.io"
    },

    "project": {
        "name": "GEO Optimization Engagement",
        "package": "growth",
        "package_display": "GEO Growth",
        "description": "Comprehensive GEO services to improve AI search visibility."
    },

    "engagement": {
        "type": "one-time",
        "duration": "90 days",
        "start_date": "March 30, 2026",
        "end_date": "June 28, 2026"
    },

    "context": {
        "geo_score": 58,
        "score_label": "Fair",
        "key_issues": [
            "JavaScript rendering blocks AI crawler access",
            "Missing Product schema markup on key pages",
            "Limited AI-optimized content across product categories"
        ]
    },

    "objectives": [
        "Improve GEO Score from 58 to 75+ within 90 days",
        "Deploy AI configuration files (llms.txt, enhanced robots.txt)",
        "Implement comprehensive Schema.org markup",
        "Create AI-optimized content for key product categories",
        "Establish monitoring dashboard for ongoing visibility tracking"
    ],

    "scope": {
        "in_scope": [
            "Full technical GEO audit and implementation",
            "AI configuration file deployment (llms.txt, robots.txt)",
            "Schema.org markup (Organization, Product, FAQPage)",
            "AI-optimized content creation (up to 10 pages)",
            "Platform-specific optimization with validation via Perplexity API",
            "90-day monitoring dashboard",
            "Weekly progress reports"
        ],
        "out_of_scope": [
            "Server-side rendering (SSR) implementation",
            "Core website redesign or development",
            "Traditional SEO services (keyword research, link building)",
            "Paid advertising or PPC management",
            "Content beyond the specified 10-page limit"
        ]
    },

    "deliverables": [
        {
            "number": 1,
            "name": "Technical Foundation",
            "description": "AI configuration files, crawler access optimization, basic schema",
            "due": "Week 1-2"
        },
        {
            "number": 2,
            "name": "Authority Building",
            "description": "Platform presence setup, enhanced schema markup",
            "due": "Week 3-4"
        },
        {
            "number": 3,
            "name": "Content Optimization",
            "description": "AI-optimized content for key pages (up to 10)",
            "due": "Week 5-8"
        },
        {
            "number": 4,
            "name": "Validation & Launch",
            "description": "Perplexity API citation testing, monitoring dashboard, final report",
            "due": "Week 9-12"
        }
    ],

    "milestones": [
        {"week": "Week 2", "milestone": "Technical foundation complete", "score_target": "65"},
        {"week": "Week 4", "milestone": "Authority signals deployed", "score_target": "70"},
        {"week": "Week 8", "milestone": "Content optimization complete", "score_target": "73"},
        {"week": "Week 12", "milestone": "Final validation and handoff", "score_target": "75+"}
    ],

    "resources": {
        "peakweb": [
            "GEO Specialist (primary contact)",
            "Technical implementation team",
            "Content strategist"
        ],
        "client": [
            "CMS access credentials (read/write)",
            "Google Analytics access (read)",
            "Google Search Console access (read)",
            "Brand assets and photography",
            "Timely feedback on content drafts (within 48 hours)",
            "Designated point of contact for approvals"
        ]
    },

    "pricing": {
        "type": "one-time",
        "total": "$2,500",
        "breakdown": [
            {"item": "Technical Foundation (Week 1-2)", "amount": "$750"},
            {"item": "Authority Building (Week 3-4)", "amount": "$500"},
            {"item": "Content Optimization (Week 5-8)", "amount": "$750"},
            {"item": "Validation & Launch (Week 9-12)", "amount": "$500"}
        ],
        "payment_schedule": [
            {"milestone": "Upon signing", "percentage": "50%", "amount": "$1,250"},
            {"milestone": "Week 6 checkpoint", "percentage": "25%", "amount": "$625"},
            {"milestone": "Final delivery", "percentage": "25%", "amount": "$625"}
        ],
        "expenses": "All standard expenses included. Travel or premium third-party tools require pre-approval.",
        "currency": "USD"
    },

    "change_management": (
        "Changes to scope must be submitted in writing. Peakweb will provide a "
        "change order with revised timeline and pricing within 48 hours. No work "
        "on changes begins until written approval is received."
    ),

    "assumptions": [
        "Client will provide CMS access within 5 business days of signing",
        "Client feedback on content drafts within 48 business hours",
        "No major website redesign during engagement period",
        "Current hosting and domain remain stable",
        "Client has authority to make content and technical changes"
    ],

    "acceptance_criteria": (
        "Deliverables are considered accepted if no written objections are received "
        "within 5 business days of delivery. Final acceptance is confirmed by "
        "documented citation rate improvement via Perplexity API testing against the baseline."
    ),

    "term": {
        "duration": "90 days from Effective Date",
        "termination_notice": "14 days written notice",
        "termination_payment": "Payment for completed work through termination date"
    }
}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # No args - use sample data for testing
        print("No JSON file provided, using sample data for testing...")
        data = SAMPLE_DATA
        output_file = "PeakwebSOW-Sample.pdf"
    else:
        # Load JSON data
        json_path = sys.argv[1]
        if not os.path.exists(json_path):
            print(f"Error: File not found: {json_path}")
            sys.exit(1)

        with open(json_path, 'r') as f:
            data = json.load(f)

        # Output filename
        if len(sys.argv) >= 3:
            output_file = sys.argv[2]
        else:
            client_name = data.get('client', {}).get('company_name', 'Client')
            safe_name = ''.join(c for c in client_name if c.isalnum() or c in ' -_').strip()
            safe_name = safe_name.replace(' ', '')
            date_str = datetime.now().strftime('%Y-%m-%d')
            output_file = f"PeakwebSOW-{safe_name}-{date_str}.pdf"

    # Generate the SOW
    generator = SOWGenerator(data, output_file)
    generator.generate()


if __name__ == "__main__":
    main()
