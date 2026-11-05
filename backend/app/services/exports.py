"""CSV / JSON / Markdown / PDF exports derived from live records."""
from __future__ import annotations

import csv
import io
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def rows_to_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})
    return buf.getvalue().encode()


def rows_to_md(title: str, rows: list[dict], intro: str = "") -> bytes:
    lines = [f"# {title}", ""]
    if intro:
        lines += [intro, ""]
    if rows:
        cols = list(rows[0].keys())
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "---|" * len(cols))
        for r in rows:
            vals = [json.dumps(r[c]) if isinstance(r[c], (dict, list)) else str(r[c] if r[c] is not None else "")
                    for c in cols]
            lines.append("| " + " | ".join(v.replace("|", "\\|").replace("\n", " ") for v in vals) + " |")
    else:
        lines.append("_No records._")
    return ("\n".join(lines) + "\n").encode()


def rows_to_pdf(title: str, rows: list[dict], intro: str = "") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), title=title, leftMargin=28, rightMargin=28)
    st = getSampleStyleSheet()
    small = st["BodyText"].clone("small", fontSize=7, leading=9)
    story = [Paragraph(title, st["Title"])]
    if intro:
        story += [Paragraph(intro, st["BodyText"]), Spacer(1, 8)]
    if rows:
        cols = list(rows[0].keys())
        data = [[Paragraph(f"<b>{c}</b>", small) for c in cols]]
        for r in rows[:1000]:
            data.append([Paragraph(str(r[c] if not isinstance(r[c], (dict, list)) else json.dumps(r[c]))[:300]
                                   .replace("&", "&amp;").replace("<", "&lt;"), small) for c in cols])
        tbl = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                                 ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                                 ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(tbl)
    else:
        story.append(Paragraph("No records.", st["BodyText"]))
    doc.build(story)
    return buf.getvalue()


def render(fmt: str, title: str, rows: list[dict], payload: object, intro: str = "") -> tuple[bytes, str]:
    if fmt == "json":
        return json.dumps(payload, indent=2, default=str).encode(), "application/json"
    if fmt == "csv":
        return rows_to_csv(rows), "text/csv"
    if fmt == "md":
        return rows_to_md(title, rows, intro), "text/markdown"
    if fmt == "pdf":
        return rows_to_pdf(title, rows, intro), "application/pdf"
    raise ValueError("format must be csv, json, md or pdf")
