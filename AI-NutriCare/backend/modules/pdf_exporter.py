from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

def generate_pdf(diet):

    buffer = BytesIO()   # 🔥 Create PDF in memory

    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>AI-NutriCare Diet Plan</b>", styles['Title']))

    for meal, food in diet.items():
        elements.append(Paragraph(f"<b>{meal}:</b> {food}", styles['BodyText']))

    doc.build(elements)

    buffer.seek(0)

    return buffer
