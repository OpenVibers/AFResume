#!/usr/bin/env python3
"""Build the two-page US-Letter resume PDF from the site's own content.

Everything on the page comes from the repo so the PDF and alexfrison.net
never drift:

  src/data/profile.json              name, tagline, pitch, contact, metrics, education
  src/content/experience/*.json      roles, sorted by `order`
  src/content/skills/*.json          skill groups, sorted by `order`
  src/content/projects/<slug>.mdx    selected projects (frontmatter only)

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

from reportlab.lib.colors import HexColor
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
# Palette
# --------------------------------------------------------------------------
PAPER = HexColor("#f5f6fb")
CARD = HexColor("#ffffff")
BORDER = HexColor("#dfe4f2")
INK = HexColor("#0c1020")
BODY = HexColor("#2a3148")
MUTED = HexColor("#5c6683")
BLUE = HexColor("#3b63f0")
CORAL = HexColor("#f0562a")
VIOLET = HexColor("#7c5cff")
MINT = HexColor("#16b98a")

# --------------------------------------------------------------------------
# Page geometry
# --------------------------------------------------------------------------
PAGE_W, PAGE_H = letter
MARGIN = 36.0                      # 0.5in
CONTENT_W = PAGE_W - 2 * MARGIN
TOP = PAGE_H - MARGIN
BOTTOM = MARGIN
CARD_PAD = 9.0

# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
FONT_CANDIDATES = [
    # (family label, regular, bold, italic)
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
    """Copy of a TTF with TrueType hinting stripped.

    reportlab keeps the hint programs when it subsets a font, and for heavily
    hinted families (Liberation, DejaVu) they are most of the embedded bytes.
    PDF viewers ignore them, so dropping them halves the file size with no
    visible change. Falls back to the original path if fontTools is missing.
    """
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


# Font Awesome 4 code points
ICON = {
    "email": "", "phone": "", "site": "", "linkedin": "",
    "github": "", "location": "", "link": "", "education": "",
}

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
        self.body = style("body", 9.2, 11.6, BODY)
        self.summary = style("summary", 8.5, 10.4, MUTED, FONT["italic"])
        self.bullet = style("bullet", 8.5, 10.2, BODY, leftIndent=9, bulletIndent=0,
                            bulletFontName=FONT["regular"], bulletFontSize=8.5, bulletColor=BLUE)
        self.bullet_compact = style("bulletc", 8.5, 10.0, BODY, leftIndent=9, bulletIndent=0,
                                    bulletFontName=FONT["regular"], bulletFontSize=8.5, bulletColor=BLUE)
        self.stack = style("stack", 7.2, 9.0, MUTED)
        self.metric_label = style("mlabel", 7.2, 8.8, MUTED)
        self.proj_title = style("ptitle", 8.6, 10.4, INK, FONT["bold"])
        self.proj_summary = style("psum", 7.6, 9.2, BODY)
        self.proj_link = style("plink", 7.4, 9.0, BLUE)
        self.skill_items = style("skills", 8.4, 10.3, BODY)
        self.edu = style("edu", 8.4, 10.3, BODY)


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


def small_caps(c, x: float, y_base: float, text: str, size: float, color, tracking: float = 0.7,
               font: str | None = None) -> float:
    """Tracked uppercase label drawn directly on the canvas. Returns width."""
    font = font or FONT["bold"]
    c.saveState()  # Tc is graphics state and would otherwise leak into later text
    t = c.beginText(x, y_base)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(tracking)
    t.textOut(text.upper())
    t.setCharSpace(0)
    c.drawText(t)
    c.restoreState()
    return pdfmetrics.stringWidth(text.upper(), font, size) + tracking * len(text)


def icon(c, x: float, y_base: float, glyph: str, size: float, color) -> float:
    c.saveState()
    c.setFont("FA", size)
    c.setFillColor(color)
    c.drawString(x, y_base, glyph)
    c.restoreState()
    return pdfmetrics.stringWidth(glyph, "FA", size)


def hairline(c, x0: float, y: float, x1: float, color=BORDER, width: float = 0.6) -> None:
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x0, y, x1, y)
    c.restoreState()


def card(c, x: float, y_top: float, w: float, h: float, radius: float = 4.0) -> None:
    c.saveState()
    c.setFillColor(CARD)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.7)
    c.roundRect(x, y_top - h, w, h, radius, stroke=1, fill=1)
    c.restoreState()


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


SECTION_LABEL_SIZE = 7.6
SECTION_LABEL_H = SECTION_LABEL_SIZE + 6.5


def section_label(c, x: float, y_top: float, text: str, width: float) -> float:
    """Small-caps blue label with a short coral tick and a hairline to the right. Returns height."""
    size = SECTION_LABEL_SIZE
    base = y_top - size
    w = small_caps(c, x, base, text, size, BLUE, tracking=1.0)
    hairline(c, x, base - 3.2, x + 16, CORAL, 1.2)
    hairline(c, x + w + 8, base + size * 0.32, x + width)
    return SECTION_LABEL_H


# --------------------------------------------------------------------------
# Blocks. Each block function draws when `draw` is True and always returns
# the height it occupies, so callers can measure before drawing a card.
# --------------------------------------------------------------------------

def block_header(c, profile: dict, y_top: float, draw: bool) -> float:
    x = MARGIN
    y = y_top
    name_size, tag_size = 24.0, 10.2
    if draw:
        c.setFillColor(INK)
        c.setFont(FONT["bold"], name_size)
        c.drawString(x, y - name_size * 0.78, profile["name"])
    y -= name_size * 0.78 + 6
    if draw:
        c.setFillColor(MUTED)
        c.setFont(FONT["regular"], tag_size)
        c.drawString(x, y - tag_size * 0.78, profile["tagline"])
    y -= tag_size * 0.78 + 8

    # Contact line with icons; wraps to a second line if needed.
    items = [
        ("email", profile.get("emailDisplay") or profile.get("email"), f"mailto:{profile['email']}" if profile.get("email") else None),
        ("phone", profile.get("phoneDisplay") or profile.get("phone"), f"tel:{profile['phone']}" if profile.get("phone") else None),
        ("site", profile.get("siteDisplay"), profile.get("site")),
        ("linkedin", profile.get("linkedinDisplay"), profile.get("linkedin")),
        ("github", profile.get("githubDisplay"), profile.get("github")),
        ("location", profile.get("locationShort") or profile.get("location"), None),
    ]
    items = [it for it in items if it[1]]
    size, isize, gap, igap = 8.6, 8.2, 14.0, 4.5
    line_h = 12.0
    cx, base = x, y - size * 0.78
    for key, text, url in items:
        w = isize + igap + pdfmetrics.stringWidth(text, FONT["regular"], size)
        if cx > x and cx + w > x + CONTENT_W:
            cx = x
            base -= line_h
        if draw:
            icon(c, cx, base, ICON[key], isize, BLUE)
            c.setFillColor(BODY)
            c.setFont(FONT["regular"], size)
            c.drawString(cx + isize + igap, base, text)
            if url:
                c.linkURL(url, (cx, base - 2.5, cx + w, base + size), relative=0, thickness=0)
        cx += w + gap
    y = base - 4
    return y_top - y


def block_metrics(c, metrics: list[dict], st: Styles, y_top: float, draw: bool) -> float:
    n = len(metrics)
    gap = 8.0
    w = (CONTENT_W - gap * (n - 1)) / n
    num_size, suf_size = 17.0, 9.5
    pad = 7.0
    inner_w = w - 2 * pad
    # measure the tallest label
    label_paras = [para(esc(m["label"]), st.metric_label) for m in metrics]
    label_h = max(para_height(p, inner_w) for p in label_paras)
    h = pad + num_size * 0.78 + 5 + label_h + pad
    if draw:
        for i, (m, lp) in enumerate(zip(metrics, label_paras)):
            x = MARGIN + i * (w + gap)
            card(c, x, y_top, w, h)
            base = y_top - pad - num_size * 0.78
            c.setFillColor(CORAL)
            c.setFont(FONT["bold"], num_size)
            num = f"{m['num']:,}" if isinstance(m["num"], int) else str(m["num"])
            c.drawString(x + pad, base, num)
            nw = pdfmetrics.stringWidth(num, FONT["bold"], num_size)
            if m.get("suffix"):
                c.setFont(FONT["bold"], suf_size)
                c.drawString(x + pad + nw + 1, base, m["suffix"])
            draw_para(c, lp, x + pad, base - 5, inner_w)
    return h


def block_profile(c, profile: dict, st: Styles, y_top: float, draw: bool) -> float:
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_label(c, x, y, "Profile", w)
    y -= SECTION_LABEL_H
    p = para(esc(profile["pitch"]), st.body)
    h = para_height(p, w)
    if draw:
        draw_para(c, p, x, y, w)
    y -= h + 1
    y -= CARD_PAD
    return y_top - y


def role_header(c, role: dict, st: Styles, x: float, w: float, y_top: float, draw: bool) -> float:
    """Role title, company · location, right-aligned dates (mint dot if current)."""
    title_size, meta_size, date_size = 10.0, 8.6, 8.4
    y = y_top
    dates = f"{role.get('start', '')} – {role.get('end', '')}".strip(" –")
    dw = pdfmetrics.stringWidth(dates, FONT["regular"], date_size)
    base = y - title_size * 0.78
    if draw:
        c.setFillColor(INK)
        c.setFont(FONT["bold"], title_size)
        c.drawString(x, base, role["role"])
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
        c.drawString(x, base, role["company"])
        cw = pdfmetrics.stringWidth(role["company"], FONT["bold"], meta_size)
        if role.get("link"):
            c.linkURL(role["link"], (x, base - 2, x + cw, base + meta_size), relative=0, thickness=0)
        if role.get("location"):
            c.setFillColor(MUTED)
            c.setFont(FONT["regular"], meta_size)
            c.drawString(x + cw, base, f"  ·  {role['location']}")
    y = base - 3.2
    return y_top - y


def stack_line(c, role: dict, st: Styles, x: float, w: float, y_top: float, draw: bool) -> float:
    stack = role.get("stack") or []
    if not stack:
        return 0
    p = para(f"<b>Stack</b>&nbsp;&nbsp;{esc(' · '.join(stack))}", st.stack)
    h = para_height(p, w)
    if draw:
        draw_para(c, p, x, y_top, w)
    return h


def block_role_full(c, role: dict, st: Styles, x: float, w: float, y_top: float, draw: bool) -> float:
    y = y_top
    y -= role_header(c, role, st, x, w, y, draw)
    if role.get("summary"):
        p = para(esc(role["summary"]), st.summary)
        h = para_height(p, w)
        if draw:
            draw_para(c, p, x, y, w)
        y -= h + 2.5
    for b in role.get("bullets", []):
        p = para(esc(b), st.bullet, bullet="•")
        h = para_height(p, w)
        if draw:
            draw_para(c, p, x, y, w)
        y -= h
    y -= 3.0
    y -= stack_line(c, role, st, x, w, y, draw)
    return y_top - y


def block_role_compact(c, role: dict, st: Styles, x: float, w: float, y_top: float, draw: bool) -> float:
    y = y_top
    y -= role_header(c, role, st, x, w, y, draw)
    for b in role.get("bullets", [])[:COMPACT_BULLETS]:
        p = para(esc(b), st.bullet_compact, bullet="•")
        h = para_height(p, w)
        if draw:
            draw_para(c, p, x, y, w)
        y -= h
    return y_top - y


def block_experience(c, roles: list[dict], st: Styles, y_top: float, label: str, compact: bool, draw: bool) -> float:
    x, w = MARGIN + CARD_PAD, CONTENT_W - 2 * CARD_PAD
    y = y_top - CARD_PAD
    if draw:
        section_label(c, x, y, label, w)
    y -= SECTION_LABEL_H
    fn = block_role_compact if compact else block_role_full
    sep = 7.0 if compact else 8.0
    for i, role in enumerate(roles):
        if i:
            if draw:
                hairline(c, x, y - sep / 2, x + w)
            y -= sep
        y -= fn(c, role, st, x, w, y, draw)
    y -= CARD_PAD - 1
    return y_top - y


def block_projects(c, projects: list[dict], st: Styles, y_top: float, draw: bool) -> tuple[float, list[str]]:
    """2 rows × 3 columns of small cards. Returns (height, truncated titles)."""
    truncated: list[str] = []
    y = y_top
    if draw:
        section_label(c, MARGIN, y, "Selected work", CONTENT_W)
    y -= SECTION_LABEL_H
    cols, gap, pad = 3, 8.0, 7.0
    cw = (CONTENT_W - gap * (cols - 1)) / cols
    inner = cw - 2 * pad
    max_lines = 3
    prepared = []
    for pr in projects:
        title = pr.get("title", "")
        summary, trunc = truncate_to_lines(pr.get("summary", ""), st.proj_summary, inner, max_lines)
        if trunc:
            truncated.append(title)
        url = (pr.get("links") or {}).get("live") if isinstance(pr.get("links"), dict) else None
        prepared.append((title, summary, url))
    title_h = st.proj_title.leading
    sum_h = st.proj_summary.leading * max_lines
    link_h = st.proj_link.leading
    ch = pad + title_h + 2 + sum_h + 3 + link_h + pad
    rows = (len(prepared) + cols - 1) // cols
    if draw:
        for i, (title, summary, url) in enumerate(prepared):
            r, col = divmod(i, cols)
            x = MARGIN + col * (cw + gap)
            top = y - r * (ch + gap)
            card(c, x, top, cw, ch)
            ty = top - pad
            tsize = st.proj_title.fontSize
            while tsize > 7.4 and pdfmetrics.stringWidth(title, FONT["bold"], tsize) > inner:
                tsize -= 0.2
            c.setFillColor(INK)
            c.setFont(FONT["bold"], tsize)
            c.drawString(x + pad, ty - tsize * 0.78, title)
            ty -= title_h + 2
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
        section_label(c, x, y, "Skills", w)
    y -= SECTION_LABEL_H
    row_gap = 2.8
    for i, g in enumerate(skills):
        items = [it["name"] for it in g.get("items", []) if it.get("name")]
        label = f'<font name="{FONT["bold"]}" size="6.9" color="#0c1020">{esc(g["group"].upper())}</font>'
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
        section_label(c, x, y, "Education & links", w)
    y -= SECTION_LABEL_H
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
    size, isize = 8.2, 7.8
    base = y - size * 0.78
    cx = x
    if draw:
        for key, text, url in links:
            if not (text and url):
                continue
            iw = icon(c, cx, base, ICON[key], isize, BLUE)
            c.setFillColor(BLUE)
            c.setFont(FONT["regular"], size)
            c.drawString(cx + iw + 4, base, text)
            tw = iw + 4 + pdfmetrics.stringWidth(text, FONT["regular"], size)
            c.linkURL(url, (cx, base - 2, cx + tw, base + size), relative=0, thickness=0)
            cx += tw + 16
    y = base - 2 - CARD_PAD
    return y_top - y


def footer(c, profile: dict, page: int, total: int, updated: str) -> None:
    size = 7.4
    base = 20.0
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
    y -= block_header(c, profile, y, draw=True)
    y -= 4
    y -= block_metrics(c, pick_metrics(profile["metrics"]), st, y, draw=True)
    y -= 10
    h, drawer = measured(block_profile, profile, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h + 10
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
    y -= h + 8
    h, truncated = block_projects(c, projects, st, y, draw=True)
    report["truncated"] = truncated
    y -= h + 8
    h, drawer = measured(block_skills, skills, st, y)
    card(c, MARGIN, y, CONTENT_W, h)
    drawer()
    y -= h + 8
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
