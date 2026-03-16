from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def export_diet_plan(patient_name, diet_plan):

    file_name = patient_name + "_Diet_Plan.pdf"

    c = canvas.Canvas(file_name, pagesize=letter)

    c.drawString(100, 750, "AI NutriCare - Personalized Diet Plan")
    c.drawString(100, 720, "Patient Name: " + patient_name)

    y = 690
    for line in diet_plan:
        c.drawString(100, y, line)
        y -= 20

    c.save()

    return file_name
