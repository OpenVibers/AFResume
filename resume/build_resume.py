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
METRIC_KEYWORDS = ["shipped", "lines of production", "payment processors", "sox compliance", "years running"]
FULL_ROLES = 2            # PowerChat + OpenVibe get full treatment on page 1
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
MARGIN = 23.0
CONTENT_W = PAGE_W - 2 * MARGIN
TOP = PAGE_H - MARGIN
BOTTOM = MARGIN
CARD_PAD = 6.0

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


# profile.json `roles[]` (the header chip row) → icon, matched by keyword; falls back to
# the generic "engineer" glyph so an unrecognized role degrades instead of going icon-less.
ROLE_ICON_KEYWORDS = [
    ("idea", "\uf0eb"), ("business", "\uf0b1"), ("owner", "\uf0b1"), ("automat", "\uf085"),
    ("platform", "\uf233"), ("architect", "\uf233"), ("founder", "\uf135"),
    ("analyst", "\uf201"), ("data", "\uf201"), ("ai ", "\uf2db"), ("product", "\uf1b2"),
    ("team", "\uf0c0"), ("leader", "\uf0c0"), ("problem", "\uf0ad"), ("full-stack", "\uf0ac"),
    ("developer", "\uf121"), ("engineer", "\uf121"),
]
DEFAULT_ROLE_ICON = "\uf121"  # code


def role_icon(text: str) -> str:
    t = (text or "").lower()
    for kw, glyph in ROLE_ICON_KEYWORDS:
        if kw in t:
            return glyph
    return DEFAULT_ROLE_ICON


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
        self.summary = style("summary", 8.1, 9.8, MUTED, FONT["italic"])
        self.bullet = style("bullet", 8.2, 9.9, BODY, leftIndent=9, bulletIndent=0,
                            bulletFontName=FONT["regular"], bulletFontSize=8.2, bulletColor=BLUE)
        self.bullet_compact = style("bulletc", 8.2, 10.0, BODY, leftIndent=9, bulletIndent=0,
                                    bulletFontName=FONT["regular"], bulletFontSize=8.2, bulletColor=BLUE)
        self.stack = style("stack", 6.9, 8.3, MUTED)
        self.metric_label = style("mlabel", 7.0, 8.5, MUTED)
        self.proj_title = style("ptitle", 8.5, 10.2, INK, FONT["bold"])
        self.proj_summary = style("psum", 7.5, 9.0, BODY)
        self.proj_link = style("plink", 7.3, 8.8, BLUE)
        self.skill_items = style("skills", 8.2, 9.7, BODY)
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
    """A full-width colored banner: name + tagline, then two chip rows spanning the whole
    width — "what I do" (role chips) and "how to reach me" (contact chips) — instead of
    squeezing contact info into a narrow right-side column, which is cramped, is stuck a
    fixed height regardless of how much text wraps, and had a hardcoded icon-circle color
    that didn't move with the chosen theme. One wrap/draw helper serves both rows, so
    neither can disagree between its measured and drawn width."""
    x = MARGIN
    w = CONTENT_W
    name_size, tag_size = 20.0, 9.2
    pad = 10.5
    inner_w = w - pad * 2

    def wrap(items, font, size, icon_w, pad_x, gap):
        rows: list[list[tuple[dict, float]]] = [[]]
        cx = 0.0
        for it in items:
            cw = pdfmetrics.stringWidth(it["text"], font, size) + pad_x + icon_w
            if cx > 0 and cx + cw > inner_w:
                rows.append([])
                cx = 0.0
            rows[-1].append((it, cw))
            cx += cw + gap
        return rows

    def draw_rows(rows, row_top, chip_h, font, size, icon_w, pad_x, gap, bg, bg_alpha, fg, glyph_of):
        for row in rows:
            cx2 = x + pad
            for it, cw in row:
                c.saveState()
                c.setFillColor(bg)
                c.setFillAlpha(bg_alpha)
                c.roundRect(cx2, row_top - chip_h, cw, chip_h, chip_h / 2, stroke=0, fill=1)
                c.restoreState()
                ty2 = row_top - chip_h / 2 - size * 0.36
                glyph = glyph_of(it)
                tx = cx2 + pad_x / 2
                if glyph:
                    icon(c, tx, ty2, glyph, size, fg)
                    tx += icon_w
                c.setFillColor(fg)
                c.setFont(font, size)
                c.drawString(tx, ty2, it["text"])
                if it.get("url"):
                    c.linkURL(it["url"], (cx2, row_top - chip_h, cx2 + cw, row_top), relative=0, thickness=0)
                cx2 += cw + gap
            row_top -= chip_h + 5
        return row_top

    roles = [{"text": r, "url": None} for r in (profile.get("roles") or [])[:6]]
    role_font, role_size, role_pad_x, role_icon_w, role_gap = FONT["bold"], 7.6, 20.0, 13.0, 7.0
    role_rows = wrap(roles, role_font, role_size, role_icon_w, role_pad_x, role_gap)
    role_h = role_size + 6.5
    role_total_h = len(role_rows) * role_h + max(0, len(role_rows) - 1) * 5

    contact_items = [
        {"text": profile.get("emailDisplay") or profile.get("email"), "icon": "email", "url": f"mailto:{profile['email']}" if profile.get("email") else None},
        {"text": profile.get("phoneDisplay") or profile.get("phone"), "icon": "phone", "url": f"tel:{profile['phone']}" if profile.get("phone") else None},
        {"text": profile.get("siteDisplay"), "icon": "site", "url": profile.get("site")},
        {"text": profile.get("linkedinDisplay"), "icon": "linkedin", "url": profile.get("linkedin")},
        {"text": profile.get("locationShort") or profile.get("location"), "icon": "location", "url": None},
    ]
    contact_items = [it for it in contact_items if it["text"]]
    contact_font, contact_size, contact_pad_x, contact_icon_w, contact_gap = FONT["regular"], 8.6, 18.0, 15.0, 8.0
    contact_rows = wrap(contact_items, contact_font, contact_size, contact_icon_w, contact_pad_x, contact_gap)
    contact_h = contact_size + 7
    contact_total_h = len(contact_rows) * contact_h + max(0, len(contact_rows) - 1) * 6

    group_gap = 6.0
    banner_h = pad + name_size * 0.78 + 5 + tag_size * 0.78 + 13 + role_total_h + group_gap + contact_total_h + pad

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
    ty -= tag_size * 0.78 + 10

    if draw:
        ty = draw_rows(role_rows, ty, role_h, role_font, role_size, role_icon_w, role_pad_x, role_gap,
                        BLUE_SOFT, 0.4, white, lambda it: role_icon(it["text"]))
        ty -= group_gap - 5
        draw_rows(contact_rows, ty, contact_h, contact_font, contact_size, contact_icon_w, contact_pad_x, contact_gap,
                  white, 0.16, white, lambda it: ICON[it["icon"]])

    return banner_h


def block_feature_cards(c, seeking: list[dict], st: Styles, y_top: float, draw: bool) -> float:
    """A 2×2 grid, one card per profile.json `seeking` entry: icon, one-line title (still
    truncated as a last resort if a future label is unusually long — but at this width none of
    the current four are), a divider, and its detail sentence as a bullet.

    Two columns instead of four gives each title roughly double the width a four-across row
    had, so the truncation that made every title unreadable ("Honestly, o…to…") stops being
    the normal case. Row height is still a single shared value (the taller of the two detail
    texts in that row), computed and used identically for measuring and drawing."""
    cols = 2
    n = len(seeking)
    rows = [seeking[i:i + cols] for i in range(0, n, cols)]
    gap = 8.0
    w = (CONTENT_W - gap * (cols - 1)) / cols
    pad = 8.5
    icon_r = 11.0
    inner_w = w - 2 * pad
    title_w = inner_w - icon_r * 2 - 10
    title_st = ParagraphStyle("fctitle", fontName=FONT["bold"], fontSize=9.6, leading=1, textColor=INK)
    detail_st = ParagraphStyle("fcdetail", fontName=FONT["regular"], fontSize=7.6, leading=9.4, textColor=MUTED,
                                bulletFontName=FONT["regular"], bulletFontSize=7.6, bulletColor=BLUE)
    prepared = []
    for s in seeking:
        title_text = s["label"]
        while pdfmetrics.stringWidth(title_text, title_st.fontName, title_st.fontSize) > title_w and len(title_text) > 4:
            title_text = title_text[:-2].rstrip(",;: —–-") + "…"
        detail_p = para(esc(s.get("detail", "")), detail_st, bullet="•")
        prepared.append((title_text, detail_p))
    title_row_h = max(icon_r * 2, title_st.fontSize * 1.2)
    row_gap = 7.0
    row_heights = []
    for r in range(len(rows)):
        chunk = prepared[r * cols:(r + 1) * cols]
        detail_h = max(para_height(p, inner_w) for _, p in chunk)
        row_heights.append(pad + title_row_h + 9 + detail_h + pad)
    h = sum(row_heights) + row_gap * (len(rows) - 1)
    if draw:
        row_top = y_top
        for r, row in enumerate(rows):
            rh = row_heights[r]
            for ci in range(len(row)):
                idx = r * cols + ci
                s = seeking[idx]
                title_text, detail_p = prepared[idx]
                x = MARGIN + ci * (w + gap)
                card(c, x, row_top, w, rh, radius=12)
                top = row_top - pad
                icon_cy = top - title_row_h / 2
                icon_circle(c, x + pad + icon_r, icon_cy, icon_r, seeking_icon(s["label"]), BLUE, ICON_BG, 10.6)
                c.setFillColor(INK)
                c.setFont(title_st.fontName, title_st.fontSize)
                c.drawString(x + pad + icon_r * 2 + 10, icon_cy - title_st.fontSize * 0.36, title_text)
                rule_y = top - title_row_h - 6
                hairline(c, x + pad, rule_y, x + w - pad)
                draw_para(c, detail_p, x + pad, rule_y - 8, inner_w)
            row_top -= rh + row_gap
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
    label_st = ParagraphStyle("mlabel2", fontName=FONT["regular"], fontSize=7.1, leading=8.5, textColor=MUTED)
    text_w = col_w - pad - icon_r * 2 - 8 - 6
    label_paras = [para(esc(m.get("short") or m["label"]), label_st) for m in metrics]
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
            # A thin underline is the only cue a static PDF has for "this text is a live
            # link" — plain bold-blue looks identical to every other (non-linked) company name.
            c.saveState()
            c.setStrokeColor(BLUE)
            c.setLineWidth(0.6)
            c.line(x + icon_col, base - 1.4, x + icon_col + cw, base - 1.4)
            c.restoreState()
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
    y -= 1.4
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
    sep = 2.5 if compact else 4.0
    for i, role in enumerate(roles):
        if i:
            if draw:
                hairline(c, x, y - sep / 2, x + w)
            y -= sep
        y -= fn(c, role, st, x, w, y, draw)
    y -= CARD_PAD - 1
    return y_top - y


def block_projects(c, projects: list[dict], st: Styles, y_top: float, draw: bool) -> tuple[float, list[str]]:
    """2 rows x 3 columns of small cards, each with a category icon and -- if it has a live URL --
    a small link-out badge in the top-right corner instead of a separate domain-text row.
    Shorter two-line summaries: punchy over complete; the full write-up is one tap away at
    alexfrison.net/portfolio. Returns (height, truncated titles)."""
    truncated: list[str] = []
    y = y_top
    if draw:
        section_header(c, MARGIN, y, "Selected work", CONTENT_W, ICON["link"])
    y -= SECTION_PILL_H + SECTION_GAP
    cols, gap, pad = 3, 7.0, 8.0
    cw = (CONTENT_W - gap * (cols - 1)) / cols
    icon_col = 20.0
    link_badge = 16.0
    inner = cw - 2 * pad
    title_w = inner - icon_col - link_badge
    max_lines = 2
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
    ch = pad + title_h + 6 + sum_h + pad
    rows = (len(prepared) + cols - 1) // cols
    if draw:
        for i, (title, summary, url, cat) in enumerate(prepared):
            r, col = divmod(i, cols)
            x = MARGIN + col * (cw + gap)
            top = y - r * (ch + gap)
            card(c, x, top, cw, ch, radius=10)
            ty = top - pad
            glyph = CATEGORY_ICON.get(cat, DEFAULT_ICON)
            icon_circle(c, x + pad + 6.5, ty - 6.5, 7.0, glyph, BLUE, ICON_BG, 7.0)
            if url:
                bx, by = x + cw - pad - link_badge, ty - link_badge + 3
                c.saveState()
                c.setFillColor(ICON_BG)
                c.roundRect(bx, by, link_badge, link_badge, 5, stroke=0, fill=1)
                c.restoreState()
                iw = pdfmetrics.stringWidth(ICON["link"], "FA", 7.0)
                icon(c, bx + (link_badge - iw) / 2, by + 4.6, ICON["link"], 7.0, BLUE)
                c.linkURL(url, (x, top - ch, x + cw, top), relative=0, thickness=0)
            tsize = st.proj_title.fontSize
            while tsize > 7.0 and pdfmetrics.stringWidth(title, FONT["bold"], tsize) > title_w:
                tsize -= 0.2
            c.setFillColor(INK)
            c.setFont(FONT["bold"], tsize)
            c.drawString(x + pad + icon_col, ty - tsize * 0.78, title)
            ty -= title_h + 6
            draw_para(c, para(esc(summary), st.proj_summary), x + pad, ty, inner)
    y -= rows * ch + (rows - 1) * gap
    return y_top - y, truncated


def block_skills(c, skills: list[dict], st: Styles, y_top: float, draw: bool) -> float:
    """A two-column matrix — each group still gets its own label line above its item list
    (a clear break, not one run-on paragraph with the label inlined at the front), but two
    columns roughly halve the section's height versus stacking every group in one column,
    and read like an actual skills matrix instead of a long scroll of text."""
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_header(c, x, y, "Skills", w, "")
    y -= SECTION_PILL_H + SECTION_GAP
    label_size = 7.2
    label_gap = 2.0
    group_gap = 6.0
    col_gap = 20.0
    col_w = (w - col_gap) / 2
    mid = (len(skills) + 1) // 2
    columns = [skills[:mid], skills[mid:]]

    def col_height(groups: list[dict]) -> float:
        ch = 0.0
        for i, g in enumerate(groups):
            if i:
                ch += group_gap
            items = [it["name"] for it in g.get("items", []) if it.get("name")]
            ch += label_size * 0.78 + label_gap
            ch += para_height(para(esc(" · ".join(items)), st.skill_items), col_w)
        return ch

    heights = [col_height(g) for g in columns]
    total_h = max(heights) if heights else 0.0

    if draw:
        for ci, groups in enumerate(columns):
            cx = x + ci * (col_w + col_gap)
            cy = y
            for i, g in enumerate(groups):
                if i:
                    cy -= group_gap
                items = [it["name"] for it in g.get("items", []) if it.get("name")]
                c.setFillColor(BLUE_DARK)
                c.setFont(FONT["bold"], label_size)
                c.drawString(cx, cy - label_size * 0.78, g["group"].upper())
                cy -= label_size * 0.78 + label_gap
                p = para(esc(" · ".join(items)), st.skill_items)
                ph = para_height(p, col_w)
                draw_para(c, p, cx, cy, col_w)
                cy -= ph
        if len(columns) > 1 and columns[1]:
            vline(c, x + col_w + col_gap / 2, y - total_h, y, BORDER, 0.5)
    y -= total_h + CARD_PAD
    return y_top - y


def block_education(c, profile: dict, st: Styles, y_top: float, draw: bool) -> float:
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_header(c, x, y, "Education", w, ICON["education"])
    y -= SECTION_PILL_H + SECTION_GAP
    p = para(esc(profile.get("education", "")), st.edu)
    h = para_height(p, w)
    if draw:
        draw_para(c, p, x, y, w)
    y -= h + CARD_PAD - 3
    return y_top - y


def block_links(c, profile: dict, st: Styles, y_top: float, draw: bool) -> float:
    """Site, GitHub, LinkedIn and email as a row of their own — pulled out of Education,
    which they had nothing to do with beyond both being "stuff at the bottom of the page"."""
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_header(c, x, y, "Links", w, ICON["link"])
    y -= SECTION_PILL_H + SECTION_GAP
    links = [
        ("site", profile.get("siteDisplay"), profile.get("site")),
        ("github", profile.get("githubDisplay"), profile.get("github")),
        ("linkedin", profile.get("linkedinDisplay"), profile.get("linkedin")),
        ("email", profile.get("emailDisplay"), f"mailto:{profile['email']}" if profile.get("email") else None),
    ]
    links = [l for l in links if l[1] and l[2]]
    size = 8.6
    base = y - size * 0.78
    n = max(len(links), 1)
    col_w = w / n
    if draw:
        for i, (key, text, url) in enumerate(links):
            cx = x + i * col_w
            icon_circle(c, cx + 7.5, base + 3.2, 8.0, ICON[key], BLUE, ICON_BG, 7.6)
            c.setFillColor(BLUE)
            c.setFont(FONT["regular"], size)
            c.drawString(cx + 18, base, text)
            tw = 18 + pdfmetrics.stringWidth(text, FONT["regular"], size)
            c.linkURL(url, (cx, base - 3, cx + tw, base + size + 2), relative=0, thickness=0)
    y = base - 3 - CARD_PAD + 5
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
    # profile.resumePdf is *written* by this script (sync_resume_pdf_path) and names the previous
    # build's hash, so it must not feed the next one — otherwise every run gets a new filename.
    hashed = dict(data)
    hashed["profile"] = {k: v for k, v in data["profile"].items() if k != "resumePdf"}
    blob = json.dumps(hashed, sort_keys=True, default=str).encode("utf-8")
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
    y -= 5
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
    y -= h + 2
    h, truncated = block_projects(c, projects, st, y, draw=True)
    report["truncated"] = truncated
    y -= h + 2
    h, drawer = measured(block_skills, skills, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h + 2
    h, drawer = measured(block_education, profile, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h + 2
    h, drawer = measured(block_links, profile, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h
    check(y, "page 2 links")
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

    # Every preset color, including the default ("blue"), goes through the exact same
    # configure_palette() call — there is no separate hardcoded default anymore. That used to be
    # the bug behind "why is the default orange": the very first build ran before any palette
    # call, so it kept the *original* fixed BLUE/CORAL module constants (a blue header next to an
    # unrelated hardcoded orange), while every preset below it got the newer monochromatic
    # derivation. One code path now produces all thirteen files.
    presets = json.loads((ROOT / "src/data/theme-presets.json").read_text(encoding="utf-8"))
    default_name = "blue"
    manifest: dict[str, str] = {}
    for p in presets:
        configure_palette(p["hex"])
        is_default = p["name"] == default_name
        rel = f"Alex_Frison_Resume_{month_tag}_{h}.pdf" if is_default else f"Alex_Frison_Resume_Themed_{p['name']}_{h}.pdf"
        print(f"{p['name']}{' (default)' if is_default else ''}:")
        out = build_one(rel, warnings)
        keep.add(out)
        manifest[p["name"]] = f"/{rel}"
        if is_default:
            manifest["default"] = f"/{rel}"
            sync_resume_pdf_path(f"/{rel}")
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
