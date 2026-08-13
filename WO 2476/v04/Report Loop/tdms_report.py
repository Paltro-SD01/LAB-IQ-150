"""
tdms_report.py
==============
TDMS  →  Professional PDF Report Generator
-------------------------------------------
ONE file. Works three ways:

  1. LabVIEW Python Node  →  call any function below directly
  2. GUI (standalone)     →  python tdms_report.py
  3. CLI (quick test)     →  python tdms_report.py path/to/file.tdms

Install (once):
    pip install nptdms matplotlib numpy scipy Pillow

─────────────────────────────────────────────────────────────
LABVIEW PYTHON NODE  —  functions exposed
─────────────────────────────────────────────────────────────

  health_check()
    In  : (none)
    Out : str  — dependency check result

  get_channel_list(tdms_path)
    In  : str
    Out : str  — comma-separated channel names

  get_channel_stats(tdms_path, channel_name)
    In  : str, str
    Out : str  — JSON with n/mean/std/min/max/…

  generate_report_simple(
      tdms_path,         str   Input 0  — path to .tdms file
      output_path,       str   Input 1  — path for output .pdf
      x_label,           str   Input 2  — X channel name
      y_labels_csv,      str   Input 3  — Y channels comma-separated
      report_title,      str   Input 4  — "" = default title
      doc_no,            str   Input 5  — "" = default doc number
      left_logo_path,    str   Input 6  — "" = no logo
      right_logo_path,   str   Input 7  — "" = no logo
      footer_link_text,  str   Input 8  — "" = show source filename
      footer_link_url)   str   Input 9  — "" = no hyperlink
    Out : "SUCCESS: <path>"  or  "ERROR: <msg>"

  generate_report_multi(
      tdms_path,         str   Input 0
      output_path,       str   Input 1
      plots_json,        str   Input 2  — JSON array of plot groups
      left_logo_path,    str   Input 3  — "" = no logo
      right_logo_path,   str   Input 4  — "" = no logo
      footer_link_text,  str   Input 5
      footer_link_url)   str   Input 6
    Out : "SUCCESS: <path>"  or  "ERROR: <msg>"
─────────────────────────────────────────────────────────────
"""

# ── Standard library
import os
import sys
import json
import math
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

# ── Scientific / plotting
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.image as mpimg
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import AutoMinorLocator

# ── Optional: scipy for skewness / kurtosis
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ── TDMS reader
try:
    from nptdms import TdmsFile
except ImportError:
    print("ERROR: nptdms not installed.  Run:  pip install nptdms")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
#  REPORT METADATA  (overridable from LabVIEW via function args)
# ═══════════════════════════════════════════════════════════════

REPORT_META = {
    "title":        "Tribological Test Analysis Report",
    "subtitle":     "TDMS Data Processing & Statistical Evaluation",
    "org":          "Tribology & Mechanical Testing Laboratory",
    "doc_no":       "RPT-TDMS-001",
    "revision":     "Rev A",
    "confidential": "CONFIDENTIAL",
}

# ── Branding (logos + footer hyperlink)
BRANDING = {
    "left_logo_path":   "",   # absolute path to left-header logo
    "right_logo_path":  "",   # absolute path to right-header logo
    "footer_link_text": "",   # text shown in footer left
    "footer_link_url":  "",   # URL (native PDF clickable annotation)
}


# ═══════════════════════════════════════════════════════════════
#  CHANNEL DEFINITIONS
# ═══════════════════════════════════════════════════════════════

CHANNEL_LABELS = [
    "Time(Sec)", "Normal Load (N)", "Friction Force(N)",
    "Coefficient of Friction", "Depth (Microns)", "Speed (RPM)",
    "Frequency (Hz)", "Angle (Degree)", "Cyclic Friction Force (N)",
    "Cyclic Co-Efficient Friction Force",
    "Stage Temperature (Degree Celsius)",
    "Sample Temperature (Degree Celsius)",
    "Stroke Length (mm)", "Scratch Speed (mm/sec)",
    "Amb Humidity (%Rh)", "Amb Temperature (Deg C)",
    "Acoustic (mV)", "Mx(Nm)", "My(Nm)", "Mz (Nm)",
    "Humidity(%Rh)", "Sliding Distance (mm)",
    "Wear Track Diameter(mm)", "Fx(N)", "Fy(N)",
    "MTM Ball Speed(RPM)", "MTM Disc Speed (RPM)",
    "Entrainment Speed", "Slide Role", "Slip(%)",
    "Rotary Speed (m/sec)", "MTM Ball Speed (m/sec)",
    "MTM Disc Speed (m/sec)", "ECR (ohms)",
]


# ═══════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────
# PALETTE - white background, black text, clean and simple
C = {
    "page":         "#FFFFFF",
    "panel":        "#FFFFFF",
    "row_even":     "#FFFFFF",
    "row_odd":      "#F5F5F5",
    "header_bar":   "#FFFFFF",   # pure white header
    "cover_accent": "#F0F0F0",   # very light gray cover band (almost white)
    "txt_dark":     "#000000",
    "txt_body":     "#222222",
    "txt_muted":    "#555555",
    "txt_light":    "#888888",
    "txt_white":    "#FFFFFF",
    "hdr_text":     "#000000",   # black title text
    "hdr_sub":      "#444444",   # dark gray secondary text
    "accent_navy":  "#111111",   # near-black for table headers
    "accent_blue":  "#2255AA",   # standard link blue (hyperlinks only)
    "accent_teal":  "#CCCCCC",   # light gray stripe
    "accent_sky":   "#888888",
    "accent_slate": "#CCCCCC",
    "border":       "#CCCCCC",
    "grid":         "#EEEEEE",
    "spine":        "#CCCCCC",
}

LINE_COLORS = [
    "#1155AA",
    "#117755",
    "#AA6600",
    "#662288",
    "#AA1111",
    "#005577",
    "#226644",
    "#774400",
    "#334488",
    "#882244",
]


# ═══════════════════════════════════════════════════════════════
#  TDMS LOADER  +  CHANNEL MATCHER
# ═══════════════════════════════════════════════════════════════

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
    """
    Robust channel name matcher with scored priority:
      1. Exact match (after normalisation)
      2. All words of label found inside channel name
      3. All words of channel name found inside label
      4. Majority (>=70%) of label words found in channel name
    Returns the best-scoring available key, or None.
    """
    def norm(s):
        import re
        s = s.lower()
        s = re.sub(r"[()/_\-]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def words(s):
        return [w for w in norm(s).split() if len(w) >= 2]

    ln     = norm(label)
    lwords = words(label)

    best_key   = None
    best_score = -1

    for avail in available:
        ch_name = avail.split(" / ")[-1] if " / " in avail else avail
        cn      = norm(ch_name)
        cwords  = words(ch_name)
        score   = 0

        if ln == cn:
            score = 100
        elif lwords and all(w in cn for w in lwords):
            score = 80
        elif cwords and all(w in ln for w in cwords):
            score = 60
        elif lwords:
            matches = sum(1 for w in lwords if w in cn)
            ratio   = matches / len(lwords)
            if ratio >= 0.70:
                score = int(40 * ratio)

        if score > best_score:
            best_score = score
            best_key   = avail

    return best_key if best_score >= 40 else None


def resolve_y_labels(y_labels: list, raw_data: dict,
                     known_channels: list = None) -> list:
    """
    Match each y_label to an actual TDMS data key.

    Strategy:
      - If known_channels is provided (sent from LabVIEW), first find the
        best canonical name from that list, then look it up in raw_data.
        This gives EXACT matching when LabVIEW sends the real channel names.
      - Otherwise fall back to direct fuzzy match against raw_data keys.

    Returns list of (display_label, numpy_array) tuples.
    """
    avail  = list(raw_data.keys())
    result = []

    for y_lbl in y_labels:
        resolved_key = None

        if known_channels:
            # Step 1: match label to canonical channel name from known list
            canonical = best_match(y_lbl, known_channels)
            if canonical:
                # Step 2: find that canonical name inside raw_data
                resolved_key = best_match(canonical, avail)

        if not resolved_key:
            # Fallback: direct fuzzy match against TDMS keys
            resolved_key = best_match(y_lbl, avail)

        if resolved_key:
            result.append((y_lbl, raw_data[resolved_key]))
            print(f"    [OK] '{y_lbl}' -> '{resolved_key}'")
        else:
            print(f"    [!!] '{y_lbl}' -> NOT FOUND")

    return result



# ═══════════════════════════════════════════════════════════════
#  STATISTICS
# ═══════════════════════════════════════════════════════════════

def compute_stats(arr: np.ndarray) -> dict:
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        nan = float("nan")
        return {k: nan for k in ["n","mean","median","std","variance",
                                  "min","max","range","rms",
                                  "skewness","kurtosis","cv_pct"]}
    mean = float(np.mean(arr))
    std  = float(np.std(arr,  ddof=1)) if len(arr) > 1 else 0.0
    var  = float(np.var(arr,  ddof=1)) if len(arr) > 1 else 0.0
    mn, mx = float(np.min(arr)), float(np.max(arr))
    rms  = float(np.sqrt(np.mean(arr**2)))
    cv   = (std / mean * 100) if mean != 0 else float("nan")
    skew = kurt = float("nan")
    if HAS_SCIPY and len(arr) > 3:
        skew = float(scipy_stats.skew(arr))
        kurt = float(scipy_stats.kurtosis(arr))
    return {
        "n": int(len(arr)), "mean": mean, "median": float(np.median(arr)),
        "std": std, "variance": var, "min": mn, "max": mx,
        "range": mx - mn, "rms": rms,
        "skewness": skew, "kurtosis": kurt, "cv_pct": cv,
    }


def fmt(v, dec=4):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "N/A"
    if isinstance(v, int):
        return f"{v:,}"
    mag = abs(v)
    if mag == 0:
        return "0.0000"
    if mag >= 1e6 or (0 < mag < 1e-3):
        return f"{v:.4e}"
    return f"{v:.{dec}f}"


# ═══════════════════════════════════════════════════════════════
#  MATPLOTLIB GLOBAL STYLE
# ═══════════════════════════════════════════════════════════════

def _apply_style():
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


# ═══════════════════════════════════════════════════════════════
#  LOGO HELPER
# ═══════════════════════════════════════════════════════════════

def _draw_logo(fig, rect: list, img_path: str):
    """
    Render a logo image inside a figure-level axes at rect=[x, y, w, h].
    Draws a clean white card background so dark/black text logos stand out.
    """
    if not img_path or not os.path.isfile(img_path):
        return
    try:
        img = mpimg.imread(img_path)
        ax  = fig.add_axes(rect)
        ax.set_facecolor("#FFFFFF")
        # Draw a white card patch behind image
        ax.add_patch(mpatches.FancyBboxPatch(
            (0, 0), 1, 1, boxstyle="square,pad=0",
            fc="#FFFFFF", ec="#CBD5E1", linewidth=0.6,
            transform=ax.transAxes, zorder=0))
        ax.axis("off")
        ax.imshow(img, aspect="equal", interpolation="lanczos",
                  origin="upper", zorder=1)
    except Exception as e:
        print(f"[!] Logo load error ({img_path}): {e}")


# ═══════════════════════════════════════════════════════════════
#  PAGE CHROME  (header + stripe + footer — every page)
# ═══════════════════════════════════════════════════════════════

_LOGO_W = 0.105    # 10.5 % of figure width per logo badge
_HDR_Y  = 0.945
_HDR_H  = 0.055
_STR_H  = 0.005    # thin accent stripe

def _draw_chrome(fig, page_num: int, total_pages: int,
                 tdms_name: str, section: str = ""):
    b = BRANDING
    has_left  = bool(b["left_logo_path"]  and os.path.isfile(b["left_logo_path"]))
    has_right = bool(b["right_logo_path"] and os.path.isfile(b["right_logo_path"]))

    # ── Light header bar ──────────────────────────────────────────────
    hdr = fig.add_axes([0, _HDR_Y, 1, _HDR_H])
    hdr.set_facecolor(C["header_bar"])   # light cool-gray
    hdr.axis("off")

    # Subtle bottom border line on header
    hdr.plot([0, 1], [0, 0], color=C["accent_slate"], lw=0.8,
             transform=hdr.transAxes, clip_on=False)

    # ── Text layout ────────────────────────────────────────────────────
    # Title: CENTERED horizontally between the two logo zones
    # Doc/Rev: right-aligned before right logo, small, muted
    # Section: smaller line below title (only on inner pages)
    # ──────────────────────────────────────────────────────────────────
    right_edge = 1 - _LOGO_W - 0.010 if has_right else 0.986

    # Report title — CENTERED between logos
    hdr.text(0.50, 0.58, REPORT_META["title"],
             va="center", ha="center", fontsize=9, fontweight="bold",
             color=C["hdr_text"], transform=hdr.transAxes)

    # Section name — centred, smaller, below title
    if section:
        hdr.text(0.50, 0.22, section[:70], va="center", ha="center",
                 fontsize=7, color=C["hdr_sub"],
                 transform=hdr.transAxes)

    # Doc no | Revision — right-aligned
    hdr.text(right_edge, 0.58,
             f"{REPORT_META['doc_no']}  |  {REPORT_META['revision']}",
             va="center", ha="right", fontsize=6.5,
             color=C["hdr_sub"], transform=hdr.transAxes)

    # ── Logo badges ───────────────────────────────────────────────────
    if has_left:
        _draw_logo(fig,
                   [0.003, _HDR_Y + 0.003, _LOGO_W - 0.003, _HDR_H - 0.006],
                   b["left_logo_path"])
    if has_right:
        _draw_logo(fig,
                   [1 - _LOGO_W + 0.001, _HDR_Y + 0.003,
                    _LOGO_W - 0.003, _HDR_H - 0.006],
                   b["right_logo_path"])

    # ── Thin accent stripe below header ───────────────────────────────
    stripe = fig.add_axes([0, _HDR_Y - _STR_H, 1, _STR_H])
    stripe.set_facecolor(C["accent_teal"])
    stripe.axis("off")

    # ── Footer ────────────────────────────────────────────────────────
    ftr = fig.add_axes([0, 0, 1, 0.028])
    ftr.set_facecolor(C["panel"])
    ftr.axis("off")
    ftr.plot([0, 1], [0.96, 0.96], color=C["border"], lw=0.7,
             transform=ftr.transAxes, clip_on=False)

    link_text = b["footer_link_text"].strip()
    link_url  = b["footer_link_url"].strip()
    if link_text:
        t = ftr.text(0.014, 0.38, link_text, va="center", fontsize=6.5,
                     color=C["accent_blue"], fontweight="bold",
                     transform=ftr.transAxes)
        if link_url:
            t.set_url(link_url)
    else:
        ftr.text(0.014, 0.38, f"Source: {tdms_name}", va="center",
                 fontsize=6.5, color=C["txt_light"],
                 transform=ftr.transAxes)

    ftr.text(0.50, 0.38,
             f"Generated: {datetime.now().strftime('%m/%d/%Y  %I:%M:%S %p')}",
             va="center", ha="center", fontsize=6.5,
             color=C["txt_light"], transform=ftr.transAxes)
    ftr.text(0.986, 0.38, f"Page {page_num} of {total_pages}",
             va="center", ha="right", fontsize=7,
             color=C["txt_muted"], transform=ftr.transAxes)


# ═══════════════════════════════════════════════════════════════
#  PAGE 1 — COVER
# ═══════════════════════════════════════════════════════════════

def _make_cover(pdf, tdms_path, plots_config):
    b = BRANDING
    has_left  = bool(b["left_logo_path"]  and os.path.isfile(b["left_logo_path"]))
    has_right = bool(b["right_logo_path"] and os.path.isfile(b["right_logo_path"]))

    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    ax  = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(C["page"])
    ax.axis("off")

    # Cover header band — white with a thin gray bottom border
    ax.add_patch(mpatches.FancyBboxPatch(
        (0, 0.80), 1, 0.20, boxstyle="square,pad=0",
        fc=C["cover_accent"], ec="none", transform=ax.transAxes, zorder=1))
    # Thin bottom border on cover band
    ax.plot([0, 1], [0.800, 0.800], color=C["border"], lw=1.0,
            transform=ax.transAxes, clip_on=False, zorder=4)

    # Logos inside white badges
    COVER_LOGO_W = 0.155
    if has_left:
        _draw_logo(fig, [0.012, 0.812, COVER_LOGO_W, 0.170], b["left_logo_path"])
    if has_right:
        _draw_logo(fig, [1 - COVER_LOGO_W - 0.012, 0.812, COVER_LOGO_W, 0.170], b["right_logo_path"])

    # Title — CENTERED, black text (on light gray background)
    ax.text(0.50, 0.900, REPORT_META["title"],
            fontsize=22, fontweight="bold", ha="center", va="center",
            color=C["txt_dark"], transform=ax.transAxes, zorder=4)

    rows = [
        ("Document No.",  REPORT_META["doc_no"]),
        ("Revision",      REPORT_META["revision"]),
        ("Organization",  REPORT_META["org"]),
        ("Source File",   os.path.basename(tdms_path)),
        ("Report Date",   datetime.now().strftime("%m/%d/%Y")),
        ("Total Plots",   str(len(plots_config))),
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

    ax.add_patch(mpatches.FancyBboxPatch(
        (0.520, 0.080), 0.445, 0.700,
        boxstyle="round,pad=0.005", fc=C["panel"],
        ec=C["border"], linewidth=0.7, transform=ax.transAxes, zorder=0))
    ax.text(0.537, 0.748, "PLOT  INDEX", fontsize=10, fontweight="bold",
            color=C["accent_blue"], transform=ax.transAxes)
    ax.plot([0.527, 0.960], [0.732, 0.732], color=C["accent_teal"],
            lw=1.2, transform=ax.transAxes, clip_on=False)

    col_xs = [0.537, 0.570, 0.660]
    row_y  = 0.714
    for hd, cx in zip(["No.", "X Parameter", "Y Parameter(s)"], col_xs):
        ax.text(cx, row_y, hd, fontsize=7.5, fontweight="bold",
                color=C["txt_muted"], transform=ax.transAxes)
    row_y -= 0.018
    ax.plot([0.527, 0.960], [row_y, row_y], color=C["border"],
            lw=0.5, transform=ax.transAxes, clip_on=False)

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
        ax.text(col_xs[0], row_y, str(i+1), fontsize=7.5,
                color=C["txt_muted"], transform=ax.transAxes)
        ax.text(col_xs[1], row_y, cfg["x_label"][:16],
                fontsize=7, color=C["txt_body"], transform=ax.transAxes)
        # Print all Y labels — wrap to second line if too long
        y_str = ", ".join(cfg["y_labels"])
        if len(y_str) <= 44:
            ax.text(col_xs[2], row_y, y_str,
                    fontsize=6.8, color=C["txt_body"], transform=ax.transAxes)
        else:
            ax.text(col_xs[2], row_y + 0.006, y_str[:44],
                    fontsize=6.5, color=C["txt_body"], transform=ax.transAxes)
            ax.text(col_xs[2], row_y - 0.010, y_str[44:88],
                    fontsize=6.5, color=C["txt_body"], transform=ax.transAxes)

    ax.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 0.042, boxstyle="square,pad=0",
        fc=C["panel"], ec="none", transform=ax.transAxes, zorder=1))
    ax.plot([0, 1], [0.042, 0.042], color=C["border"],
            lw=0.8, transform=ax.transAxes, clip_on=False)

    link_text = b["footer_link_text"].strip()
    link_url  = b["footer_link_url"].strip()
    if link_text:
        t = ax.text(0.012, 0.020, link_text, va="center", fontsize=7,
                    color=C["accent_blue"], fontweight="bold",
                    transform=ax.transAxes, zorder=2)
        if link_url:
            t.set_url(link_url)
    ax.text(0.500, 0.020,
            f"{REPORT_META['doc_no']}  |  {REPORT_META['revision']}  |  Page 1",
            ha="center", va="center", fontsize=7,
            color=C["txt_light"], transform=ax.transAxes, zorder=2)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
#  PAGE 2 — TABLE OF CONTENTS
# ═══════════════════════════════════════════════════════════════

def _make_toc(pdf, plots_config, total_pages, tdms_name):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    _draw_chrome(fig, 2, total_pages, tdms_name, "Table of Contents")
    ax = fig.add_axes([0.07, 0.06, 0.86, 0.86])
    ax.set_facecolor(C["page"])
    ax.axis("off")
    ax.text(0, 0.965, "TABLE OF CONTENTS", fontsize=14,
            fontweight="bold", color=C["accent_navy"], transform=ax.transAxes)
    ax.add_patch(mpatches.FancyBboxPatch(
        (-0.01, 0.935), 1.02, 0.006, boxstyle="square,pad=0",
        fc=C["accent_teal"], ec="none", transform=ax.transAxes))

    sections = [
        ("1.", "Cover Page",          "1",  False),
        ("2.", "Table of Contents",   "2",  False),
        ("3.", "Executive Summary",   "3",  False),
        ("4.", "Measurement Plots",   "4",  False),
    ]
    for i, cfg in enumerate(plots_config):
        y_lbl = ", ".join(cfg["y_labels"])  # show ALL y labels
        sections.append((
            f"  4.{i+1}.",
            f"Plot {i+1}:  {cfg['x_label']}  ->  {y_lbl[:80]}",
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
        fs = 9 if not is_sub else 8.5
        fw = "bold" if not is_sub else "normal"
        cl = C["txt_dark"] if not is_sub else C["txt_body"]
        ind = 0.0 if not is_sub else 0.035
        ax.text(ind,        row_y, num,   fontsize=fs, fontweight=fw,
                color=cl, transform=ax.transAxes)
        ax.text(ind + 0.07, row_y, title, fontsize=fs,
                color=cl, transform=ax.transAxes)
        ax.text(1.00, row_y, page, fontsize=fs, fontweight=fw,
                color=C["accent_blue"], ha="right",
                transform=ax.transAxes)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
#  PAGE 3 — EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════

def _make_exec_summary(pdf, all_stats, total_pages, tdms_name):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    _draw_chrome(fig, 3, total_pages, tdms_name, "Executive Summary")
    ax = fig.add_axes([0.04, 0.05, 0.92, 0.87])
    ax.set_facecolor(C["page"])
    ax.axis("off")
    ax.text(0, 0.960, "3.  EXECUTIVE SUMMARY", fontsize=13,
            fontweight="bold", color=C["accent_navy"], transform=ax.transAxes)
    ax.add_patch(mpatches.FancyBboxPatch(
        (-0.01, 0.930), 1.02, 0.005, boxstyle="square,pad=0",
        fc=C["accent_teal"], ec="none", transform=ax.transAxes))
    ax.text(0, 0.908,
            "Statistical overview of all measured channels.  "
            "Values computed on finite (non-NaN) data only.",
            fontsize=8.5, color=C["txt_muted"], transform=ax.transAxes)

    # CV (%) removed as not required
    col_heads = ["Channel / Parameter","N","Mean","Std Dev",
                 "Variance","Min","Max","Range","RMS"]
    col_x     = [0.000,0.310,0.385,0.460,0.535,0.615,0.692,0.768,0.876]
    col_align = ["l","r","r","r","r","r","r","r","r"]

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
                    f"  ... {len(all_stats)-i} more channels on plot pages",
                    fontsize=7, color=C["txt_muted"], transform=ax.transAxes)
            break
        s  = entry["stats"]
        bg = C["row_even"] if i % 2 == 0 else C["row_odd"]
        ax.add_patch(mpatches.FancyBboxPatch(
            (-0.01, row_y - 0.012), 1.02, 0.034,
            boxstyle="square,pad=0", fc=bg, ec=C["border"],
            linewidth=0.2, transform=ax.transAxes))
        vals = [entry["label"][:42], fmt(s["n"]),
                fmt(s["mean"]), fmt(s["std"]), fmt(s["variance"]),
                fmt(s["min"]), fmt(s["max"]), fmt(s["range"]),
                fmt(s["rms"])]
        for val, cx, ca in zip(vals, col_x, col_align):
            ax.text(cx, row_y, val, fontsize=7.5, color=C["txt_body"],
                    transform=ax.transAxes,
                    ha="left" if ca == "l" else "right")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
#  SECTION DIVIDER PAGE
# ═══════════════════════════════════════════════════════════════

def _make_divider(pdf, section_num, title, subtitle,
                  page_num, total_pages, tdms_name):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    _draw_chrome(fig, page_num, total_pages, tdms_name, title)
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
    ax.text(0.50, 0.52, subtitle, fontsize=11,
            color=C["txt_muted"], ha="center",
            transform=ax.transAxes, zorder=2)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ==============================================================
#  PER-CHANNEL PAGE  -  ONE full-page chart per Y channel
# ==============================================================

def _make_plot_page(pdf, x_data, y_label, y_arr, x_label,
                    plot_num, page_num, total_pages, tdms_name):
    """
    Render one Y channel per page.
    Layout (figure-fraction coords, origin bottom-left):
      Header  : 0.945 - 1.000  (drawn by _draw_chrome)
      Stripe  : 0.940 - 0.945
      Title   : 0.910 - 0.940  (text)
      Chart   : 0.360 - 0.905  (axes)
      Stats   : 0.040 - 0.340  (axes)
      Footer  : 0.000 - 0.028  (drawn by _draw_chrome)
    """
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(C["page"])
    _draw_chrome(fig, page_num, total_pages, tdms_name,
                 f"4.{plot_num}  {y_label}")

    # -- Chart axes -------------------------------------------------------
    CT, CB = 0.920, 0.270          # chart starts near top of content area
    ax = fig.add_axes([0.07, CB, 0.90, CT - CB])
    ax.set_facecolor(C["panel"])
    for sp in ax.spines.values():
        sp.set_color(C["spine"]); sp.set_linewidth(0.6)
    ax.grid(True, color=C["grid"], linestyle="--", linewidth=0.5, alpha=0.8)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.tick_params(which="minor", length=2.5, color=C["border"])
    ax.tick_params(axis="both", colors=C["txt_muted"], labelsize=8)

    # Trim arrays to same length
    n   = min(len(x_data), len(y_arr))
    xs  = x_data[:n]
    ys  = y_arr[:n]

    # Filter to finite values only (removes NaN / Inf spikes)
    mask = np.isfinite(xs) & np.isfinite(ys)
    xs_f = xs[mask]
    ys_f = ys[mask]

    color = LINE_COLORS[0]

    if len(xs_f) > 0:
        ax.plot(xs_f, ys_f, color=color, linewidth=1.4,
                alpha=0.90, zorder=3, solid_capstyle="round")
        ax.fill_between(xs_f, ys_f, alpha=0.07, color=color, zorder=2)
        mv = float(np.nanmean(ys_f))
        ax.axhline(y=mv, color=color, linewidth=1.0,
                   linestyle="--", alpha=0.60, zorder=4,
                   label=f"Mean = {fmt(mv, 4)}")
        ax.legend(loc="upper left", fontsize=8, framealpha=0.85,
                  edgecolor=C["border"])
    else:
        ax.text(0.5, 0.5, "No finite data", ha="center", va="center",
                fontsize=14, color=C["txt_muted"], transform=ax.transAxes)
        mv = float("nan")

    ax.set_xlabel(x_label, fontsize=9, labelpad=6, color=C["txt_body"],
                  fontweight="bold")
    ax.set_ylabel(y_label, fontsize=9, labelpad=6, color=color,
                  fontweight="bold")

    # -- Statistics table ------------------------------------------------
    ST, SB = 0.240, 0.038          # reduced height stats band
    sa = fig.add_axes([0.07, SB, 0.90, ST - SB])
    sa.set_facecolor(C["page"])
    sa.axis("off")

    s = compute_stats(ys_f if len(xs_f) > 0 else ys)

    stat_defs = [
        ("n",        "N (Samples)"),
        ("mean",     "Mean"),
        ("median",   "Median"),
        ("std",      "Std Dev"),
        ("variance", "Variance"),
        ("min",      "Minimum"),
        ("max",      "Maximum"),
        ("range",    "Range"),
        ("rms",      "RMS"),
    ]

    # Header bar
    HDR_H = 0.18
    sa.add_patch(mpatches.FancyBboxPatch(
        (0.0, 1.0 - HDR_H), 1.0, HDR_H, boxstyle="square,pad=0",
        fc=C["accent_navy"], ec="none", transform=sa.transAxes, zorder=2))
    sa.text(0.010, 1.0 - HDR_H * 0.5,
            f"Statistical Summary  --  {y_label}",
            va="center", fontsize=9, fontweight="bold",
            color=C["txt_white"], transform=sa.transAxes, zorder=3)

    n_cols  = 9
    COL_W   = 1.0 / n_cols
    ROW_H   = (1.0 - HDR_H) / 2.0    # two rows: labels + values

    # Labels row
    ry_lbl = 1.0 - HDR_H - ROW_H * 0.42
    for ci, (sk, sl) in enumerate(stat_defs):
        cx = ci * COL_W
        bg = C["row_even"] if ci % 2 == 0 else C["row_odd"]
        sa.add_patch(mpatches.FancyBboxPatch(
            (cx, 1.0 - HDR_H - ROW_H), COL_W, ROW_H,
            boxstyle="square,pad=0", fc=bg, ec=C["border"],
            linewidth=0.3, transform=sa.transAxes))
        sa.text(cx + COL_W * 0.5, ry_lbl, sl,
                ha="center", va="center", fontsize=9.0,
                color=C["txt_muted"], transform=sa.transAxes)

    # Values row
    ry_val = 1.0 - HDR_H - ROW_H - ROW_H * 0.50
    for ci, (sk, sl) in enumerate(stat_defs):
        cx  = ci * COL_W
        bg  = C["row_odd"] if ci % 2 == 0 else C["row_even"]
        val = fmt(s[sk], 5 if sk == "variance" else 4)
        sa.add_patch(mpatches.FancyBboxPatch(
            (cx, 0.0), COL_W, ROW_H,
            boxstyle="square,pad=0", fc=bg, ec=C["border"],
            linewidth=0.3, transform=sa.transAxes))
        sa.text(cx + COL_W * 0.5, ry_val, val,
                ha="center", va="center", fontsize=11.0,
                fontweight="bold", color=C["txt_dark"],
                transform=sa.transAxes)

    # Outer border
    sa.add_patch(mpatches.FancyBboxPatch(
        (0.0, 0.0), 1.0, 1.0, boxstyle="square,pad=0",
        fc="none", ec=C["border"], linewidth=0.8,
        transform=sa.transAxes))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
#  APPENDIX
# ═══════════════════════════════════════════════════════════════

def _make_appendix(pdf, raw_data, page_num_start, total_pages, tdms_name):
    """
    Render ALL channels across as many pages as needed.
    Returns the number of pages generated.
    """
    import math
    ROWS_PER_PAGE = 28        # rows that fit per page
    ROW_STEP      = 0.030     # height per row in axes fraction
    ROW_H_BOX     = 0.026     # box height (slightly less than step)
    HEADER_START  = 0.875     # y where column header row is drawn
    DATA_START    = HEADER_START - 0.038   # first data row top
    STOP_Y        = 0.028     # don't draw below this

    all_channels = list(raw_data.items())
    n_total      = len(all_channels)
    n_pages      = max(1, math.ceil(n_total / ROWS_PER_PAGE))

    col_heads = ["#", "Channel Key  (Group / Name)",
                 "Samples", "Min", "Mean", "Max", "Std Dev"]
    col_x     = [0.000, 0.040, 0.640, 0.710, 0.780, 0.848, 0.918]

    for pg in range(n_pages):
        page_num   = page_num_start + pg
        batch      = all_channels[pg * ROWS_PER_PAGE : (pg + 1) * ROWS_PER_PAGE]
        page_label = f"(Page {pg+1} of {n_pages})" if n_pages > 1 else ""

        fig = plt.figure(figsize=(11.69, 8.27))
        fig.patch.set_facecolor(C["page"])
        _draw_chrome(fig, page_num, total_pages, tdms_name,
                     "Appendix - Channel Inventory")
        ax = fig.add_axes([0.04, 0.05, 0.92, 0.87])
        ax.set_facecolor(C["page"])
        ax.axis("off")

        # Section title (first page only)
        if pg == 0:
            ax.text(0, 0.960, "5.  APPENDIX -- CHANNEL INVENTORY",
                    fontsize=13, fontweight="bold",
                    color=C["accent_navy"], transform=ax.transAxes)
            ax.add_patch(mpatches.FancyBboxPatch(
                (-0.01, 0.930), 1.02, 0.004, boxstyle="square,pad=0",
                fc=C["border"], ec="none", transform=ax.transAxes))
            ax.text(0, 0.905,
                    f"All {n_total} numeric channels in the source TDMS file.  {page_label}",
                    fontsize=8.5, color=C["txt_muted"], transform=ax.transAxes)
        else:
            ax.text(0, 0.960,
                    f"5.  APPENDIX -- CHANNEL INVENTORY  {page_label}",
                    fontsize=13, fontweight="bold",
                    color=C["accent_navy"], transform=ax.transAxes)
            ax.add_patch(mpatches.FancyBboxPatch(
                (-0.01, 0.930), 1.02, 0.004, boxstyle="square,pad=0",
                fc=C["border"], ec="none", transform=ax.transAxes))

        # Column header
        row_y = HEADER_START
        ax.add_patch(mpatches.FancyBboxPatch(
            (-0.01, row_y - 0.014), 1.02, 0.040,
            boxstyle="square,pad=0", fc=C["accent_navy"], ec="none",
            transform=ax.transAxes))
        for hd, cx in zip(col_heads, col_x):
            ax.text(cx, row_y, hd, fontsize=7.5, fontweight="bold",
                    color=C["txt_white"], transform=ax.transAxes)

        # Data rows
        row_y = DATA_START
        for local_i, (key, arr) in enumerate(batch):
            global_i = pg * ROWS_PER_PAGE + local_i
            row_y   -= ROW_STEP
            if row_y < STOP_Y:
                break
            a  = arr[np.isfinite(arr)]
            bg = C["row_even"] if local_i % 2 == 0 else C["row_odd"]
            ax.add_patch(mpatches.FancyBboxPatch(
                (-0.01, row_y - 0.008), 1.02, ROW_H_BOX,
                boxstyle="square,pad=0", fc=bg, ec=C["border"],
                linewidth=0.2, transform=ax.transAxes))
            vals = [
                str(global_i + 1),
                key[:65],
                f"{len(a):,}",
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

    return n_pages


# ═══════════════════════════════════════════════════════════════
#  CORE ORCHESTRATOR  (used by GUI, CLI and LabVIEW wrappers)
# ═══════════════════════════════════════════════════════════════

def generate_pdf(tdms_path: str, plots_config: list,
                 output_path: str, branding: dict = None):
    """
    Generate the full PDF report.
    branding keys: left_logo_path, right_logo_path,
                   footer_link_text, footer_link_url
    """
    if branding:
        for k, v in branding.items():
            if k in BRANDING:
                BRANDING[k] = v

    print(f"\n[+] Loading TDMS: {tdms_path}")
    raw_data = load_tdms(tdms_path)
    avail    = list(raw_data.keys())
    print(f"    {len(avail)} numeric channels found.")

    resolved = []
    for cfg in plots_config:
        x_key = best_match(cfg["x_label"], avail)
        if not x_key:
            print(f"[!] X '{cfg['x_label']}' not found -- skipped.")
            continue
        # Use known_channels if available in cfg for better matching
        known = cfg.get("known_channels", None)
        y_sets = resolve_y_labels(cfg["y_labels"], raw_data, known)
        if y_sets:
            resolved.append({"x_label": cfg["x_label"],
                             "x_data":  raw_data[x_key],
                             "y_datasets": y_sets})

    if not resolved:
        print("[!] No valid plots. Aborting.")
        return

    seen = {}
    for rp in resolved:
        for (lbl, arr) in rp["y_datasets"]:
            if lbl not in seen:
                seen[lbl] = arr
    all_stats  = [{"label": lbl, "stats": compute_stats(arr)}
                  for lbl, arr in seen.items()]
    # Count total Y channels and appendix pages
    import math
    n_total_ych      = sum(len(rp["y_datasets"]) for rp in resolved)
    n_appendix_pages = max(1, math.ceil(len(raw_data) / 28))
    # Pages: cover + toc + exec + sec4_div + plots + sec5_div + appendix_pages
    total_pages = 5 + n_total_ych + 1 + n_appendix_pages
    tdms_name   = os.path.basename(tdms_path)

    _apply_style()
    with PdfPages(output_path) as pdf:
        print("[+] Cover...")
        _make_cover(pdf, tdms_path, plots_config)
        print("[+] Table of Contents...")
        _make_toc(pdf, plots_config, total_pages, tdms_name)
        print("[+] Executive Summary...")
        _make_exec_summary(pdf, all_stats, total_pages, tdms_name)
        _make_divider(pdf, "4", "Measurement Plots",
                      "One chart per channel with statistical summary",
                      4, total_pages, tdms_name)

        # One page per Y channel
        plot_num = 0
        for rp in resolved:
            for y_label, y_arr in rp["y_datasets"]:
                plot_num += 1
                page_num  = 4 + plot_num
                print(f"[+] Plot {plot_num}/{n_total_ych}: {y_label} vs {rp['x_label']}...")
                _make_plot_page(pdf,
                                rp["x_data"], y_label, y_arr,
                                rp["x_label"],
                                plot_num, page_num,
                                total_pages, tdms_name)

        app_pg = 4 + n_total_ych + 1   # section 5 divider page number
        _make_divider(pdf, "5", "Appendix",
                      "Full channel inventory from TDMS file",
                      app_pg, total_pages, tdms_name)
        print(f"[+] Appendix ({n_appendix_pages} page(s), {len(raw_data)} channels)...")
        _make_appendix(pdf, raw_data, app_pg + 1, total_pages, tdms_name)

        d = pdf.infodict()
        d["Title"]        = REPORT_META["title"]
        d["Author"]       = REPORT_META["org"]
        d["Subject"]      = tdms_name
        d["Keywords"]     = "TDMS tribology friction wear statistics"
        d["CreationDate"] = datetime.now().strftime("D:%Y%m%d%H%M%S")

    print(f"\n✅  Report saved → {output_path}\n")


# ═══════════════════════════════════════════════════════════════
#  LabVIEW PYTHON NODE FUNCTIONS
#  Point LabVIEW Module Path → this file.  Call any function below.
# ═══════════════════════════════════════════════════════════════

def health_check() -> str:
    """Verify Python session + all dependencies. Wire output to String Indicator."""
    lines = [f"Python : {sys.version}"]
    missing = []
    for pkg, pip_name in [("nptdms","nptdms"),("matplotlib","matplotlib"),
                           ("numpy","numpy"),("scipy","scipy"),("PIL","Pillow")]:
        try:
            mod = __import__(pkg)
            lines.append(f"  {pkg:<14}: OK  (v{getattr(mod,'__version__','?')})")
        except ImportError:
            lines.append(f"  {pkg:<14}: MISSING → pip install {pip_name}")
            missing.append(pip_name)
    lines.append(f"File   : {os.path.abspath(__file__)}")
    prefix = "WARNING" if missing else "OK"
    if missing:
        lines.append(f"\nInstall: pip install {' '.join(missing)}")
    else:
        lines.append("\nAll dependencies OK — ready.")
    return f"{prefix}|\n" + "\n".join(lines)


def get_channel_list(tdms_path: str) -> str:
    """Return comma-separated channel names. Split on ',' in LabVIEW."""
    try:
        data = load_tdms(tdms_path)
        return ",".join(data.keys()) if data else "ERROR: No numeric channels."
    except Exception as exc:
        return f"ERROR: {exc}"


def get_channel_stats(tdms_path: str, channel_name: str) -> str:
    """Return JSON string with n/mean/std/min/max/… for one channel."""
    try:
        data = load_tdms(tdms_path)
        key  = best_match(channel_name, list(data.keys()))
        if key is None:
            return json.dumps({"error": f"'{channel_name}' not found."})
        s = compute_stats(data[key])
        s["channel"] = key
        return json.dumps(
            {k: (None if isinstance(v, float) and math.isnan(v) else v)
             for k, v in s.items()}, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def generate_report_simple(*args) -> str:
    """
    Generate PDF — single plot group.
    Accepts 4 to 13 positional arguments from LabVIEW safely:

      args[0]  : tdms_path        (str)  — full path to .tdms file
      args[1]  : output_path      (str)  — full path for output .pdf
      args[2]  : x_label          (str)  — X-axis channel name
      args[3]  : y_labels_csv     (str)  — comma-separated Y channel names
      args[4]  : report_title     (str)  — report title (optional)
      args[5]  : doc_no           (str)  — document number (optional)
      args[6]  : left_logo_path   (str)  — path to left logo image (optional)
      args[7]  : right_logo_path  (str)  — path to right logo image (optional)
      args[8]  : footer_link_text (str)  — footer hyperlink label (optional)
      args[9]  : footer_link_url  (str)  — footer hyperlink URL (optional)
      args[10] : organization     (str)  — organization name (optional)
      args[11] : revision         (str)  — document revision e.g. 'Rev A' (optional)
      args[12] : channel_list_csv (str)  — ALL available channel names from
                                           LabVIEW, comma-separated (optional).
                                           When provided, Python uses these
                                           EXACT names for matching instead of
                                           guessing from the TDMS file keys.
                                           Add new channels here as your system grows.
    """
    try:
        if len(args) < 2:
            return "ERROR: At least tdms_path and output_path must be provided."

        tdms_path        = str(args[0])  if len(args) > 0  and args[0]  is not None else ""
        output_path      = str(args[1])  if len(args) > 1  and args[1]  is not None else ""
        x_label          = str(args[2])  if len(args) > 2  and args[2]  is not None else "Time(Sec)"
        y_labels_csv     = str(args[3])  if len(args) > 3  and args[3]  is not None else ""
        report_title     = str(args[4])  if len(args) > 4  and args[4]  is not None else ""
        doc_no           = str(args[5])  if len(args) > 5  and args[5]  is not None else ""
        left_logo_path   = str(args[6])  if len(args) > 6  and args[6]  is not None else ""
        right_logo_path  = str(args[7])  if len(args) > 7  and args[7]  is not None else ""
        footer_link_text = str(args[8])  if len(args) > 8  and args[8]  is not None else ""
        footer_link_url  = str(args[9])  if len(args) > 9  and args[9]  is not None else ""
        organization     = str(args[10]) if len(args) > 10 and args[10] is not None else ""
        revision         = str(args[11]) if len(args) > 11 and args[11] is not None else ""
        channel_list_csv = str(args[12]) if len(args) > 12 and args[12] is not None else ""

        if report_title:  REPORT_META["title"]    = report_title
        if doc_no:        REPORT_META["doc_no"]   = doc_no
        if organization:  REPORT_META["org"]      = organization
        if revision:      REPORT_META["revision"] = revision

        y_labels = [l.strip() for l in y_labels_csv.split(",") if l.strip()]
        if not y_labels:
            return "ERROR: y_labels_csv is empty."

        # Parse the known channel list (sent from LabVIEW)
        known_channels = [c.strip() for c in channel_list_csv.split(",")
                          if c.strip()] if channel_list_csv.strip() else None

        branding = {"left_logo_path":   left_logo_path.strip(),
                    "right_logo_path":  right_logo_path.strip(),
                    "footer_link_text": footer_link_text.strip(),
                    "footer_link_url":  footer_link_url.strip()}

        # Pass known_channels into the plot config so generate_pdf can use them
        generate_pdf(tdms_path,
                     [{"x_label": x_label,
                       "y_labels": y_labels,
                       "known_channels": known_channels}],
                     output_path, branding)

        # ── Write diagnostic log ──────────────────────────────────────────
        log = output_path.replace(".pdf", "_log.txt")
        try:
            raw_data = load_tdms(tdms_path)
            avail    = list(raw_data.keys())
            x_match  = best_match(x_label, avail)
            y_matches = [(lbl,
                          (best_match(best_match(lbl, known_channels) or lbl, avail)
                           if known_channels
                           else best_match(lbl, avail)) or "NOT FOUND")
                         for lbl in y_labels]
            with open(log, "w", encoding="utf-8") as f:
                f.write(f"SUCCESS {datetime.now()}\n")
                f.write(f"TDMS     : {tdms_path}\n")
                f.write(f"Output   : {output_path}\n")
                f.write(f"Org      : {organization or '(none)'}\n")
                f.write(f"Revision : {revision or '(none)'}\n")
                f.write(f"Known CH : {'YES (' + str(len(known_channels)) + ' channels)' if known_channels else 'NO (fuzzy only)'}\n\n")
                f.write("--- Channel Match Results ---\n")
                f.write(f"  X: '{x_label}' -> '{x_match or 'NOT FOUND'}'\n")
                for lbl, matched in y_matches:
                    ok = "OK " if matched != "NOT FOUND" else "!!!"
                    f.write(f"  [{ok}] Y '{lbl}' -> '{matched}'\n")
                f.write(f"\n--- Available TDMS channels ({len(avail)}) ---\n")
                for ch in avail:
                    f.write(f"  {ch}\n")
                if known_channels:
                    f.write(f"\n--- Provided channel list ({len(known_channels)}) ---\n")
                    for i, ch in enumerate(known_channels):
                        f.write(f"  [{i}] {ch}\n")
        except Exception as log_err:
            try:
                with open(log, "w", encoding="utf-8") as f:
                    f.write(f"SUCCESS (log error: {log_err})\n")
            except Exception:
                pass

        return f"SUCCESS: {output_path}"
    except Exception as exc:
        return f"ERROR: {exc}\n{traceback.format_exc(limit=4)}"


def generate_report_4args(tdms_path: str, output_path: str,
                          x_label: str, y_labels_csv: str) -> str:
    """Explicit 4-argument version for LabVIEW Python Node."""
    return generate_report_simple(tdms_path, output_path, x_label, y_labels_csv)


def generate_report_12args(tdms_path: str, output_path: str,
                            x_label: str, y_labels_csv: str,
                            report_title: str, doc_no: str,
                            left_logo_path: str, right_logo_path: str,
                            footer_link_text: str, footer_link_url: str,
                            organization: str, revision: str) -> str:
    """Explicit 12-argument version for LabVIEW Python Node."""
    return generate_report_simple(tdms_path, output_path, x_label, y_labels_csv,
                                  report_title, doc_no, left_logo_path, right_logo_path,
                                  footer_link_text, footer_link_url,
                                  organization, revision)


def generate_report_13args(tdms_path: str, output_path: str,
                            x_label: str, y_labels_csv: str,
                            report_title: str, doc_no: str,
                            left_logo_path: str, right_logo_path: str,
                            footer_link_text: str, footer_link_url: str,
                            organization: str, revision: str,
                            channel_list_csv: str) -> str:
    """
    Explicit 13-argument version for LabVIEW Python Node.
    channel_list_csv: ALL channel names from your system,
    comma-separated. Example:
    'Time(Sec),Normal Load (N),Friction Force(N),Coefficient of Friction,...'
    Add new channels here as your instrument grows.
    """
    return generate_report_simple(tdms_path, output_path, x_label, y_labels_csv,
                                  report_title, doc_no, left_logo_path, right_logo_path,
                                  footer_link_text, footer_link_url,
                                  organization, revision, channel_list_csv)


def generate_report_multi(*args) -> str:
    """
    Generate PDF — multiple plot groups from a JSON array.
    Accepts 3 to 7 positional arguments safely.
    """
    try:
        if len(args) < 3:
            return "ERROR: At least tdms_path, output_path, and plots_json must be provided."

        tdms_path        = str(args[0]) if len(args) > 0 and args[0] is not None else ""
        output_path      = str(args[1]) if len(args) > 1 and args[1] is not None else ""
        plots_json       = str(args[2]) if len(args) > 2 and args[2] is not None else "[]"
        left_logo_path   = str(args[3]) if len(args) > 3 and args[3] is not None else ""
        right_logo_path  = str(args[4]) if len(args) > 4 and args[4] is not None else ""
        footer_link_text = str(args[5]) if len(args) > 5 and args[5] is not None else ""
        footer_link_url  = str(args[6]) if len(args) > 6 and args[6] is not None else ""

        raw = json.loads(plots_json)
        if not isinstance(raw, list) or not raw:
            return "ERROR: plots_json must be a non-empty JSON array."
        plots_config = []
        for item in raw:
            x = item.get("x", "")
            y = item.get("y", [])
            if isinstance(y, str):
                y = [s.strip() for s in y.split(",") if s.strip()]
            if x and y:
                plots_config.append({"x_label": x, "y_labels": y})
        if not plots_config:
            return "ERROR: No valid plot groups in plots_json."

        branding = {"left_logo_path":   left_logo_path.strip(),
                    "right_logo_path":  right_logo_path.strip(),
                    "footer_link_text": footer_link_text.strip(),
                    "footer_link_url":  footer_link_url.strip()}

        generate_pdf(tdms_path, plots_config, output_path, branding)
        return f"SUCCESS: {output_path}"
    except json.JSONDecodeError as exc:
        return f"ERROR: Invalid JSON — {exc}"
    except Exception as exc:
        return f"ERROR: {exc}\n{traceback.format_exc(limit=4)}"


# ═══════════════════════════════════════════════════════════════
#  TKINTER GUI  (standalone use — not needed for LabVIEW)
# ═══════════════════════════════════════════════════════════════

GUI_BG  = "#F8FAFC"
GUI_CARD= "#EFF6FF"
GUI_HDR = "#1E3A5F"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TDMS Professional Report Generator")
        self.configure(bg=GUI_BG)
        self.geometry("980x900")
        self.resizable(True, True)
        self._plots = []
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

    def _section(self, parent, title):
        tk.Label(parent, text=title, bg=GUI_BG, fg=C["accent_navy"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(6,3))

    def _card(self, parent):
        f = tk.Frame(parent, bg=GUI_CARD, padx=14, pady=10,
                     relief="flat", bd=1,
                     highlightbackground=C["border"], highlightthickness=1)
        f.pack(fill="x")
        return f

    def _build_ui(self):
        hdr = tk.Frame(self, bg=GUI_HDR, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="TDMS Professional Report Generator",
                 font=("Segoe UI", 16, "bold"),
                 bg=GUI_HDR, fg="white").pack()
        tk.Label(hdr,
                 text="Each Y = separate subplot  ·  Logos  ·  Hyperlink  ·  Statistics",
                 font=("Segoe UI", 9), bg=GUI_HDR, fg="#BAE6FD").pack()

        body = tk.Frame(self, bg=GUI_BG, padx=24, pady=14)
        body.pack(fill="both", expand=True)

        self._tdms_var = tk.StringVar(value="No TDMS file selected…")
        self._out_var  = tk.StringVar(value="")
        for label, var, cmd in [
            ("📂  Open TDMS File", self._tdms_var, self._pick_tdms),
            ("💾  Output PDF",     self._out_var,  self._pick_output),
        ]:
            r = tk.Frame(body, bg=GUI_BG)
            r.pack(fill="x", pady=3)
            self._btn(r, label, cmd).pack(side="left")
            tk.Label(r, textvariable=var, bg=GUI_BG, fg=C["txt_muted"],
                     font=("Segoe UI", 9), anchor="w",
                     wraplength=680).pack(side="left", padx=12)

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=6)

        # Metadata
        self._section(body, "Report Metadata")
        mf = self._card(body)
        for i, (key, label) in enumerate([("title","Report Title"),
                                           ("org","Organization"),
                                           ("doc_no","Document No.")]):
            tk.Label(mf, text=label+":", bg=GUI_CARD, fg=C["txt_muted"],
                     font=("Segoe UI", 9)).grid(row=0, column=i*2,
                                                 sticky="w", padx=(4,4), pady=3)
            var = tk.StringVar(value=REPORT_META[key])
            var.trace_add("write",
                lambda *a, k=key, v=var: REPORT_META.update({k: v.get()}))
            tk.Entry(mf, textvariable=var, bg="white", fg=C["txt_dark"],
                     relief="solid", bd=1, font=("Segoe UI", 9),
                     width=24).grid(row=0, column=i*2+1,
                                    sticky="w", padx=(0,12), pady=3)

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=6)

        # Branding
        self._section(body, "Branding  —  Logos & Hyperlink")
        bf = self._card(body)
        self._left_logo_var  = tk.StringVar(value="")
        self._right_logo_var = tk.StringVar(value="")
        self._link_text_var  = tk.StringVar(value="")
        self._link_url_var   = tk.StringVar(value="")
        for ri, (label, var, is_file) in enumerate([
            ("Header LEFT logo  (PNG/JPG):", self._left_logo_var,  True),
            ("Header RIGHT logo (PNG/JPG):", self._right_logo_var, True),
            ("Footer link text:",            self._link_text_var,  False),
            ("Footer link URL:",             self._link_url_var,   False),
        ]):
            tk.Label(bf, text=label, bg=GUI_CARD, fg=C["txt_muted"],
                     font=("Segoe UI", 9)).grid(row=ri, column=0,
                                                 sticky="w", padx=(4,6), pady=3)
            tk.Entry(bf, textvariable=var, bg="white", fg=C["txt_dark"],
                     relief="solid", bd=1, font=("Segoe UI", 9),
                     width=52).grid(row=ri, column=1,
                                    sticky="ew", padx=(0,6), pady=3)
            if is_file:
                self._btn(bf, "Browse",
                          lambda v=var: self._browse_img(v),
                          bg=C["txt_muted"], hbg=C["accent_navy"],
                          fs=8).grid(row=ri, column=2, padx=(0,4), pady=3)
        bf.columnconfigure(1, weight=1)

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=6)

        # Plot builder
        self._section(body, "Configure X–Y Plots")
        builder = self._card(body)
        tk.Label(builder, text="X Axis:", bg=GUI_CARD, fg=C["txt_muted"],
                 font=("Segoe UI",9)).grid(row=0, column=0, sticky="w", pady=4)
        self._x_var = tk.StringVar(value=CHANNEL_LABELS[0])
        ttk.Combobox(builder, textvariable=self._x_var,
                     values=CHANNEL_LABELS, state="readonly",
                     width=44).grid(row=0, column=1, padx=10, sticky="w")
        tk.Label(builder, text="Y Channels\n(each = own subplot):",
                 bg=GUI_CARD, fg=C["txt_muted"],
                 font=("Segoe UI",9), justify="right").grid(
            row=1, column=0, sticky="nw", pady=6)
        yf = tk.Frame(builder, bg=GUI_CARD)
        yf.grid(row=1, column=1, padx=10, sticky="w")
        self._y_list = tk.Listbox(yf, selectmode=tk.MULTIPLE,
                                   bg="white", fg=C["txt_dark"],
                                   selectbackground=C["accent_blue"],
                                   selectforeground="white",
                                   font=("Segoe UI",9), height=7, width=52,
                                   activestyle="none", relief="solid", bd=1)
        for ch in CHANNEL_LABELS:
            self._y_list.insert(tk.END, ch)
        ys = ttk.Scrollbar(yf, orient="vertical", command=self._y_list.yview)
        self._y_list.configure(yscrollcommand=ys.set)
        self._y_list.pack(side="left")
        ys.pack(side="left", fill="y")
        self._btn(builder, "➕  Add Plot Group",
                  self._add_plot).grid(row=2, column=1, sticky="w", pady=(8,0))

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=6)
        self._section(body, "Queued Plot Groups")
        lf = tk.Frame(body, bg=GUI_CARD, relief="flat", bd=1,
                      highlightbackground=C["border"], highlightthickness=1)
        lf.pack(fill="both", expand=True)
        self._plot_lb = tk.Listbox(lf, bg="white", fg=C["txt_dark"],
                                    font=("Segoe UI",9), height=4,
                                    selectbackground=C["accent_blue"],
                                    selectforeground="white",
                                    activestyle="none", relief="flat", bd=0)
        self._plot_lb.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self._plot_lb.yview)
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
                                fg=C["accent_teal"], font=("Segoe UI",9))
        self._status.pack()
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("TCombobox", fieldbackground="white",
                    foreground=C["txt_dark"])

    def _browse_img(self, var):
        p = filedialog.askopenfilename(
            title="Select logo image",
            filetypes=[("Images","*.png *.jpg *.jpeg *.bmp"),
                       ("All files","*.*")])
        if p: var.set(p)

    def _pick_tdms(self):
        p = filedialog.askopenfilename(
            title="Select TDMS file",
            filetypes=[("TDMS","*.tdms"),("All","*.*")])
        if p:
            self._tdms_path = p
            self._tdms_var.set(p)
            self._out_var.set(os.path.splitext(p)[0] + "_report.pdf")

    def _pick_output(self):
        p = filedialog.asksaveasfilename(
            title="Save PDF as…", defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")])
        if p: self._out_var.set(p)

    def _add_plot(self):
        sel = self._y_list.curselection()
        if not sel:
            messagebox.showwarning("No Y", "Select at least one Y channel.")
            return
        y_labels = [CHANNEL_LABELS[i] for i in sel]
        self._plots.append({"x_label": self._x_var.get(),
                             "y_labels": y_labels})
        n = len(self._plots)
        self._plot_lb.insert(
            tk.END, f"Plot {n}:  {self._x_var.get()}  →  {' | '.join(y_labels)}")
        self._y_list.selection_clear(0, tk.END)
        self._status.config(
            text=f"✓  Plot {n} added ({len(y_labels)} subplots).",
            fg=C["accent_teal"])

    def _remove_plot(self):
        sel = self._plot_lb.curselection()
        if not sel: return
        idx = sel[0]
        self._plot_lb.delete(idx)
        self._plots.pop(idx)
        items = list(self._plot_lb.get(0, tk.END))
        self._plot_lb.delete(0, tk.END)
        for i, itm in enumerate(items):
            self._plot_lb.insert(
                tk.END, f"Plot {i+1}:  " + itm.split(":  ", 1)[-1])

    def _generate(self):
        if not self._tdms_path or not os.path.isfile(self._tdms_path):
            messagebox.showerror("Error", "Select a valid TDMS file.")
            return
        out = self._out_var.get()
        if not out:
            messagebox.showerror("Error", "Set output PDF path.")
            return
        if not self._plots:
            messagebox.showerror("Error", "Add at least one plot group.")
            return
        branding = {"left_logo_path":   self._left_logo_var.get().strip(),
                    "right_logo_path":  self._right_logo_var.get().strip(),
                    "footer_link_text": self._link_text_var.get().strip(),
                    "footer_link_url":  self._link_url_var.get().strip()}
        self._status.config(text="⏳  Generating…", fg=C["accent_blue"])
        self.update_idletasks()
        try:
            generate_pdf(self._tdms_path, self._plots, out, branding)
            self._status.config(text=f"✅  Saved: {out}", fg=C["accent_teal"])
            messagebox.showinfo("Done", f"Report saved!\n\n{out}")
        except Exception as exc:
            self._status.config(text=f"❌  {exc}", fg="#DC2626")
            messagebox.showerror("Error", str(exc))


# ═══════════════════════════════════════════════════════════════
#  CLI / ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def _cli_demo(tdms_path: str):
    plots_config = [
        {"x_label": "Time(Sec)",
         "y_labels": ["Normal Load (N)","Friction Force(N)",
                      "Coefficient of Friction"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["Depth (Microns)"]},
        {"x_label": "Sliding Distance (mm)",
         "y_labels": ["Coefficient of Friction","Friction Force(N)"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["Stage Temperature (Degree Celsius)",
                      "Sample Temperature (Degree Celsius)"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["Acoustic (mV)","ECR (ohms)"]},
        {"x_label": "Time(Sec)",
         "y_labels": ["Fx(N)","Fy(N)","Mx(Nm)","My(Nm)"]},
    ]
    generate_pdf(tdms_path, plots_config,
                 os.path.splitext(tdms_path)[0] + "_report.pdf")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        _cli_demo(sys.argv[1])
    else:
        App().mainloop()