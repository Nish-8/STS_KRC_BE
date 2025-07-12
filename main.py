from typing import Union
from utils import mclient
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
from models import ClientRequest
from fastapi.responses import StreamingResponse
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4  # Import A4 size
from num2words import num2words
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import Table, Paragraph, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from fpdf import FPDF
from io import BytesIO
from num2words import num2words
import os

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from num2words import num2words
import os

app = FastAPI()

LOGO_PATH = "https://e7.pngegg.com/pngimages/99/538/png-clipart-shiva-om-symbol-hinduism-om-text-logo.png"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.get("/sts_krc/get_vehicles_and_clients")
async def get_client_details(request: Request):
    try:
        vehicle_list = []

        # Fetch vehicle lists
        krc_vehicles = await mclient.STS.sts_vehicles.find_one({}, {"_id": 0})
        sts_vehicles = await mclient.KRC.krc_vehicles.find_one({}, {"_id": 0})

        if not krc_vehicles and not sts_vehicles:
            raise HTTPException(status_code=404, detail="No vehicles found in both sources")

        # Merge vehicle lists safely
        if krc_vehicles and "v_list" in krc_vehicles:
            vehicle_list += krc_vehicles["v_list"]
        if sts_vehicles and "v_list" in sts_vehicles:
            vehicle_list += sts_vehicles["v_list"]

        # Fetch clients
        client_details = await mclient.sts_krc_common_details.clients.find(
            {}, {"_id": 0, "client_address": 0}
        ).to_list(length=None)

        return {
            "vehicles": vehicle_list,
            "clients": client_details or []
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_pdf(company_name,company_id, bill_info, bill_entries):
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4
    footer_y_position = 100

    styles = getSampleStyleSheet()

    # Custom styles (don't assign to styles dictionary)
    style_center = ParagraphStyle(name='center', parent=styles["Normal"], alignment=TA_CENTER)
    adhoc_style = ParagraphStyle(name='adhoc', parent=styles["Normal"], alignment=TA_CENTER, spaceBefore=4, fontName='Helvetica-Oblique')

    client_name_style = ParagraphStyle(
        "ClientName",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
    )

    mixed_style = ParagraphStyle(
        "Mixed",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT
    )

    # Header and branding
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "img", "om.png")
    sts_sign = os.path.join(current_dir,"img","sts_sign.png")
    krc_sign = os.path.join(current_dir,"img","krc_sign.png")
    if os.path.exists(image_path):
        pdf.drawImage(image_path, width / 2 - 15, height - 40, width=30, height=30)

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(width / 2, height - 65, company_name)
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(width / 2, height - 85, "FLEET OWNERS AND TRANSPORT CONTRACTORS")
    pdf.drawCentredString(width / 2, height - 98, "SPECIALIST IN: CONTAINERS HANDLING")
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, height - 115, "4010 Bima Complex, Plot No 119, Kalamboli, Navi Mumbai, 410218")
    pdf.drawCentredString(width / 2, height - 128, "Mob: 9004338109 / 9820342499 / 9022202210")
    pdf.drawCentredString(width / 2, height - 140, "Email: pd43643@gmail.com / pravindubey665@gmail.com")
    pdf.line(30, height - 150, width - 30, height - 150)

    # Bill info section
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, height - 170, f"Bill No: {bill_info['billNo']}")
    pdf.drawString(200, height - 170, f"Bill Date: {bill_info['billDate']}")

    client_paragraph = Paragraph(f"<b>Client Name:</b> {bill_info['clientName']}", client_name_style)
    client_width, client_height = client_paragraph.wrap(width - 80, 100)
    client_y = height - 190
    client_paragraph.drawOn(pdf, 40, client_y - client_height)

    address_paragraph = Paragraph(f"<b>Address:</b> {bill_info['clientAddress']}", mixed_style)
    address_width, address_height = address_paragraph.wrap(width - 80, 100)
    address_y = client_y - client_height - 10
    address_paragraph.drawOn(pdf, 40, address_y - address_height)

    payment_paragraph = Paragraph(f"<b>Payment Terms:</b> {bill_info['paymentTerms']}", mixed_style)
    payment_width, payment_height = payment_paragraph.wrap(width - 80, 100)
    payment_y = address_y - address_height - 10
    payment_paragraph.drawOn(pdf, 40, payment_y - payment_height)

    # Entries table
    table_x = 30
    table_y = payment_y - payment_height - 20

    table_data = [["From", "To", "LR No", "Vehicle No", "Description", "Product", "Advance", "Amount"]]
    total_amount = 0
    span_indices = []

    for entry in bill_entries:
        table_data.append([
            entry["dateFrom"],
            entry["dateTo"],
            entry["lrNo"],
            entry["vehicleNo"],
            Paragraph(entry["description"], style_center),
            Paragraph(entry["productType"], style_center),
            Paragraph(str(entry["advance"]), style_center),
            entry["totalAmount"]
        ])
        total_amount += float(entry["totalAmount"])

        for adhoc in entry.get("adhocAmounts", []):
            row_index = len(table_data)
            table_data.append([
                Paragraph(f"<b>\u2003Adhoc:</b> {adhoc['description']}", adhoc_style),
                '', '', '', '', '', '',
                Paragraph(str(adhoc["amount"]), style_center)
            ])
            span_indices.append(row_index)
            total_amount += float(adhoc["amount"])

    table = Table(table_data, colWidths=[60, 60, 50, 70, 90, 80, 70, 70])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    for row in span_indices:
        style.add('SPAN', (0, row), (6, row))
        style.add('ALIGN', (7, row), (7, row), 'CENTER')
        style.add('BACKGROUND', (0, row), (-1, row), colors.whitesmoke)

    table.setStyle(style)
    table.wrapOn(pdf, width, height)
    table_width, table_height = table._width, table._height

    if table_y - table_height < footer_y_position + 120:
        pdf.showPage()
        table_y = height - 50

    table.drawOn(pdf, table_x, table_y - table_height)

    # Footer
    total_advance = sum(int(entry["advance"]) for entry in bill_entries)
    balance = total_amount - total_advance
    amount_in_words = num2words(balance, lang="en_IN")

    pdf.line(30, footer_y_position + 110, width - 30, footer_y_position + 110)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, footer_y_position + 90, "PAN No: APBPD0457N" if company_id == 1 else "APBPD0464P")
    pdf.drawString(40, footer_y_position + 75, "Amount In Words: ")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(140, footer_y_position + 75, f"Rupees {amount_in_words} Only")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(width - 150, footer_y_position + 95, f"Total: {total_amount}")
    pdf.drawString(width - 150, footer_y_position + 85, f"Less Adv.: {total_advance}")
    pdf.drawString(width - 150, footer_y_position + 65, f"Balance: {balance}")

    pdf.line(30, footer_y_position + 60, width - 30, footer_y_position + 60)
    # First row: Bank Name and Branch Name

    pdf.drawString(40, footer_y_position + 40, "GST/ Service TAX payable By :- Consignor / Consignee")
    pdf.drawString(40, footer_y_position + 20, "Bank Name : Bank Of India")
    pdf.drawString(180, footer_y_position + 20, "Branch Name : CBD Belapur")

    # Second row: A/C No and IFSC Code
    pdf.drawString(40,footer_y_position + 5, f"A/C No : {'011620110000897' if company_id == 1 else '011620110000899'}")

    pdf.drawString(180, footer_y_position + 5, "IFSC CODE : BKID0000116")
    
    pdf.rect(35, footer_y_position - 15, 290, 50)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, footer_y_position - 30, "Subject To Navi Mumbai Jurisdiction")
    pdf.drawString(40, footer_y_position - 42, "NOTE: Bill must be paid within 15 days by A/C payee's Cheque Only")
    pdf.drawString(40, footer_y_position - 54, "Interest @25% per annum will be charged on all outstanding bills")
    pdf.drawString(40, footer_y_position - 66, "Please Pay By Account Payee Cheque / NEFT Only")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(width - 200, footer_y_position + 20, company_name)

    try:
        pdf.drawImage(krc_sign if company_id == 1 else sts_sign, width - 150, footer_y_position - 20, width=80, height=30, mask='auto')
    except:
        print("Signature not found, skipping...")

    pdf.drawString(width - 150, footer_y_position - 30, "Authorized Signature")
    pdf.showPage()
    pdf.save()
    pdf_buffer.seek(0)
    return pdf_buffer

@app.post("/sts_krc/generate-pdf/")
async def generate_pdf(data: dict):
    bill_info = data["billingInfo"]
    bill_entries = data["billingEntries"]
    company_id = data['company_id']

    if not bill_info or not bill_entries or not company_id:
        return JSONResponse(status_code=400, content={"message": "Invalid request body", "success": False})
    
    bill_doc = {
        "billNo": bill_info["billNo"],
        "billDate": bill_info["billDate"],
        "client": {
            "clientId": bill_info["clientId"],
            "clientAddress": bill_info["clientAddress"],
            "clientName": bill_info["clientName"],
        },
        "clientAddress": bill_info["clientAddress"],
        "paymentTerms": bill_info["paymentTerms"],
        "financialYear": bill_info["fy"],
        "entries": bill_entries,
    }


    company_name = ""
    if company_id == 1:
        db = mclient.KRC.krc_bill_info
        company_name = "KRISHNARAJ CARRIERS"
    elif company_id == 2:
        db = mclient.STS.sts_bill_info
        company_name = "SANDEEP TRANSFREIGHT SERVICE"

    is_bill_data_stored = await db.update_one({"billNo":bill_info['billNo']}, {"$set": bill_doc}, upsert=True)
    pdf_buffer = await create_pdf(company_name,company_id, bill_info, bill_entries)
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=bill.pdf"})

@app.get("/sts_krc/server_ping/")
async def server_ping():
    return JSONResponse(status_code=200, content={"message": "Server is running", "success": True})

@app.post("/sts_krc/downloadInvoice/")
async def downloadInvoice(request:Request):
    try:
        data = await request.json()
        company_id = data['company_id']
        bill_no = data['billNo']
        company_name = ""
        if int(company_id) == 1:
            db = mclient.KRC.krc_bill_info
            company_name = "KRISHNARAJ CARRIERS"
        else:
            db = mclient.STS.sts_bill_info
            company_name = "SANDEEP TRANSFREIGHT SERVICE"
            
        res = await db.find_one({"billNo":bill_no},{"_id":0})

        if res:
            bill_info = {
                "billNo":res['billNo'],
                "billDate": res['billDate'],
                "clientId": res['client']['clientId'],
                "clientAddress": res['client']['clientAddress'],
                "clientName": res['client']['clientName'],
                "paymentTerms": res['paymentTerms'],
                "fy": res['financialYear'],
            }
            pdf_buffer = await create_pdf(company_name,int(company_id), bill_info, res['entries'])
            return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=bill.pdf"})
            
    except:
        traceback.print_exc()
        
@app .post("/sts_krc/get_bill_no/")
async def get_bill_no(request:Request):
    try:
        data = await request.json()
        if not data:
            return JSONResponse(status_code=400,content={"message":"Company Id is not provided", "success":False})
        company_id = int(data['company_id'])
        if int(company_id) == 1:
            db = mclient.KRC.krc_bill_info
        else:
            db = mclient.STS.sts_bill_info

        bill_numbers = await db.find({},{"_id":0,"billNo":1}).to_list(length=None)
        get_next_bill_no = await db.find_one({},{"_id":0,"billNo":1},sort=[("billNo",-1)])
        if get_next_bill_no:
            next_bill_no = int(get_next_bill_no['billNo'])
            print("next_bill_no>>>", next_bill_no,type(next_bill_no))
            next_bill_no += 1
        else:
            next_bill_no = 0

        if not bill_numbers:
            return JSONResponse(status_code=404,content={"message":"Bo bills found for the company", "success":False})
        return JSONResponse(status_code=200,content={"message":"Bill numbers fetched successfully", "success":True, "bills":bill_numbers, "next_bill_no":next_bill_no})
    except:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": "Internal server error", "success": False})

@app.post("/sts_krc/get_bill_details/")
async def get_bill_details(request:Request):
    try:
        data= await request.json()
        company_id = data['company_id']
        bill_no = data['bill_no']
        if not company_id or not bill_no:
            return JSONResponse(status_code=400,content={"message":"Company Id or bill number is not provided", "success":False})
        if company_id == 1:
            db = mclient.KRC.krc_bill_info
        else:
            db = mclient.STS.sts_bill_info

        bill_details = await db.find_one({"billNo":bill_no},{"_id":0})
        if not bill_details:
            return JSONResponse(status_code=404, content={"message":"Bill not found","success":False})
        
        return JSONResponse(status_code=200,content={"message":"Bill details fetched successfully","success":True,"bill_details":bill_details})
    except:
        traceback.print_exc()
        return JSONResponse(status_code=500,content = {"message":"Internal server error","success":False})
    
@app.post("/sts_krc/update_bill_entry/")
async def update_bill_entry(request:Request):
    try:
        data= await request.json()
        company_id = data['company_id']
        bill_no = data['bill_no']
        lr_index = data['entry_index']
        updated_entry = data['updated_entry']
        if not company_id or not bill_no:
            return JSONResponse(status_code=400,content={"message":"Company Id or bill number is not provided", "success":False})
        if company_id == 1:
            db = mclient.KRC.krc_bill_info
        else:
            db = mclient.STS.sts_bill_info
        res = await db.update_one({"billNo":bill_no},{"$set": {f"entries.{lr_index}": updated_entry}})
        # if not res.modified_count :
        #     return JSONResponse(status_code=404, content={"message":"Bill not found","success":False})

        return JSONResponse(status_code=200,content={"message":"Bill updated successfully","success":True, })
    except:
        traceback.print_exc()
        return JSONResponse(status_code=500,content = {"message":"Internal server error","success":False})
    
@app.post("/sts_krc/get_client_address/")
async def get_client_address(request:Request):
   
    try:
        data = await request.json()
        client_id = data['client_id']

        collection = mclient.sts_krc_common_details.clients

        # FIXED: use correct query and projection
        client = await collection.find_one(
            {"client_id": client_id}, 
            {"_id": 0, "client_address": 1}
        )

        print("res ++++++++", client)

        if client:
            return {"client_address": client["client_address"]}
            
        else:
            return JSONResponse(
                status_code=404,
                content={"message": "Client not found", "success": False}
            )

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error", "success": False}
        )