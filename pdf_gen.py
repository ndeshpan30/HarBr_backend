from fpdf import FPDF

def generate_health_card(data: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Property Health Card", ln=True, align="C")
    pdf.ln(10)
    
    # Body
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"ULPIN: {data.get('ulpin', 'N/A')}", ln=True)
    pdf.cell(0, 10, f"Market Rent: Rs. {data.get('rent', 0):,}", ln=True)
    pdf.cell(0, 10, f"Effective Rent: Rs. {data.get('effective_rent', 0):,}", ln=True)
    pdf.cell(0, 10, f"Deposit: Rs. {data.get('deposit', 0):,}", ln=True)
    
    pdf.ln(20)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, "This document is AI-generated for demonstration purposes.", ln=True, align="C")
    
    return pdf.output(dest='S').encode('latin-1')
