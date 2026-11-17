import os
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_documents"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def generate_txt():
    path = SAMPLE_DIR / "Global_AI_Security_Policy.txt"
    content = """GLOBAL ENTERPRISE ARTIFICIAL INTELLIGENCE & DATA SECURITY POLICY
Document Version: 2.4 | Effective Date: January 15, 2024
Author: Corporate Information Security Office (CISO)

1. PURPOSE AND APPLICABILITY
This document sets the mandatory governance and technical standards for designing, deploying, and consuming Artificial Intelligence (AI) and Machine Learning (ML) systems across all business divisions. This policy applies to all full-time employees, contractors, and third-party vendors.

2. DATA CLASSIFICATION AND TRAINING RESTRICTIONS
Customer Personally Identifiable Information (PII), protected health data, and financial credentials must never be inputted into public, unvetted LLM consumer applications.
All internal documents classified as "Confidential" or "Restricted" must be processed exclusively through zero-retention private enterprise API endpoints or on-premise hosted vector databases.
Training data sets must undergo rigorous decontamination to remove PII, internal IP addresses, API secrets, and cryptographic private keys prior to fine-tuning.

3. ACCESS CONTROL AND MULTI-FACTOR AUTHENTICATION
Role-Based Access Control (RBAC) is enforced across all vector database clusters and inference endpoints.
Multi-Factor Authentication (MFA) is strictly mandatory for all administrative access, deployment pipelines, and remote access connections.
Passwords must be at least 14 characters in length, containing uppercase letters, numerals, and special characters, and must be rotated every 90 days.

4. MODEL AUDITING, EVALUATION AND HALLUCINATION PREVENTION
Any model deployed to production must maintain a minimum factual accuracy benchmark of 95% on internal validation benchmarks.
All customer-facing AI responses must use Retrieval-Augmented Generation (RAG) with verifiable citation sources.
If relevant documents do not contain the answer to a user query, the model is strictly required to decline the question rather than extrapolate.

5. INCIDENT RESPONSE AND REPORTING
Any suspected data exfiltration, prompt injection exploit, or unauthorized model fine-tuning must be reported to security-ops@enterprise.internal within 60 minutes of detection.
Violations of this policy will result in immediate credential revocation and disciplinary review.
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"Generated TXT: {path}")

def generate_docx():
    path = SAMPLE_DIR / "Q3_Financial_Performance_Report.docx"
    doc = docx.Document()
    
    title = doc.add_heading("Apex Global Enterprises - Q3 Financial Performance Report", 0)
    
    doc.add_heading("1. Executive Summary", level=1)
    doc.add_paragraph(
        "During the third quarter of fiscal year 2024, Apex Global Enterprises delivered record financial performance. "
        "Total revenue reached $142.8 million, representing a 28% year-over-year increase compared to $111.5 million in Q3 2023. "
        "Growth was primarily driven by our AI Document Intelligence SaaS platform and enterprise cloud migration services."
    )
    
    doc.add_heading("2. Segment Breakdown", level=1)
    doc.add_paragraph(
        "Enterprise Software Solutions accounted for $88.4 million (62% of revenue), expanding 34% YoY. "
        "Professional Consulting and Implementation contributed $36.2 million (25% of revenue). "
        "Managed Cloud Infrastructure services generated $18.2 million (13% of revenue)."
    )
    
    # Financial metrics table
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Business Segment'
    hdr_cells[1].text = 'Q3 2023 Revenue ($M)'
    hdr_cells[2].text = 'Q3 2024 Revenue ($M)'
    hdr_cells[3].text = 'YoY Growth (%)'
    
    data = [
        ("Enterprise Software", "66.0", "88.4", "+34%"),
        ("Professional Services", "30.5", "36.2", "+19%"),
        ("Managed Cloud Infrastructure", "15.0", "18.2", "+21%"),
        ("Total Consolidated", "111.5", "142.8", "+28%")
    ]
    
    for row in data:
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            row_cells[i].text = val
            
    doc.add_heading("3. Operational Highlights & Capital Expenditure", level=1)
    doc.add_paragraph(
        "Operating margin improved by 420 basis points to 24.6%, up from 20.4% in the prior year quarter. "
        "Operating cash flow was $48.2 million with free cash flow of $39.5 million. "
        "Capital expenditure for the quarter was $8.7 million, focused on expanding our high-performance GPU compute clusters in Northern Virginia and Frankfurt."
    )
    
    doc.add_heading("4. Q4 Outlook and Forward Guidance", level=1)
    doc.add_paragraph(
        "For the fourth quarter of 2024, management expects consolidated revenue between $155 million and $160 million. "
        "Full-year revenue guidance is raised to $545 million to $552 million, reflecting strong contract pipeline conversion."
    )
    
    doc.save(str(path))
    print(f"Generated DOCX: {path}")

def generate_pdf():
    path = SAMPLE_DIR / "Cloud_Architecture_and_SLA.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=15
    )
    h1_style = ParagraphStyle(
        'Heading1Style',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0284C7'),
        spaceBefore=12,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=body_style,
        leftIndent=15,
        spaceAfter=4
    )

    story = []

    # PAGE 1
    story.append(Paragraph("Enterprise Cloud Architecture & SLA Specification", title_style))
    story.append(Paragraph("Document Ref: ARC-2024-V3 | Classification: Technical Standards", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("1. System Architecture Overview", h1_style))
    story.append(Paragraph(
        "The DocuIntel Cloud platform operates on a resilient multi-tier microservices architecture hosted across three availability zones. "
        "The ingress layer utilizes Cloudflare Enterprise CDN for DDoS protection, TLS 1.3 termination, and Web Application Firewall (WAF) rule enforcement. "
        "The application tier runs on Kubernetes (EKS) with horizontal pod autoscaling configured to scale worker pods when CPU utilization exceeds 70%.",
        body_style
    ))
    story.append(Paragraph(
        "The storage architecture decouples stateless compute from persistent vector storage. "
        "Vector indexes are distributed across persistent NVMe volumes with automated asynchronous snapshot replication to S3 glacier every 4 hours.",
        body_style
    ))
    story.append(Spacer(1, 15))
    story.append(Paragraph("2. Availability Tiers and Service Level Agreement (SLA)", h1_style))
    story.append(Paragraph(
        "Apex Cloud guarantees an uptime SLA of 99.95% for all Enterprise tier customers, excluding scheduled monthly maintenance windows. "
        "Scheduled maintenance occurs on the first Sunday of each calendar month between 02:00 AM and 04:00 AM UTC with at least 7 days advance notification.",
        body_style
    ))
    story.append(PageBreak())

    # PAGE 2
    story.append(Paragraph("2. Service Credits and Incident Response Tiers", h1_style))
    story.append(Paragraph(
        "In the event that monthly uptime falls below 99.95%, eligible enterprise customers are entitled to financial service credits applied to their monthly invoicing cycle:",
        body_style
    ))
    story.append(Paragraph("&bull; 99.0% to 99.94% Uptime: 10% Service Credit", bullet_style))
    story.append(Paragraph("&bull; 95.0% to 98.99% Uptime: 25% Service Credit", bullet_style))
    story.append(Paragraph("&bull; Below 95.0% Uptime: 50% Service Credit", bullet_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("3. Incident Severity Levels & Response Times", h1_style))
    story.append(Paragraph(
        "The Technical Assistance Center (TAC) classifies incidents into four severity levels with contractual response windows:",
        body_style
    ))
    story.append(Paragraph("<b>Severity 1 (Critical Outage)</b>: Complete system degradation or data unavailability. Initial response within 15 minutes, 24/7/365 dedicated engineering bridge.", bullet_style))
    story.append(Paragraph("<b>Severity 2 (Major Impairment)</b>: Core feature disabled with no direct workaround. Initial response within 1 hour.", bullet_style))
    story.append(Paragraph("<b>Severity 3 (Moderate Impact)</b>: Non-critical feature failure or minor performance latency. Initial response within 4 business hours.", bullet_style))
    story.append(Paragraph("<b>Severity 4 (General Inquiry)</b>: Configuration question or feature request. Initial response within 24 business hours.", bullet_style))
    story.append(PageBreak())

    # PAGE 3
    story.append(Paragraph("4. Disaster Recovery and Data Retention", h1_style))
    story.append(Paragraph(
        "The Disaster Recovery (DR) plan is designed for maximum business continuity and rapid recovery during regional datacenter outages. "
        "The Recovery Time Objective (RTO) is guaranteed at 30 minutes, and the Recovery Point Objective (RPO) is strictly under 5 minutes.",
        body_style
    ))
    story.append(Paragraph(
        "All data at rest is encrypted using AES-256 GCM encryption with customer-managed keys (AWS KMS / GCP Cloud KMS). "
        "Data in transit is encrypted using TLS 1.3 with forward secrecy. "
        "Backup snapshots are retained for 365 days in immutable write-once-read-many (WORM) compliant cloud storage.",
        body_style
    ))
    story.append(Paragraph("5. Compliance & Certifications", h1_style))
    story.append(Paragraph(
        "The infrastructure maintains annual compliance certifications under SOC 2 Type II, ISO/IEC 27001:2022, HIPAA Security Rule, and GDPR Article 28 data processor standards.",
        body_style
    ))

    doc.build(story)
    print(f"Generated PDF: {path}")

if __name__ == "__main__":
    generate_txt()
    generate_docx()
    generate_pdf()
