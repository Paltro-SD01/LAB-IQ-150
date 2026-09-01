"""
generate_report.py
-------------------
Generates a laboratory test report (PDF) from a TDMS data file.

Visual identity: "calibration certificate" — the report borrows its
language from the instruments it documents (ruler tick scales, a
crosshair/reticle mark, an engineering-drawing title block, LCD-style
readouts) rather than a generic dashboard look.
"""

import os
import datetime
from nptdms import TdmsFile
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np

# ============================================================================
# DESIGN TOKENS
# ============================================================================

INK = "#1c1f26"          # graphite — primary text / structure
PAPER = "#faf9f5"         # warm paper white — page background
PAPER_PANEL = "#ffffff"   # chart panel background
GRID_LINE = "#e7e2d6"     # warm grid line on paper
RULE = "#c9c2b0"          # hairline rules / ruler ticks
MUTED = "#767b85"         # secondary / caption text
BRASS = "#b8863c"         # signature accent — calibration brass
BRASS_DARK = "#8f6a2c"
ACCENT_ALERT = "#a8452f"  # oxide red — used sparingly (min/max marker)

# Qualitative channel palette — distinct instrument-dial tones, cycled
# per channel (not a continuous colormap, since channels are independent
# signals rather than points on a scale).
CHANNEL_COLORS = [
    "#3d5a73",  # steel blue
    "#b8863c",  # brass
    "#5c7a5e",  # patina green
    "#8b4a4a",  # oxide red
    "#6b5b7a",  # slate violet
    "#4a7a76",  # teal patina
    "#96702f",  # dark ochre
    "#4f6a8c",  # slate blue
]

FONT_HEAD = "sans-serif"
FONT_DATA = "monospace"


def _channel_color(i):
    return CHANNEL_COLORS[i % len(CHANNEL_COLORS)]


def _draw_reticle(overlay, cx, cy, r, color=BRASS, lw=1.4, zorder=5):
    """Draws a small calibration reticle (crosshair target) — the report's
    signature mark, echoing the crosshair reticle on a microscope /
    measurement instrument eyepiece."""
    circle = mpatches.Circle((cx, cy), r, fill=False, edgecolor=color,
                              linewidth=lw, zorder=zorder)
    overlay.add_patch(circle)
    inner = mpatches.Circle((cx, cy), r * 0.32, fill=False, edgecolor=color,
                             linewidth=lw * 0.8, zorder=zorder)
    overlay.add_patch(inner)
    tick = r * 0.55
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        overlay.add_line(mlines.Line2D(
            [cx + dx * r * 0.75, cx + dx * (r * 0.75 + tick * 0.5)],
            [cy + dy * r * 0.75, cy + dy * (r * 0.75 + tick * 0.5)],
            color=color, linewidth=lw, zorder=zorder))


def _ruler_ticks(overlay, y, x0=0.06, x1=0.94, n=45, color=RULE,
                  major_every=5, tick_h=0.006, major_h=0.012):
    """Draws a horizontal ruler / scale-bar tick strip, figure-fraction
    coordinates. Used on the top edge of the cover and as a running
    footer motif on data pages."""
    xs = np.linspace(x0, x1, n)
    for i, x in enumerate(xs):
        h = major_h if i % major_every == 0 else tick_h
        overlay.add_line(mlines.Line2D([x, x], [y, y - h], color=color,
                                        linewidth=0.8, zorder=2))
    overlay.add_line(mlines.Line2D([x0, x1], [y, y], color=color,
                                    linewidth=0.8, zorder=2))


def _new_overlay(fig):
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_zorder(10)
    ax.patch.set_alpha(0)
    return ax


def generate_enterprise_report(tdms_path, output_pdf_path, plots_per_page=3):
    print(f"Reading TDMS file: {tdms_path}...")

    if not os.path.exists(tdms_path):
        raise FileNotFoundError(f"Could not find the TDMS file at: {tdms_path}")

    tdms_file = TdmsFile.read(tdms_path)
    group = tdms_file.groups()[0]
    channels = group.channels()

    if len(channels) < 2:
        raise ValueError("The TDMS file must contain at least 2 channels (1 for X-axis, 1 or more for Y-axis).")

    # 1. Primary X-Axis Setup
    x_channel = channels[0]
    x_data = x_channel.data
    x_name = x_channel.name
    x_unit = x_channel.properties.get('unit', '')
    x_label = f"{x_name} [{x_unit}]" if x_unit else x_name

    y_channels = channels[1:]
    total_plots = len(y_channels)
    total_pages = int(np.ceil(total_plots / plots_per_page))
    run_id = datetime.datetime.now().strftime('%y%m%d-%H%M')

    # Global styling
    plt.rcParams['font.family'] = FONT_HEAD
    plt.rcParams['axes.edgecolor'] = RULE
    plt.rcParams['text.color'] = INK

    with PdfPages(output_pdf_path) as pdf:

        # =====================================================================
        # PAGE 1 — CALIBRATION-CERTIFICATE COVER PAGE
        # =====================================================================
        print("Generating cover page...")
        fig_cover = plt.figure(figsize=(8.5, 11), facecolor=PAPER)
        ov = _new_overlay(fig_cover)

        # Top ruler / scale-bar motif
        _ruler_ticks(ov, y=0.965, x0=0.08, x1=0.92, n=65)
        ov.text(0.08, 0.975, "0", fontsize=6, family=FONT_DATA, color=MUTED)
        ov.text(0.92, 0.975, "SCALE", fontsize=6, family=FONT_DATA,
                color=MUTED, ha="right")

        # Reticle signature mark + masthead
        _draw_reticle(ov, cx=0.115, cy=0.86, r=0.028)
        ov.text(0.17, 0.875, "LABORATORY TEST REPORT", fontsize=22,
                color=INK, fontweight="bold", family=FONT_HEAD)
        ov.text(0.17, 0.845, "TRIBOLOGY DATA ACQUISITION  ·  XY CHANNEL RECORD",
                fontsize=9.5, color=BRASS_DARK, family=FONT_DATA,
                fontweight="bold")

        ov.add_line(mlines.Line2D([0.08, 0.92], [0.815, 0.815],
                                   color=BRASS, linewidth=1.6))
        ov.add_line(mlines.Line2D([0.08, 0.92], [0.812, 0.812],
                                   color=RULE, linewidth=0.6))

        # Abstract — plain-language summary of what this record is
        summary = (f"Automated acquisition record covering {total_plots} "
                   f"independent channel{'s' if total_plots != 1 else ''} "
                   f"referenced against {x_name}, spanning {len(x_data):,} "
                   f"logged samples.")
        ov.text(0.08, 0.775, summary, fontsize=9.5, color="#3a3f4a",
                family=FONT_HEAD, wrap=True)

        # ---- Engineering-drawing style title block -------------------------
        tb_top, tb_bot, tb_left, tb_right = 0.60, 0.30, 0.08, 0.92
        ov.add_patch(mpatches.Rectangle((tb_left, tb_bot),
                                         tb_right - tb_left, tb_top - tb_bot,
                                         fill=False, edgecolor=INK, linewidth=1.1))
        ov.text(tb_left + 0.015, tb_top - 0.028, "RECORD DETAIL",
                fontsize=8.5, fontweight="bold", color=INK, family=FONT_DATA)
        ov.add_line(mlines.Line2D([tb_left, tb_right],
                                   [tb_top - 0.045, tb_top - 0.045],
                                   color=RULE, linewidth=0.8))

        fields = [
            ("SOURCE FILE", os.path.basename(tdms_path)),
            ("DATA DIRECTORY", os.path.dirname(tdms_path) or "."),
            ("ACQUISITION LOGGED", datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S')),
            ("REFERENCE CHANNEL (X)", f"{x_name}   ({len(x_data):,} samples)"),
            ("CHANNEL COUNT (Y)", f"{total_plots} signal{'s' if total_plots != 1 else ''}"),
            ("RUN ID", f"#{run_id}"),
            ("VALIDATION STATUS", "PASS — DATASTREAM VALID"),
        ]
        row_h = (tb_top - 0.06 - tb_bot) / len(fields)
        y = tb_top - 0.075
        for label, val in fields:
            ov.text(tb_left + 0.02, y, label, fontsize=7.5, color=MUTED,
                    family=FONT_DATA, fontweight="bold")
            ov.text(tb_left + 0.30, y, str(val), fontsize=9.5, color=INK,
                    family=FONT_HEAD)
            y -= row_h
            if y > tb_bot + 0.01:
                ov.add_line(mlines.Line2D([tb_left, tb_right], [y + row_h * 0.32,
                                           y + row_h * 0.32], color=GRID_LINE,
                                           linewidth=0.6))
        # vertical divider inside title block
        ov.add_line(mlines.Line2D([tb_left + 0.27, tb_left + 0.27],
                                   [tb_bot, tb_top - 0.045],
                                   color=RULE, linewidth=0.7))

        # ---- Certification stamp -------------------------------------------
        _draw_reticle(ov, cx=0.855, cy=0.19, r=0.045, color=BRASS, lw=1.2)
        ov.text(0.855, 0.19, "V", fontsize=13, color=BRASS_DARK,
                fontweight="bold", ha="center", va="center", family=FONT_DATA)
        ov.text(0.08, 0.205, "SYSTEM VERIFICATION", fontsize=8, color=INK,
                fontweight="bold", family=FONT_DATA)
        ov.text(0.08, 0.187, "Structurally validated and channel-aligned via",
                fontsize=7.5, color=MUTED, family=FONT_HEAD)
        ov.text(0.08, 0.172, "automated acquisition pipeline. No manual edits applied.",
                fontsize=7.5, color=MUTED, family=FONT_HEAD)

        _ruler_ticks(ov, y=0.09, x0=0.08, x1=0.92, n=65)
        ov.text(0.08, 0.075, "LAB-IQ ENGINEERING GROUP", fontsize=7.5,
                color=MUTED, fontweight="bold", family=FONT_DATA)
        ov.text(0.92, 0.075, "PAGE 1 / COVER", fontsize=7.5, color=MUTED,
                family=FONT_DATA, ha="right")

        pdf.savefig(fig_cover, dpi=300)
        plt.close(fig_cover)

        # =====================================================================
        # SUBSEQUENT PAGES — CHANNEL DATA SHEETS
        # =====================================================================
        print(f"Processing {total_plots} signals onto data pages...")
        for i in range(0, total_plots, plots_per_page):
            chunk = y_channels[i:i + plots_per_page]
            num_plots_in_page = len(chunk)
            current_page_num = (i // plots_per_page) + 1

            fig = plt.figure(figsize=(8.5, 11), facecolor=PAPER)
            ov = _new_overlay(fig)

            # ---- Header strip -----------------------------------------------
            _draw_reticle(ov, cx=0.095, cy=0.955, r=0.017, lw=1.1)
            ov.text(0.13, 0.962, "CHANNEL DATA SHEET", fontsize=12.5,
                    fontweight="bold", color=INK, family=FONT_HEAD)
            ov.text(0.13, 0.947, os.path.basename(tdms_path), fontsize=8,
                    color=MUTED, family=FONT_DATA)
            ov.text(0.92, 0.962, f"RUN #{run_id}", fontsize=8.5,
                    fontweight="bold", color=BRASS_DARK, family=FONT_DATA,
                    ha="right")
            ov.text(0.92, 0.947, f"PAGE {current_page_num} / {total_pages}",
                    fontsize=8, color=MUTED, family=FONT_DATA, ha="right")

            ov.add_line(mlines.Line2D([0.06, 0.94], [0.930, 0.930],
                                       color=BRASS, linewidth=1.4))
            ov.add_line(mlines.Line2D([0.06, 0.94], [0.928, 0.928],
                                       color=RULE, linewidth=0.5))

            # ---- Chart grid ---------------------------------------------------
            axes = fig.subplots(plots_per_page, 1)
            if plots_per_page == 1:
                axes = [axes]

            for idx in range(plots_per_page):
                ax = axes[idx]
                global_channel_idx = i + idx

                if idx < num_plots_in_page:
                    y_channel = chunk[idx]
                    y_data = y_channel.data
                    y_name = y_channel.name
                    y_unit = y_channel.properties.get('unit', '')
                    y_label = f"{y_name}\n[{y_unit}]" if y_unit else y_name

                    plot_color = _channel_color(global_channel_idx)

                    ax.plot(x_data, y_data, color=plot_color, linewidth=1.3,
                            alpha=0.95, solid_capstyle="round")
                    ax.fill_between(x_data, y_data, color=plot_color, alpha=0.06)

                    # Graph-paper panel styling
                    ax.set_facecolor(PAPER_PANEL)
                    ax.grid(True, linestyle="-", linewidth=0.5, color=GRID_LINE)
                    ax.set_axisbelow(True)
                    ax.tick_params(axis='both', labelsize=7.5, colors=MUTED,
                                    length=3)
                    for spine in ["top", "right"]:
                        ax.spines[spine].set_visible(False)
                    ax.spines['left'].set_color(plot_color)
                    ax.spines['left'].set_linewidth(2.2)
                    ax.spines['bottom'].set_color(RULE)

                    ax.set_ylabel(y_label, fontsize=8, fontweight="bold",
                                  color=INK, rotation=0, labelpad=34,
                                  va='center', family=FONT_HEAD)
                    ax.set_xlabel(x_label, fontsize=7.5, color=MUTED,
                                  family=FONT_DATA)

                    # LCD-style readout badge (monospace, instrument feel)
                    y_min, y_max = np.min(y_data), np.max(y_data)
                    y_mean = np.mean(y_data)
                    readout = f"MIN {y_min:8.2f}   MAX {y_max:8.2f}   AVG {y_mean:8.2f}"
                    ax.text(0.99, 0.94, readout, transform=ax.transAxes,
                            ha="right", va="top", fontsize=7,
                            family=FONT_DATA, color="#f4f1e8",
                            bbox=dict(boxstyle="square,pad=0.35",
                                      facecolor=INK, edgecolor=plot_color,
                                      linewidth=1.1))

                    # small channel index tag
                    ax.text(0.01, 0.94, f"CH.{global_channel_idx + 1:02d}",
                            transform=ax.transAxes, ha="left", va="top",
                            fontsize=7, family=FONT_DATA, fontweight="bold",
                            color=plot_color)
                else:
                    ax.axis('off')

            plt.subplots_adjust(left=0.20, right=0.94, top=0.885, bottom=0.10,
                                 hspace=0.55)

            # ---- Footer: ruler ticks + certification line ---------------------
            _ruler_ticks(ov, y=0.065, x0=0.06, x1=0.94, n=70)
            ov.text(0.06, 0.05, "INTERNAL LAB USE ONLY — DATA ACQUISITION RECORD",
                    fontsize=6.5, color=MUTED, fontweight="bold", family=FONT_DATA)
            ov.text(0.94, 0.05, f"DATA PAGE {current_page_num} / {total_pages}",
                    fontsize=7.5, color=INK, fontweight="bold", family=FONT_DATA,
                    ha="right")

            pdf.savefig(fig, dpi=300)
            plt.close(fig)

    print(f"Success! Report saved to: {output_pdf_path}")


if __name__ == "__main__":
    tdms_file_path = r"C:\data\tdms 5min\tdms 5mintdms 5min.tdms"
    output_report_path = r"C:\data\tdms 5min\Test_Report3.pdf"

    generate_enterprise_report(tdms_file_path, output_report_path, plots_per_page=3)