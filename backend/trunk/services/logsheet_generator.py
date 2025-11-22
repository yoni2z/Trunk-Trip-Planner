from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from datetime import datetime
import os

def generate_daily_log_pdf(day_data, trip, output_dir="logs"):
    os.makedirs(output_dir, exist_ok=True)
    
    # FIXED: Use str(trip.id) and avoid smart quotes
    filename = f"logs/Log_Day_{day_data['day']}_{str(trip.id)[:8]}.pdf"
    c = canvas.Canvas(filename, pagesize=LETTER)
    width, height = LETTER

    # Use only ASCII characters – NO smart quotes, NO en-dashes!
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 0.8*inch, "DRIVER'S DAILY LOG")

    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 1.1*inch, 
                        "Property-Carrying Vehicle - 70-Hour/8-Day Rule")

    # Driver Info
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.5*inch, height - 1.8*inch, "Driver Name: ______________________________")
    c.drawString(0.5*inch, height - 2.1*inch, "Co-Driver: _________________________________")
    c.drawString(0.5*inch, height - 2.4*inch, f"Home Terminal: {trip.current_location}")
    c.drawString(4*inch, height - 1.8*inch, f"Date: {day_data['date']}")
    c.drawString(4*inch, height - 2.1*inch, "Truck #: ________  Trailer #: ________")

    # 24-hour grid
    y = height - 3.5*inch
    c.setFont("Helvetica", 7)
    for h in range(25):
        x = 0.5*inch + h * 0.3*inch
        c.drawString(x - 5, y - 0.2*inch, str(h % 24))
        c.line(x, y, x, y + 0.8*inch)

    # Duty status lines (thick colored lines)
    start_x = 0.5*inch + 5 * 0.3*inch  # 5 AM start
    c.setLineWidth(4)

    # 1. Off Duty (black)
    c.setStrokeColorRGB(0, 0, 0)
    c.line(start_x, y + 0.1*inch, start_x + 1*0.3*inch, y + 0.1*inch)

    # 2. On Duty - Pickup (blue)
    c.setStrokeColorRGB(0, 0.5, 1)
    c.line(start_x + 1*0.3*inch, y + 0.7*inch, start_x + 2*0.3*inch, y + 0.7*inch)

    # 3. Driving (yellow/orange)
    c.setStrokeColorRGB(1, 0.7, 0)
    drive_end = start_x + (2 + day_data["driving_hours"]) * 0.3*inch
    c.line(start_x + 2*0.3*inch, y + 0.55*inch, drive_end, y + 0.55*inch)

    # 30-min break if needed
    if day_data.get("includes_30min_break"):
        c.setStrokeColorRGB(0, 0.5, 1)
        break_x = start_x + (2 + 8) * 0.3*inch
        c.line(break_x, y + 0.7*inch, break_x + 0.5*0.3*inch, y + 0.7*inch)

    # Final Off Duty
    c.setStrokeColorRGB(0, 0, 0)
    c.line(drive_end, y + 0.1*inch, width - 0.5*inch, y + 0.1*inch)

    # Remarks (ASCII only!)
    c.setFont("Helvetica", 9)
    remarks_y = y - 0.8*inch
    c.drawString(0.5*inch, remarks_y, f"Start: {day_data['start_time']} | End: {day_data['off_duty_start']}")
    c.drawString(0.5*inch, remarks_y - 0.3*inch, 
                 f"Total Driving: {day_data['driving_hours']}h | On Duty: {day_data['on_duty_hours']}h")
    if day_data.get("fuel_stop"):
        c.drawString(0.5*inch, remarks_y - 0.6*inch, "Fuel stop taken (30 min)")

    # Total Miles & Hours Box
    c.rect(width - 3*inch, height - 5.5*inch, 2.5*inch, 1*inch)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 2.8*inch, height - 5.2*inch, "TOTAL HOURS TODAY")
    c.setFont("Helvetica", 10)
    c.drawString(width - 2.8*inch, height - 5.5*inch, f"Driving: {day_data['driving_hours']}h")
    c.drawString(width - 1.5*inch, height - 5.5*inch, f"On Duty: {day_data['on_duty_hours']}h")

    c.showPage()
    c.save()
    return filename