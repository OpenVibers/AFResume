#!/usr/bin/env python3
"""Build the two-page US-Letter resume PDF from the site's own content.

Everything on the page comes from the repo so the PDF and alexfrison.net
never drift:

  src/data/profile.json              name, tagline, pitch, contact, metrics, education
  src/content/experience/*.json      roles, sorted by `order`
  src/content/skills/*.json          skill groups, sorted by `order`
  src/content/projects/<slug>.mdx    selected projects (frontmatter only)

Visual language: a colored gradient header banner, icon-circle metrics, pill-shaped
section headers with an icon, a role-kind icon in front of every job title, and an
icon per project card — the "awesome, icon-heavy" look the site's earlier resume PDF
had, rebuilt on the current content so it can never drift from the site again.

Run from the repo root:  python3 resume/build_resume.py
Output: public/<profile.resumePdf>  (public/Alex_Frison_Resume_Sep_2026.pdf)
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as _canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Content selection (labels only; no résumé text lives in this file)
# --------------------------------------------------------------------------
SELECTED_PROJECTS = [
    "openvibe-live",
    "openvibe-network",
    "powerchat-payments",
    "powerchat-developer-api",
    "live-translation",
    "irdr-autonomous-bot",
]
# Metrics strip: pick by a keyword found in the label, in this order.
# Falls back to the first four metrics if fewer than four match.
METRIC_KEYWORDS = ["services", "routes", "payment processors", "irdrs", "years"]
FULL_ROLES = 3            # roles with summary + all bullets on page 1
COMPACT_BULLETS = 2       # bullets per role on page 2

# --------------------------------------------------------------------------
# Palette — brighter than a plain business doc on purpose: this is the same
# blue/violet/coral/mint signal palette the site uses, just on paper.
# --------------------------------------------------------------------------
PAPER = HexColor("#f2f4fb")
CARD = HexColor("#ffffff")
CARD_TINT = HexColor("#f6f8ff")
BORDER = HexColor("#dbe1f5")
INK = HexColor("#0c1020")
BODY = HexColor("#2a3148")
MUTED = HexColor("#5c6683")
BLUE = HexColor("#3b63f0")
BLUE_DARK = HexColor("#22399c")
BLUE_SOFT = HexColor("#6c8bf5")
VIOLET = HexColor("#7c5cff")
CORAL = HexColor("#f0562a")
MINT = HexColor("#16b98a")
ICON_BG = HexColor("#e4eaff")

# --------------------------------------------------------------------------
# Page geometry
# --------------------------------------------------------------------------
PAGE_W, PAGE_H = letter
MARGIN = 28.0
CONTENT_W = PAGE_W - 2 * MARGIN
TOP = PAGE_H - MARGIN
BOTTOM = MARGIN
CARD_PAD = 7.0

# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
FONT_CANDIDATES = [
    ("Inter",
     "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
     "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
     None),
    ("Liberation Sans",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"),
    ("DejaVu Sans",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
]
FA_PATH = HERE / "fonts" / "fontawesome-webfont.ttf"

FONT = {"regular": "Helvetica", "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique", "label": "Helvetica (built-in)"}
UNICODE_OK = False


def dehinted(path: str) -> str:
    """Copy of a TTF with TrueType hinting stripped (viewers ignore it; subsetting keeps it)."""
    try:
        from fontTools.ttLib import TTFont as FTFont
    except ImportError:
        return path
    try:
        f = FTFont(path)
        for table in ("fpgm", "prep", "cvt ", "hdmx", "LTSH", "VDMX", "gasp", "kern", "GPOS", "GSUB", "DSIG"):
            if table in f:
                del f[table]
        glyf = f["glyf"]
        for g in glyf.glyphs.values():
            g.expand(glyf)
            if hasattr(g, "program"):
                g.program.fromBytecode(b"")
        out_dir = Path(tempfile.mkdtemp(prefix="resume-fonts-"))
        out = out_dir / Path(path).name
        f.save(str(out))
        return str(out)
    except Exception:
        return path


def register_fonts() -> None:
    global UNICODE_OK
    for label, reg, bold, ital in FONT_CANDIDATES:
        if os.path.exists(reg) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("Body", dehinted(reg)))
            pdfmetrics.registerFont(TTFont("Body-Bold", dehinted(bold)))
            if ital and os.path.exists(ital):
                pdfmetrics.registerFont(TTFont("Body-Italic", dehinted(ital)))
                italic = "Body-Italic"
            else:
                italic = "Body"
            pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic=italic, boldItalic="Body-Bold")
            FONT.update(regular="Body", bold="Body-Bold", italic=italic, label=label)
            UNICODE_OK = True
            break
    if not FA_PATH.exists():
        sys.exit(f"missing icon font: {FA_PATH}")
    pdfmetrics.registerFont(TTFont("FA", str(FA_PATH)))


# Font Awesome 4.7 code points — every one checked against the embedded font's cmap.
ICON = {
    "email": "", "phone": "", "site": "", "linkedin": "",
    "github": "", "location": "", "link": "", "education": "",
}
# Role `kind` (src/content/experience/*.json) → icon, mirrors the site's Timeline.astro.
KIND_ICON = {
    "engineering": "", "founder": "", "analytics": "",
    "operations": "", "sales": "",
}
# Project `category` (src/content/config.ts enum) → icon, mirrors ProjectGrid.astro.
CATEGORY_ICON = {
    "openvibe": "", "powerchat": "", "amazon": "", "ai": "",
    "infra": "", "game": "", "tools": "", "python": "",
    "hardware": "", "web": "",
}
# profile.json `metrics[].icon` (an FA6 class string, e.g. "fa-solid fa-cubes-stacked") →
# FA4 codepoint. Matched by the first keyword found, so a new metric icon degrades to a
# sensible default (star) instead of crashing.
METRIC_ICON_KEYWORDS = [
    ("cubes", ""), ("route", ""), ("code", ""), ("toolbox", ""),
    ("credit-card", ""), ("magnifying-glass", ""), ("tower-broadcast", ""),
    ("building", ""), ("chart", ""),
]
DEFAULT_ICON = ""  # star


def metric_icon(css_class: str) -> str:
    c = (css_class or "").lower()
    for kw, glyph in METRIC_ICON_KEYWORDS:
        if kw in c:
            return glyph
    return DEFAULT_ICON


# profile.json `seeking[].label` → icon for the feature-card row, matched by keyword.
SEEKING_ICON_KEYWORDS = [
    ("anything", ""), ("engineer", ""), ("analytic", ""), ("data", ""),
    ("sales", ""), ("ops", ""), ("support", ""), ("ai ", ""), ("founding", ""),
]


def seeking_icon(label: str) -> str:
    lo = (label or "").lower()
    for kw, glyph in SEEKING_ICON_KEYWORDS:
        if kw in lo:
            return glyph
    return DEFAULT_ICON

# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def load_json_dir(path: Path) -> list[dict]:
    items = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(path.glob("*.json"))]
    return sorted(items, key=lambda d: d.get("order", 999))


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    out: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key, raw = key.strip(), raw.strip()
        if raw.startswith(("{", "[")):
            try:
                out[key] = json.loads(raw)
            except json.JSONDecodeError:
                out[key] = raw
        elif len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            out[key] = raw[1:-1]
        elif raw in ("true", "false"):
            out[key] = raw == "true"
        else:
            try:
                out[key] = int(raw)
            except ValueError:
                out[key] = raw
    return out


def load_content() -> dict:
    profile = json.loads((ROOT / "src/data/profile.json").read_text(encoding="utf-8"))
    experience = load_json_dir(ROOT / "src/content/experience")
    skills = load_json_dir(ROOT / "src/content/skills")
    projects = []
    for slug in SELECTED_PROJECTS:
        fm = parse_frontmatter(ROOT / "src/content/projects" / f"{slug}.mdx")
        if fm:
            projects.append(fm)
    return dict(profile=profile, experience=experience, skills=skills, projects=projects)


def pick_metrics(metrics: list[dict]) -> list[dict]:
    picked = []
    for kw in METRIC_KEYWORDS:
        for m in metrics:
            if kw in m["label"].lower() and m not in picked:
                picked.append(m)
                break
    if len(picked) < 4:
        picked = metrics[:4]
    return picked[:5]


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------

def esc(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if not UNICODE_OK:
        s = s.replace("→", " to ").replace("×", "x")
    return s


def style(name: str, size: float, leading: float, color, font: str | None = None, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=font or FONT["regular"], fontSize=size, leading=leading,
                          textColor=color, alignment=TA_LEFT, **kw)


class Styles:
    def __init__(self) -> None:
        self.body = style("body", 8.7, 10.8, BODY)
        self.summary = style("summary", 8.0, 9.6, MUTED, FONT["italic"])
        self.bullet = style("bullet", 8.1, 9.5, BODY, leftIndent=9, bulletIndent=0,
                            bulletFontName=FONT["regular"], bulletFontSize=8.1, bulletColor=BLUE)
        self.bullet_compact = style("bulletc", 8.1, 9.5, BODY, leftIndent=9, bulletIndent=0,
                                    bulletFontName=FONT["regular"], bulletFontSize=8.1, bulletColor=BLUE)
        self.stack = style("stack", 6.9, 8.3, MUTED)
        self.metric_label = style("mlabel", 7.0, 8.5, MUTED)
        self.proj_title = style("ptitle", 8.5, 10.2, INK, FONT["bold"])
        self.proj_summary = style("psum", 7.5, 9.0, BODY)
        self.proj_link = style("plink", 7.3, 8.8, BLUE)
        self.skill_items = style("skills", 8.3, 10.1, BODY)
        self.edu = style("edu", 8.3, 10.1, BODY)
        self.chip = style("chip", 7.6, 9.2, BLUE_DARK, FONT["bold"])
        self.hero_line = style("heroline", 8.6, 11.2, white)


def para(text: str, st: ParagraphStyle, bullet: str | None = None) -> Paragraph:
    return Paragraph(text, st, bulletText=bullet) if bullet else Paragraph(text, st)


def para_height(p: Paragraph, width: float) -> float:
    _, h = p.wrap(width, 10_000)
    return h


def draw_para(c, p: Paragraph, x: float, y_top: float, width: float) -> float:
    """Draw paragraph with its top edge at y_top; return its height."""
    _, h = p.wrap(width, 10_000)
    p.drawOn(c, x, y_top - h)
    return h


def truncate_to_lines(text: str, st: ParagraphStyle, width: float, max_lines: int) -> tuple[str, bool]:
    """Shorten `text` word by word until it fits in max_lines. Returns (text, truncated)."""
    limit = st.leading * max_lines + 0.5
    if para_height(Paragraph(esc(text), st), width) <= limit:
        return text, False
    words = text.split()
    while words:
        words.pop()
        candidate = " ".join(words).rstrip(",;:") + "…"
        if para_height(Paragraph(esc(candidate), st), width) <= limit:
            return candidate, True
    return "…", True


def icon(c, x: float, y_base: float, glyph: str, size: float, color) -> float:
    c.saveState()
    c.setFont("FA", size)
    c.setFillColor(color)
    c.drawString(x, y_base, glyph)
    c.restoreState()
    return pdfmetrics.stringWidth(glyph, "FA", size)


def icon_circle(c, cx: float, cy: float, r: float, glyph: str, fg, bg, font_size: float, stroke=None) -> None:
    """A filled circle with a centered FontAwesome glyph — the site's recurring icon-badge motif."""
    c.saveState()
    c.setFillColor(bg)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(0.8)
        c.circle(cx, cy, r, stroke=1, fill=1)
    else:
        c.circle(cx, cy, r, stroke=0, fill=1)
    c.setFont("FA", font_size)
    c.setFillColor(fg)
    gw = pdfmetrics.stringWidth(glyph, "FA", font_size)
    c.drawString(cx - gw / 2, cy - font_size * 0.36, glyph)
    c.restoreState()


def hairline(c, x0: float, y: float, x1: float, color=BORDER, width: float = 0.6) -> None:
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x0, y, x1, y)
    c.restoreState()


def card(c, x: float, y_top: float, w: float, h: float, radius: float = 8.0, fill=CARD, stroke=BORDER) -> None:
    c.saveState()
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.75)
    c.roundRect(x, y_top - h, w, h, radius, stroke=1, fill=1)
    c.restoreState()


def chip(c, x: float, y_base: float, text: str, st: ParagraphStyle, glyph: str | None = None,
         fg=BLUE_DARK, bg=ICON_BG, border=None) -> float:
    """A small rounded pill — used for the header's role chips. Returns the width consumed."""
    isize = st.fontSize + 0.4
    iw = (pdfmetrics.stringWidth(glyph, "FA", isize) + 5) if glyph else 0
    tw = pdfmetrics.stringWidth(text, st.fontName, st.fontSize)
    pad_x, h = 8.0, st.leading + 6
    w = pad_x * 2 + iw + tw
    c.saveState()
    c.setFillColor(bg)
    if border:
        c.setStrokeColor(border)
        c.setLineWidth(0.8)
        c.roundRect(x, y_base - 3.4, w, h, h / 2, stroke=1, fill=1)
    else:
        c.roundRect(x, y_base - 3.4, w, h, h / 2, stroke=0, fill=1)
    cx = x + pad_x
    if glyph:
        icon(c, cx, y_base, glyph, isize, fg)
        cx += iw
    c.setFillColor(fg)
    c.setFont(st.fontName, st.fontSize)
    c.drawString(cx, y_base, text)
    c.restoreState()
    return w


def gradient_bar(c) -> None:
    """Signature 3-stop bar across the very top of the page."""
    c.saveState()
    p = c.beginPath()
    p.rect(0, PAGE_H - 5, PAGE_W, 5)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(0, PAGE_H, PAGE_W, PAGE_H, [BLUE, VIOLET, CORAL], [0.0, 0.5, 1.0], extend=True)
    c.restoreState()


def page_background(c) -> None:
    c.saveState()
    c.setFillColor(PAPER)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    c.restoreState()
    gradient_bar(c)


SECTION_LABEL_SIZE = 7.8
SECTION_PILL_H = 16.0
SECTION_GAP = 5.0


def section_header(c, x: float, y_top: float, text: str, width: float, glyph: str) -> float:
    """A colored capsule with an icon disc and a white label — the site's section-header motif,
    on paper. Returns the height consumed (the capsule plus a little breathing room)."""
    h = SECTION_PILL_H
    c.saveState()
    c.setFillColor(BLUE)
    c.roundRect(x, y_top - h, width, h, h / 2, stroke=0, fill=1)
    c.restoreState()
    icon_circle(c, x + h / 2, y_top - h / 2, h / 2 - 2.6, glyph, BLUE, BLUE_SOFT, 7.8)
    c.saveState()
    c.setFillColor(white)
    c.setFont(FONT["bold"], SECTION_LABEL_SIZE)
    c.drawString(x + h + 3, y_top - h / 2 - SECTION_LABEL_SIZE * 0.36, text)
    c.restoreState()
    return h + SECTION_GAP


# --------------------------------------------------------------------------
# Blocks. Each block function draws when `draw` is True and always returns
# the height it occupies, so callers can measure before drawing a card.
# --------------------------------------------------------------------------

def block_header(c, profile: dict, st: Styles, y_top: float, draw: bool) -> float:
    """A full-width blue banner: name + tagline on the left, a contact panel on the
    right — the site's hero, compressed onto paper. Compact on purpose: the feature-card
    row right under it (block_feature_cards) is where the "what I do" chips live now."""
    x = MARGIN
    w = CONTENT_W
    name_size, tag_size = 20.0, 9.2
    pad = 12.0

    items = [
        ("email", profile.get("emailDisplay") or profile.get("email"), f"mailto:{profile['email']}" if profile.get("email") else None),
        ("phone", profile.get("phoneDisplay") or profile.get("phone"), f"tel:{profile['phone']}" if profile.get("phone") else None),
        ("site", profile.get("siteDisplay"), profile.get("site")),
        ("linkedin", profile.get("linkedinDisplay"), profile.get("linkedin")),
    ]
    items = [it for it in items if it[1]]
    panel_w = 168.0
    row_h = 13.0
    panel_h = pad * 0.5 + len(items) * row_h

    banner_h = pad + name_size * 0.78 + 5 + tag_size * 0.78 + pad
    banner_h = max(banner_h, pad * 1.6 + panel_h)

    if draw:
        c.saveState()
        c.setFillColor(BLUE)
        c.roundRect(x, y_top - banner_h, w, banner_h, 12, stroke=0, fill=1)
        p = c.beginPath()
        p.roundRect(x, y_top - banner_h, w, banner_h, 12)
        c.clipPath(p, stroke=0, fill=0)
        c.setFillColor(VIOLET)
        c.setFillAlpha(0.16)
        c.ellipse(x + w - 60, y_top - banner_h + 4, x + w + 90, y_top - banner_h + 110, stroke=0, fill=1)
        c.restoreState()

    ty = y_top - pad
    if draw:
        c.setFillColor(white)
        c.setFont(FONT["bold"], name_size)
        c.drawString(x + pad, ty - name_size * 0.78, profile["name"])
    ty -= name_size * 0.78 + 5
    if draw:
        c.setFillColor(HexColor("#dbe4ff"))
        c.setFont(FONT["regular"], tag_size)
        c.drawString(x + pad, ty - tag_size * 0.78, profile["tagline"])

    px = x + w - panel_w - pad
    py_top = y_top - (banner_h - panel_h) / 2
    if draw:
        c.saveState()
        c.setFillColor(white)
        c.setFillAlpha(0.14)
        c.roundRect(px, py_top - panel_h, panel_w, panel_h, 9, stroke=0, fill=1)
        c.restoreState()
        base = py_top - row_h * 0.72
        for key, text, url in items:
            icon_circle(c, px + 12, base + 2.4, 7.6, ICON[key], white, HexColor("#5578e8"), 6.8)
            c.setFillColor(white)
            c.setFont(FONT["regular"], 7.6)
            c.drawString(px + 24, base, text)
            if url:
                c.linkURL(url, (px, base - 4, px + panel_w, base + 10), relative=0, thickness=0)
            base -= row_h
        loc = profile.get("locationShort") or profile.get("location")
        if loc:
            icon_circle(c, px + 12, base + 2.4, 7.6, ICON["location"], white, HexColor("#5578e8"), 6.8)
            c.setFillColor(white)
            c.setFont(FONT["regular"], 7.6)
            c.drawString(px + 24, base, loc)

    return banner_h


def block_feature_cards(c, seeking: list[dict], st: Styles, y_top: float, draw: bool) -> float:
    """A row of small icon-badge chips, one per profile.json `seeking` entry — the "what I'm
    open to" teaser row the earlier resume design had, now driven by the same list the site's
    Now.astro section renders, so it can't say something different from the site. Deliberately
    compact (one line each): the detail sentence behind each label lives on the site."""
    n = max(1, len(seeking))
    gap = 7.0
    w = (CONTENT_W - gap * (n - 1)) / n
    pad = 6.0
    icon_r = 7.0
    inner_w = w - 2 * pad - icon_r * 2 - 5
    label_st = ParagraphStyle("fclabel", fontName=FONT["bold"], fontSize=7.6, leading=8.8, textColor=INK)
    h = pad * 2 + icon_r * 2
    if draw:
        for i, s in enumerate(seeking):
            x = MARGIN + i * (w + gap)
            card(c, x, y_top, w, h, radius=h / 2, fill=CARD_TINT)
            cy = y_top - h / 2
            icon_circle(c, x + pad + icon_r, cy, icon_r, seeking_icon(s["label"]), BLUE, ICON_BG, 7.6)
            label, _ = truncate_to_lines(s["label"], label_st, inner_w, 2)
            draw_para(c, para(esc(label), label_st), x + pad + icon_r * 2 + 6, cy + label_st.leading * 0.42, inner_w)
    return h


def block_metrics(c, metrics: list[dict], st: Styles, y_top: float, draw: bool) -> float:
    n = len(metrics)
    gap = 8.0
    w = (CONTENT_W - gap * (n - 1)) / n
    num_size, suf_size = 14.5, 8.4
    pad = 6.0
    icon_r = 8.0
    inner_w = w - 2 * pad
    label_paras = [para(esc(m["label"]), st.metric_label) for m in metrics]
    label_h = max(para_height(p, inner_w) for p in label_paras)
    h = pad + icon_r * 2 + 4 + num_size * 0.78 + 3 + label_h + pad
    if draw:
        for i, (m, lp) in enumerate(zip(metrics, label_paras)):
            x = MARGIN + i * (w + gap)
            card(c, x, y_top, w, h, radius=10, fill=CARD_TINT)
            top = y_top - pad
            icon_circle(c, x + pad + icon_r, top - icon_r, icon_r, metric_icon(m.get("icon", "")), BLUE, ICON_BG, 8.2)
            base = top - icon_r * 2 - 4 - num_size * 0.78
            c.setFillColor(CORAL)
            c.setFont(FONT["bold"], num_size)
            num = f"{m['num']:,}" if isinstance(m["num"], int) else str(m["num"])
            c.drawString(x + pad, base, num)
            nw = pdfmetrics.stringWidth(num, FONT["bold"], num_size)
            if m.get("suffix"):
                c.setFont(FONT["bold"], suf_size)
                c.drawString(x + pad + nw + 1, base, m["suffix"])
            draw_para(c, lp, x + pad, base - 4, inner_w)
    return h


def block_profile(c, profile: dict, st: Styles, y_top: float, draw: bool) -> float:
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_header(c, x, y, "Profile", w, "")
    y -= SECTION_PILL_H + SECTION_GAP
    p = para(esc(profile["pitch"]), st.body)
    h = para_height(p, w)
    if draw:
        draw_para(c, p, x, y, w)
    y -= h + 1
    y -= CARD_PAD
    return y_top - y


def role_header(c, role: dict, st: Styles, x: float, w: float, y_top: float, draw: bool) -> float:
    """Kind icon, role title, company · location, right-aligned dates (mint dot if current)."""
    title_size, meta_size, date_size = 9.5, 8.3, 8.1
    icon_col = 15.0
    y = y_top
    dates = f"{role.get('start', '')} – {role.get('end', '')}".strip(" –")
    dw = pdfmetrics.stringWidth(dates, FONT["regular"], date_size)
    base = y - title_size * 0.78
    if draw:
        glyph = KIND_ICON.get(role.get("kind"), DEFAULT_ICON)
        icon_circle(c, x + 6, base + title_size * 0.28, 7.4, glyph, BLUE, ICON_BG, 7.2)
        c.setFillColor(INK)
        c.setFont(FONT["bold"], title_size)
        c.drawString(x + icon_col, base, role["role"])
        c.setFillColor(MUTED)
        c.setFont(FONT["regular"], date_size)
        c.drawRightString(x + w, base + 0.6, dates)
        if role.get("current") or str(role.get("end", "")).lower() == "present":
            c.setFillColor(MINT)
            c.circle(x + w - dw - 7.5, base + 3.4, 2.1, stroke=0, fill=1)
    y = base - 2.6
    base = y - meta_size * 0.78
    if draw:
        c.setFillColor(BLUE)
        c.setFont(FONT["bold"], meta_size)
        c.drawString(x + icon_col, base, role["company"])
        cw = pdfmetrics.stringWidth(role["company"], FONT["bold"], meta_size)
        if role.get("link"):
            c.linkURL(role["link"], (x + icon_col, base - 2, x + icon_col + cw, base + meta_size), relative=0, thickness=0)
        if role.get("location"):
            c.setFillColor(MUTED)
            c.setFont(FONT["regular"], meta_size)
            c.drawString(x + icon_col + cw, base, f"  ·  {role['location']}")
    y = base - 2.0
    return y_top - y


def stack_line(c, role: dict, st: Styles, x: float, w: float, y_top: float, draw: bool) -> float:
    stack = role.get("stack") or []
    if not stack:
        return 0
    p = para(f"<b>Stack</b>&nbsp;&nbsp;{esc(' · '.join(stack))}", st.stack)
    h = para_height(p, w)
    if draw:
        draw_para(c, p, x + 15.0, y_top, w - 15.0)
    return h


def block_role_full(c, role: dict, st: Styles, x: float, w: float, y_top: float, draw: bool) -> float:
    y = y_top
    y -= role_header(c, role, st, x, w, y, draw)
    xi, wi = x + 15.0, w - 15.0
    if role.get("summary"):
        p = para(esc(role["summary"]), st.summary)
        h = para_height(p, wi)
        if draw:
            draw_para(c, p, xi, y, wi)
        y -= h + 2.5
    for b in role.get("bullets", []):
        p = para(esc(b), st.bullet, bullet="•")
        h = para_height(p, wi)
        if draw:
            draw_para(c, p, xi, y, wi)
        y -= h
    y -= 1.8
    y -= stack_line(c, role, st, x, w, y, draw)
    return y_top - y


def block_role_compact(c, role: dict, st: Styles, x: float, w: float, y_top: float, draw: bool) -> float:
    y = y_top
    y -= role_header(c, role, st, x, w, y, draw)
    xi, wi = x + 15.0, w - 15.0
    for b in role.get("bullets", [])[:COMPACT_BULLETS]:
        p = para(esc(b), st.bullet_compact, bullet="•")
        h = para_height(p, wi)
        if draw:
            draw_para(c, p, xi, y, wi)
        y -= h
    return y_top - y


def block_experience(c, roles: list[dict], st: Styles, y_top: float, label: str, compact: bool, draw: bool) -> float:
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_header(c, x, y, label, w, "")
    y -= SECTION_PILL_H + SECTION_GAP
    fn = block_role_compact if compact else block_role_full
    sep = 4.0 if compact else 5.0
    for i, role in enumerate(roles):
        if i:
            if draw:
                hairline(c, x, y - sep / 2, x + w)
            y -= sep
        y -= fn(c, role, st, x, w, y, draw)
    y -= CARD_PAD - 1
    return y_top - y


def block_projects(c, projects: list[dict], st: Styles, y_top: float, draw: bool) -> tuple[float, list[str]]:
    """2 rows × 3 columns of small cards, each with a category icon. Returns (height, truncated titles)."""
    truncated: list[str] = []
    y = y_top
    if draw:
        section_header(c, MARGIN, y, "Selected work", CONTENT_W, "")
    y -= SECTION_PILL_H + SECTION_GAP
    cols, gap, pad = 3, 8.0, 7.0
    cw = (CONTENT_W - gap * (cols - 1)) / cols
    icon_col = 20.0
    inner = cw - 2 * pad
    title_w = inner - icon_col
    max_lines = 3
    prepared = []
    for pr in projects:
        title = pr.get("title", "")
        summary, trunc = truncate_to_lines(pr.get("summary", ""), st.proj_summary, inner, max_lines)
        if trunc:
            truncated.append(title)
        url = (pr.get("links") or {}).get("live") if isinstance(pr.get("links"), dict) else None
        prepared.append((title, summary, url, pr.get("category")))
    title_h = st.proj_title.leading
    sum_h = st.proj_summary.leading * max_lines
    link_h = st.proj_link.leading
    ch = pad + title_h + 3 + sum_h + 3 + link_h + pad
    rows = (len(prepared) + cols - 1) // cols
    if draw:
        for i, (title, summary, url, cat) in enumerate(prepared):
            r, col = divmod(i, cols)
            x = MARGIN + col * (cw + gap)
            top = y - r * (ch + gap)
            card(c, x, top, cw, ch, radius=8)
            ty = top - pad
            glyph = CATEGORY_ICON.get(cat, DEFAULT_ICON)
            icon_circle(c, x + pad + 6.5, ty - 6.5, 7.0, glyph, BLUE, ICON_BG, 7.0)
            tsize = st.proj_title.fontSize
            while tsize > 7.2 and pdfmetrics.stringWidth(title, FONT["bold"], tsize) > title_w:
                tsize -= 0.2
            c.setFillColor(INK)
            c.setFont(FONT["bold"], tsize)
            c.drawString(x + pad + icon_col, ty - tsize * 0.78, title)
            ty -= title_h + 3
            draw_para(c, para(esc(summary), st.proj_summary), x + pad, ty, inner)
            ty -= sum_h + 3
            if url:
                disp = re.sub(r"^https?://", "", url).rstrip("/")
                iw = icon(c, x + pad, ty - st.proj_link.fontSize * 0.78, ICON["link"], 7.0, BLUE)
                c.setFillColor(BLUE)
                c.setFont(FONT["regular"], st.proj_link.fontSize)
                c.drawString(x + pad + iw + 4, ty - st.proj_link.fontSize * 0.78, disp)
                c.linkURL(url, (x, top - ch, x + cw, top), relative=0, thickness=0)
    y -= rows * ch + (rows - 1) * gap
    return y_top - y, truncated


def block_skills(c, skills: list[dict], st: Styles, y_top: float, draw: bool) -> float:
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_header(c, x, y, "Skills", w, "")
    y -= SECTION_PILL_H + SECTION_GAP
    row_gap = 2.6
    for i, g in enumerate(skills):
        items = [it["name"] for it in g.get("items", []) if it.get("name")]
        label = f'<font name="{FONT["bold"]}" size="6.8" color="#22399c">{esc(g["group"].upper())}</font>'
        p = para(f"{label}&nbsp;&nbsp;&nbsp;{esc(' · '.join(items))}", st.skill_items)
        h = para_height(p, w)
        if draw:
            if i:
                hairline(c, x, y + row_gap / 2 + 0.5, x + w, BORDER, 0.4)
            draw_para(c, p, x, y, w)
        y -= h + row_gap
    y -= CARD_PAD - row_gap
    return y_top - y


def block_education(c, profile: dict, st: Styles, y_top: float, draw: bool) -> float:
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_header(c, x, y, "Education & links", w, "")
    y -= SECTION_PILL_H + SECTION_GAP
    p = para(esc(profile.get("education", "")), st.edu)
    h = para_height(p, w)
    if draw:
        draw_para(c, p, x, y, w)
    y -= h + 4
    links = [
        ("site", profile.get("siteDisplay"), profile.get("site")),
        ("github", profile.get("githubDisplay"), profile.get("github")),
        ("linkedin", profile.get("linkedinDisplay"), profile.get("linkedin")),
        ("email", profile.get("emailDisplay"), f"mailto:{profile['email']}" if profile.get("email") else None),
    ]
    size, isize = 8.1, 7.6
    base = y - size * 0.78
    cx = x
    if draw:
        for key, text, url in links:
            if not (text and url):
                continue
            icon_circle(c, cx + 6.5, base + 3.0, 7.0, ICON[key], BLUE, ICON_BG, 7.0)
            c.setFillColor(BLUE)
            c.setFont(FONT["regular"], size)
            c.drawString(cx + 15, base, text)
            tw = 15 + pdfmetrics.stringWidth(text, FONT["regular"], size)
            c.linkURL(url, (cx, base - 2, cx + tw, base + size), relative=0, thickness=0)
            cx += tw + 16
    y = base - 2 - CARD_PAD
    return y_top - y


def footer(c, profile: dict, page: int, total: int, updated: str) -> None:
    size = 7.3
    base = 18.0
    c.saveState()
    c.setFillColor(MUTED)
    c.setFont(FONT["regular"], size)
    if page == total:
        text = f"{profile['name']}  ·  {profile.get('siteDisplay', '')}  ·  updated {updated}"
        c.drawString(MARGIN, base, text)
        if profile.get("site"):
            c.linkURL(profile["site"], (MARGIN, base - 2, MARGIN + pdfmetrics.stringWidth(text, FONT["regular"], size), base + size), relative=0, thickness=0)
    else:
        c.drawString(MARGIN, base, f"{profile['name']}  ·  continued on page {page + 1}")
    c.drawRightString(PAGE_W - MARGIN, base, f"{page} / {total}")
    c.restoreState()


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------
MONTHS = {"jan": "January", "feb": "February", "mar": "March", "apr": "April", "may": "May", "jun": "June",
          "jul": "July", "aug": "August", "sep": "September", "oct": "October", "nov": "November", "dec": "December"}


def updated_label(pdf_name: str) -> str:
    m = re.search(r"_([A-Za-z]{3})_(\d{4})\.pdf$", pdf_name)
    if m and m.group(1).lower() in MONTHS:
        return f"{MONTHS[m.group(1).lower()]} {m.group(2)}"
    return _dt.date.today().strftime("%B %Y")


def build(out_path: Path) -> dict:
    data = load_content()
    profile, experience, skills, projects = data["profile"], data["experience"], data["skills"], data["projects"]
    st = Styles()
    report: dict = {"truncated": [], "warnings": []}

    c = _canvas.Canvas(str(out_path), pagesize=letter, pageCompression=1)
    c.setTitle(f"{profile['name']} – Resume")
    c.setAuthor(profile["name"])
    c.setSubject(profile.get("tagline", ""))
    c.setCreator("resume/build_resume.py (reportlab)")
    c.setKeywords(", ".join(profile.get("roles", [])))
    updated = updated_label(out_path.name)

    def measured(fn, *args):
        """Return (height, drawer) so the enclosing card can be drawn first."""
        h = fn(c, *args, draw=False)
        return h, (lambda: fn(c, *args, draw=True))

    def check(y: float, what: str) -> None:
        if y < BOTTOM:
            report["warnings"].append(f"{what} overflows page bottom by {BOTTOM - y:.1f}pt")

    # ---- Page 1 ----
    page_background(c)
    y = TOP
    y -= block_header(c, profile, st, y, draw=True)
    y -= 6
    y -= block_feature_cards(c, profile.get("seeking", []), st, y, draw=True)
    y -= 6
    y -= block_metrics(c, pick_metrics(profile["metrics"]), st, y, draw=True)
    y -= 7
    h, drawer = measured(block_profile, profile, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h + 7
    h, drawer = measured(block_experience, experience[:FULL_ROLES], st, y, "Experience", False)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h
    check(y, "page 1 experience")
    report["page1_bottom_gap"] = y - BOTTOM
    footer(c, profile, 1, 2, updated)
    c.showPage()

    # ---- Page 2 ----
    page_background(c)
    y = TOP
    h, drawer = measured(block_experience, experience[FULL_ROLES:], st, y, "Experience (continued)", True)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h + 6
    h, truncated = block_projects(c, projects, st, y, draw=True)
    report["truncated"] = truncated
    y -= h + 6
    h, drawer = measured(block_skills, skills, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h + 6
    h, drawer = measured(block_education, profile, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h
    check(y, "page 2 education")
    report["page2_bottom_gap"] = y - BOTTOM
    footer(c, profile, 2, 2, updated)
    c.showPage()
    c.save()
    return report


def main() -> None:
    register_fonts()
    profile = json.loads((ROOT / "src/data/profile.json").read_text(encoding="utf-8"))
    rel = profile.get("resumePdf", "/Alex_Frison_Resume.pdf").lstrip("/")
    out = ROOT / "public" / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    report = build(out)
    size_kb = out.stat().st_size / 1024
    print(f"wrote {out} ({size_kb:.1f} KB)")
    print(f"text font: {FONT['label']}; icons: Font Awesome 4")
    print(f"page 1 bottom gap: {report['page1_bottom_gap']:.1f}pt; page 2 bottom gap: {report['page2_bottom_gap']:.1f}pt")
    if report["truncated"]:
        print("truncated project summaries: " + ", ".join(report["truncated"]))
    for w in report["warnings"]:
        print("WARNING: " + w)
    if report["warnings"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
