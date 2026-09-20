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
FULL_ROLES = 2            # roles with summary + all bullets on page 1 (feature-cards + a full metrics strip need the room)
COMPACT_BULLETS = 2       # bullets per role on page 2

# --------------------------------------------------------------------------
# Palette — brighter than a plain business doc on purpose: this is the same
# blue/violet/coral/mint signal palette the site uses, just on paper.
# --------------------------------------------------------------------------
PAPER = HexColor("#f2f4fb")
CARD = HexColor("#ffffff")
CARD_TINT = HexColor("#eef1fc")
BORDER = HexColor("#c3ccec")
INK = HexColor("#0c1020")
BODY = HexColor("#2a3148")
MUTED = HexColor("#5c6683")
BLUE = HexColor("#3b63f0")
BLUE_DARK = HexColor("#22399c")
BLUE_SOFT = HexColor("#6c8bf5")
VIOLET = HexColor("#7c5cff")
CORAL = HexColor("#f0562a")
MINT = HexColor("#16b98a")
ICON_BG = HexColor("#dbe3ff")

# --------------------------------------------------------------------------
# Page geometry
# --------------------------------------------------------------------------
PAGE_W, PAGE_H = letter
MARGIN = 28.0
CONTENT_W = PAGE_W - 2 * MARGIN
TOP = PAGE_H - MARGIN
BOTTOM = MARGIN
CARD_PAD = 6.5

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


# Proper nouns worth bolding wherever they appear in a bullet or the profile paragraph — the
# same trick the earlier resume PDF used to make itself skimmable in five seconds. Numbers with
# a "+"/"K+"/"%" are bolded unconditionally (they're never inside a URL or code fragment here).
HIGHLIGHT_TERMS = [
    "OpenVibe", "PowerChat", "Amazon", "Verizon Wireless", "GameServerStats",
    "Anthropic", "SOX", "OAuth2", "Streamlabs",
]
_HIGHLIGHT_NUM_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?(?:\+|[Kk]\+|%)")
_HIGHLIGHT_TERM_RE = re.compile("|".join(re.escape(t) for t in sorted(HIGHLIGHT_TERMS, key=len, reverse=True)))


def highlight(text: str) -> str:
    """esc() the text, then wrap standout numbers and known proper nouns in <b>. Order matters:
    escaping first means the regexes only ever see already-safe text, so re.sub can't reopen a
    tag or eat an entity."""
    s = esc(text)
    s = _HIGHLIGHT_NUM_RE.sub(lambda m: f"<b>{m.group(0)}</b>", s)
    s = _HIGHLIGHT_TERM_RE.sub(lambda m: f"<b>{m.group(0)}</b>", s)
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


def hairline(c, x0: float, y: float, x1: float, color=None, width: float = 0.6) -> None:
    c.saveState()
    c.setStrokeColor(BORDER if color is None else color)
    c.setLineWidth(width)
    c.line(x0, y, x1, y)
    c.restoreState()


def vline(c, x: float, y0: float, y1: float, color=None, width: float = 0.6) -> None:
    c.saveState()
    c.setStrokeColor(BORDER if color is None else color)
    c.setLineWidth(width)
    c.line(x, y0, x, y1)
    c.restoreState()


SHADOW = HexColor("#c5cce3")


def card(c, x: float, y_top: float, w: float, h: float, radius: float = 8.0, fill=None, stroke=None,
         shadow: bool = True) -> None:
    """A rounded card with a real drop shadow and a visibly darker border than the page
    background — the earlier version's near-white-on-near-white fill made every card
    disappear at normal viewing size. This one is meant to read as a distinct card even on a
    phone screen, not just at full zoom.

    fill/stroke default to None (resolved to the *current* CARD/BORDER globals here, not at
    def-time) so build_themed_pdfs.py can repoint the whole palette per call to configure_palette()
    and every already-defined function picks it up on its next call."""
    fill = CARD if fill is None else fill
    stroke = BORDER if stroke is None else stroke
    c.saveState()
    if shadow:
        c.setFillColor(SHADOW)
        c.roundRect(x + 1.6, y_top - h - 1.6, w, h, radius, stroke=0, fill=1)
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(1.1)
    c.roundRect(x, y_top - h, w, h, radius, stroke=1, fill=1)
    c.restoreState()


def chip(c, x: float, y_base: float, text: str, st: ParagraphStyle, glyph: str | None = None,
         fg=None, bg=None, border=None) -> float:
    """A small rounded pill. Currently unused by block_header (which draws its chips inline so
    it can lay them out on the banner itself), kept for any future inline-pill need."""
    fg = BLUE_DARK if fg is None else fg
    bg = ICON_BG if bg is None else bg
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
        ("location", profile.get("locationShort") or profile.get("location"), None),
    ]
    items = [it for it in items if it[1]]
    panel_w = 178.0
    row_h = 13.0
    panel_h = pad * 0.5 + len(items) * row_h

    # Role chips, wrapped into rows against the space left of the contact panel — computed once,
    # geometrically, and reused for both the height calc and the draw pass, so (unlike the
    # feature cards above) there is no separate "measure" vs "draw" width that could disagree.
    roles = (profile.get("roles") or [])[:6]
    chip_font, chip_size, chip_pad_x, chip_gap = FONT["bold"], 7.6, 20.0, 7.0
    chips_w = w - pad * 2 - panel_w - 14
    chip_rows: list[list[tuple[str, float]]] = [[]]
    cx = 0.0
    for r in roles:
        cw = pdfmetrics.stringWidth(r, chip_font, chip_size) + chip_pad_x
        if cx > 0 and cx + cw > chips_w:
            chip_rows.append([])
            cx = 0.0
        chip_rows[-1].append((r, cw))
        cx += cw + chip_gap
    chip_h = chip_size + 10
    chips_total_h = len(chip_rows) * chip_h + max(0, len(chip_rows) - 1) * 5

    banner_h = pad + name_size * 0.78 + 5 + tag_size * 0.78 + 12 + chips_total_h + pad
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
    ty -= tag_size * 0.78 + 12

    if draw:
        row_top = ty
        for row in chip_rows:
            cx2 = x + pad
            for text, cw in row:
                c.saveState()
                c.setFillColor(BLUE_SOFT)
                c.setFillAlpha(0.4)
                c.roundRect(cx2, row_top - chip_h, cw, chip_h, chip_h / 2, stroke=0, fill=1)
                c.restoreState()
                c.setFillColor(white)
                c.setFont(chip_font, chip_size)
                c.drawString(cx2 + chip_pad_x / 2, row_top - chip_h / 2 - chip_size * 0.36, text)
                cx2 += cw + chip_gap
            row_top -= chip_h + 5

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

    return banner_h


def block_feature_cards(c, seeking: list[dict], st: Styles, y_top: float, draw: bool) -> float:
    """Four bordered cards, one per profile.json `seeking` entry: an icon circle, a bold
    one-line title (truncated with an ellipsis if it doesn't fit — the full label is never
    hidden, since it also has its own place on the site's Now.astro section), a divider, and
    its detail sentence as a bullet.

    Titles here are deliberately capped to a single line rather than left to wrap: with four
    cards forced to a shared height, letting one label wrap to 2-3 lines either stretched every
    other card into wasted blank space or — when the wrap was measured against one width and
    room was tighter at draw time — let the detail text collide with the title's last line.
    A fixed one-line title makes every card's height the same simple sum, with no dependency on
    how long any one label happens to be."""
    n = max(1, len(seeking))
    gap = 8.0
    w = (CONTENT_W - gap * (n - 1)) / n
    pad = 8.0
    icon_r = 11.0
    inner_w = w - 2 * pad
    title_w = inner_w - icon_r * 2 - 8
    title_st = ParagraphStyle("fctitle", fontName=FONT["bold"], fontSize=9.2, leading=1, textColor=INK)
    detail_st = ParagraphStyle("fcdetail", fontName=FONT["regular"], fontSize=7.4, leading=9.0, textColor=MUTED,
                                bulletFontName=FONT["regular"], bulletFontSize=7.4, bulletColor=BLUE)
    prepared = []
    for s in seeking:
        title_text = s["label"]
        while pdfmetrics.stringWidth(title_text, title_st.fontName, title_st.fontSize) > title_w and len(title_text) > 4:
            title_text = title_text[:-2].rstrip(",;: —–-") + "…"
        detail_text, _ = truncate_to_lines(s.get("detail", ""), detail_st, inner_w, 3)
        detail_p = para(esc(detail_text), detail_st, bullet="•")
        prepared.append((title_text, detail_p))
    title_row_h = max(icon_r * 2, title_st.fontSize * 1.2)
    detail_h = max(para_height(p, inner_w) for _, p in prepared)
    h = pad + title_row_h + 8 + detail_h + pad
    if draw:
        for i, (s, (title_text, detail_p)) in enumerate(zip(seeking, prepared)):
            x = MARGIN + i * (w + gap)
            card(c, x, y_top, w, h, radius=10)
            top = y_top - pad
            icon_cy = top - title_row_h / 2
            icon_circle(c, x + pad + icon_r, icon_cy, icon_r, seeking_icon(s["label"]), BLUE, ICON_BG, 9.6)
            c.setFillColor(INK)
            c.setFont(title_st.fontName, title_st.fontSize)
            c.drawString(x + pad + icon_r * 2 + 8, icon_cy - title_st.fontSize * 0.36, title_text)
            rule_y = top - title_row_h - 5
            hairline(c, x + pad, rule_y, x + w - pad)
            draw_para(c, detail_p, x + pad, rule_y - 7, inner_w)
    return h


def block_metrics(c, metrics: list[dict], st: Styles, y_top: float, draw: bool) -> float:
    """One continuous rounded strip divided by hairlines, icon on the left of each column and
    a bold colored number + label to its right — the earlier PDF's metric strip, not a row of
    separate boxed cards."""
    n = len(metrics)
    col_w = CONTENT_W / n
    icon_r = 11.0
    num_size = 15.0
    pad = 10.0
    label_st = ParagraphStyle("mlabel2", fontName=FONT["regular"], fontSize=6.9, leading=8.2, textColor=MUTED)
    text_w = col_w - pad - icon_r * 2 - 8 - 6
    label_paras = [para(esc(m["label"]), label_st) for m in metrics]
    label_h = max(para_height(p, text_w) for p in label_paras)
    h = max(icon_r * 2 + 12, num_size + label_h + 6) + 12
    if draw:
        card(c, MARGIN, y_top, CONTENT_W, h, radius=12)
        cy = y_top - h / 2
        for i, (m, lp) in enumerate(zip(metrics, label_paras)):
            x = MARGIN + i * col_w
            if i:
                vline(c, x, y_top - h + 8, y_top - 8)
            icon_circle(c, x + pad + icon_r, cy, icon_r, metric_icon(m.get("icon", "")), BLUE, ICON_BG, 9.8)
            tx = x + pad + icon_r * 2 + 8
            num = f"{m['num']:,}" if isinstance(m["num"], int) else str(m["num"])
            top_y = cy + (num_size + 2 + label_h) / 2
            c.setFillColor(CORAL)
            c.setFont(FONT["bold"], num_size)
            c.drawString(tx, top_y - num_size * 0.78, num)
            nw = pdfmetrics.stringWidth(num, FONT["bold"], num_size)
            if m.get("suffix"):
                c.setFont(FONT["bold"], num_size * 0.6)
                c.drawString(tx + nw + 1, top_y - num_size * 0.78, m["suffix"])
            draw_para(c, lp, tx, top_y - num_size - 2, text_w)
    return h


def block_profile(c, profile: dict, st: Styles, y_top: float, draw: bool) -> float:
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_header(c, x, y, "Profile", w, "")
    y -= SECTION_PILL_H + SECTION_GAP
    p = para(highlight(profile["pitch"]), st.body)
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
        p = para(highlight(b), st.bullet, bullet="•")
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
        p = para(highlight(b), st.bullet_compact, bullet="•")
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
    return _dt.date.today().strftime("%B %Y")


def content_hash(data: dict) -> str:
    """Eight hex chars of the résumé content's own hash — not the rendered PDF's bytes, which
    would change on every run just from reportlab's embedded creation timestamp. The filename
    only changes when the content actually does, so a stale cached or downloaded copy is always
    a *different* filename from the current one instead of the same name silently going stale."""
    import hashlib
    blob = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:8]


def sync_resume_pdf_path(new_rel: str) -> None:
    """Point src/data/profile.json's resumePdf at the freshly built file, in place — a targeted
    line replace, not a full json.dump round-trip, so the rest of the file's formatting doesn't
    move around in the diff."""
    path = ROOT / "src/data/profile.json"
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(r'"resumePdf":\s*"[^"]*"', f'"resumePdf": "{new_rel}"', text, count=1)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")


def clean_old_files(pattern: str, keep: set[Path]) -> None:
    """Remove previously built files matching `pattern` other than the ones just built, so
    hashed filenames from old content (or an old preset list) don't pile up on disk and stay
    reachable to be confused with the current ones."""
    keep_resolved = {p.resolve() for p in keep}
    for f in (ROOT / "public").glob(pattern):
        if f.resolve() not in keep_resolved:
            f.unlink()


# --------------------------------------------------------------------------
# Theme colors — hex → HSL → derived accent/violet/ember/mint, the same math
# Base.astro's pre-paint script uses client-side, ported here so a pre-built themed PDF and the
# live site's picked color are the same family of colors, not just two unrelated blues.
# --------------------------------------------------------------------------

def hex_to_hsl(hex_str: str) -> tuple[float, float, float]:
    hex_str = hex_str.lstrip("#")
    r, g, b = (int(hex_str[i:i + 2], 16) / 255 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        h = s = 0.0
    else:
        d = mx - mn
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h /= 6
    return h * 360, s * 100, l * 100


def hsl_to_hex(h: float, s: float, l: float) -> str:
    h = h % 360
    s, l = s / 100, l / 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:
        r, g, b = c, x, 0.0
    elif h < 120:
        r, g, b = x, c, 0.0
    elif h < 180:
        r, g, b = 0.0, c, x
    elif h < 240:
        r, g, b = 0.0, x, c
    elif h < 300:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return "#{:02x}{:02x}{:02x}".format(round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))


def configure_palette(base_hex: str) -> None:
    """Repoint every palette global at a derivative of `base_hex`. Called once per preset color
    before re-running build(); every drawing function reads these globals at call time (see the
    None-sentinel defaults on card()/hairline()/vline()/chip() above), so nothing needs to be
    threaded through as a parameter."""
    global PAPER, CARD, CARD_TINT, BORDER, BLUE, BLUE_DARK, BLUE_SOFT, VIOLET, CORAL, MINT, ICON_BG, SHADOW
    # Monochromatic on purpose: tints and shades of one hue, never a complementary jump. A full
    # complementary (hue+180) is fine as a small dot on a dark UI but reads as a clash on white
    # paper once it's the color of large bold numbers — every accent role here stays in the same
    # hue family so the sheet can never look like two unrelated colors fighting each other.
    h, s, l = hex_to_hsl(base_hex)
    accent = hsl_to_hex(h, max(55.0, min(s, 90.0)), max(48.0, min(l, 68.0)))
    BLUE = HexColor(accent)
    VIOLET = HexColor(hsl_to_hex(h, max(s - 8, 45), min(l + 6, 72)))     # a touch lighter — "Experience"
    CORAL = HexColor(hsl_to_hex(h, min(s + 12, 95), max(l - 20, 32)))     # deeper, richer — big numbers
    MINT = HexColor(hsl_to_hex(h, max(s - 18, 35), min(l + 16, 78)))      # softer — "Skills"
    BLUE_DARK = HexColor(hsl_to_hex(h, min(s + 10, 95), max(l - 30, 16)))
    BLUE_SOFT = HexColor(hsl_to_hex(h, max(s - 10, 40), min(l + 12, 78)))
    ICON_BG = HexColor(hsl_to_hex(h, 55, 91))
    CARD_TINT = HexColor(hsl_to_hex(h, 30, 96))
    BORDER = HexColor(hsl_to_hex(h, 35, 84))
    PAPER = HexColor(hsl_to_hex(h, 22, 97))
    SHADOW = HexColor(hsl_to_hex(h, 20, 80))


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
    y -= h + 4
    h, truncated = block_projects(c, projects, st, y, draw=True)
    report["truncated"] = truncated
    y -= h + 4
    h, drawer = measured(block_skills, skills, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h + 4
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


def build_one(rel: str, warnings_out: list[str]) -> Path:
    out = ROOT / "public" / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    report = build(out)
    size_kb = out.stat().st_size / 1024
    print(f"  wrote {rel} ({size_kb:.1f} KB) — page gaps {report['page1_bottom_gap']:.1f}pt / {report['page2_bottom_gap']:.1f}pt")
    if report["truncated"]:
        print("  truncated project summaries: " + ", ".join(report["truncated"]))
    warnings_out.extend(report["warnings"])
    return out


def main() -> None:
    register_fonts()
    data = load_content()
    h = content_hash(data)
    month_tag = _dt.date.today().strftime("%b_%Y")
    warnings: list[str] = []
    keep: set[Path] = set()

    # The canonical PDF: the one every "Download PDF" link points at, no color choice involved.
    print("canonical:")
    rel = f"Alex_Frison_Resume_{month_tag}_{h}.pdf"
    out = build_one(rel, warnings)
    keep.add(out)
    sync_resume_pdf_path(f"/{rel}")

    # One PDF per preset accent color — pre-built here so the "themed PDF" download on the site
    # is a plain static link, never a client-side jsPDF render. src/data/theme-presets.json is
    # the same list ThemePicker.astro reads, so the swatches you can pick from the site and the
    # colors you can download in are always the same set.
    presets = json.loads((ROOT / "src/data/theme-presets.json").read_text(encoding="utf-8"))
    manifest = {"default": f"/{rel}"}
    print("themed:")
    for p in presets:
        configure_palette(p["hex"])
        t_rel = f"Alex_Frison_Resume_Themed_{p['name']}_{h}.pdf"
        t_out = build_one(t_rel, warnings)
        keep.add(t_out)
        manifest[p["name"]] = f"/{t_rel}"
    (ROOT / "src/data/theme-pdf-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    clean_old_files("Alex_Frison_Resume_*.pdf", keep)
    print(f"\ncontent hash: {h} (filenames only change when the résumé content does)")
    print(f"text font: {FONT['label']}; icons: Font Awesome 4")
    for w in warnings:
        print("WARNING: " + w)
    if warnings:
        sys.exit(1)


if __name__ == "__main__":
    main()
