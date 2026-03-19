#!/usr/bin/env python3
"""
Fill Peakweb Pitch Deck Template

Uses the template PDF as a base and replaces {{PLACEHOLDER}} values
with actual client data, preserving the exact design and styling.
"""

import fitz  # PyMuPDF
import json
import re
import sys
import os

# Path to the template
TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples/peakweb/PeakwebGEOProposal-Template.pdf"
)

def find_and_replace_placeholders(doc, data):
    """
    Find all {{PLACEHOLDER}} text in the document and replace with values from data.
    Uses redaction to properly remove original text before inserting replacement.
    """
    replacements_made = 0

    # Colors as RGB tuples (0-1 range)
    DEEP_BLUE = (10/255, 44/255, 73/255)
    STONE = (252/255, 247/255, 230/255)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Get all text instances with their positions
        text_dict = page.get_text("dict")

        # Collect all replacements to make on this page
        replacements = []

        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"]

                    # Check if this span contains any {{PLACEHOLDER}}
                    if "{{" in text and "}}" in text:
                        bbox = span["bbox"]
                        font = span["font"]
                        size = span["size"]
                        color = span["color"]

                        # Replace all placeholders in this text
                        new_text = text
                        for match in re.finditer(r'\{\{([^}]+)\}\}', text):
                            placeholder = match.group(1)
                            key = placeholder.strip()

                            if key in data:
                                value = str(data[key])
                                new_text = new_text.replace("{{" + placeholder + "}}", value)
                            else:
                                print(f"  Warning: No data for placeholder '{key}' on page {page_num + 1}")

                        if new_text != text:
                            replacements.append({
                                "bbox": bbox,
                                "old_text": text,
                                "new_text": new_text,
                                "font": font,
                                "size": size,
                                "color": color
                            })

        # Phase 1: Add redaction annotations to remove original text
        for r in replacements:
            bbox = r["bbox"]
            text_color_int = r["color"]

            # Determine fill color for redaction based on original text color
            if text_color_int == 0xffffff:  # White text on dark bg
                fill_color = DEEP_BLUE
            elif text_color_int == 0x01efa0:  # Green text
                if page_num == 10:  # Page 11 - dark background
                    fill_color = DEEP_BLUE
                else:
                    fill_color = STONE
            else:
                fill_color = STONE

            # Expand bbox slightly
            rect = fitz.Rect(bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1)
            page.add_redact_annot(rect, fill=fill_color)

        # Apply all redactions at once
        page.apply_redactions()

        # Phase 2: Insert replacement text
        for r in replacements:
            bbox = r["bbox"]
            text_color_int = r["color"]

            # Convert color int to RGB tuple
            text_color = (
                ((text_color_int >> 16) & 0xFF) / 255,
                ((text_color_int >> 8) & 0xFF) / 255,
                (text_color_int & 0xFF) / 255
            )

            # Use Helvetica as fallback font
            fontname = "helv"

            # Insert new text at the original position
            # Text baseline is at bbox bottom minus a small offset
            text_point = fitz.Point(bbox[0], bbox[3] - 2)

            page.insert_text(
                text_point,
                r["new_text"],
                fontname=fontname,
                fontsize=r["size"],
                color=text_color
            )

            replacements_made += 1
            print(f"  Page {page_num + 1}: Replaced '{r['old_text'][:50]}...' -> '{r['new_text'][:50]}...'")

    return replacements_made


def fill_template(data, output_path):
    """
    Fill the template PDF with data and save to output_path.
    """
    print(f"Loading template: {TEMPLATE_PATH}")

    if not os.path.exists(TEMPLATE_PATH):
        print(f"ERROR: Template not found at {TEMPLATE_PATH}")
        sys.exit(1)

    # Open template
    doc = fitz.open(TEMPLATE_PATH)

    print(f"Template has {len(doc)} pages")
    print(f"Replacing placeholders with {len(data)} data values...")

    # Find and replace all placeholders
    count = find_and_replace_placeholders(doc, data)

    print(f"Made {count} replacements")

    # Save the result
    doc.save(output_path)
    doc.close()

    print(f"Saved filled PDF to: {output_path}")
    return output_path


# Sample data for testing - matches the Denver Sprinkler example
SAMPLE_DATA = {
    # Page 1 - Cover
    "CONTACT_NAME, TITLE": "Ramon Robles, Owner",
    "CLIENT_NAME": "Denver Sprinkler & Landscape",
    "CLIENT_WEBSITE": "denversprinklerservices.com",
    "REPORT_DATE": "March 17, 2026",

    # Page 2 - Executive Summary
    "SAMPLE_QUERY": "Who does sprinkler repair in Denver?",
    "YEARS": "25",
    "BBB_RATING": "A+",
    "CITY": "Denver",
    "INDUSTRY": "landscaping",
    "SERVICE_TYPE": "sprinkler",
    "SERVICE_TYPE_PLURAL": "sprinkler services",

    # Page 3 - Current Score
    "SCORE_LABEL": "FAIR",
    "SCORE_DESCRIPTION": "Your website is functional but not optimized for AI systems. AI search engines can access your site but rarely cite or recommend it.",
    "WORKING_1": "Your website is accessible - AI systems can read your content",
    "WORKING_2": "Strong reputation - BBB A+ rating, Trees.com #6 in Denver",
    "WORKING_3": "Complete contact info - address, phone, hours clearly listed",
    "WORKING_4": "Professional website - clean design, mobile-friendly, secure",
    "MEANS_1": "Lost phone calls from potential customers who never hear your name",
    "MEANS_2": "Competitors who optimize for AI get recommended instead of you",
    "MEANS_3": "Your 25 years of experience and A+ rating are invisible",

    # Page 4 - Issues
    "ISSUE_1_TITLE": "AI Systems Don't Know Who You Are",
    "ISSUE_1_BODY": "Your business has no 'identity' in AI databases - no Wikipedia page, no LinkedIn company page, minimal online presence beyond your website.",
    "ISSUE_1_CALLOUT": "Impact: Lost leads from 30-40% of people using AI to find services",

    "ISSUE_2_TITLE": "Your Website Has No Dates On Anything",
    "ISSUE_2_BODY": "Not a single page shows when it was published or last updated. AI systems assume undated content is stale.",
    "ISSUE_2_EXAMPLE": "Real example: Customer asks about 2026 prices - AI cites competitor's dated blog, ignores your undated page.",

    "ISSUE_3_TITLE": "20+ Testimonials Are Hidden From AI",
    "ISSUE_3_BODY": "You have 20+ customer testimonials but they're not marked up in a way AI systems can read.",
    "ISSUE_3_CALLOUT": "This is fixable in under an hour with proper schema markup.",

    "ISSUE_4_TITLE": "No Instructions for AI Systems",
    "ISSUE_4_BODY": "Your website has no llms.txt or ai.txt file telling AI systems what your business does.",
    "ISSUE_4_CALLOUT": "Adding this takes 30 minutes and immediately helps AI understand you.",

    "ISSUE_5_TITLE": "Service Pages Lack Detail",
    "ISSUE_5_BODY": "Your service pages are thin on content - AI needs detailed, specific information to recommend you.",
    "ISSUE_5_CALLOUT": "Expanding these pages helps both AI and human visitors.",

    "ISSUE_6_TITLE": "Missing Structured Data",
    "ISSUE_6_BODY": "AI systems look for schema.org markup to understand businesses. Yours has minimal markup.",
    "ISSUE_6_CALLOUT": "LocalBusiness schema should include services, areas, hours, reviews.",

    # Page 5 - What Happens If Nothing
    "NOTHING_SHORT_1": "Competitors who optimize will get recommended more often",
    "NOTHING_SHORT_2": "You'll continue missing leads from AI search (30-40% of queries)",
    "NOTHING_SHORT_3": "The gap between you and optimized competitors widens",
    "NOTHING_LONG_1": "AI search becomes the dominant way people find services",
    "NOTHING_LONG_2": "Businesses without AI visibility become invisible",
    "NOTHING_LONG_3": "Playing catch-up gets harder as competitors build authority",

    # Page 6 - Opportunity
    "PROJECTED": "85/100",
    "OPP_1_DESC": "Deploy AI configuration files (llms.txt, robots.txt updates)",
    "OPP_2_DESC": "Build verified presence on platforms AI trusts (LinkedIn, Wikipedia)",
    "OPP_3_DESC": "Resolve conflicting information across directories",
    "OPP_4_DESC": "Add dates, update content, show freshness signals",

    # Page 7 - Implementation
    "W1_SCORE": "65/100",
    "W2_SCORE": "72/100",
    "W3_SCORE": "80/100",
    "W4_SCORE": "85/100",

    # Page 8 - ROI
    "CUSTOMERS_PER_MONTH": "2-3",
    "MONTHLY_REV": "$1,000-6,000",
    "ANNUAL_IMPACT": "$12,000-72,000",

    # Page 10 - Before/After
    "BEFORE_LINE_1": "Customer: 'Hey ChatGPT, who should I call for sprinkler repair in Denver?'",
    "BEFORE_LINE_2": "ChatGPT: 'Here are some well-reviewed options:'",
    "BEFORE_LINE_3": "- GreenCo Irrigation (mentioned in multiple sources)",
    "BEFORE_LINE_4": "- Colorado Sprinkler Pros (4.8 stars, many reviews)",
    "BEFORE_LINE_5": "Your business: Not mentioned",

    "AFTER_LINE_1": "Customer: 'Hey ChatGPT, who should I call for sprinkler repair in Denver?'",
    "AFTER_LINE_2": "ChatGPT: 'Here are some well-reviewed options:'",
    "AFTER_LINE_3": "- Denver Sprinkler and Landscape (25+ years, BBB A+, serving Denver since 2011)",
    "AFTER_LINE_4": "- GreenCo Irrigation",
    "AFTER_LINE_5": "- Colorado Sprinkler Pros",
    "AFTER_LINE_6": "Your business: Mentioned FIRST with specific credibility signals",

    # FAQs
    "FAQ_1_Q": "Is this really necessary? My business is doing fine.",
    "FAQ_1_A": "Your business IS doing fine. But 30-40% of people now use AI to find services. That percentage is growing fast. The question isn't whether you need this - it's whether you want those leads going to you or your competitors.",
    "FAQ_2_Q": "How long until I see results?",
    "FAQ_2_A": "Quick wins (technical fixes) show impact within 2-4 weeks. Authority building takes 2-3 months. Full optimization typically takes 90 days to reach target score.",

    # Page 11 - Bottom Line
    "BOTTOM_LINE_1": "You've built an excellent business over 25 years.",
    "BOTTOM_LINE_2": "The only thing holding you back is that AI systems don't know about it yet.",
    "BOTTOM_LINE_CLOSER": "Let's fix that.",

    # Page 12
    "CLIENT_NAME_FULL": "Denver Sprinkler & Landscape"
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Use sample data for testing
        print("No JSON file provided, using sample data for testing...")
        data = SAMPLE_DATA
        output = "PeakwebGEOProposal-Sample.pdf"
    elif len(sys.argv) == 2:
        # Load JSON file
        json_path = sys.argv[1]
        with open(json_path, 'r') as f:
            data = json.load(f)
        output = f"PeakwebGEOProposal-{data.get('CLIENT_NAME', 'Output').replace(' ', '')}.pdf"
    else:
        json_path = sys.argv[1]
        output = sys.argv[2]
        with open(json_path, 'r') as f:
            data = json.load(f)

    fill_template(data, output)
