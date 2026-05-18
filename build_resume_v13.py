"""
build_resume_v13.py — Alex Frison resume (2026 edition).

Improvements over v12:
- Pulls the rich detail that lives on alexfrison.net (SOX/IRDR work,
  Anthropic SQL copilot, autonomous root-cause bot, OpenVibe 15-microservice
  kernel, HoboQuest custom engine, GameServerStats LLC scale, Verizon
  district-level recognition).
- New "Impact at a glance" metrics strip on page 1 (recruiter-skim friendly).
- Tighter typography, denser content, fewer wasted bands of blank space.
- Page 1 = pitch + first three roles (recent + revenue-relevant).
- Page 2 = remaining roles, six featured projects with live URLs, full
  technical stack, education + links footer.
- Same palette so it stays visually consistent with the site.

Run:
    cd /opt/repos/alexfrison.net && python build_resume_v13.py
Outputs:
    Alex_Frison_Resume.pdf            (next to the script)
"""

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

pdfmetrics.registerFont(TTFont('FA', 'fontawesome-webfont.ttf'))

PAGE_W, PAGE_H = letter

# --- palette ----------------------------------------------------------------
BG = HexColor('#eef2f7')
BLUE = HexColor('#4f84d6')
BLUE_DARK = HexColor('#2a4f90')
BLUE_LINE = HexColor('#7ea8ee')
BLUE_SOFT = HexColor('#5f92de')
TEXT = HexColor('#34548f')
SUBTLE = HexColor('#5a73a8')
SHADOW = HexColor('#d9dee8')
CARD_BG = HexColor('#f8fbff')
ACCENT_GOLD = HexColor('#c98b1f')  # used only for metric numerals

# --- styles -----------------------------------------------------------------
BODY = ParagraphStyle('Body', fontName='Helvetica', fontSize=9.6, leading=11.4,
                     textColor=TEXT, spaceAfter=0)
COMPANY = ParagraphStyle('Company', fontName='Helvetica-Bold', fontSize=9.6,
                        leading=11, textColor=BLUE)
LOCATION = ParagraphStyle('Location', fontName='Helvetica-Oblique', fontSize=8.6,
                          leading=10, textColor=SUBTLE)
BULLET = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=8.6,
                       leading=10.0, textColor=TEXT)
STACK = ParagraphStyle('Stack', fontName='Helvetica-Oblique', fontSize=8.2,
                       leading=10, textColor=SUBTLE)
CARD_TITLE = ParagraphStyle('CardTitle', fontName='Helvetica-Bold', fontSize=10.7,
                            leading=12, textColor=BLUE_DARK)
CARD_DESC = ParagraphStyle('CardDesc', fontName='Helvetica', fontSize=8.35,
                           leading=9.6, textColor=TEXT)
PRODUCT_TITLE = ParagraphStyle('ProductTitle', fontName='Helvetica-Bold',
                               fontSize=10.0, leading=11.2, textColor=BLUE_DARK)
URL_STYLE = ParagraphStyle('URL', fontName='Helvetica', fontSize=8.4,
                           leading=9.2, textColor=BLUE)
LEARN = ParagraphStyle('Learn', fontName='Helvetica', fontSize=8.7,
                       leading=10, textColor=TEXT)
EXP_TITLE = ParagraphStyle('ExpTitle', fontName='Helvetica-Bold', fontSize=13.4,
                           leading=15.4, textColor=BLUE_DARK)
METRIC_NUM = ParagraphStyle('MetricNum', fontName='Helvetica-Bold', fontSize=22,
                            leading=24, textColor=BLUE_DARK, alignment=1)
METRIC_LBL = ParagraphStyle('MetricLbl', fontName='Helvetica', fontSize=7.8,
                            leading=9.2, textColor=TEXT, alignment=1)

# --- content ---------------------------------------------------------------
PROFILE = (
    "Data analyst and systems architect with 10+ years building and shipping "
    "production systems. <b>1,000+ SOX-compliance IRDRs personally researched "
    "at Amazon ICQA</b>; built an Anthropic SQL copilot and autonomous "
    "root-cause-analysis agent in daily use. Solo architect of a "
    "<b>15-microservice open-source platform kernel</b> (OpenVibe), a "
    "live-streaming stack (OpenVibe Live), and a 14-service identity network. "
    "Previously <b>district top performer &rarr; Assistant Manager at Verizon "
    "Wireless</b>, coaching 4&ndash;8 reps."
)

METRICS = [
    ('1,000+', 'SOX IRDRs hand-researched',             '\uf002'),
    ('15',     'OpenVibe microservices shipped',         '\uf233'),
    ('200K+',  'Live game servers tracked',              '\uf11b'),
    ('20+',    'Amazon TamperMonkey/<br/>Python scripts','\uf085'),
    ('10+',    'Years running my own LLC',               '\uf0b1'),
]

TOP_FEATURE_CARDS = [
    ('\uf201', 'Analytics /<br/>Data', [
        'SQL, Power Query, Excel, dashboards',
        'SOX-compliant IRDR research + LLM agents',
    ]),
    ('\uf085', 'Robotics /<br/>RME &amp; AFM', [
        'Amazon Robotics (ARS) floor monitor',
        'Pod / drive / workstation troubleshooting',
    ]),
    ('\uf07a', 'Sales /<br/>Leadership', [
        'Top performer; district-level recognition',
        'Assistant Manager; coached 4&ndash;8 reps',
    ]),
    ('\uf03d', 'Product /<br/>Engineering', [
        'OpenVibe: 15-service platform kernel',
        'OpenVibe Live, HoboQuest, OpenVibe Network',
    ]),
]

EXPERIENCE = [
    {
        'title': 'Data Analyst — ICQA',
        'date': '2024 - 2025',
        'company': 'Amazon  ·  PAE2, Arlington WA',
        'bullets': [
            'Own SOX-compliance IRDR workflow &mdash; <b>hand-researched 1,000+ inventory mismatches</b>, authored reporting satisfying Sarbanes-Oxley audit trails.',
            'Authored an Anthropic-powered <b>SQL copilot</b> + an <b>autonomous root-cause-analysis agent</b> that plans, gathers evidence, and writes complete IRDRs end-to-end &mdash; collapsing hours of manual research per defect into seconds.',
        ],
        'stack': 'SQL  ·  Excel / Power Query  ·  Python  ·  Anthropic API  ·  TamperMonkey  ·  SOX Compliance',
    },
    {
        'title': 'Amnesty Floor Monitor (AFM)  —  Amazon Robotics',
        'date': '2023 - 2024',
        'company': 'Amazon  ·  Robotics launch site',
        'bullets': [
            'Monitored Amazon Robotics (ARS) automation during launch-stage operations &mdash; enforced amnesty zones, cleared obstructions, kept pod and drive-unit flow safe.',
            'Investigated recurring pod, drive, and workstation defects on the floor; documented patterns and escalated to RME and ops leadership to drive process improvements.',
        ],
        'stack': 'Amazon Robotics  ·  AFM protocols  ·  Floor safety  ·  Defect documentation',
    },
    {
        'title': 'Assistant Manager  /  Sales Representative',
        'date': '2020 - 2023',
        'company': 'Verizon Wireless',
        'bullets': [
            'Consistently ranked among <b>top performers in the district</b> &mdash; hit and exceeded monthly quotas across smartphones, plans, accessories, device protection, financing, and Verizon Visa offers.',
            'Promoted to Assistant Manager; mentored and coached a team of 4&ndash;8 reps through weekly 1-on-1s, floor coaching, and monthly workshops on objection handling, upselling, and customer retention. Led store opens / closes, inventory, escalations, and daily huddles.',
        ],
        'stack': 'Consultative Sales  ·  Team Leadership  ·  Coaching  ·  Retail Ops  ·  Quota Attainment  ·  Customer Retention',
    },
    {
        'title': 'Founder  ·  Systems Architect  ·  Principal Engineer',
        'date': '2022 - Present',
        'company': 'OpenVibe Network',
        'bullets': [
            'Sole architect and engineer on <b>OpenVibe</b> &mdash; a 15-microservice open-source platform kernel: distributed event bus, OIDC/OAuth2 identity, media object store, live ingest + restream, real-time chat, billing ledger, AI/search backbone. Self-hosted alternative to Twitch + YouTube + Patreon + Discord. 16 phases documented, 11+ shipped.',
            '<b>OpenVibe Live</b>: live-streaming platform from scratch &mdash; WebRTC SFU, HLS, multi-destination RTMP restream (OBS &rarr; Twitch / YouTube / Kick), auto-recorded VODs, clip detection, chat, voice channels, analytics, moderation, and an embedded in-stream browser game. Fully open source.',
            '<b>HoboQuest</b> (browser MMORPG) + <b>OpenVibe Network</b> (SSO + OAuth2 across 14 services): custom isomorphic engine with Source-Engine-style client prediction, 4 live game instances; shared themes, notifications, cross-domain sessions.',
        ],
        'stack': 'TypeScript  ·  Node.js  ·  Express  ·  PostgreSQL / SQLite  ·  Redis  ·  WebRTC  ·  WebSockets  ·  OAuth2 / OIDC  ·  FFmpeg  ·  Lua  ·  C#',
    },
    {
        'title': 'Founder  ·  Developer  ·  Systems Admin',
        'date': '2015 - Present',
        'company': 'GameServerStats, LLC',
        'bullets': [
            'Built analytics platforms tracking <b>200,000+ live game servers</b>; #1 Google result for several major titles, licensed to third-party sites under written agreement.',
            'Self-built and collocated 1U / 2U servers in datacenters; designed ingestion, dashboards, DDoS resilience, and ran the entire LLC &mdash; licenses, taxes, partner relations &mdash; for 10+ years.',
        ],
        'stack': 'Node.js  ·  PHP  ·  Python  ·  MongoDB  ·  MySQL  ·  Redis  ·  NGINX  ·  Linux',
    },
    {
        'title': 'Earlier Technical &amp; Business Experience',
        'date': '2012 - 2015',
        'company': 'Devolved  ·  GModStore  ·  eBay',
        'bullets': [
            'Built multiplayer game systems, in-game economies, and digital products sold through ScriptFodder / GModStore.',
            'Created graphics, support docs, e-commerce listings, moderation workflows; ran online communities at scale.',
        ],
        'stack': 'Lua  ·  PHP  ·  MySQL  ·  Photoshop  ·  Source Engine',
    },
]

PROJECTS = [
    ('\uf135', 'OpenVibe',
     'github.com/openvibe',
     '15-microservice open-source platform kernel &mdash; identity, event bus, media store, live ingest, billing, AI/search. Sole architect across 16 phases.',
     'https://github.com/HoboStreamer/OpenVibe-Temporary-MonoRepo'),
    ('\uf0eb', 'Autonomous IRDR Root-Cause Bot',
     'Internal Amazon tool',
     'Autonomous agent that plans, gathers evidence, and files SOX-compliant IRDRs end-to-end &mdash; built on 1,000+ hand-researched reports.',
     'https://alexfrison.net/portfolio'),
    ('\uf1c0', 'Amazon SQL Copilot',
     'Internal Amazon tool',
     'Anthropic-powered SQL assistant that auto-discovers tables / FKs / semantics and streams runnable, table-aware SQL for ICQA analysts.',
     'https://alexfrison.net/portfolio'),
    ('\uf11b', 'HoboQuest',
     'hobo.quest',
     'Browser MMORPG with custom isomorphic engine &mdash; Source-Engine-style client prediction, pixel canvas, 4 live game instances. 100% open source.',
     'https://hobo.quest'),
]

CORE_STACK = [
    ('\uf201', 'Analytics / Data',
     'SQL  ·  Excel + Power Query + VBA  ·  Python (pandas)  ·  Dashboards  ·  ICQA reporting  ·  Root-cause analysis  ·  Anthropic / LLM tool-use agents'),
    ('\uf121', 'Engineering / Web',
     'JavaScript / TypeScript  ·  Node.js  ·  Express  ·  Python  ·  PHP  ·  React  ·  Vue  ·  REST APIs  ·  HTML5 / CSS  ·  WebSockets / WebRTC  ·  OAuth2 / OIDC'),
    ('\uf233', 'Systems / Infrastructure',
     'Linux  ·  NGINX  ·  PostgreSQL / MySQL / MongoDB / Redis  ·  Cloudflare  ·  DDoS resilience  ·  Self-built 1U / 2U servers'),
    ('\uf085', 'Robotics  ·  Game Dev  ·  Leadership',
     'ARS robotics support  ·  Electro-mechanical troubleshooting  ·  Lua / C# / C++  ·  Source Engine  ·  Team coaching'),
]

LINKS = [
    ('\uf0ac', 'alexfrison.net',        'https://alexfrison.net'),
    ('\uf0e0', 'Alex@AlexFrison.net',   'mailto:Alex@AlexFrison.net'),
    ('\uf095', '(425) 367-3997',        'tel:+14253673997'),
    ('\uf08c', 'linkedin.com/in/fris',  'https://www.linkedin.com/in/fris/'),
]


# --- primitives ------------------------------------------------------------
def round_rect(c, x, y, w, h, r, fill, stroke=BLUE_LINE, stroke_width=1,
              shadow=True, shadow_dx=4, shadow_dy=-4):
    if shadow:
        c.setFillColor(SHADOW)
        c.setStrokeColor(SHADOW)
        c.roundRect(x + shadow_dx, y + shadow_dy, w, h, r, fill=1, stroke=0)
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(stroke_width)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)


def para(c, html, style, x, top, width, height=400):
    p = Paragraph(html, style)
    _, h = p.wrap(width, height)
    p.drawOn(c, x, top - h)
    return h


def draw_icon_circle(c, x, y, size, glyph, fg=BLUE, bg=CARD_BG,
                    font_size=15, stroke=BLUE_LINE):
    c.setFillColor(bg)
    c.setStrokeColor(stroke)
    c.setLineWidth(1.0)
    c.circle(x + size / 2, y + size / 2, size / 2, fill=1, stroke=1)
    c.setFont('FA', font_size)
    c.setFillColor(fg)
    c.drawCentredString(x + size / 2, y + size / 2 - font_size * 0.34, glyph)


def section_header(c, x, y, w, text, glyph, h=26):
    round_rect(c, x, y, w, h, h / 2, BLUE, stroke=BLUE, stroke_width=0.8,
              shadow=True)
    draw_icon_circle(c, x + 8, y + (h - 20) / 2, 20, glyph, fg=white,
                     bg=BLUE_SOFT, font_size=11, stroke=BLUE_SOFT)
    c.setFont('Helvetica-Bold', 13)
    c.setFillColor(white)
    c.drawString(x + 36, y + (h - 13) / 2 + 1, text)


def chip_width(text):
    return pdfmetrics.stringWidth(text, 'Helvetica-Bold', 8.9) + 28


def draw_chip(c, x, y, text, glyph, h=20):
    w = chip_width(text)
    c.setFillColor(BLUE_SOFT)
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, h / 2, fill=1, stroke=1)
    c.setFont('FA', 10)
    c.setFillColor(white)
    c.drawString(x + 9, y + 5, glyph)
    c.setFont('Helvetica-Bold', 8.9)
    c.drawString(x + 22, y + 6, text)
    return w


def draw_header(c, x, y, w, h):
    round_rect(c, x, y, w, h, 26, BLUE, stroke=BLUE, stroke_width=0.8,
              shadow=True)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 30)
    c.drawString(x + 22, y + h - 42, 'Alex Frison')

    role_style = ParagraphStyle('role', fontName='Helvetica-Bold',
                                fontSize=10.4, leading=12.2, textColor=white)
    role = ('Data Analyst &nbsp;&middot;&nbsp; Software Engineer &nbsp;&middot;&nbsp; '
            'Systems Architect')
    para(c, role, role_style, x + 24, y + h - 50, 340, 14)

    subtitle_style = ParagraphStyle('subtitle', fontName='Helvetica',
                                    fontSize=9.0, leading=11.0,
                                    textColor=white)
    subtitle = ('Versatile builder across analytics, robotics support, '
                'retail sales leadership, and full-stack platforms. '
                'Pacific Northwest based &mdash; open to hybrid, remote, on-site.')
    para(c, subtitle, subtitle_style, x + 24, y + h - 64, 340, 30)

    # role chips, two rows
    row1 = [('\uf201', 'Analytics / BI'),
            ('\uf121', 'Full Stack Eng'),
            ('\uf085', 'Robotics / RME')]
    row2 = [('\uf07a', 'Sales Leadership'),
            ('\uf0b1', 'Product Builder'),
            ('\uf135', 'Systems Architect')]
    cx = x + 24
    for glyph, text in row1:
        cx += draw_chip(c, cx, y + 36, text, glyph) + 8
    cx = x + 24
    for glyph, text in row2:
        cx += draw_chip(c, cx, y + 12, text, glyph) + 8

    # contact panel
    cp_w, cp_h = 212, 92
    cp_x, cp_y = x + w - cp_w - 18, y + h - cp_h - 16
    round_rect(c, cp_x, cp_y, cp_w, cp_h, 16, BLUE_SOFT,
              stroke=BLUE_LINE, stroke_width=0.9, shadow=False)

    # three rows: phone / email / web
    items = [
        ('\uf095', '+1 (425) 367-3997',         'tel:+14253673997'),
        ('\uf0e0', 'Alex@AlexFrison.net',       'mailto:alex@alexfrison.net'),
        ('\uf0ac', 'alexfrison.net',            'https://alexfrison.net'),
        ('\uf041', 'Seattle / Arlington, WA',   None),
    ]
    row_h = (cp_h - 16) / len(items)
    for i, (glyph, text, link) in enumerate(items):
        cy = cp_y + cp_h - 8 - (i + 1) * row_h
        draw_icon_circle(c, cp_x + 10, cy + (row_h - 18) / 2, 18, glyph,
                         fg=white, bg=BLUE_SOFT, font_size=10,
                         stroke=HexColor('#a8c4ee'))
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 9.3)
        c.drawString(cp_x + 36, cy + (row_h - 9) / 2 + 1, text)
        if link:
            c.linkURL(link, (cp_x, cy, cp_x + cp_w, cy + row_h),
                     relative=0, thickness=0)


def top_feature_card(c, x, y, w, h, glyph, title_html, bullets):
    round_rect(c, x, y, w, h, 16, CARD_BG, shadow=True)
    draw_icon_circle(c, x + 12, y + h - 38, 24, glyph, fg=BLUE, bg=CARD_BG,
                     font_size=12)
    para(c, title_html, ParagraphStyle('ft', parent=CARD_TITLE, fontSize=10.6,
                                       leading=11.8),
         x + 46, y + h - 11, w - 56, 26)
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(0.7)
    c.line(x + 14, y + h - 46, x + w - 14, y + h - 46)
    html = '<br/>'.join(f'&bull;&nbsp; {b}' for b in bullets)
    para(c, html, ParagraphStyle('fb', parent=CARD_DESC, fontSize=8.0,
                                 leading=9.2),
         x + 14, y + h - 52, w - 28, 60)


def metric_strip(c, x, y, w, h, metrics):
    round_rect(c, x, y, w, h, 14, CARD_BG, shadow=True)
    n = len(metrics)
    col_w = w / n
    ICON_BG = HexColor('#ddeaf8')
    r_icon = 14  # radius → 28 pt diameter
    for i, (num, lbl, glyph) in enumerate(metrics):
        col_x = x + i * col_w
        if i > 0:
            c.setStrokeColor(BLUE_LINE)
            c.setLineWidth(0.7)
            c.line(col_x, y + 8, col_x, y + h - 8)
        # icon circle — left side, vertically centred
        ic_cx = col_x + 8 + r_icon          # circle centre x
        ic_cy = y + h / 2                    # circle centre y
        c.setFillColor(ICON_BG)
        c.setStrokeColor(BLUE_LINE)
        c.setLineWidth(0.9)
        c.circle(ic_cx, ic_cy, r_icon, fill=1, stroke=1)
        c.setFont('FA', 14)
        c.setFillColor(BLUE)
        c.drawCentredString(ic_cx, ic_cy - 5, glyph)
        # number — right of icon, upper area, centred in text zone
        tx = col_x + 8 + r_icon * 2 + 6     # left edge of text
        label_w = col_w - (tx - col_x) - 4  # text zone width
        c.setFont('Helvetica-Bold', 18)
        c.setFillColor(BLUE_DARK)
        c.drawCentredString(tx + label_w / 2, y + h - 22, num)
        # label — below number, centred in same text zone
        para(c, lbl, METRIC_LBL, tx, y + h - 24, label_w, 28)


def draw_experience(c, x, y_top, title, date, company, bullets, stack,
                   rule_gap=8, width=None):
    if width is None:
        width = PAGE_W - x - 34
    title_w = width - 110
    h = para(c, title, EXP_TITLE, x, y_top, title_w, 22)
    c.setFont('Helvetica-Bold', 10.8)
    c.setFillColor(BLUE)
    c.drawRightString(x + width, y_top - 1, date)
    y = y_top - max(h, 14) - 4
    ch = para(c, company, COMPANY, x, y, width, 14)
    y -= ch + 2
    bullet_html = '<br/>'.join(f'&bull;&nbsp; {b}' for b in bullets)
    bh = para(c, bullet_html, BULLET, x + 8, y, width - 8, 200)
    y -= bh + 3
    sh = para(c, '<font name="FA">\uf013</font>&nbsp; ' + stack, STACK,
              x + 8, y, width - 8, 30)
    bottom = y - sh - rule_gap
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(0.6)
    c.line(x, bottom, x + width, bottom)
    return bottom - 12


def product_card(c, x, y, w, h, glyph, title, url, desc, link):
    round_rect(c, x, y, w, h, 14, CARD_BG, shadow=True)
    draw_icon_circle(c, x + 10, y + h - 28, 22, glyph, fg=BLUE, bg=CARD_BG,
                     font_size=11)
    tx = x + 38
    para(c, title, ParagraphStyle('pt', parent=PRODUCT_TITLE, fontSize=10.5,
                                  leading=11.4),
         tx, y + h - 8, w - (tx - x) - 10, 16)
    para(c, f'<u>{url}</u>',
         ParagraphStyle('pu', parent=URL_STYLE, fontSize=8.0, leading=9.0),
         tx, y + h - 22, w - (tx - x) - 10, 14)
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(0.5)
    c.line(x + 12, y + h - 34, x + w - 12, y + h - 34)
    _pd_s = ParagraphStyle('pd', parent=CARD_DESC, fontSize=8.4, leading=9.6)
    _, _pd_h = Paragraph(desc, _pd_s).wrap(w - 24, h - 42)
    _pd_vp = max(0.0, (h - 42 - _pd_h) / 2.0)
    para(c, desc, _pd_s, x + 12, y + h - 38 - _pd_vp, w - 24, _pd_h + 2)
    c.linkURL(link, (x, y, x + w, y + h), relative=0, thickness=0)


def core_card(c, x, y, w, h, glyph, title, desc):
    round_rect(c, x, y, w, h, 12, CARD_BG, shadow=True)
    draw_icon_circle(c, x + 10, y + h - 28, 22, glyph, fg=BLUE, bg=CARD_BG,
                     font_size=11)
    para(c, title,
         ParagraphStyle('ct2', parent=CARD_TITLE, fontSize=10.0, leading=11.2),
         x + 40, y + h - 8, w - 50, 18)
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(0.5)
    c.line(x + 12, y + h - 32, x + w - 12, y + h - 32)
    _cd_s = ParagraphStyle('cd2', parent=CARD_DESC, fontSize=8.4, leading=9.6)
    _, _cd_h = Paragraph(desc, _cd_s).wrap(w - 24, h - 40)
    _cd_vp = max(0.0, (h - 40 - _cd_h) / 2.0)
    para(c, desc, _cd_s, x + 12, y + h - 36 - _cd_vp, w - 24, _cd_h + 2)


def links_strip(c, x, y, w, h, links):
    round_rect(c, x, y, w, h, h / 2, CARD_BG, shadow=False)
    cx = x + 14
    for glyph, text, url in links:
        draw_icon_circle(c, cx, y + (h - 18) / 2, 18, glyph, fg=BLUE,
                         bg=CARD_BG, font_size=10)
        c.setFont('Helvetica-Bold', 9.2)
        c.setFillColor(BLUE_DARK)
        c.drawString(cx + 24, y + h / 2 - 3, text)
        tw = pdfmetrics.stringWidth(text, 'Helvetica-Bold', 9.2)
        link_w = 24 + tw + 20
        c.linkURL(url, (cx - 4, y, cx + link_w, y + h),
                 relative=0, thickness=0)
        cx += link_w + 6


# --- pages -----------------------------------------------------------------
def build(path):
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle('Alex Frison Resume')
    c.setAuthor('Alex Frison')
    c.setSubject('Resume — Data Analyst · Software Engineer · Systems Architect')

    margin = 18

    # ---- page 1 ----
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    header_h = 152
    header_y = PAGE_H - margin - header_h
    draw_header(c, margin, header_y, PAGE_W - 2 * margin, header_h)

    # top feature cards
    gap = 10
    card_w = (PAGE_W - 2 * margin - gap * 3) / 4
    card_h = 92
    top_y = header_y - 8 - card_h
    for i, card in enumerate(TOP_FEATURE_CARDS):
        cx = margin + i * (card_w + gap)
        top_feature_card(c, cx, top_y, card_w, card_h, *card)

    # metrics strip
    ms_h = 52
    ms_y = top_y - 4 - ms_h
    metric_strip(c, margin, ms_y, PAGE_W - 2 * margin, ms_h, METRICS)

    # profile (compact)
    prof_header_y = ms_y - 4 - 24
    section_header(c, margin, prof_header_y, PAGE_W - 2 * margin,
                   'PROFILE', '\uf2c0', h=24)
    # profile box — auto-height based on measured text
    _prof_style = ParagraphStyle('_pp', parent=BODY, fontSize=9.0, leading=10.8)
    _prof_para = Paragraph(PROFILE, _prof_style)
    _, _prof_text_h = _prof_para.wrap(PAGE_W - 2 * margin - 28, 400)
    prof_box_h = int(_prof_text_h) + 18   # 9pt top + 9pt bottom pad
    prof_box_y = prof_header_y - 4 - prof_box_h
    round_rect(c, margin, prof_box_y, PAGE_W - 2 * margin, prof_box_h, 12,
              CARD_BG, shadow=False)
    para(c, PROFILE, _prof_style,
         margin + 14, prof_box_y + prof_box_h - 9,
         PAGE_W - 2 * margin - 28, prof_box_h - 18)

    # experience header
    exp_y = prof_box_y - 8 - 24
    section_header(c, margin, exp_y, PAGE_W - 2 * margin, 'EXPERIENCE',
                   '\uf0b1', h=24)
    cur_y = exp_y - 10
    for e in EXPERIENCE[:3]:
        cur_y = draw_experience(c, margin + 12, cur_y, e['title'], e['date'],
                                e['company'], e['bullets'], e['stack'],
                                width=PAGE_W - 2 * margin - 24)

    # page footer removed to avoid bottom-overlap; pagination is visually obvious.

    c.showPage()

    # ---- page 2 ----
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    y = PAGE_H - margin - 4
    section_header(c, margin, y - 24, PAGE_W - 2 * margin,
                   'EXPERIENCE (CONT.)', '\uf0b1', h=24)
    y -= 36
    for e in EXPERIENCE[3:5]:
        y = draw_experience(c, margin + 12, y, e['title'], e['date'],
                            e['company'], e['bullets'], e['stack'],
                            width=PAGE_W - 2 * margin - 24)

    # selected products
    section_header(c, margin, y - 10, PAGE_W - 2 * margin,
                   'SELECTED PROJECTS  ·  LIVE EXAMPLES', '\uf0c1', h=24)
    y -= 6
    pw = (PAGE_W - 2 * margin - 10) / 2
    ph = 72
    for idx, prj in enumerate(PROJECTS):
        col = idx % 2
        row = idx // 2
        px = margin + col * (pw + 10)
        py = y - 6 - row * (ph + 6) - ph
        product_card(c, px, py, pw, ph, *prj)
    rows = (len(PROJECTS) + 1) // 2
    y = y - 6 - rows * (ph + 6) - 22

    # core stack
    section_header(c, margin, y - 4, PAGE_W - 2 * margin,
                   'CORE TECHNICAL STACK', '\uf1c0', h=24)
    y -= 6
    cw = (PAGE_W - 2 * margin - 10) / 2
    ch = 72
    for i in range(len(CORE_STACK)):
        col = i % 2
        row = i // 2
        cx = margin + col * (cw + 10)
        cy = y - 6 - row * (ch + 6) - ch
        g, t, d = CORE_STACK[i]
        core_card(c, cx, cy, cw, ch, g, t, d)
    n_rows = (len(CORE_STACK) + 1) // 2
    y = y - 6 - n_rows * (ch + 6) - 22

    # education + links
    section_header(c, margin, y - 4, PAGE_W - 2 * margin,
                   'EDUCATION  ·  LEARNING  ·  ELSEWHERE', '\uf19d', h=24)
    y -= 6
    edu_text = ('<b>Snohomish High School, WA</b> &mdash; AP Statistics, '
                'Calculus, English, Creative Writing, Spanish. Self-taught '
                'systems builder since age 12 &mdash; analytics, '
                'infrastructure, graphics, photography, hardware, and '
                'practical problem solving.')
    _, _edu_h = Paragraph(edu_text, LEARN).wrap(PAGE_W - 2 * margin - 28, 60)
    edu_h = int(_edu_h) + 14
    round_rect(c, margin, y - edu_h, PAGE_W - 2 * margin, edu_h, 12, CARD_BG,
              shadow=False)
    para(c, edu_text, LEARN, margin + 14, y - 7, PAGE_W - 2 * margin - 28, _edu_h)
    y -= edu_h + 8

    links_strip(c, margin, y - 34, PAGE_W - 2 * margin, 34, LINKS)

    c.setFont('Helvetica', 7.5)
    c.setFillColor(SUBTLE)
    c.drawCentredString(PAGE_W / 2, 6,
                       'Alex Frison  ·  Resume 2026  ·  alexfrison.net')

    c.showPage()
    c.save()


if __name__ == '__main__':
    build('Alex_Frison_Resume.pdf')
    print('Wrote Alex_Frison_Resume.pdf')
