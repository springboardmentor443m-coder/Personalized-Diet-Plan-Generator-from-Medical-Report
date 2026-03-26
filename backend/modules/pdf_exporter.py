from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from io import BytesIO

def generate_pdf(structured_data, diet, user_info=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontSize=22, spaceAfter=20, textColor=colors.HexColor("#7c3aed"))
    sub_title_style = ParagraphStyle('SubTitle', parent=styles['Heading2'], fontSize=16, spaceBefore=15, spaceAfter=10, textColor=colors.HexColor("#4f46e5"))
    body_style = styles['BodyText']
    label_style = ParagraphStyle('Label', parent=styles['BodyText'], fontName='Helvetica-Bold')

    elements = []

    # Title
    elements.append(Paragraph("AI-NutriCare Clinical Diagnostic & Dietary Report", title_style))
    elements.append(Paragraph(f"Report Generated for: {structured_data.get('patient_information', {}).get('patient_name', 'Valued Patient')}", body_style))
    elements.append(Spacer(1, 20))

    # Patient Intel Section
    elements.append(Paragraph("1. Patient Baseline Intelligence", sub_title_style))
    p_info = structured_data.get('patient_information', {})
    
    intel_data = [
        [Paragraph(f"<b>Age:</b> {p_info.get('age_years', '--')} Years", body_style), Paragraph(f"<b>Gender:</b> {p_info.get('gender', '--')}", body_style)],
        [Paragraph(f"<b>Weight:</b> {p_info.get('weight_kg', '--')} kg", body_style), Paragraph(f"<b>Height:</b> {p_info.get('height_cm', '--')} cm", body_style)],
        [Paragraph(f"<b>BMI:</b> {p_info.get('calculated_bmi', '--')} ({p_info.get('bmi_category', 'N/A')})", body_style), Paragraph(f"<b>Preference:</b> {p_info.get('dietary_preference', 'N/A')}", body_style)]
    ]
    
    t = Table(intel_data, colWidths=[240, 240])
    t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Abnormal Findings Section
    abnormal_findings = structured_data.get('abnormal_findings', [])
    if abnormal_findings:
        elements.append(Paragraph("2. Critical Clinical Alerts", sub_title_style))
        for ab in abnormal_findings:
            elements.append(Paragraph(f"• <b>{ab.get('test_name', 'Unknown Test')}:</b> {ab.get('observed_value')} (Ref: {ab.get('expected_range')})", body_style))
            elements.append(Paragraph(f"  <i>Severity: {ab.get('severity', 'High')} - {ab.get('insight', '')}</i>", body_style))
            elements.append(Spacer(1, 10))
    
    elements.append(Spacer(1, 10))

    # Diet Section
    if diet:
        elements.append(Paragraph("3. AI Nutritional Protocol", sub_title_style))
        elements.append(Paragraph(f"<b>Clinical Summary:</b> {diet.get('executive_summary', 'Personalized maintenance protocol.')}", body_style))
        elements.append(Spacer(1, 10))
        
        # Daily Plan
        elements.append(Paragraph("<b>Daily Meal Blueprint:</b>", label_style))
        plan = diet.get('daily_plan', {})
        for meal, desc in plan.items():
            elements.append(Paragraph(f"<b>{meal.capitalize()}:</b>", body_style))
            # Handle the bullet points I added to the prompt
            for line in desc.split('\n'):
                if line.strip():
                    elements.append(Paragraph(f"  {line.strip()}", body_style))
            elements.append(Spacer(1, 5))
            
        elements.append(Spacer(1, 10))
        
        # Superfoods & Avoid
        elements.append(Paragraph(f"<b>Focus Superfoods:</b> {', '.join(diet.get('superfoods', []))}", body_style))
        elements.append(Paragraph(f"<b>Foods to Minimize:</b> {', '.join(diet.get('foods_to_avoid', []))}", body_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
