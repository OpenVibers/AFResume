#!/usr/bin/env python3
"""Build plain, one-column résumés for applicant tracking systems, from the same content as the site and the designed
PDF (build_resume.py), in versions aimed at different roles:

  public/Alex_Frison_Resume_Engineering.pdf    software engineering (full-stack, payments, identity, streaming)
  public/Alex_Frison_Resume_Data_Analyst.pdf   data / BI / operations analyst
  public/Alex_Frison_Resume_IT_Support.pdf     IT, help desk and technical support (near-home jobs)

The designed PDF is multi-column with icons; a tracking system reads its text layer column by column and scrambles it.
These have one column, real text in reading order, standard fonts and plain section names, so a parser gets every
line right. Facts only come from src/data/profile.json and src/content/; what differs per version is the headline, the
summary, which skills lead and which bullets each role keeps (a count, or the bullets' indexes).

Run from the repo root:  python3 resume/build_ats_resume.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent.parent
INK, MUTED, RULE = HexColor("#111111"), HexColor("#444444"), HexColor("#999999")

VERSIONS = {
    "engineering": {
        "file": "Alex_Frison_Resume_Engineering.pdf",
        "headline": "Software Engineer: full-stack TypeScript and Node.js, payments, identity and live streaming",
        "summary": (
            "Software engineer who builds complete products and keeps them running in production: platforms, APIs, "
            "payment systems, identity providers and live-streaming infrastructure. Rebuilt PowerChat's payments "
            "across five processors and designed its developer API platform; founder and sole engineer of OpenVibe, "
            "a network of seven connected apps under one login; ten years running my own company's analytics "
            "platforms and servers. Comfortable owning the whole thing: design, code, deployment and support."),
        "skills": [
            ("Languages", ["TypeScript", "JavaScript", "Python", "SQL", "Go", "PHP", "Lua", "HTML / CSS"]),
            ("Backend", ["Node.js", "Express", "REST and event-driven design", "Redis / BullMQ", "Prisma", "WebSockets"]),
            ("Data", ["PostgreSQL", "MySQL", "SQLite (WAL)", "MongoDB", "TimescaleDB"]),
            ("Frontend", ["React", "server-side rendering", "performance profiling (Core Web Vitals, CDP)"]),
            ("Payments and identity", ["Stripe Connect", "Square", "PayPal", "NMI", "Tipalti", "ledgers and idempotency",
                                       "OAuth2 / OIDC providers", "JWT (RS256) / JWKS", "SSO", "webhook signing"]),
            ("Streaming and realtime", ["WebRTC (mediasoup, werift)", "RTMP / SRT / WHIP", "HLS / DASH", "ffmpeg",
                                        "TURN / coturn", "live captions (whisper.cpp)"]),
            ("Infrastructure", ["Linux", "nginx", "systemd", "Docker", "GitLab CI", "Cloudflare", "Backblaze B2 / R2 / S3 APIs",
                                "zero-downtime deploys"]),
            ("AI", ["tool-use agents", "Anthropic and OpenAI-compatible APIs", "local inference (whisper.cpp, Ollama)"]),
        ],
        "bullets": {"PowerChat": 3, "OpenVibe": 3, "Amazon/analytics": 2, "Amazon/operations": 1, "Verizon Wireless": 2,
                    "founder": 2, "earlier": 1},
        "projects": ["openvibe-live", "openvibe-network", "openvibe-games", "irdr-autonomous-bot"],
    },
    "analyst": {
        "file": "Alex_Frison_Resume_Data_Analyst.pdf",
        "headline": "Data Analyst: SQL, Excel and Power Query, compliance reporting and automation",
        "summary": (
            "Data analyst with an engineer's toolkit. At Amazon ICQA I owned the SOX-compliance IRDR workflow, "
            "researched 1,000+ inventory discrepancies, built the SQL and Excel reporting, dashboards and leadership "
            "reports behind inventory accuracy, and turned the research into tooling other associates used every day, "
            "including an autonomous root-cause agent. Before that, ten years running my own company's analytics "
            "platforms (200,000+ live game servers tracked) and three years in sales, as an assistant manager "
            "coaching a team."),
        "skills": [
            ("Analytics", ["SQL", "Excel", "Power Query", "VBA", "dashboards and recurring reporting", "root-cause analysis",
                           "SOX controls and audit trails", "inventory accuracy and defect analysis"]),
            ("Automation", ["Python", "JavaScript / TypeScript", "TamperMonkey userscripts", "tool-use AI agents",
                            "Anthropic and OpenAI-compatible APIs"]),
            ("Data", ["PostgreSQL", "MySQL", "SQLite", "TimescaleDB", "MongoDB"]),
            ("Communication", ["leadership reports", "a network-wide quality recap deck", "technical writing and runbooks",
                               "coaching and team leadership", "consultative sales"]),
            ("Also", ["full-stack web development (Node.js, React)", "Linux and servers", "payments and billing systems"]),
        ],
        "bullets": {"PowerChat": 2, "OpenVibe": 1, "Amazon/analytics": 3, "Amazon/operations": 2, "Verizon Wireless": 2,
                    "founder": 2, "earlier": 1},
        "projects": ["irdr-autonomous-bot", "irdr-quality-recap", "amazon-userscripts"],
    },
    "support": {
        "file": "Alex_Frison_Resume_IT_Support.pdf",
        "headline": "IT and Technical Support: Linux and servers, hardware troubleshooting, customer support and escalations",
        "summary": (
            "Hands-on technical generalist in Arlington, WA. Ten years running my own company's servers: self-built "
            "and colocated 1U and 2U hardware, Linux, nginx and DDoS resilience, and later a full infrastructure "
            "migration with zero downtime and zero data loss. At Amazon Robotics I investigated recurring pod, drive-unit "
            "and workstation defects and escalated them to RME; as an ICQA data analyst I built tools other associates "
            "used every day. Three years at Verizon Wireless on phones, plans and accessories, promoted to Assistant "
            "Manager running inventory and escalations. I document what I fix: incident write-ups, runbooks and "
            "support docs."),
        "skills": [
            ("Support and troubleshooting", ["hardware and electro-mechanical troubleshooting", "root-cause analysis",
                                             "incident documentation", "escalations", "support docs and runbooks"]),
            ("Systems", ["Linux", "server hardware (self-built and colocated 1U / 2U)", "nginx", "systemd", "Docker",
                         "Cloudflare", "cloud storage (Backblaze B2 / R2 / S3 APIs)", "zero-downtime migrations"]),
            ("Network and web", ["HAR network-trace debugging (HARTools)", "DDoS resilience", "WebSockets", "TURN / coturn"]),
            ("Scripting and automation", ["Python", "JavaScript / TypeScript", "SQL", "PHP", "TamperMonkey userscripts",
                                          "Excel / Power Query / VBA"]),
            ("People", ["customer retention and consultative sales", "coaching a team of 4 to 8", "opens, closes and inventory",
                        "technical writing"]),
        ],
        "bullets": {"PowerChat": 1, "OpenVibe": [0, 2], "Amazon/analytics": [0, 2], "Amazon/operations": 2,
                    "Verizon Wireless": 3, "founder": 2},
        "projects": ["amazon-userscripts", "hartools", "openvibe-cutover", "mp-select-mini"],
    },
}


def load() -> dict:
    profile = json.loads((ROOT / "src/data/profile.json").read_text())
    roles = sorted((json.loads(p.read_text()) for p in (ROOT / "src/content/experience").glob("*.json")),
                   key=lambda r: r.get("order", 99))
    projects = {}
    for p in (ROOT / "src/content/projects").glob("*.mdx"):
        m = re.match(r"---\n(.*?)\n---", p.read_text(), re.S)
        fm = {}
        for line in (m.group(1).splitlines() if m else []):
            k, _, v = line.partition(":")
            if v.strip().startswith('"'):
                fm[k.strip()] = v.strip().strip('"')
        projects[p.stem] = fm
    return {"profile": profile, "roles": roles, "projects": projects}


def plain(s: str) -> str:
    """Plain characters for the parser: dashes and middle dots become what a keyboard types."""
    s = re.sub(r"\s*\u2014\s*", ", ", s).replace("\u2013", "-").replace("\u2192", "to").replace("\u00b7", "|")
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"'))


def bullets_for(role: dict, counts: dict) -> list[str]:
    key = role["company"] if role["company"] in counts else (
        f"Amazon/{role.get('kind')}" if role["company"] == "Amazon" else role.get("kind", ""))
    if role["company"].startswith("OpenVibe"):
        key = "OpenVibe"
    pick = counts.get(key, counts.get(role.get("kind", ""), 2))
    bullets = role.get("bullets", [])
    return [bullets[i] for i in pick if i < len(bullets)] if isinstance(pick, list) else bullets[:pick]


def build(version: str, data: dict) -> Path:
    v = VERSIONS[version]
    pr = data["profile"]
    out = ROOT / "public" / v["file"]
    st = {
        "name": ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=INK),
        "contact": ParagraphStyle("contact", fontName="Helvetica", fontSize=9.2, leading=12, textColor=MUTED),
        "headline": ParagraphStyle("headline", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=INK,
                                   spaceBefore=4),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=INK, spaceBefore=9,
                            spaceAfter=2),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.4, leading=12.4, textColor=INK, alignment=TA_LEFT),
        "role": ParagraphStyle("role", fontName="Helvetica-Bold", fontSize=9.8, leading=12.6, textColor=INK, spaceBefore=5),
        "meta": ParagraphStyle("meta", fontName="Helvetica-Oblique", fontSize=9, leading=11.6, textColor=MUTED),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.3, leading=12.2, textColor=INK,
                                 leftIndent=12, bulletIndent=2),
    }
    rule = lambda: HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=1, spaceAfter=3)  # noqa: E731
    story = [
        Paragraph(plain(pr["name"]), st["name"]),
        Paragraph(plain(" | ".join([pr["locationShort"].replace("Seattle / ", "") + " (Seattle area)", pr["phoneDisplay"],
                                    pr["email"], pr["siteDisplay"], pr["linkedinDisplay"], pr["githubDisplay"]])), st["contact"]),
        Paragraph(plain(v["headline"]), st["headline"]),
        Paragraph("SUMMARY", st["h"]), rule(), Paragraph(plain(v["summary"]), st["body"]),
        Paragraph("SKILLS", st["h"]), rule(),
    ]
    for group, items in v["skills"]:
        story.append(Paragraph(f"<b>{plain(group)}:</b> {plain(', '.join(items))}", st["body"]))
    story += [Paragraph("EXPERIENCE", st["h"]), rule()]
    for r in data["roles"]:
        chosen = bullets_for(r, v["bullets"])
        head = Paragraph(plain(f"{r['role']}, {r['company']}"), st["role"])
        meta = Paragraph(plain(" | ".join(x for x in [r.get("location", ""), f"{r['start']} to {r['end']}"] if x)), st["meta"])
        items = [Paragraph(plain(b), st["bullet"], bulletText="•") for b in chosen]
        if r.get("stack") and version == "engineering" and len(chosen) >= 2:
            items.append(Paragraph(plain("Stack: " + ", ".join(r["stack"])), st["meta"]))
        story.append(KeepTogether([head, meta, *items[:1]]))
        story += items[1:]
    story += [Paragraph("SELECTED PROJECTS", st["h"]), rule()]
    for slug in v["projects"]:
        p = data["projects"].get(slug, {})
        if p.get("title"):
            story.append(Paragraph(f"<b>{plain(p['title'])}</b>: {plain(p.get('summary', ''))}", st["bullet"],
                                   bulletText="•"))
    story += [Paragraph("EDUCATION", st["h"]), rule(), Paragraph(plain(pr["education"]), st["body"])]
    doc = SimpleDocTemplate(str(out), pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch, title=f"{pr['name']} - Resume",
                            author=pr["name"], subject=v["headline"])
    doc.build(story)
    return out


if __name__ == "__main__":
    data = load()
    for name in VERSIONS:
        print(build(name, data).relative_to(ROOT))
