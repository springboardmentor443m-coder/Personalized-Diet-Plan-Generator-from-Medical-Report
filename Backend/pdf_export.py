from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import uuid

def create_pdf(diet_text):
    filename = f"DietPlan_{uuid.uuid4().hex}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>AI-NutriCare Personalized Diet Plan</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))

    for line in diet_text.split("\n"):
        elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 0.2 * inch))

    doc.build(elements)
    return filename