"""Generate printable PDF documents without a web browser or server."""
from pathlib import Path
from xml.sax.saxutils import escape
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepInFrame

GREEN = colors.HexColor("#14765b")
INK = colors.HexColor("#24352f")
FONT = "Helvetica"
BOLD = "Helvetica-Bold"
# Embed a Unicode font for names and addresses whenever the platform provides one.
for regular, bold in [
    (Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/arial.ttf", Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/arialbd.ttf"),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
]:
    if regular.is_file() and bold.is_file():
        pdfmetrics.registerFont(TTFont("OSYRegular", str(regular)))
        pdfmetrics.registerFont(TTFont("OSYBold", str(bold)))
        FONT, BOLD = "OSYRegular", "OSYBold"
        break


def paragraph(value, size=8, color=INK, bold=False):
    return Paragraph(escape(str(value or "")).replace("\n", "<br/>"),
                     ParagraphStyle("text", fontName=BOLD if bold else FONT, fontSize=size,
                                    leading=size * 1.35, textColor=color, splitLongWords=True))


def draw_fit(pdf, text, x, y, width, height, size=8, bold=False, color=INK):
    """Draw inside a bounded box, shrinking unusually long values without clipping."""
    block = KeepInFrame(width, height, [paragraph(text, size, color, bold)], mode="shrink")
    block.wrapOn(pdf, width, height)
    block.drawOn(pdf, x, y + height - block.height)


def id_pdf(record, destination, organization, photo_path=None):
    width, height = 86 * mm, 54 * mm
    pdf = canvas.Canvas(str(destination), pagesize=(width, height))
    pdf.setTitle("OSY ID - " + record["osy_id"])
    pdf.setFillColor(GREEN)
    pdf.rect(0, height - 12 * mm, width, 12 * mm, fill=1, stroke=0)
    draw_fit(pdf, "OUT-OF-SCHOOL YOUTH", 4 * mm, height - 7 * mm, 78 * mm, 4.5 * mm, 10, True, colors.white)
    draw_fit(pdf, "IDENTIFICATION CARD", 4 * mm, height - 11 * mm, 78 * mm, 3.5 * mm, 6.5, False, colors.white)
    pdf.setFillColor(colors.HexColor("#e9f3ee"))
    pdf.rect(4 * mm, 15 * mm, 20 * mm, 24 * mm, fill=1, stroke=0)
    if photo_path and Path(photo_path).is_file():
        pdf.drawImage(str(photo_path), 4 * mm, 15 * mm, 20 * mm, 24 * mm, preserveAspectRatio=True, anchor="c", mask="auto")
    else:
        initials = "".join(part[0] for part in record["full_name"].split()[:2]).upper()
        draw_fit(pdf, initials, 7 * mm, 21 * mm, 14 * mm, 9 * mm, 22, True, GREEN)
    draw_fit(pdf, record["full_name"], 27 * mm, 31 * mm, 55 * mm, 9 * mm, 10, True)
    draw_fit(pdf, record["osy_id"], 27 * mm, 26 * mm, 55 * mm, 4.5 * mm, 8, True, GREEN)
    draw_fit(pdf, "Birthdate: " + record["birthdate"], 27 * mm, 22 * mm, 55 * mm, 4 * mm, 6.5)
    draw_fit(pdf, "Address: " + record["address"], 27 * mm, 12 * mm, 55 * mm, 9.5 * mm, 6.5)
    draw_fit(pdf, "Status: " + record["status"] + (" / Archived" if record["archived_at"] else ""),
             4 * mm, 7.5 * mm, 78 * mm, 4 * mm, 6.5)
    pdf.setStrokeColor(colors.HexColor("#dce5df"))
    pdf.line(4 * mm, 7 * mm, 82 * mm, 7 * mm)
    draw_fit(pdf, organization, 4 * mm, 1.5 * mm, 46 * mm, 5 * mm, 5.5)
    draw_fit(pdf, "Authorized signature", 54 * mm, 1.5 * mm, 28 * mm, 5 * mm, 5.5)
    pdf.showPage()
    pdf.save()


def report_pdf(rows, destination, organization, description="All current records"):
    document = SimpleDocTemplate(str(destination), pagesize=landscape(A4), leftMargin=12 * mm,
                                 rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=15 * mm,
                                 title="OSY master list", author=organization)
    story = [paragraph(organization, 15, bold=True), Spacer(1, 3 * mm), paragraph("OSY master list", 11, bold=True),
             Spacer(1, 2 * mm), paragraph(f"{description} | {len(rows)} record(s)", 8), Spacer(1, 5 * mm)]
    keys = ("osy_id", "full_name", "birthdate", "sex", "address", "contact_number", "employment_status", "status")
    headers = ("OSY ID", "Full name", "Birthdate", "Sex", "Address", "Contact", "Employment", "Status")
    data = [[paragraph(value, 8, colors.white, True) for value in headers]]
    data += [[paragraph(row.get(key), 7) for key in keys] for row in rows]
    if not rows:
        story.append(paragraph("No records match these filters.", 10))
    else:
        table = Table(data, colWidths=[29 * mm, 47 * mm, 24 * mm, 16 * mm, 66 * mm, 32 * mm, 33 * mm, 26 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f5f2")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBELOW", (0, 0), (-1, 0), .4, GREEN),
        ]))
        story.append(table)

    def footer(pdf, doc):
        pdf.setFont(FONT, 7)
        pdf.setFillColor(INK)
        pdf.drawRightString(285 * mm, 8 * mm, f"Page {doc.page}")

    document.build(story, onFirstPage=footer, onLaterPages=footer)
