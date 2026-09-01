"""
TDMS Professional PDF Report Generator  —  White / Light Theme
===============================================================
Each selected Y channel gets its own individual subplot (shared X axis).
Statistics table is pixel-perfectly aligned below the charts.

Report sections:
  1. Cover Page
  2. Table of Contents
  3. Executive Summary  (aggregated statistics for all plotted channels)
  4. Per-Plot Pages     (individual subplots per Y channel + stats table)
  5. Appendix           (full channel inventory)

Install:
    pip install nptdms matplotlib numpy scipy

Usage:
    GUI  : python tdms_report_generator.py
    CLI  : python tdms_report_generator.py path/to/file.tdms
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import AutoMinorLocator

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from nptdms import TdmsFile
except ImportError:
    print("ERROR: nptdms not installed.  Run:  pip install nptdms")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
#  REPORT METADATA
# ─────────────────────────────────────────────────────────────
REPORT_META = {
    "title":        "Tribological Test Analysis Report",
    "subtitle":     "TDMS Data Processing & Statistical Evaluation",
    "org":          "Tribology & Mechanical Testing Laboratory",
    "doc_no":       "RPT-TDMS-001",
    "revision":     "Rev A",
    "confidential": "CONFIDENTIAL",
}

# ─────────────────────────────────────────────────────────────
#  CHANNEL DEFINITIONS
# ─────────────────────────────────────────────────────────────
CHANNEL_LABELS = [
    "Time(Sec)",
    "Normal Load (N)",
    "Friction Force(N)",
    "Coefficient of Friction",
    "Depth (Microns)",
    "Speed (RPM)",
    "Frequency (Hz)",
    "Angle (Degree)",
    "Cyclic Friction Force (N)",
    "Cyclic Co-Efficient Friction Force",
    "Stage Temperature (Degree Celsius)",
    "Sample Temperature (Degree Celsius)",
    "Stroke Length (mm)",
    "Scratch Speed (mm/sec)",
    "Amb Humidity (%Rh)",
    "Amb Temperature (Deg C)",
    "Acoustic (mV)",
    "Mx(Nm)",
    "My(Nm)",
    "Mz (Nm)",
    "Humidity(%Rh)",
    "Sliding Distance (mm)",
    "Wear Track Diameter(mm)",
    "Fx(N)",
    "Fy(N)",
    "MTM Ball Speed(RPM)",
    "MTM Disc Speed (RPM)",
    "Entrainment Speed",
    "Slide Role",
    "Slip(%)",
    "Rotary Speed (m/sec)",
    "MTM Ball Speed (m/sec)",
    "MTM Disc Speed (m/sec)",
    "ECR (ohms)",
]

# ─────────────────────────────────────────────────────────────
#  COLOUR PALETTE  (white / light professional)
# ─────────────────────────────────────────────────────────────
C = {
    "page":         "#FFFFFF",
    "panel":        "#F8FAFC",
    "row_even":     "#FFFFFF",
    "row_odd":      "#F1F5F9",
    "header_bar":   "#1E3A5F",
    "cover_accent": "#1E3A5F",
    "txt_dark":     "#0F172A",
    "txt_body":     "#334155",
    "txt_muted":    "#64748B",
    "txt_light":    "#94A3B8",
    "txt_white":    "#FFFFFF",
    "accent_navy":  "#1E3A5F",
    "accent_blue":  "#2563EB",
    "accent_teal":  "#0D9488",
    "accent_sky":   "#BAE6FD",
    "accent_slate": "#CBD5E1",
    "border":       "#E2E8F0",
    "grid":         "#E2E8F0",
    "spine":        "#CBD5E1",
}

LINE_COLORS = [
    "#2563EB",   # royal blue
    "#0D9488",   # teal
    "#D97706",   # amber
    "#7C3AED",   # violet
    "#DC2626",   # crimson
    "#0891B2",   # cyan
    "#059669",   # emerald
    "#B45309",   # warm brown
    "#4338CA",   # indigo
    "#BE185D",   # rose
]


# ─────────────────────────────────────────────────────────────
#  TDMS LOADER
# ─────────────────────────────────────────────────────────────

def load_tdms(filepath: str) -> dict:
    tdms_file = TdmsFile.read(filepath)
    data = {}
    for group in tdms_file.groups():
        for channel in group.channels():
            try:
                arr = channel[:]
                if np.issubdtype(arr.dtype, np.number):
                    key = f"{group.name} / {channel.name}"
                    data[key] = arr.astype(np.float64)
            except Exception:
                pass
    return data


def best_match(label: str, available: list):
    def norm(s):
        return (s.lower()
                .replace(" ", "").replace("(", "")
                .replace(")", "").replace("/", ""))
    ln = norm(label)
    for avail in available:
        ch = avail.split(" / ")[-1] if " / " in avail else avail
        if ln in norm(ch) or norm(ch) in ln:
            return avail
    return None


# ─────────────────────────────────────────────────────────────
#  STATISTICS
# ─────────────────────────────────────────────────────────────

def compute_stats(arr: np.ndarray) -> dict:
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        nan = float("nan")
        return {k: nan for k in ["n", "mean", "median", "std", "variance",
                                  "min", "max", "range", "rms",
                                  "skewness", "kurtosis", "cv_pct"]}
    mean = float(np.mean(arr))
    std  = float(np.std(arr, ddof=1))  if len(arr) > 1 else 0.0
    var  = float(np.var(arr, ddof=1))  if len(arr) > 1 else 0.0
    mn   = float(np.min(arr))
    mx   = float(np.max(arr))
    rms  = float(np.sqrt(np.mean(arr ** 2)))
    cv   = (std / mean * 100) if mean != 0 else float("nan")
    if HAS_SCIPY and len(arr) > 3:
        skew = float(scipy_stats.skew(arr))
        kurt = float(scipy_stats.kurtosis(arr))
    else:
        skew = kurt = float("nan")
    return {
        "n": int(len(arr)), "mean": mean, "median": float(np.median(arr)),
        "std": std, "variance": var, "min": mn, "max": mx,
        "range": mx - mn, "rms": rms,
        "skewness": skew, "kurtosis": kurt, "cv_pct": cv,
    }


def fmt(v, dec=4):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    if isinstance(v, int):
        return f"{v:,}"
    mag = abs(v)
    if mag == 0:
        return "0.0000"
    if mag >= 1e6 or (0 < mag < 1e-3):
        return f"{v:.4e}"
    return f"{v:.{dec}f}"


# ─────────────────────────────────────────────────────────────
#  GLOBAL STYLE
# ─────────────────────────────────────────────────────────────

def apply_style():
    plt.rcParams.update({
        "figure.facecolor":  C["page"],
        "axes.facecolor":    C["panel"],
        "axes.edgecolor":    C["spine"],
        "axes.labelcolor":   C["txt_body"],
        "axes.titlecolor":   C["txt_dark"],
        "axes.grid":         True,
        "grid.color":        C["grid"],
        "grid.linestyle":    "--",
        "grid.linewidth":    0.5,
        "grid.alpha":        0.9,
        "xtick.color":       C["txt_muted"],
        "ytick.color":       C["txt_muted"],
        "xtick.labelsize":   7,
        "ytick.labelsize":   7,
        "font.family":       "DejaVu Sans",
        "text.color":        C["txt_body"],
        "lines.linewidth":   1.5,
        "legend.facecolor":  C["page"],
        "legend.edgecolor":  C["border"],
        "legend.labelcolor": C["txt_body"],
        "legend.fontsize":   7.5,
    })


# ─────────────────────────────────────────────────────────────
#  PAGE CHROME  (header + footer — on every page)
# ─────────────────────────────────────────────────────────────

def draw_page_chrome(fig, page_num: int, total_pages: int,
                     tdms_name: str, section: str = ""):
    # Navy header bar
    hdr = fig.add_axes([0, 0.945, 1, 0.055])
    hdr.set_facecolor(C["header_bar"])
    hdr.axis("off")
    hdr.text(0.012, 0.50, REPORT_META["title"],
             va="center", fontsize=9, fontweight="bold",
             color=C["txt_white"], transform=hdr.transAxes)
    hdr.text(0.50, 0.50, section[:80], va="center", ha="center",
             fontsize=8, color=C["accent_sky"], transform=hdr.transAxes)
    hdr.text(0.988, 0.50,
             f"{REPORT_META['doc_no']}  |  {REPORT_META['revision']}",
             va="center", ha="right", fontsize=7.5,
             color=C["accent_sky"], transform=hdr.transAxes)

    # Teal accent stripe below header
    stripe = fig.add_axes([0, 0.938, 1, 0.008])
    stripe.set_facecolor(C["accent_teal"])
    stripe.axis("off")

    # Footer
    ftr = fig.add_axes([0, 0, 1, 0.030])
    ftr.set_facecolor(C["panel"])
    ftr.axis("off")
    ftr.plot([0, 1], [0.95, 0.95], color=C["accent_slate"], lw=0.8,
             transform=ftr.transAxes, clip_on=False)
    ftr.text(0.012, 0.40, f"Source: {tdms_name}",
             va="center", fontsize=6.5, color=C["txt_light"],
             transform=ftr.transAxes)
    ftr.text(0.50, 0.40,
             f"Generated: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}  |  "
             f"{REPORT_META['confidential']}",
             va="center", ha="center", fontsize=6.5,
             color=C["txt_light"], transform=ftr.transAxes)
    ftr.text(0.988, 0.40, f"Page {page_num} of {total_pages}",
             va="center", ha="right", fontsize=7,
             color=C["txt_muted"], transform=ftr.transAxes)


# ─────────────────────────────────────────────────────────────
#  PAGE 1 — COVER
# ─────────────────────────────────────────────────────────────

def make_cover(pdf: PdfPages, tdms_path: str, plots_config: list):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    ax  = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(C["page"])
    ax.axis("off")

    # Top navy band
    ax.add_patch(mpatches.FancyBboxPatch(
        (0, 0.80), 1, 0.20, boxstyle="square,pad=0",
        fc=C["cover_accent"], ec="none", transform=ax.transAxes, zorder=1))
    # Diagonal corner
    pts = np.array([[0.75, 0.80], [1.0, 0.80], [1.0, 1.0], [0.88, 1.0]])
    ax.add_patch(mpatches.Polygon(pts, closed=True,
                                  fc="#162D4A", ec="none",
                                  transform=ax.transAxes, zorder=2))
    # Teal stripe
    ax.add_patch(mpatches.FancyBboxPatch(
        (0, 0.796), 1, 0.007, boxstyle="square,pad=0",
        fc=C["accent_teal"], ec="none", transform=ax.transAxes, zorder=3))

    ax.text(0.055, 0.925, REPORT_META["title"],
            fontsize=22, fontweight="bold",
            color=C["txt_white"], transform=ax.transAxes, zorder=4)
    ax.text(0.055, 0.855, REPORT_META["subtitle"],
            fontsize=11.5, color=C["accent_sky"],
            transform=ax.transAxes, zorder=4)

    # Metadata table (left side)
    rows = [
        ("Document No.",   REPORT_META["doc_no"]),
        ("Revision",       REPORT_META["revision"]),
        ("Organization",   REPORT_META["org"]),
        ("Source File",    os.path.basename(tdms_path)),
        ("Report Date",    datetime.now().strftime("%d %B %Y")),
        ("Total Plots",    str(len(plots_config))),
        ("Classification", REPORT_META["confidential"]),
    ]
    y_cur = 0.735
    for i, (label, value) in enumerate(rows):
        bg = C["row_even"] if i % 2 == 0 else C["row_odd"]
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.040, y_cur - 0.012), 0.440, 0.034,
            boxstyle="square,pad=0", fc=bg, ec=C["border"],
            linewidth=0.4, transform=ax.transAxes, zorder=0))
        ax.text(0.055, y_cur, label + ":", fontsize=8.5,
                color=C["txt_muted"], fontweight="bold",
                transform=ax.transAxes)
        ax.text(0.215, y_cur, value, fontsize=8.5,
                color=C["txt_dark"], transform=ax.transAxes)
        y_cur -= 0.038

    # Plot index panel (right side)
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.520, 0.080), 0.445, 0.700,
        boxstyle="round,pad=0.005",
        fc=C["panel"], ec=C["border"], linewidth=0.7,
        transform=ax.transAxes, zorder=0))

    ax.text(0.537, 0.748, "PLOT  INDEX",
            fontsize=10, fontweight="bold",
            color=C["accent_blue"], transform=ax.transAxes)
    ax.plot([0.527, 0.960], [0.732, 0.732],
            color=C["accent_teal"], lw=1.2,
            transform=ax.transAxes, clip_on=False)

    col_xs = [0.537, 0.570, 0.660]
    row_y  = 0.714
    for hd, cx in zip(["No.", "X Parameter", "Y Parameter(s)"], col_xs):
        ax.text(cx, row_y, hd, fontsize=7.5, fontweight="bold",
                color=C["txt_muted"], transform=ax.transAxes)
    row_y -= 0.018
    ax.plot([0.527, 0.960], [row_y, row_y],
            color=C["border"], lw=0.5,
            transform=ax.transAxes, clip_on=False)

    for i, cfg in enumerate(plots_config):
        row_y -= 0.030
        if row_y < 0.095:
            ax.text(col_xs[0], row_y + 0.010,
                    f"… +{len(plots_config)-i} more",
                    fontsize=6.5, color=C["txt_muted"],
                    transform=ax.transAxes)
            break
        bg = C["row_even"] if i % 2 == 0 else C["row_odd"]
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.525, row_y - 0.010), 0.434, 0.026,
            boxstyle="square,pad=0", fc=bg, ec="none",
            transform=ax.transAxes, zorder=0))
        ax.text(col_xs[0], row_y, str(i + 1), fontsize=7.5,
                color=C["txt_muted"], transform=ax.transAxes)
        ax.text(col_xs[1], row_y, cfg["x_label"][:18],
                fontsize=7.5, color=C["txt_body"], transform=ax.transAxes)
        ax.text(col_xs[2], row_y,
                ", ".join(cfg["y_labels"])[:38],
                fontsize=7, color=C["txt_body"], transform=ax.transAxes)

    # Bottom footer bar
    ax.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 0.042, boxstyle="square,pad=0",
        fc=C["panel"], ec="none", transform=ax.transAxes, zorder=1))
    ax.plot([0, 1], [0.042, 0.042], color=C["border"], lw=0.8,
            transform=ax.transAxes, clip_on=False)
    ax.text(0.500, 0.020,
            f"{REPORT_META['doc_no']}  |  {REPORT_META['revision']}  |  "
            f"{REPORT_META['confidential']}  |  Page 1",
            ha="center", va="center", fontsize=7,
            color=C["txt_light"], transform=ax.transAxes, zorder=2)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
#  PAGE 2 — TABLE OF CONTENTS
# ─────────────────────────────────────────────────────────────

def make_toc(pdf: PdfPages, plots_config: list,
             total_pages: int, tdms_name: str):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    draw_page_chrome(fig, 2, total_pages, tdms_name, "Table of Contents")

    ax = fig.add_axes([0.07, 0.06, 0.86, 0.86])
    ax.set_facecolor(C["page"])
    ax.axis("off")

    ax.text(0, 0.965, "TABLE OF CONTENTS",
            fontsize=14, fontweight="bold",
            color=C["accent_navy"], transform=ax.transAxes)
    ax.add_patch(mpatches.FancyBboxPatch(
        (-0.01, 0.935), 1.02, 0.006,
        boxstyle="square,pad=0", fc=C["accent_teal"], ec="none",
        transform=ax.transAxes))

    sections = [
        ("1.",   "Cover Page",              "1",  False),
        ("2.",   "Table of Contents",       "2",  False),
        ("3.",   "Executive Summary",       "3",  False),
        ("4.",   "Measurement Plots",       "4",  False),
    ]
    for i, cfg in enumerate(plots_config):
        y_lbl = ", ".join(cfg["y_labels"])
        sections.append((
            f"  4.{i+1}.",
            f"Plot {i+1}:  {cfg['x_label']}  →  {y_lbl[:52]}",
            str(5 + i), True,
        ))
    sections.append(("5.", "Appendix – Channel Inventory",
                     str(5 + len(plots_config)), False))

    row_y = 0.895
    for i, (num, title, page, is_sub) in enumerate(sections):
        row_y -= 0.050 if not is_sub else 0.042
        bg = C["row_odd"] if i % 2 == 0 else C["row_even"]
        ax.add_patch(mpatches.FancyBboxPatch(
            (-0.01, row_y - 0.015), 1.02, 0.038,
            boxstyle="square,pad=0", fc=bg, ec=C["border"],
            linewidth=0.25, transform=ax.transAxes))
        fs     = 9   if not is_sub else 8.5
        fw     = "bold" if not is_sub else "normal"
        color  = C["txt_dark"] if not is_sub else C["txt_body"]
        indent = 0.0 if not is_sub else 0.035
        ax.text(indent,        row_y, num,   fontsize=fs, fontweight=fw,
                color=color, transform=ax.transAxes)
        ax.text(indent + 0.07, row_y, title, fontsize=fs,
                color=color, transform=ax.transAxes)
        ax.text(1.00,          row_y, page,  fontsize=fs, fontweight=fw,
                color=C["accent_blue"], ha="right",
                transform=ax.transAxes)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
#  PAGE 3 — EXECUTIVE SUMMARY
# ─────────────────────────────────────────────────────────────

def make_executive_summary(pdf: PdfPages, all_stats: list,
                            total_pages: int, tdms_name: str):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    draw_page_chrome(fig, 3, total_pages, tdms_name, "Executive Summary")

    ax = fig.add_axes([0.04, 0.05, 0.92, 0.87])
    ax.set_facecolor(C["page"])
    ax.axis("off")

    ax.text(0, 0.960, "3.  EXECUTIVE SUMMARY",
            fontsize=13, fontweight="bold",
            color=C["accent_navy"], transform=ax.transAxes)
    ax.add_patch(mpatches.FancyBboxPatch(
        (-0.01, 0.930), 1.02, 0.005, boxstyle="square,pad=0",
        fc=C["accent_teal"], ec="none", transform=ax.transAxes))
    ax.text(0, 0.908,
            "Statistical overview of all measured channels included in this report.  "
            "All values are computed on finite (non-NaN) data points only.",
            fontsize=8.5, color=C["txt_muted"], transform=ax.transAxes)

    col_heads = ["Channel / Parameter", "N",
                 "Mean", "Std Dev", "Variance",
                 "Min", "Max", "Range", "RMS", "CV (%)"]
    col_x     = [0.000, 0.310, 0.375, 0.445,
                 0.515, 0.585, 0.650, 0.718, 0.788, 0.870]
    col_align = ["l", "r", "r", "r", "r", "r", "r", "r", "r", "r"]

    # Table header
    row_y = 0.875
    ax.add_patch(mpatches.FancyBboxPatch(
        (-0.01, row_y - 0.014), 1.02, 0.040,
        boxstyle="square,pad=0", fc=C["accent_navy"], ec="none",
        transform=ax.transAxes))
    for hd, cx, ca in zip(col_heads, col_x, col_align):
        ax.text(cx, row_y, hd, fontsize=7.5, fontweight="bold",
                color=C["txt_white"], transform=ax.transAxes,
                ha="left" if ca == "l" else "right")

    row_y -= 0.038
    for i, entry in enumerate(all_stats):
        row_y -= 0.038
        if row_y < 0.04:
            ax.text(0, row_y + 0.012,
                    f"  … {len(all_stats)-i} more channels on individual plot pages",
                    fontsize=7, color=C["txt_muted"],
                    transform=ax.transAxes)
            break
        s  = entry["stats"]
        bg = C["row_even"] if i % 2 == 0 else C["row_odd"]
        ax.add_patch(mpatches.FancyBboxPatch(
            (-0.01, row_y - 0.012), 1.02, 0.034,
            boxstyle="square,pad=0", fc=bg, ec=C["border"],
            linewidth=0.2, transform=ax.transAxes))
        values = [
            entry["label"][:42], fmt(s["n"]), fmt(s["mean"]),
            fmt(s["std"]), fmt(s["variance"]), fmt(s["min"]),
            fmt(s["max"]), fmt(s["range"]), fmt(s["rms"]),
            fmt(s["cv_pct"], 2),
        ]
        for val, cx, ca in zip(values, col_x, col_align):
            ax.text(cx, row_y, val, fontsize=7.5,
                    color=C["txt_body"], transform=ax.transAxes,
                    ha="left" if ca == "l" else "right")

    ax.text(0, 0.022,
            "CV = Coefficient of Variation = (Std Dev / |Mean|) × 100.  "
            "N/A = insufficient data or mean ≈ 0.",
            fontsize=6.8, color=C["txt_light"], transform=ax.transAxes)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
#  SECTION DIVIDER PAGE
# ─────────────────────────────────────────────────────────────

def make_section_divider(pdf: PdfPages, section_num: str, title: str,
                         subtitle: str, page_num: int, total_pages: int,
                         tdms_name: str):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    draw_page_chrome(fig, page_num, total_pages, tdms_name, title)

    ax = fig.add_axes([0, 0.10, 1, 0.83])
    ax.set_facecolor(C["page"])
    ax.axis("off")

    ax.text(0.50, 0.45, section_num, fontsize=160, fontweight="bold",
            color="#F1F5F9", ha="center", va="center",
            transform=ax.transAxes, zorder=0)
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.25, 0.58), 0.50, 0.010, boxstyle="square,pad=0",
        fc=C["accent_teal"], ec="none", transform=ax.transAxes, zorder=1))
    ax.text(0.50, 0.70, f"Section {section_num}", fontsize=11,
            color=C["txt_muted"], ha="center",
            transform=ax.transAxes, zorder=2)
    ax.text(0.50, 0.63, title, fontsize=20, fontweight="bold",
            color=C["accent_navy"], ha="center",
            transform=ax.transAxes, zorder=2)
    ax.text(0.50, 0.52, subtitle, fontsize=11, color=C["txt_muted"],
            ha="center", transform=ax.transAxes, zorder=2)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
#  PER-PLOT PAGE — individual subplot per Y channel
# ─────────────────────────────────────────────────────────────

def make_plot_page(pdf: PdfPages,
                   x_data:      np.ndarray,
                   y_datasets:  list,          # [(label, array), …]
                   x_label:     str,
                   plot_num:    int,
                   page_num:    int,
                   total_pages: int,
                   tdms_name:   str):
    """
    Each Y channel gets its own subplot.
    All subplots share the same X axis.
    A statistics table sits below the chart area.
    """
    n_y = len(y_datasets)

    # ── Subplot grid based on number of Y channels
    if   n_y == 1: nrows, ncols = 1, 1
    elif n_y == 2: nrows, ncols = 2, 1
    elif n_y == 3: nrows, ncols = 3, 1
    elif n_y == 4: nrows, ncols = 2, 2
    elif n_y <= 6: nrows, ncols = 3, 2
    else:          nrows, ncols = 4, 2   # max 8 on one page

    n_visible = min(n_y, nrows * ncols)

    # ── Vertical space split between charts and stats
    if n_y <= 2:
        chart_top, chart_bot = 0.930, 0.380
        stats_top, stats_bot = 0.345, 0.042
    elif n_y <= 4:
        chart_top, chart_bot = 0.930, 0.340
        stats_top, stats_bot = 0.305, 0.042
    else:
        chart_top, chart_bot = 0.930, 0.295
        stats_top, stats_bot = 0.260, 0.042

    # ── Figure
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    sec = f"4.{plot_num}  Plot {plot_num}  —  {x_label}"
    draw_page_chrome(fig, page_num, total_pages, tdms_name, sec)

    # ── Overall plot title
    y_names = ", ".join(l for l, _ in y_datasets[:3])
    if n_y > 3:
        y_names += f"  +{n_y-3} more"
    fig.text(0.52, chart_top + 0.003,
             f"Plot {plot_num}:   {y_names}   vs   {x_label}",
             ha="center", va="bottom",
             fontsize=10, fontweight="bold", color=C["txt_dark"])

    # ── GridSpec for subplots
    hspace = 0.10 if ncols == 1 else 0.20
    wspace = 0.22 if ncols  > 1 else 0.0
    gs = GridSpec(nrows, ncols, figure=fig,
                  left=0.08,  right=0.96,
                  top=chart_top, bottom=chart_bot,
                  hspace=hspace, wspace=wspace)

    chart_axes = []
    shared_x   = None
    for idx in range(n_visible):
        r, c = divmod(idx, ncols)
        if shared_x is None:
            ax = fig.add_subplot(gs[r, c])
            shared_x = ax
        else:
            ax = fig.add_subplot(gs[r, c], sharex=shared_x)
        chart_axes.append(ax)

    # ── Draw each individual subplot
    for idx, ax in enumerate(chart_axes):
        y_label, y_data = y_datasets[idx]
        color  = LINE_COLORS[idx % len(LINE_COLORS)]
        n      = min(len(x_data), len(y_data))
        xs, ys = x_data[:n], y_data[:n]

        # Axes styling
        ax.set_facecolor(C["panel"])
        for sp in ax.spines.values():
            sp.set_color(C["spine"])
            sp.set_linewidth(0.5)
        ax.grid(True, color=C["grid"], linestyle="--",
                linewidth=0.5, alpha=0.85)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        ax.tick_params(which="minor", length=2.5, color=C["border"])
        ax.tick_params(axis="both", colors=C["txt_muted"], labelsize=7)

        # Hide X tick labels on non-bottom rows to avoid clutter
        is_last_row = ((idx // ncols) == nrows - 1) or (idx == n_visible - 1)
        if not is_last_row:
            plt.setp(ax.get_xticklabels(), visible=False)
            ax.tick_params(axis="x", length=0)

        # Plot data line + fill
        ax.plot(xs, ys, color=color, linewidth=1.5,
                alpha=0.88, zorder=3, solid_capstyle="round")
        ax.fill_between(xs, ys, alpha=0.08, color=color, zorder=2)

        # Mean reference line
        mean_val = float(np.nanmean(ys))
        ax.axhline(y=mean_val, color=color, linewidth=0.85,
                   linestyle=":", alpha=0.65, zorder=4)

        # Y axis label (colored, channel name)
        ax.set_ylabel(y_label[:26], fontsize=7.5, labelpad=4,
                      color=color, fontweight="bold")

        # Channel name badge — top-left
        ax.text(0.010, 0.96, y_label,
                fontsize=6.8, color=color, fontweight="bold",
                transform=ax.transAxes, va="top",
                bbox=dict(boxstyle="round,pad=0.25", fc="white",
                          ec=color, lw=0.6, alpha=0.90))

        # Mean value badge — top-right
        ax.text(0.990, 0.96, f"μ = {fmt(mean_val, 4)}",
                fontsize=6.8, color=color,
                transform=ax.transAxes, va="top", ha="right",
                bbox=dict(boxstyle="round,pad=0.25", fc="white",
                          ec=color, lw=0.5, alpha=0.85))

        # X label only on bottom-row axes
        if is_last_row:
            ax.set_xlabel(x_label, fontsize=8.5, labelpad=5,
                          color=C["txt_body"])

    # ── STATISTICS TABLE ─────────────────────────────────────
    stats_ax = fig.add_axes([0.03, stats_bot,
                             0.94, stats_top - stats_bot])
    stats_ax.set_facecolor(C["page"])
    stats_ax.axis("off")

    stat_defs = [
        ("n",        "N  (Samples)"),
        ("mean",     "Mean"),
        ("median",   "Median"),
        ("std",      "Std Deviation  (σ)"),
        ("variance", "Variance  (σ²)"),
        ("min",      "Minimum"),
        ("max",      "Maximum"),
        ("range",    "Range  (Max − Min)"),
        ("rms",      "RMS"),
        ("cv_pct",   "CV  (%)"),
    ]
    n_stat_rows = len(stat_defs)

    # Pre-compute all channel stats
    ch_stats = [compute_stats(arr) for _, arr in y_datasets]

    # Column layout constants
    LABEL_FRAC  = 0.160              # fraction for row-label column
    DATA_FRAC   = (1.0 - LABEL_FRAC) / n_y   # per-channel column width
    INNER_PAD   = 0.006              # left padding inside each cell

    # ── Navy header band
    HDR_H = 0.115
    stats_ax.add_patch(mpatches.FancyBboxPatch(
        (0.0, 1.0 - HDR_H), 1.0, HDR_H,
        boxstyle="square,pad=0",
        fc=C["accent_navy"], ec="none",
        transform=stats_ax.transAxes, zorder=2))
    stats_ax.text(INNER_PAD, 1.0 - HDR_H * 0.5,
                  "Statistical Summary",
                  va="center", fontsize=8.5, fontweight="bold",
                  color=C["txt_white"], transform=stats_ax.transAxes, zorder=3)

    # Per-channel column header cells (colored)
    for ci, (y_label, _) in enumerate(y_datasets):
        cx = LABEL_FRAC + ci * DATA_FRAC
        col_color = LINE_COLORS[ci % len(LINE_COLORS)]
        # Light color band behind channel name
        stats_ax.add_patch(mpatches.FancyBboxPatch(
            (cx + 0.001, 1.0 - HDR_H + 0.002),
            DATA_FRAC - 0.003, HDR_H - 0.004,
            boxstyle="square,pad=0",
            fc=col_color, ec="none", alpha=0.14,
            transform=stats_ax.transAxes, zorder=1))
        stats_ax.text(cx + INNER_PAD, 1.0 - HDR_H * 0.5,
                      y_label[:20],
                      va="center", fontsize=7.5, fontweight="bold",
                      color=col_color,
                      transform=stats_ax.transAxes, zorder=3)

    # ── Data rows
    ROW_H = (1.0 - HDR_H) / n_stat_rows

    for ri, (sk, sl) in enumerate(stat_defs):
        ry_top = 1.0 - HDR_H - ri * ROW_H        # top of this row
        ry_ctr = ry_top - ROW_H * 0.50            # vertical centre

        bg = C["row_even"] if ri % 2 == 0 else C["row_odd"]

        # Full-row background
        stats_ax.add_patch(mpatches.FancyBboxPatch(
            (0.0, ry_top - ROW_H), 1.0, ROW_H,
            boxstyle="square,pad=0", fc=bg,
            ec=C["border"], linewidth=0.20,
            transform=stats_ax.transAxes))

        # Row label
        stats_ax.text(INNER_PAD, ry_ctr, sl,
                      va="center", fontsize=7.5,
                      color=C["txt_body"],
                      transform=stats_ax.transAxes)

        # Vertical divider — end of label column
        stats_ax.plot([LABEL_FRAC, LABEL_FRAC],
                      [ry_top - ROW_H, ry_top],
                      color=C["accent_slate"], lw=0.7,
                      transform=stats_ax.transAxes, clip_on=False)

        # Data cells
        for ci, s in enumerate(ch_stats):
            cx = LABEL_FRAC + ci * DATA_FRAC
            dec = 5 if sk == "variance" else 4
            val = fmt(s[sk], dec)

            stats_ax.text(cx + INNER_PAD, ry_ctr, val,
                          va="center", fontsize=7.5,
                          color=C["txt_dark"],
                          transform=stats_ax.transAxes)

            # Vertical divider between data columns (not after last)
            if ci < n_y - 1:
                x_div = cx + DATA_FRAC
                stats_ax.plot([x_div, x_div],
                              [ry_top - ROW_H, ry_top],
                              color=C["border"], lw=0.4,
                              transform=stats_ax.transAxes, clip_on=False)

    # Outer border around entire stats block
    stats_ax.add_patch(mpatches.FancyBboxPatch(
        (0.0, 0.0), 1.0, 1.0, boxstyle="square,pad=0",
        fc="none", ec=C["accent_slate"], linewidth=0.8,
        transform=stats_ax.transAxes))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
#  APPENDIX
# ─────────────────────────────────────────────────────────────

def make_appendix(pdf: PdfPages, raw_data: dict,
                  page_num: int, total_pages: int, tdms_name: str):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    draw_page_chrome(fig, page_num, total_pages, tdms_name,
                     "Appendix – Channel Inventory")

    ax = fig.add_axes([0.04, 0.05, 0.92, 0.87])
    ax.set_facecolor(C["page"])
    ax.axis("off")

    ax.text(0, 0.960, "5.  APPENDIX — CHANNEL INVENTORY",
            fontsize=13, fontweight="bold",
            color=C["accent_navy"], transform=ax.transAxes)
    ax.add_patch(mpatches.FancyBboxPatch(
        (-0.01, 0.930), 1.02, 0.005, boxstyle="square,pad=0",
        fc=C["accent_teal"], ec="none", transform=ax.transAxes))
    ax.text(0, 0.905,
            f"All {len(raw_data)} numeric channels detected in the source TDMS file.",
            fontsize=8.5, color=C["txt_muted"], transform=ax.transAxes)

    col_heads = ["#", "Channel Key  (Group / Name)",
                 "Samples", "Min", "Mean", "Max", "Std Dev"]
    col_x     = [0.000, 0.040, 0.640, 0.710, 0.780, 0.848, 0.918]

    row_y = 0.875
    ax.add_patch(mpatches.FancyBboxPatch(
        (-0.01, row_y - 0.014), 1.02, 0.040,
        boxstyle="square,pad=0", fc=C["accent_navy"], ec="none",
        transform=ax.transAxes))
    for hd, cx in zip(col_heads, col_x):
        ax.text(cx, row_y, hd, fontsize=7.5, fontweight="bold",
                color=C["txt_white"], transform=ax.transAxes)
    row_y -= 0.038

    for i, (key, arr) in enumerate(raw_data.items()):
        row_y -= 0.034
        if row_y < 0.03:
            ax.text(0, row_y + 0.010,
                    f"  … and {len(raw_data)-i} more channels",
                    fontsize=7, color=C["txt_muted"],
                    transform=ax.transAxes)
            break
        a  = arr[np.isfinite(arr)]
        bg = C["row_even"] if i % 2 == 0 else C["row_odd"]
        ax.add_patch(mpatches.FancyBboxPatch(
            (-0.01, row_y - 0.010), 1.02, 0.030,
            boxstyle="square,pad=0", fc=bg, ec=C["border"],
            linewidth=0.2, transform=ax.transAxes))
        vals = [
            str(i + 1), key[:62], f"{len(a):,}",
            fmt(float(np.min(a))  if len(a) else float("nan"), 3),
            fmt(float(np.mean(a)) if len(a) else float("nan"), 3),
            fmt(float(np.max(a))  if len(a) else float("nan"), 3),
            fmt(float(np.std(a))  if len(a) else float("nan"), 3),
        ]
        for val, cx in zip(vals, col_x):
            ax.text(cx, row_y, val, fontsize=7.5,
                    color=C["txt_body"], transform=ax.transAxes)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
#  MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────

def generate_pdf(tdms_path: str, plots_config: list, output_path: str):
    print(f"\n[+] Loading TDMS: {tdms_path}")
    raw_data = load_tdms(tdms_path)
    avail    = list(raw_data.keys())
    print(f"    {len(avail)} numeric channels found:")
    for ch in avail:
        print(f"      • {ch}  ({len(raw_data[ch])} samples)")

    # Resolve channel names
    resolved_plots = []
    for cfg in plots_config:
        x_key = best_match(cfg["x_label"], avail)
        if x_key is None:
            print(f"[!] X '{cfg['x_label']}' not found — plot skipped.")
            continue
        y_datasets = []
        for y_lbl in cfg["y_labels"]:
            y_key = best_match(y_lbl, avail)
            if y_key:
                y_datasets.append((y_lbl, raw_data[y_key]))
                print(f"    ✓ Matched Y '{y_lbl}' → '{y_key}'")
            else:
                print(f"    [!] Y '{y_lbl}' not found — skipped.")
        if y_datasets:
            resolved_plots.append({
                "x_label":    cfg["x_label"],
                "x_data":     raw_data[x_key],
                "y_datasets": y_datasets,
            })

    if not resolved_plots:
        print("[!] No valid plot configurations resolved. Check channel names.")
        return

    # Executive summary stats
    seen = {}
    for rp in resolved_plots:
        for (lbl, arr) in rp["y_datasets"]:
            if lbl not in seen:
                seen[lbl] = arr
    all_stats = [{"label": lbl, "stats": compute_stats(arr)}
                 for lbl, arr in seen.items()]

    # Total page count:
    # cover + toc + exec + section4 + plots + section5 + appendix
    total_pages = 6 + len(resolved_plots)
    tdms_name   = os.path.basename(tdms_path)

    apply_style()

    with PdfPages(output_path) as pdf:
        print("[+] Rendering: Cover…")
        make_cover(pdf, tdms_path, plots_config)

        print("[+] Rendering: Table of Contents…")
        make_toc(pdf, plots_config, total_pages, tdms_name)

        print("[+] Rendering: Executive Summary…")
        make_executive_summary(pdf, all_stats, total_pages, tdms_name)

        make_section_divider(pdf, "4", "Measurement Plots",
                             "Individual X–Y subplots with statistical evaluation",
                             4, total_pages, tdms_name)

        for pi, rp in enumerate(resolved_plots, 1):
            y_names = ", ".join(l for l, _ in rp["y_datasets"])
            print(f"[+] Rendering: Plot {pi}/{len(resolved_plots)} "
                  f"({rp['x_label']} → {y_names})…")
            make_plot_page(
                pdf,
                rp["x_data"], rp["y_datasets"], rp["x_label"],
                pi, 4 + pi, total_pages, tdms_name)

        app_page = 5 + len(resolved_plots)
        make_section_divider(pdf, "5", "Appendix",
                             "Full channel inventory from TDMS file",
                             app_page, total_pages, tdms_name)
        make_appendix(pdf, raw_data, app_page + 1, total_pages, tdms_name)

        d = pdf.infodict()
        d["Title"]        = REPORT_META["title"]
        d["Author"]       = REPORT_META["org"]
        d["Subject"]      = tdms_name
        d["Keywords"]     = "TDMS tribology friction wear statistics"
        d["CreationDate"] = datetime.now().strftime("D:%Y%m%d%H%M%S")

    print(f"\n✅  Report saved → {output_path}\n")


# ─────────────────────────────────────────────────────────────
#  TKINTER GUI
# ─────────────────────────────────────────────────────────────

GUI_BG   = "#F8FAFC"
GUI_CARD = "#EFF6FF"
GUI_HDR  = "#1E3A5F"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TDMS Professional Report Generator")
        self.configure(bg=GUI_BG)
        self.geometry("960x810")
        self.resizable(True, True)
        self._plots     = []
        self._tdms_path = None
        self._build_ui()

    def _btn(self, parent, text, cmd,
             bg=C["accent_blue"], hbg="#1D4ED8", fs=10, **kw):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg="white", activebackground=hbg,
                      activeforeground="white", relief="flat",
                      font=("Segoe UI", fs, "bold"),
                      padx=14, pady=6, cursor="hand2", bd=0, **kw)
        b.bind("<Enter>", lambda e: b.config(bg=hbg))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=GUI_HDR, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="TDMS Professional Report Generator",
                 font=("Segoe UI", 16, "bold"),
                 bg=GUI_HDR, fg="white").pack()
        tk.Label(hdr,
                 text="Tribology & Test Measurement — "
                      "Each Y channel rendered as a separate plot",
                 font=("Segoe UI", 9), bg=GUI_HDR, fg="#BAE6FD").pack()

        body = tk.Frame(self, bg=GUI_BG, padx=24, pady=14)
        body.pack(fill="both", expand=True)

        # File selection
        self._tdms_var = tk.StringVar(value="No TDMS file selected…")
        self._out_var  = tk.StringVar(value="")
        for label, var, cmd in [
            ("📂  Open TDMS File", self._tdms_var, self._pick_tdms),
            ("💾  Output PDF",     self._out_var,  self._pick_output),
        ]:
            r = tk.Frame(body, bg=GUI_BG)
            r.pack(fill="x", pady=3)
            self._btn(r, label, cmd).pack(side="left")
            tk.Label(r, textvariable=var, bg=GUI_BG,
                     fg=C["txt_muted"], font=("Segoe UI", 9),
                     anchor="w", wraplength=680).pack(side="left", padx=12)

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=8)

        # Report metadata
        tk.Label(body, text="Report Metadata", bg=GUI_BG,
                 fg=C["accent_navy"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(2, 4))
        mf = tk.Frame(body, bg=GUI_CARD, padx=12, pady=8,
                      relief="flat", bd=1,
                      highlightbackground=C["border"],
                      highlightthickness=1)
        mf.pack(fill="x")
        for i, (key, label) in enumerate([
            ("title",  "Report Title"),
            ("org",    "Organization"),
            ("doc_no", "Document No."),
        ]):
            tk.Label(mf, text=label + ":", bg=GUI_CARD,
                     fg=C["txt_muted"],
                     font=("Segoe UI", 9)).grid(
                row=0, column=i * 2, sticky="w", padx=(8, 4), pady=3)
            var = tk.StringVar(value=REPORT_META[key])
            var.trace_add("write",
                lambda *a, k=key, v=var: REPORT_META.update({k: v.get()}))
            tk.Entry(mf, textvariable=var, bg="white",
                     fg=C["txt_dark"], relief="solid", bd=1,
                     font=("Segoe UI", 9), width=26).grid(
                row=0, column=i * 2 + 1,
                sticky="w", padx=(0, 16), pady=3)

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=8)

        # Plot builder
        tk.Label(body, text="Configure X–Y Plots",
                 bg=GUI_BG, fg=C["accent_navy"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(2, 4))

        builder = tk.Frame(body, bg=GUI_CARD, padx=14, pady=10,
                           relief="flat", bd=1,
                           highlightbackground=C["border"],
                           highlightthickness=1)
        builder.pack(fill="x")

        tk.Label(builder, text="X Axis:", bg=GUI_CARD,
                 fg=C["txt_muted"],
                 font=("Segoe UI", 9)).grid(row=0, column=0,
                                             sticky="w", pady=4)
        self._x_var = tk.StringVar(value=CHANNEL_LABELS[0])
        ttk.Combobox(builder, textvariable=self._x_var,
                     values=CHANNEL_LABELS, state="readonly",
                     width=44).grid(row=0, column=1, padx=10, sticky="w")

        tk.Label(builder,
                 text="Y Channels\n(each gets its\nown subplot):",
                 bg=GUI_CARD, fg=C["txt_muted"],
                 font=("Segoe UI", 9), justify="right").grid(
            row=1, column=0, sticky="nw", pady=6)

        yf = tk.Frame(builder, bg=GUI_CARD)
        yf.grid(row=1, column=1, padx=10, sticky="w")
        self._y_list = tk.Listbox(
            yf, selectmode=tk.MULTIPLE,
            bg="white", fg=C["txt_dark"],
            selectbackground=C["accent_blue"],
            selectforeground="white",
            font=("Segoe UI", 9), height=8, width=52,
            activestyle="none", relief="solid", bd=1)
        for ch in CHANNEL_LABELS:
            self._y_list.insert(tk.END, ch)
        ys = ttk.Scrollbar(yf, orient="vertical", command=self._y_list.yview)
        self._y_list.configure(yscrollcommand=ys.set)
        self._y_list.pack(side="left")
        ys.pack(side="left", fill="y")

        self._btn(builder, "➕  Add Plot Group", self._add_plot).grid(
            row=2, column=1, sticky="w", pady=(8, 0))

        tk.Label(builder,
                 text="Tip: Select up to 8 Y channels — each renders as a separate subplot on one page.",
                 bg=GUI_CARD, fg=C["txt_light"],
                 font=("Segoe UI", 8)).grid(
            row=3, column=1, sticky="w", pady=(4, 0))

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=8)

        tk.Label(body, text="Queued Plot Groups",
                 bg=GUI_BG, fg=C["accent_navy"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(2, 4))
        lf = tk.Frame(body, bg=GUI_CARD, relief="flat", bd=1,
                      highlightbackground=C["border"],
                      highlightthickness=1)
        lf.pack(fill="both", expand=True)
        self._plot_lb = tk.Listbox(
            lf, bg="white", fg=C["txt_dark"],
            font=("Segoe UI", 9), height=5,
            selectbackground=C["accent_blue"],
            selectforeground="white",
            activestyle="none", relief="flat", bd=0)
        self._plot_lb.pack(side="left", fill="both", expand=True,
                           padx=4, pady=4)
        sb = ttk.Scrollbar(lf, orient="vertical",
                            command=self._plot_lb.yview)
        self._plot_lb.configure(yscrollcommand=sb.set)
        sb.pack(side="left", fill="y")

        rr = tk.Frame(body, bg=GUI_BG)
        rr.pack(fill="x", pady=3)
        self._btn(rr, "🗑  Remove Selected", self._remove_plot,
                  bg="#DC2626", hbg="#B91C1C").pack(side="left")

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=8)
        self._btn(body, "🚀  Generate PDF Report",
                  self._generate, bg="#059669", hbg="#047857",
                  fs=12).pack(pady=6)
        self._status = tk.Label(body, text="", bg=GUI_BG,
                                fg=C["accent_teal"],
                                font=("Segoe UI", 9))
        self._status.pack()
        self._style_ttk()

    def _style_ttk(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("TCombobox",
                    fieldbackground="white", background="white",
                    foreground=C["txt_dark"],
                    selectbackground=C["accent_blue"],
                    arrowcolor=C["txt_muted"])

    def _pick_tdms(self):
        p = filedialog.askopenfilename(
            title="Select TDMS file",
            filetypes=[("TDMS files", "*.tdms"), ("All files", "*.*")])
        if p:
            self._tdms_path = p
            self._tdms_var.set(p)
            self._out_var.set(os.path.splitext(p)[0] + "_report.pdf")

    def _pick_output(self):
        p = filedialog.asksaveasfilename(
            title="Save PDF report as…", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")])
        if p:
            self._out_var.set(p)

    def _add_plot(self):
        x_label = self._x_var.get()
        sel = self._y_list.curselection()
        if not sel:
            messagebox.showwarning("No Y selected",
                                   "Select at least one Y channel.")
            return
        y_labels = [CHANNEL_LABELS[i] for i in sel]
        self._plots.append({"x_label": x_label, "y_labels": y_labels})
        n = len(self._plots)
        y_str = " | ".join(y_labels)
        self._plot_lb.insert(
            tk.END, f"Plot {n}:  {x_label}  →  {y_str}")
        self._y_list.selection_clear(0, tk.END)
        self._status.config(
            text=f"✓  Plot {n} added ({len(y_labels)} subplots).",
            fg=C["accent_teal"])

    def _remove_plot(self):
        sel = self._plot_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        self._plot_lb.delete(idx)
        self._plots.pop(idx)
        items = list(self._plot_lb.get(0, tk.END))
        self._plot_lb.delete(0, tk.END)
        for i, itm in enumerate(items):
            self._plot_lb.insert(
                tk.END, f"Plot {i+1}:  " + itm.split(":  ", 1)[-1])
        self._status.config(text="Plot removed.", fg=C["accent_blue"])

    def _generate(self):
        if not self._tdms_path or not os.path.isfile(self._tdms_path):
            messagebox.showerror("Error", "Please select a valid TDMS file.")
            return
        out = self._out_var.get()
        if not out:
            messagebox.showerror("Error", "Please set an output PDF path.")
            return
        if not self._plots:
            messagebox.showerror("Error", "Add at least one plot group.")
            return
        self._status.config(text="⏳  Generating… please wait.",
                            fg=C["accent_blue"])
        self.update_idletasks()
        try:
            generate_pdf(self._tdms_path, self._plots, out)
            self._status.config(text=f"✅  Saved: {out}",
                                fg=C["accent_teal"])
            messagebox.showinfo("Done", f"Report generated!\n\n{out}")
        except Exception as exc:
            self._status.config(text=f"❌  {exc}", fg="#DC2626")
            messagebox.showerror("Error", str(exc))


# ─────────────────────────────────────────────────────────────
#  CLI DEMO
# ─────────────────────────────────────────────────────────────

def cli_demo(tdms_path: str):
    plots_config = [
        {"x_label": "Time(Sec)",
         "y_labels": ["Normal Load (N)", "Friction Force(N)",
                      "Coefficient of Friction"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["Depth (Microns)"]},
        {"x_label": "Sliding Distance (mm)",
         "y_labels": ["Coefficient of Friction", "Friction Force(N)"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["Stage Temperature (Degree Celsius)",
                      "Sample Temperature (Degree Celsius)"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["Acoustic (mV)", "ECR (ohms)"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["Fx(N)", "Fy(N)", "Mx(Nm)", "My(Nm)"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["MTM Ball Speed (m/sec)", "MTM Disc Speed (m/sec)"]},
    ]
    out_path = os.path.splitext(tdms_path)[0] + "_report.pdf"
    generate_pdf(tdms_path, plots_config, out_path)


# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        cli_demo(sys.argv[1])
    else:
        app = App()
        app.mainloop()