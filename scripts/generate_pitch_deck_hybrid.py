#!/usr/bin/env python3
"""
Hybrid Peakweb Pitch Deck Generator

Uses the template PDF for backgrounds and design elements,
then renders dynamic content (text, charts, gauges) programmatically
with proper font handling and text wrapping.
"""

import fitz  # PyMuPDF
import json
import math
import sys
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
TEMPLATE_PATH = os.path.join(PROJECT_DIR, "examples/peakweb/PeakwebGEOProposal-Template.pdf")
FONTS_DIR = os.path.join(PROJECT_DIR, "assets/fonts")

# Colors (RGB 0-1)
DEEP_BLUE = (10/255, 44/255, 73/255)
AQUAMARINE = (1/255, 239/255, 160/255)
LIGHT_GREEN = (188/255, 255/255, 138/255)
MIDNIGHT_GREEN = (10/255, 62/255, 60/255)
LILAC = (152/255, 146/255, 181/255)
STONE = (252/255, 247/255, 230/255)
WHITE = (1, 1, 1)

# Page dimensions (US Letter)
PAGE_WIDTH = 612
PAGE_HEIGHT = 792


class PitchDeckGenerator:
    def __init__(self, template_path=TEMPLATE_PATH):
        self.template_path = template_path
        self.doc = None
        self.fonts = {}

    def load_template(self):
        """Load the template PDF."""
        self.doc = fitz.open(self.template_path)
        self._register_fonts()
        self._redact_all_placeholders()

    def _redact_all_placeholders(self):
        """Find and redact all lines containing {{PLACEHOLDER}}.

        For inline placeholders, we need to redact the ENTIRE LINE (all spans),
        not just the placeholder span, because the surrounding static text
        would otherwise remain visible and create duplicates.
        """

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text_dict = page.get_text("dict")

            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    # Check if ANY span in this line contains a placeholder
                    line_has_placeholder = False
                    line_color = None

                    for span in line["spans"]:
                        text = span["text"]
                        if "{{" in text and "}}" in text:
                            line_has_placeholder = True
                            line_color = span["color"]
                            break

                    if line_has_placeholder:
                        # Calculate bounding box for the ENTIRE line
                        x0 = min(span["bbox"][0] for span in line["spans"])
                        y0 = min(span["bbox"][1] for span in line["spans"])
                        x1 = max(span["bbox"][2] for span in line["spans"])
                        y1 = max(span["bbox"][3] for span in line["spans"])

                        # Determine fill color
                        if line_color == 0xffffff:  # White text = dark bg
                            fill = DEEP_BLUE
                        elif line_color == 0x01efa0:  # Green text
                            fill = DEEP_BLUE if page_num == 10 else STONE
                        else:  # Dark text = light bg
                            fill = STONE

                        # Redact the entire line
                        rect = fitz.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
                        page.add_redact_annot(rect, fill=fill)

            # Apply all redactions for this page
            page.apply_redactions()

    def _register_fonts(self):
        """Register Outfit fonts for use in the document."""
        font_files = {
            'outfit-thin': os.path.join(FONTS_DIR, 'Outfit-Thin.ttf'),
            'outfit-light': os.path.join(FONTS_DIR, 'Outfit-Light.ttf'),
            'outfit-regular': os.path.join(FONTS_DIR, 'Outfit-Regular.ttf'),
            'outfit-semibold': os.path.join(FONTS_DIR, 'Outfit-SemiBold.ttf'),
        }

        for name, path in font_files.items():
            if os.path.exists(path):
                self.fonts[name] = path
            else:
                print(f"Warning: Font not found: {path}")

    def clear_rect(self, page, rect, color=STONE):
        """Clear a rectangular area by redacting and filling with color."""
        page.add_redact_annot(rect, fill=color)
        page.apply_redactions()

    def draw_text(self, page, text, x, y, font='outfit-thin', size=10, color=DEEP_BLUE,
                  max_width=None, align='left', line_height=1.3):
        """
        Draw text with optional wrapping.
        Returns the final y position after drawing.
        """
        font_path = self.fonts.get(font)

        if max_width and len(text) * size * 0.5 > max_width:
            # Need to wrap text
            return self._draw_wrapped_text(page, text, x, y, font_path, size, color,
                                          max_width, align, line_height)
        else:
            # Single line
            page.insert_text(
                fitz.Point(x, y),
                text,
                fontfile=font_path,
                fontsize=size,
                color=color
            )
            return y + size * line_height

    def _draw_wrapped_text(self, page, text, x, y, font_path, size, color,
                           max_width, align, line_height):
        """Draw text with word wrapping."""
        words = text.split()
        lines = []
        current_line = []

        # Approximate character width (will vary by font)
        avg_char_width = size * 0.45

        for word in words:
            test_line = ' '.join(current_line + [word])
            line_width = len(test_line) * avg_char_width

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        # Draw each line
        for line in lines:
            if align == 'center':
                line_width = len(line) * avg_char_width
                line_x = x + (max_width - line_width) / 2
            elif align == 'right':
                line_width = len(line) * avg_char_width
                line_x = x + max_width - line_width
            else:
                line_x = x

            page.insert_text(
                fitz.Point(line_x, y),
                line,
                fontfile=font_path,
                fontsize=size,
                color=color
            )
            y += size * line_height

        return y

    def draw_score_gauge(self, page, score, x, y, width=80, height=40):
        """
        Draw a semi-circular score gauge.
        Score should be an integer 0-100.
        """
        # Ensure score is an integer
        score = int(score) if isinstance(score, (int, float)) else 0

        cx = x + width / 2
        cy = y + height
        radius = min(width / 2, height) * 0.9

        # Background arc (gray)
        self._draw_arc(page, cx, cy, radius, 180, 0, (0.85, 0.85, 0.85), 8)

        # Score arc (colored based on score)
        if score >= 75:
            arc_color = AQUAMARINE
        elif score >= 50:
            arc_color = (1, 0.8, 0)  # Yellow/orange
        else:
            arc_color = (0.9, 0.3, 0.3)  # Red

        # Calculate end angle based on score (0-100 maps to 180-0 degrees)
        if score > 0:
            end_angle = 180 - (score / 100 * 180)
            self._draw_arc(page, cx, cy, radius, 180, end_angle, arc_color, 8)

        # Score text in center
        score_text = str(score)
        text_x = cx - 20 if score >= 10 else cx - 12
        self.draw_text(page, score_text, text_x, cy - 5,
                      font='outfit-semibold', size=24, color=DEEP_BLUE)
        self.draw_text(page, "/ 100", cx + 12, cy - 5,
                      font='outfit-thin', size=12, color=DEEP_BLUE)

    def _draw_arc(self, page, cx, cy, radius, start_angle, end_angle, color, width):
        """Draw an arc using line segments."""
        steps = 30
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)

        points = []
        for i in range(steps + 1):
            angle = start_rad + (end_rad - start_rad) * i / steps
            px = cx + radius * math.cos(angle)
            py = cy - radius * math.sin(angle)  # Negative because PDF y is inverted
            points.append(fitz.Point(px, py))

        for i in range(len(points) - 1):
            page.draw_line(points[i], points[i+1], color=color, width=width)

    def draw_progress_bar(self, page, progress, x, y, width=200, height=12,
                          bg_color=(0.9, 0.9, 0.9), fill_color=AQUAMARINE):
        """Draw a horizontal progress bar."""
        # Background
        bg_rect = fitz.Rect(x, y, x + width, y + height)
        page.draw_rect(bg_rect, color=bg_color, fill=bg_color)

        # Fill
        fill_width = width * (progress / 100)
        fill_rect = fitz.Rect(x, y, x + fill_width, y + height)
        page.draw_rect(fill_rect, color=fill_color, fill=fill_color)

    def draw_bullet_list(self, page, items, x, y, font='outfit-thin', size=9.5,
                         color=DEEP_BLUE, max_width=450, bullet="•", spacing=13.5):
        """Draw a bulleted list."""
        for item in items:
            # Draw bullet
            page.insert_text(
                fitz.Point(x, y),
                bullet,
                fontfile=self.fonts.get(font),
                fontsize=size,
                color=color
            )
            # Draw text
            y = self.draw_text(page, item, x + 12, y, font=font, size=size,
                              color=color, max_width=max_width - 12)
            y += spacing - size  # Additional spacing between items
        return y

    def generate(self, data, output_path):
        """Generate the pitch deck with the given data."""
        self.load_template()

        # Process each page
        self._render_page_1(data)
        self._render_page_2(data)
        self._render_page_3(data)
        self._render_page_4(data)
        self._render_page_5(data)
        self._render_page_6(data)
        self._render_page_7(data)
        self._render_page_8(data)
        # Pages 9 is static (pricing)
        self._render_page_10(data)
        self._render_page_11(data)
        self._render_page_12(data)

        # Save
        self.doc.save(output_path)
        self.doc.close()
        print(f"Generated: {output_path}")

    def _render_page_1(self, data):
        """Cover page - client info.

        The template already has the layout - we just need to place text
        where the {{PLACEHOLDER}} values were redacted.
        """
        page = self.doc[0]

        # Contact name and title - position from template extraction
        self.draw_text(page, data.get('CONTACT_NAME, TITLE', ''), 72, 405,
                      font='outfit-thin', size=13, color=WHITE, max_width=220)

        # Client/Company name
        self.draw_text(page, data.get('CLIENT_NAME', ''), 72, 423,
                      font='outfit-thin', size=11, color=WHITE, max_width=220)

        # Website
        self.draw_text(page, data.get('CLIENT_WEBSITE', ''), 316, 405,
                      font='outfit-thin', size=11, color=WHITE, max_width=220)

        # Date
        self.draw_text(page, data.get('REPORT_DATE', ''), 72, 458,
                      font='outfit-thin', size=11, color=WHITE)

    def _render_page_2(self, data):
        """Executive Summary page.

        Clear entire content paragraphs that have inline placeholders
        and redraw them completely.
        """
        page = self.doc[1]

        sample_query = data.get('SAMPLE_QUERY', 'your services')
        years = data.get('YEARS', '')
        bbb = data.get('BBB_RATING', '')
        city = data.get('CITY', 'your area')
        industry = data.get('INDUSTRY', 'your industry')
        service = data.get('SERVICE_TYPE', 'services')

        # Clear the entire first paragraph area (intro paragraph)
        self.clear_rect(page, fitz.Rect(50, 140, 590, 180), STONE)

        # Redraw intro paragraph
        intro = f'When someone asks ChatGPT, Google AI, or Perplexity a question like "{sample_query}" your business is rarely mentioned – even though you have {years} years of experience and an {bbb} BBB rating.'
        self.draw_text(page, intro, 54, 155, font='outfit-thin', size=10,
                      color=DEEP_BLUE, max_width=520)

        # Clear the "Right now" paragraph area
        self.clear_rect(page, fitz.Rect(50, 305, 590, 365), STONE)

        # Redraw "Right now" paragraph
        right_now = f"Right now, AI systems answering questions about {city} {industry} or {service} services rarely mention your business. Not because you're not qualified, but because your website doesn't communicate effectively with AI systems yet."
        self.draw_text(page, right_now, 54, 320, font='outfit-thin', size=10,
                      color=DEEP_BLUE, max_width=520)

    def _render_page_3(self, data):
        """Your Current Score page.

        Clear content areas and redraw:
        - Score display area
        - Progress bar
        - Score label/description
        - What's Working Well bullets
        - What This Means section
        """
        page = self.doc[2]

        score = data.get('GEO_SCORE', 53)
        if isinstance(score, str):
            try:
                score = int(score)
            except:
                score = 53

        # Clear the entire score display row (includes template's static "53 / 100")
        self.clear_rect(page, fitz.Rect(225, 255, 595, 300), STONE)

        # Draw score number and "/ 100"
        self.draw_text(page, str(score), 500, 282, font='outfit-semibold',
                      size=28, color=DEEP_BLUE)
        self.draw_text(page, "/ 100", 540, 282, font='outfit-thin',
                      size=14, color=DEEP_BLUE)

        # Draw progress bar
        self.draw_progress_bar(page, score, 233, 269, width=245, height=10)

        # Clear and redraw score label/description area
        self.clear_rect(page, fitz.Rect(215, 305, 595, 360), STONE)
        score_label = data.get('SCORE_LABEL', 'FAIR')
        score_desc = data.get('SCORE_DESCRIPTION', '')
        self.draw_text(page, f"{score_label} – {score_desc}", 225, 322,
                      font='outfit-thin', size=9.5, color=DEEP_BLUE, max_width=360)

        # Clear and redraw "What's Working Well" section
        self.clear_rect(page, fitz.Rect(230, 380, 595, 470), STONE)
        working = [
            data.get('WORKING_1', ''),
            data.get('WORKING_2', ''),
            data.get('WORKING_3', ''),
            data.get('WORKING_4', ''),
        ]
        working = [w for w in working if w]
        self.draw_bullet_list(page, working, 239, 392, max_width=345, spacing=13.5)

        # Clear and redraw "What This Means" section
        self.clear_rect(page, fitz.Rect(215, 500, 595, 590), STONE)
        city = data.get('CITY', 'your area')
        industry = data.get('INDUSTRY', 'your industry')
        service_plural = data.get('SERVICE_TYPE_PLURAL', 'services')

        means_intro = f"When AI systems answer questions about {city} {industry} or {service_plural}, they rarely mention your business. This means:"
        self.draw_text(page, means_intro, 217, 515, font='outfit-thin', size=10,
                      color=DEEP_BLUE, max_width=370)

        means = [
            data.get('MEANS_1', ''),
            data.get('MEANS_2', ''),
            data.get('MEANS_3', ''),
        ]
        means = [m for m in means if m]
        self.draw_bullet_list(page, means, 239, 545, max_width=345, spacing=13.5)

    def _render_page_4(self, data):
        """The 6 Key Issues page."""
        page = self.doc[3]

        issues = []
        for i in range(1, 7):
            issue = {
                'title': data.get(f'ISSUE_{i}_TITLE', ''),
                'body': data.get(f'ISSUE_{i}_BODY', ''),
                'callout': data.get(f'ISSUE_{i}_CALLOUT', '') or data.get(f'ISSUE_{i}_EXAMPLE', ''),
            }
            if issue['title']:
                issues.append(issue)

        # Clear and render each issue
        y_positions = [157, 253, 321, 418, 514, 611]  # Approximate y positions for each issue

        for i, (issue, y) in enumerate(zip(issues, y_positions)):
            # Clear issue area
            self.clear_rect(page, fitz.Rect(50, y - 5, 560, y + 85), STONE)

            # Issue title
            self.draw_text(page, f"{i+1}. {issue['title']}", 54, y + 12,
                          font='outfit-thin', size=14, color=DEEP_BLUE, max_width=500)

            # Issue body
            self.draw_text(page, issue['body'], 54, y + 35,
                          font='outfit-thin', size=10, color=DEEP_BLUE, max_width=500)

            # Callout (if any)
            if issue['callout']:
                self.draw_text(page, issue['callout'], 70, y + 65,
                              font='outfit-thin', size=9.5, color=MIDNIGHT_GREEN, max_width=480)

    def _render_page_5(self, data):
        """What Happens If You Do Nothing page."""
        page = self.doc[4]

        # Short term consequences
        self.clear_rect(page, fitz.Rect(75, 150, 560, 210), STONE)
        short_term = [
            data.get('NOTHING_SHORT_1', ''),
            data.get('NOTHING_SHORT_2', ''),
            data.get('NOTHING_SHORT_3', ''),
        ]
        short_term = [s for s in short_term if s]
        self.draw_bullet_list(page, short_term, 81, 165, max_width=450)

        # Long term consequences
        self.clear_rect(page, fitz.Rect(75, 218, 560, 280), STONE)
        long_term = [
            data.get('NOTHING_LONG_1', ''),
            data.get('NOTHING_LONG_2', ''),
            data.get('NOTHING_LONG_3', ''),
        ]
        long_term = [l for l in long_term if l]
        self.draw_bullet_list(page, long_term, 81, 233, max_width=450)

    def _render_page_6(self, data):
        """The Opportunity page."""
        page = self.doc[5]

        # Projected score
        self.clear_rect(page, fitz.Rect(380, 190, 560, 235), STONE)
        projected = data.get('PROJECTED', '85/100')
        self.draw_text(page, projected, 390, 220, font='outfit-thin',
                      size=24, color=AQUAMARINE)

        # Opportunity descriptions
        self.clear_rect(page, fitz.Rect(75, 295, 450, 420), STONE)
        y = 308
        for i in range(1, 5):
            desc = data.get(f'OPP_{i}_DESC', '')
            if desc:
                self.draw_text(page, desc, 82, y, font='outfit-thin',
                              size=9, color=DEEP_BLUE, max_width=360)
                y += 31

    def _render_page_7(self, data):
        """Implementation Roadmap page."""
        page = self.doc[6]

        # Week scores
        scores = [
            ('W1_SCORE', 197),
            ('W2_SCORE', 258),
            ('W3_SCORE', 319),
            ('W4_SCORE', 380),
        ]

        for key, y in scores:
            score = data.get(key, '')
            if score:
                self.clear_rect(page, fitz.Rect(280, y - 8, 350, y + 8), STONE)
                self.draw_text(page, score, 290, y + 3, font='outfit-thin',
                              size=8, color=LILAC)

        # City reference in week 3
        self.clear_rect(page, fitz.Rect(80, 323, 400, 340), STONE)
        city = data.get('CITY', 'your area')
        self.draw_text(page, f"Publish AI-optimized content that positions you as the {city} authority",
                      84, 335, font='outfit-thin', size=9, color=DEEP_BLUE)

    def _render_page_8(self, data):
        """ROI page."""
        page = self.doc[7]

        # Clear ROI numbers area
        self.clear_rect(page, fitz.Rect(70, 430, 560, 480), STONE)

        # ROI figures
        customers = data.get('CUSTOMERS_PER_MONTH', '')
        monthly = data.get('MONTHLY_REV', '')
        annual = data.get('ANNUAL_IMPACT', '')

        x_positions = [90, 250, 400]
        values = [customers, monthly, annual]

        for x, val in zip(x_positions, values):
            if val:
                self.draw_text(page, val, x, 460, font='outfit-thin',
                              size=24, color=AQUAMARINE)

    def _render_page_10(self, data):
        """Before/After + FAQ page."""
        page = self.doc[9]

        # Before section
        self.clear_rect(page, fitz.Rect(60, 195, 560, 290), STONE)
        y = 210
        for i in range(1, 6):
            line = data.get(f'BEFORE_LINE_{i}', '')
            if line:
                self.draw_text(page, line, 68, y, font='outfit-thin',
                              size=9, color=DEEP_BLUE, max_width=480)
                y += 14

        # After section
        self.clear_rect(page, fitz.Rect(60, 330, 560, 435), STONE)
        y = 345
        for i in range(1, 7):
            line = data.get(f'AFTER_LINE_{i}', '')
            if line:
                self.draw_text(page, line, 68, y, font='outfit-thin',
                              size=9, color=DEEP_BLUE, max_width=480)
                y += 14

        # FAQs
        self.clear_rect(page, fitz.Rect(50, 560, 560, 660), STONE)

        # FAQ 1
        q1 = data.get('FAQ_1_Q', '')
        a1 = data.get('FAQ_1_A', '')
        if q1:
            self.draw_text(page, f'"{q1}"', 54, 580, font='outfit-thin',
                          size=11, color=MIDNIGHT_GREEN)
            self.draw_text(page, a1, 54, 598, font='outfit-thin',
                          size=9.5, color=DEEP_BLUE, max_width=500)

        # FAQ 2
        q2 = data.get('FAQ_2_Q', '')
        a2 = data.get('FAQ_2_A', '')
        if q2:
            self.draw_text(page, f'"{q2}"', 54, 625, font='outfit-thin',
                          size=11, color=MIDNIGHT_GREEN)
            self.draw_text(page, a2, 54, 643, font='outfit-thin',
                          size=9.5, color=DEEP_BLUE, max_width=500)

    def _render_page_11(self, data):
        """Bottom Line / CTA page."""
        page = self.doc[10]

        # Clear the center text area (on dark background)
        self.clear_rect(page, fitz.Rect(200, 400, 420, 470), DEEP_BLUE)

        # Bottom line text
        line1 = data.get('BOTTOM_LINE_1', '')
        line2 = data.get('BOTTOM_LINE_2', '')
        closer = data.get('BOTTOM_LINE_CLOSER', '')

        if line1:
            self.draw_text(page, line1, 220, 425, font='outfit-thin',
                          size=10, color=WHITE, max_width=180, align='center')
        if line2:
            self.draw_text(page, line2, 220, 442, font='outfit-thin',
                          size=10, color=WHITE, max_width=180, align='center')
        if closer:
            self.draw_text(page, closer, 220, 462, font='outfit-thin',
                          size=10, color=AQUAMARINE, max_width=180, align='center')

    def _render_page_12(self, data):
        """Final page with disclaimer."""
        page = self.doc[11]

        # Clear and redraw the footer text
        self.clear_rect(page, fitz.Rect(150, 745, 470, 765), STONE)

        date = data.get('REPORT_DATE', '')
        client = data.get('CLIENT_NAME_FULL', data.get('CLIENT_NAME', ''))

        footer = f"This report was prepared {date}, for {client}."
        self.draw_text(page, footer, 180, 758, font='outfit-thin',
                      size=7.5, color=(74/255, 122/255, 148/255))


# Sample data for testing
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

    "CUSTOMERS_PER_MONTH": "1-2",
    "MONTHLY_REV": "$500-2,000",
    "ANNUAL_IMPACT": "$6,000-24,000",

    "BEFORE_LINE_1": "Hunter: 'Hey ChatGPT, who does quality taxidermy in Anchorage?'",
    "BEFORE_LINE_2": "ChatGPT: 'Here are some options in the Anchorage area:'",
    "BEFORE_LINE_3": "- Northland Taxidermy (mentioned on hunting forums)",
    "BEFORE_LINE_4": "- Alaska Wildlife Creations (has Google reviews)",
    "BEFORE_LINE_5": "Your business: Not mentioned",

    "AFTER_LINE_1": "Hunter: 'Hey ChatGPT, who does quality taxidermy in Anchorage?'",
    "AFTER_LINE_2": "ChatGPT: 'Here are some highly regarded options:'",
    "AFTER_LINE_3": "- Wild Reflections Studio (23+ years exp, Animal Artistry trained, sheep specialist)",
    "AFTER_LINE_4": "- Northland Taxidermy",
    "AFTER_LINE_5": "- Alaska Wildlife Creations",
    "AFTER_LINE_6": "Your business: Mentioned FIRST with your unique credentials",

    "FAQ_1_Q": "Can Wix sites really be optimized for AI?",
    "FAQ_1_A": "Yes, but it requires workarounds. We can add schema via Wix's custom code feature, create an llms.txt, and potentially deploy AI-optimized landing pages that complement your main site.",

    "FAQ_2_Q": "How long until I see results?",
    "FAQ_2_A": "Technical fixes show impact in 2-4 weeks. Building authority through content and citations takes 2-3 months. Full optimization typically reaches target score in 90 days.",

    "BOTTOM_LINE_1": "You've built a stellar reputation over 23 years.",
    "BOTTOM_LINE_2": "AI systems just don't know about it yet.",
    "BOTTOM_LINE_CLOSER": "Let's change that.",
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Using sample data for testing...")
        data = SAMPLE_DATA
        output = "PeakwebGEOProposal-WildReflections-Test.pdf"
    elif len(sys.argv) == 2:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
        client = data.get('CLIENT_NAME', 'Output').replace(' ', '')
        output = f"PeakwebGEOProposal-{client}.pdf"
    else:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
        output = sys.argv[2]

    generator = PitchDeckGenerator()
    generator.generate(data, output)
