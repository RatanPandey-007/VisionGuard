import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_pdf_report(record: dict, output_pdf_path: str):
    """
    Generates a professional inspection report PDF for a single device quality run.
    :param record: dict containing keys: 'id', 'timestamp', 'product_id', 'result', 'defect_type', 'confidence', 'image_path', 'model_version'
    :param output_pdf_path: file path to save the PDF
    """
    # Ensure reports directory exists
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    # 1. Setup Document
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    
    story = []
    
    # 2. Setup styles
    styles = getSampleStyleSheet()
    
    # Custom colors
    NAVY = colors.HexColor("#1A365D")
    GREEN = colors.HexColor("#2F855A")
    RED = colors.HexColor("#C53030")
    GREY = colors.HexColor("#E2E8F0")
    TEXT_DARK = colors.HexColor("#2D3748")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=NAVY,
        spaceAfter=5
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=20
    )
    
    section_h2 = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=15,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK
    )
    
    bold_left_style = ParagraphStyle(
        'BoldLeft',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    # 3. Document Headers
    story.append(Paragraph("VISIONGUARD EDGE", title_style))
    story.append(Paragraph("AI-POWERED MSME QUALITY INSPECTION REPORT (OFFLINE PROTO)", subtitle_style))
    story.append(Spacer(1, 5))
    
    # 4. Meta Table
    meta_data = [
        [Paragraph("Inspection ID", bold_left_style), Paragraph(str(record.get('id', 'N/A')), body_style),
         Paragraph("Date/Time", bold_left_style), Paragraph(record.get('timestamp', 'N/A'), body_style)],
        [Paragraph("Product ID", bold_left_style), Paragraph(record.get('product_id', 'N/A'), body_style),
         Paragraph("Model Version", bold_left_style), Paragraph(record.get('model_version', 'N/A'), body_style)]
    ]
    
    t_meta = Table(meta_data, colWidths=[100, 160, 100, 160])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('GRID', (0,0), (-1,-1), 1, GREY),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(t_meta)
    story.append(Spacer(1, 15))
    
    # 5. Inspection Result Badge
    result = record.get('result', 'FAIL')
    defect_type = record.get('defect_type', '')
    confidence = record.get('confidence', 0.0)
    
    res_color = GREEN if result == 'PASS' else RED
    res_text = "🟢 QUALITY PASSED (PASS)" if result == 'PASS' else "🔴 DEFECT DETECTED (FAIL)"
    
    result_style = ParagraphStyle(
        'ResultText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=colors.white,
        alignment=1 # Center
    )
    
    card_data = [[Paragraph(res_text, result_style)]]
    t_card = Table(card_data, colWidths=[520])
    t_card.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), res_color),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_card)
    story.append(Spacer(1, 10))
    
    # 6. Detailed findings summary
    findings_data = [
        [Paragraph("Visual Classification Check", bold_left_style), 
         Paragraph(defect_type if defect_type else "None (No visual anomalies detected)", body_style)],
        [Paragraph("AI Inference Confidence", bold_left_style), 
         Paragraph(f"{confidence}%", body_style)]
    ]
    t_findings = Table(findings_data, colWidths=[180, 340])
    t_findings.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, GREY),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#EDF2F7")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_findings)
    story.append(Spacer(1, 15))
    
    # 7. Image Section
    story.append(Paragraph("Inspection Visual Record", section_h2))
    img_path = record.get('image_path')
    
    rendered_image = False
    if img_path and os.path.exists(img_path):
        try:
            # Aspect ratio 640x480 -> 4:3.
            # Scale to width 360, height 270 (fits letter page nicely).
            r_image = Image(img_path, width=320, height=240)
            r_image.hAlign = 'CENTER'
            story.append(r_image)
            rendered_image = True
        except Exception as e:
            story.append(Paragraph(f"<i>Error rendering inspection image: {str(e)}</i>", body_style))
            
    if not rendered_image:
        # Placeholder grey box
        dummy_data = [[Paragraph("Visual image capture reference was not archived or is unavailable.", body_style)]]
        t_dummy = Table(dummy_data, colWidths=[320], rowHeights=[240])
        t_dummy.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EDF2F7")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 1, GREY),
        ]))
        story.append(t_dummy)
        
    story.append(Spacer(1, 15))
    
    # 8. Actionable Recommendation Section
    story.append(Paragraph("Industrial Quality Recommendations", section_h2))
    
    recs = []
    if result == 'PASS':
        recs.append("🔍 Proceed to next assembly or test stage. No physical work required.")
        recs.append("📊 Record logged in database. Continues feedback diagnostics to dashboard.")
    else:
        if defect_type == "Missing Component":
            recs.append("⚠️ Check placement head feed tray loader. The designated part was not placed.")
            recs.append("🔧 Route code PCB to Manual Refit Station to place missing chip component.")
        elif defect_type == "Component Misalignment":
            recs.append("⚠️ Adjust conveyor guide rails or recalibrate camera spatial alignment coordinates.")
            recs.append("🔧 Perform hot-air rework on the component to realign pad positions.")
        elif defect_type == "Solder Defect":
            recs.append("⚠️ Check liquidus profiles in the reflow zone. Clean paste printer stencil masks.")
            recs.append("🔧 Apply local flux and perform manual touchup with micro-soldering tip.")
        else: # Surface Anomaly or other
            recs.append("⚠️ Board shows contamination or foreign materials. Wash board using IPA baths.")
            recs.append("🔧 Reject if copper pads look oxidized. Return unit to panel supplier.")

    rec_style = ParagraphStyle(
        'Recs',
        parent=body_style,
        spaceAfter=4
    )
    for r in recs:
        story.append(Paragraph(r, rec_style))
        
    story.append(Spacer(1, 20))
    
    # Footer disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        textColor=colors.HexColor("#718096"),
        alignment=1 # Center
    )
    story.append(Paragraph(
        "Notice: This report is generated automatically by VisionGuard Edge AI Prototype engine for hackathon review. "
        "It is intended to serve as a design framework for industrial IoT quality systems.",
        disclaimer_style
    ))
    
    # 9. Build Template
    doc.build(story)

if __name__ == "__main__":
    mock_rec = {
        "id": 42,
        "timestamp": "2026-08-20 12:00:00",
        "product_id": "PCB-042",
        "result": "FAIL",
        "defect_type": "Component Misalignment",
        "confidence": 94.6,
        "image_path": "data/inspections/mock_PCB-1000.jpg",
        "model_version": "YOLOv8n-PCB-v1.0"
    }
    generate_pdf_report(mock_rec, "reports/test_report.pdf")
    print("Test report compiled in reports/test_report.pdf")
