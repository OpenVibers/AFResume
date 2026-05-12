from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

pdfmetrics.registerFont(TTFont('FA', 'fontawesome-webfont.ttf'))

PAGE_W, PAGE_H = letter

# Palette
BG = HexColor('#eef2f7')
BLUE = HexColor('#4f84d6')
BLUE_DARK = HexColor('#2a4f90')
BLUE_LINE = HexColor('#7ea8ee')
BLUE_SOFT = HexColor('#5f92de')
TEXT = HexColor('#34548f')
SHADOW = HexColor('#d9dee8')
CARD_BG = HexColor('#f8fbff')

# Typography
BODY = ParagraphStyle('Body', fontName='Helvetica', fontSize=10.4, leading=12.1, textColor=TEXT, spaceAfter=0)
COMPANY = ParagraphStyle('Company', fontName='Helvetica-Bold', fontSize=9.8, leading=11, textColor=BLUE)
BULLET = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=9.15, leading=10.25, textColor=TEXT)
CARD_TITLE = ParagraphStyle('CardTitle', fontName='Helvetica-Bold', fontSize=10.9, leading=12.2, textColor=BLUE_DARK)
CARD_DESC = ParagraphStyle('CardDesc', fontName='Helvetica', fontSize=8.35, leading=9.15, textColor=TEXT)
PRODUCT_TITLE = ParagraphStyle('ProductTitle', fontName='Helvetica-Bold', fontSize=10.2, leading=11.4, textColor=BLUE_DARK)
URL_STYLE = ParagraphStyle('URL', fontName='Helvetica', fontSize=8.7, leading=9.4, textColor=BLUE)
LEARN = ParagraphStyle('Learn', fontName='Helvetica', fontSize=8.7, leading=9.8, textColor=TEXT)
EXP_TITLE = ParagraphStyle('ExpTitle', fontName='Helvetica-Bold', fontSize=14.6, leading=16.0, textColor=BLUE_DARK)

products = [
    ('\uf0ac','HoboTools','hobo.tools','Shared-account ecosystem and network hub','https://hobo.tools'),
    ('\uf03d','HoboStreamer','hobostreamer.com','Streaming, clips, VODs, chat, creator tools','https://hobostreamer.com'),
    ('\uf041','HoboMaps','maps.hobo.tools','Map overlays, research, and survival data','https://maps.hobo.tools'),
    ('\uf11b','HoboQuest','hobo.quest','Browser MMORPG, multiplayer games, live canvas','https://hobo.quest'),
]

core_cards = [
    ('\uf201','Analytics / Data','SQL, Excel, reporting, dashboards, defect research, integrity, and root-cause analysis'),
    ('\uf121','Engineering / Web','JavaScript, TypeScript, Node.js, Python, PHP, React, Vue, Electron, HTML5, CSS/SASS, REST APIs'),
    ('\uf1c0','Systems / Infrastructure','Linux, Windows Server, NGINX, Apache, MongoDB, Redis, Cloudflare, deployment, scaling, and DDoS resilience'),
    ('\uf11b','Game Dev / Product','Lua, C#, C++, gameplay systems, creator tooling, UX, graphics, and product thinking'),
]


def round_rect(c, x, y, w, h, r, fill, stroke=BLUE_LINE, stroke_width=1, shadow=True, shadow_dx=4, shadow_dy=-4):
    if shadow:
        c.setFillColor(SHADOW)
        c.setStrokeColor(SHADOW)
        c.roundRect(x+shadow_dx, y+shadow_dy, w, h, r, fill=1, stroke=0)
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(stroke_width)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)


def para(c, html, style, x, top, width, height=200):
    p = Paragraph(html, style)
    _, h = p.wrap(width, height)
    p.drawOn(c, x, top-h)
    return h


def draw_icon_circle(c, x, y, size, glyph, fg=BLUE, bg=CARD_BG, font_size=15):
    c.setFillColor(bg)
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(1.1)
    c.circle(x + size/2, y + size/2, size/2, fill=1, stroke=1)
    c.setFont('FA', font_size)
    c.setFillColor(fg)
    c.drawCentredString(x + size/2, y + size/2 - font_size*0.34, glyph)


def section_header(c, x, y, w, text, glyph):
    round_rect(c, x, y, w, 30, 15, BLUE, stroke=BLUE, stroke_width=0.8, shadow=True)
    draw_icon_circle(c, x+10, y+4, 22, glyph, fg=white, bg=BLUE_SOFT, font_size=12)
    c.setFont('Helvetica-Bold', 15)
    c.setFillColor(white)
    c.drawString(x+38, y+9, text)


def chip_width(text):
    return pdfmetrics.stringWidth(text, 'Helvetica-Bold', 8.9) + 28


def draw_chip(c, x, y, text, glyph, h=22):
    w = chip_width(text)
    c.setFillColor(BLUE_SOFT)
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, h/2, fill=1, stroke=1)
    c.setFont('FA', 10)
    c.setFillColor(white)
    c.drawString(x+9, y+6, glyph)
    c.setFont('Helvetica-Bold', 8.9)
    c.drawString(x+22, y+7, text)
    return w


def draw_header(c, x, y, w, h):
    round_rect(c, x, y, w, h, 28, BLUE, stroke=BLUE, stroke_width=0.8, shadow=True)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 31)
    c.drawString(x+20, y+h-46, 'Alex Frison')

    subtitle_style = ParagraphStyle('subtitle', fontName='Helvetica-Bold', fontSize=10.3, leading=11.0, textColor=white)
    subtitle = ('Data analyst and systems-minded builder across analytics, robotics support, retail sales leadership, and full-stack platforms.')
    para(c, subtitle, subtitle_style, x+22, y+h-74, 330, 40)

    # Chips - always inside the header; fixed 2-row layout
    row1 = [('\uf201','Analytics / BI'),('\uf121','Full Stack Eng'),('\uf0ad','Robotics / RME')]
    row2 = [('\uf07a','Sales Leadership'),('\uf0b1','Product Builder')]
    cx = x + 22
    for glyph, text in row1:
        cx += draw_chip(c, cx, y+42, text, glyph) + 10
    cx = x + 22
    for glyph, text in row2:
        cx += draw_chip(c, cx, y+14, text, glyph) + 10

    # contact panel
    cp_w, cp_h = 206, 84
    cp_x, cp_y = x + w - cp_w - 18, y + h - cp_h - 18
    round_rect(c, cp_x, cp_y, cp_w, cp_h, 18, BLUE_SOFT, stroke=BLUE_LINE, stroke_width=0.9, shadow=False)
    top_icon_y = cp_y + cp_h - 36
    bottom_icon_y = cp_y + 12
    draw_icon_circle(c, cp_x+12, top_icon_y, 24, '\uf095', fg=white, bg=BLUE_SOFT, font_size=12)
    draw_icon_circle(c, cp_x+12, bottom_icon_y, 24, '\uf0e0', fg=white, bg=BLUE_SOFT, font_size=11)
    c.setStrokeColor(HexColor('#83a8e6'))
    c.setLineWidth(0.8)
    c.line(cp_x+18, cp_y + cp_h/2, cp_x+cp_w-18, cp_y + cp_h/2)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 10.5)
    c.drawString(cp_x+42, cp_y + cp_h - 20, '+1 (425) 367-3997')
    c.drawString(cp_x+42, cp_y + 28, 'Alex@AlexFrison.net')


def top_feature_card(c, x, y, w, h, glyph, title_html, bullets, desc_size=8.45):
    round_rect(c, x, y, w, h, 18, CARD_BG, shadow=True)
    draw_icon_circle(c, x+14, y+h-46, 28, glyph, fg=BLUE, bg=CARD_BG, font_size=14)
    para(c, title_html, ParagraphStyle('ft', parent=CARD_TITLE, fontSize=11.2, leading=12.5), x+52, y+h-14, w-66, 26)
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(0.8)
    c.line(x+18, y+h-52, x+w-18, y+h-52)
    html = '<br/>'.join(f'&bull; {b}' for b in bullets)
    para(c, html, ParagraphStyle('fb', parent=CARD_DESC, fontSize=desc_size, leading=9.1), x+18, y+h-60, w-36, 60)


def product_card(c, x, y, w, h, glyph, title, url, desc, link):
    round_rect(c, x, y, w, h, 16, CARD_BG, shadow=True)
    draw_icon_circle(c, x+12, y+h-16-22, 22, glyph, fg=BLUE, bg=CARD_BG, font_size=11)
    tx = x + 42
    para(c, title, ParagraphStyle('pt', parent=PRODUCT_TITLE, fontSize=10.1, leading=10.9), tx, y+h-10, w-(tx-x)-12, 18)
    para(c, f'<u>{url}</u>', ParagraphStyle('pu', parent=URL_STYLE, fontSize=8.6, leading=8.9), tx, y+h-30, w-(tx-x)-12, 14)
    para(c, desc, ParagraphStyle('pd', parent=CARD_DESC, fontSize=8.4, leading=8.8), tx, y+18, w-(tx-x)-12, 24)
    c.linkURL(link, (x, y, x+w, y+h), relative=0, thickness=0)


def core_card(c, x, y, w, h, glyph, title, desc):
    round_rect(c, x, y, w, h, 16, CARD_BG, shadow=True)
    draw_icon_circle(c, x+12, y+h-14-22, 22, glyph, fg=BLUE, bg=CARD_BG, font_size=12)
    para(c, title, ParagraphStyle('ct2', parent=CARD_TITLE, fontSize=10.8, leading=11.4), x+42, y+h-10, w-54, 18)
    # More left margin and slightly lower top to separate from title.
    para(c, desc, ParagraphStyle('cd2', parent=CARD_DESC, fontSize=8.45, leading=9.0), x+58, y+30, w-70, 24)


def draw_experience(c, x, y_top, title, date, company, bullets, rule_gap=10):
    title_style = ParagraphStyle('et', parent=EXP_TITLE, fontSize=14.6, leading=16.0)
    title_w = PAGE_W - x - 34 - 132
    h = para(c, title, title_style, x, y_top, title_w, 24)
    c.setFont('Helvetica-Bold', 11.8)
    c.setFillColor(BLUE)
    c.drawRightString(PAGE_W-34, y_top-1, date)
    y = y_top - max(h, 14) - 7
    ch = para(c, company, COMPANY, x, y, PAGE_W-x-34, 14)
    y -= ch + 3
    bullet_html = '<br/>'.join(f'&bull; {b}' for b in bullets)
    bh = para(c, bullet_html, BULLET, x+10, y, PAGE_W-x-44, 60)
    bottom = y - bh - rule_gap
    c.setStrokeColor(BLUE_LINE)
    c.setLineWidth(0.8)
    c.line(x, bottom, PAGE_W-34, bottom)
    return bottom - 14


def build(path):
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle('Alex Frison Resume')

    for page in [1, 2]:
        c.setFillColor(BG)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        x = 18
        if page == 1:
            header_h = 170
            header_y = PAGE_H - 18 - header_h
            draw_header(c, x, header_y, PAGE_W-36, header_h)

            # top feature cards, tighter to header to reduce blank band
            top_y = header_y - 8 - 126
            gap = 14
            card_w = (PAGE_W - 36 - gap*3) / 4
            card_h = 126
            xs = [x, x+card_w+gap, x+(card_w+gap)*2, x+(card_w+gap)*3]
            top_feature_card(c, xs[0], top_y, card_w, card_h, '\uf201', 'Analytics /<br/>Data', [
                'SQL, Excel, Inventory Control / Quality Assurance reporting',
                'Defect review and discrepancy analysis',
                'Live dashboards and analytics'
            ])
            top_feature_card(c, xs[1], top_y, card_w, card_h, '\uf0ad', 'RME /<br/>Robotics', [
                'Amazon Robotics FC launch and automation',
                'Robotics support and troubleshooting',
                'Electro-mech hardware exposure'
            ])
            top_feature_card(c, xs[2], top_y, card_w, card_h, '\uf07a', 'Sales /<br/>Leadership', [
                'Plans, devices, financing',
                'Coaching, meetings, escalations',
                'Retention and quota execution'
            ])
            top_feature_card(c, xs[3], top_y, card_w, card_h, '\uf03d', 'Product /<br/>Streaming', [
                'HoboTools, HoboStreamer, HoboQuest',
                'Clips, VODs, creator tools',
                'Cross-service UX and operations'
            ], desc_size=8.0)

            profile_header_y = top_y - 22 - 16
            section_header(c, x, profile_header_y, PAGE_W-36, 'PROFILE', '\uf2c0')
            profile_box_y = profile_header_y - 50
            round_rect(c, x, profile_box_y-4, PAGE_W-36, 46, 18, CARD_BG, shadow=False)
            profile = ('Versatile data analyst and systems-minded builder with experience across Amazon ICQA analytics, Amazon RME support, retail sales leadership, and full-stack product development. Strong at turning operational context into clear reporting, stakeholder-ready analysis, practical tools, and process improvements.')
            para(c, profile, BODY, x+18, profile_box_y+38, PAGE_W-72, 30)

            exp_header_y = profile_box_y - 38
            section_header(c, x, exp_header_y, PAGE_W-36, 'EXPERIENCE', '\uf0b1')
            cur_y = exp_header_y - 16
            cur_y = draw_experience(c, x+18, cur_y, 'Data Analyst', '2024 - Present', 'Amazon', [
                'Built ICQA SQL and Excel reporting for inventory accuracy, discrepancy review, and defect visibility.',
                'Turned mismatch findings into dashboards, recurring reports, and stakeholder-ready analysis for operational decisions.'
            ])
            cur_y = draw_experience(c, x+18, cur_y, 'Reliability, Maintenance, and Engineering', '2023 - 2024', 'Amazon', [
                'Supported launch-stage ARS robotics and conveyance operations while monitoring automation flow, floor conditions, and equipment behavior.',
                'Assisted troubleshooting across robotics, uptime, safety, and electro-mechanical issues in a high-change launch environment.'
            ])
            draw_experience(c, x+18, cur_y, 'Assistant Manager / Sales Representative', '2020 - 2023', 'Verizon Wireless', [
                'Sold smartphones, wireless plans, accessories, protection, financing, and credit-card offers in a quota-driven retail environment; earned district-level recognition.',
                'Coached associates, ran monthly meetings and workshops, and improved customer service, retention, merchandising, and inventory ownership.'
            ], rule_gap=8)
        else:
            y = PAGE_H - 26
            y = draw_experience(c, x, y, 'Founder / Product Engineer / Streaming & Game Builder', 'Present', 'Hobo Tools / HoboStreamer / HoboQuest / HoboMaps', [
                'Built shared-account web products across Hobo Tools, HoboStreamer, HoboQuest, and HoboMaps with unified UX, connected identity, and cross-service navigation.',
                'Developed creator-facing streaming systems including clips, VODs, chat, moderation, analytics, restream support, and multi-path delivery; also built browser multiplayer game experiences and creator tools using Lua, C#, C++, gameplay systems, and product-minded UX.'
            ])
            y = draw_experience(c, x, y, 'Founder / Developer / Systems Admin', '2015 - Present', 'GameServerStats, LLC', [
                'Built analytics-focused web platforms that track 200,000+ live game servers using JavaScript, Node.js, PHP, Python, SQL, MongoDB, Redis, HTML, and CSS.',
                'Designed ingestion, search, dashboards, Linux infrastructure, scaling, DDoS resilience, support workflows, and business reporting.'
            ])
            y = draw_experience(c, x, y, 'Earlier Technical and Business Experience', '2012 - Present', 'Devolved, GModStore.com, eBay', [
                'Built multiplayer game systems, digital products, graphics, support docs, e-commerce listings, moderation workflows, and monetized online communities.'
            ], rule_gap=6)

            prod_header_y = y - 16
            section_header(c, x, prod_header_y, PAGE_W-36, 'SELECTED PRODUCTS / LIVE EXAMPLES', '\uf0c1')
            pw = (PAGE_W - 36 - 18) / 2
            ph = 66
            py1 = prod_header_y - 72
            xs = [x, x+pw+18]
            product_card(c, xs[0], py1, pw, ph, *products[0])
            product_card(c, xs[1], py1, pw, ph, *products[1])
            py2 = py1 - 76
            product_card(c, xs[0], py2, pw, ph, *products[2])
            product_card(c, xs[1], py2, pw, ph, *products[3])

            core_header_y = py2 - 28
            section_header(c, x, core_header_y, PAGE_W-36, 'CORE TECHNICAL STACK', '\uf1c0')
            cw = (PAGE_W - 36 - 18) / 2
            ch = 58
            cy1 = core_header_y - 64
            core_card(c, x, cy1, cw, ch, core_cards[0][0], core_cards[0][1], core_cards[0][2])
            core_card(c, x+cw+18, cy1, cw, ch, core_cards[1][0], core_cards[1][1], core_cards[1][2])
            cy2 = cy1 - 66
            core_card(c, x, cy2, cw, ch, core_cards[2][0], core_cards[2][1], core_cards[2][2])
            core_card(c, x+cw+18, cy2, cw, ch, core_cards[3][0], core_cards[3][1], core_cards[3][2])

            learn_header_y = cy2 - 28
            section_header(c, x, learn_header_y, PAGE_W-36, 'EDUCATION / LEARNING', '\uf19d')
            learn_box_y = learn_header_y - 48
            round_rect(c, x, learn_box_y, PAGE_W-36, 40, 16, CARD_BG, shadow=False)
            learn_text = ('Snohomish High School, WA - AP Statistics, Calculus, English, Creative Writing, Spanish - Self-taught systems builder with a strong self-starter mindset, focused on analytics, infrastructure, graphics, photography, and practical problem solving.')
            para(c, learn_text, LEARN, x+16, learn_box_y+27, PAGE_W-68, 20)

        c.showPage()
    c.save()


if __name__ == '__main__':
    build('Alex_Frison_Resume.pdf')
