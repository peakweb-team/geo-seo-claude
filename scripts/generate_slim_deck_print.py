#!/usr/bin/env python3
"""
Peakweb GEO Snapshot — Slim 3-Page Pitch Deck (Print-Ready)

Derivative of generate_slim_deck.py tuned for commercial printing:
  - 9 pt bleed (≈ 0.125 in / 3 mm) on all sides — backgrounds extend past
    the trim edge so no white slivers appear after guillotine cutting
  - All text and logos remain at the original 0.75 in safe margin, well inside
    the 0.25–0.5 in safe-area requirement
  - Output page size: letter + bleed (630 × 810 pts)

The trim marks / media box follow the standard bleed convention:
    trim box  = 612 × 792 pts (letter)
    media box = 630 × 810 pts (letter + 2 × 9 pt bleed)

Usage:
    python3 generate_slim_deck_print.py                       # sample data
    python3 generate_slim_deck_print.py data.json             # custom client
    python3 generate_slim_deck_print.py data.json out.pdf     # custom output
"""

import json
import os
import sys

from reportlab.pdfgen import canvas

from generate_slim_deck import (
    DEFAULT_DATA,
    SlimDeckGenerator,
    register_fonts,
    # page geometry
    PAGE_WIDTH, PAGE_HEIGHT, MARGIN,
    # colours
    AQUAMARINE, DEEP_BLUE, STONE, WHITE,
)

# ─── Bleed constants ──────────────────────────────────────────────────────────
BLEED = 9                              # ≈ 0.125 in / 3 mm
BLEED_W = PAGE_WIDTH  + 2 * BLEED     # 630 pts
BLEED_H = PAGE_HEIGHT + 2 * BLEED     # 810 pts


class PrintSlimDeckGenerator(SlimDeckGenerator):
    """Print-ready variant: all full-width backgrounds extend into bleed zone."""

    # ── Canvas setup ──────────────────────────────────────────────────────────

    def generate(self):
        register_fonts()
        self.c = canvas.Canvas(self.output_path, pagesize=(BLEED_W, BLEED_H))
        # Shift origin so all inherited coordinates align with the trim box.
        # (0, 0) in our drawing space = bottom-left of the trim box.
        self.c.translate(BLEED, BLEED)
        self._page_1()
        self._page_2()
        self._page_3()
        self.c.save()
        print(f"Generated (print-ready with {BLEED}pt bleed): {self.output_path}")

    # ── Page initialisation ───────────────────────────────────────────────────

    def _new_page(self, bg=WHITE):
        if self._page_num > 0:
            self.c.showPage()
            # showPage() resets the graphics state — re-apply trim-box origin.
            self.c.translate(BLEED, BLEED)
        self._page_num += 1
        # Fill the full media box (trim + bleed zone on all sides).
        self.c.setFillColorRGB(*bg)
        self.c.rect(-BLEED, -BLEED, BLEED_W, BLEED_H, fill=1, stroke=0)

    # ── Header ────────────────────────────────────────────────────────────────

    def _draw_header(self, dark_bg=False, logo_path=None):
        """Header bar extended into top, left, and right bleed zones."""
        hdr_h = 42
        # Bleed-extended Deep Blue bar
        self.c.setFillColorRGB(*DEEP_BLUE)
        self.c.rect(-BLEED, PAGE_HEIGHT - hdr_h,
                    PAGE_WIDTH + 2 * BLEED, hdr_h + BLEED,
                    fill=1, stroke=0)
        # Logo and client text — delegate to parent (positions are at MARGIN =
        # 0.75 in, already well within the safe zone; no change needed).
        super()._draw_header(dark_bg, logo_path)
        # Re-extend the aquamarine accent stripe (parent drew trim-width only).
        self.c.setFillColorRGB(*AQUAMARINE)
        self.c.rect(-BLEED, PAGE_HEIGHT - hdr_h - 3,
                    PAGE_WIDTH + 2 * BLEED, 3,
                    fill=1, stroke=0)

    # ── Section title band ────────────────────────────────────────────────────

    def _section_title_band(self, title, y_top=747, band_h=50):
        """Stone section band extended into left and right bleed zones."""
        self.c.setFillColorRGB(*STONE)
        self.c.rect(-BLEED, y_top - band_h,
                    PAGE_WIDTH + 2 * BLEED, band_h,
                    fill=1, stroke=0)
        # Parent re-draws the same Stone rect (harmless) then adds title text
        # and underline — let it handle that without duplicating the logic.
        return super()._section_title_band(title, y_top, band_h)

    # ── Full-width inline bands (OPPORTUNITY on p1, amber risk on p2) ─────────

    def _full_width_rect(self, y, h, color):
        """Full-width rect extended into left and right bleed zones."""
        self.c.setFillColorRGB(*color)
        self.c.rect(-BLEED, y, PAGE_WIDTH + 2 * BLEED, h, fill=1, stroke=0)


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
        client_slug = (
            data.get("client_name", "Client")
            .replace(" & ", "-")
            .replace(" ", "-")
        )
        output = f"PeakwebGEOSnapshot-{client_slug}-Print.pdf"

    gen = PrintSlimDeckGenerator(data, output)
    gen.generate()


if __name__ == "__main__":
    main()
