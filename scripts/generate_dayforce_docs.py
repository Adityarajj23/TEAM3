#!/usr/bin/env python3
"""Generate realistic multi-format requirement documents for the Dayforce QE workspace.

Produces:
1. data/dayforce_sample_docs/Dayforce_PRD_v1.2.pdf (ReportLab binary PDF)
2. data/dayforce_sample_docs/Dayforce_SRS_v1.0.docx (python-docx Word document)
3. data/dayforce_sample_docs/Business_Rules.xlsx (openpyxl multi-sheet workbook)
4. data/dayforce_sample_docs/Dayforce_API_Integration.md (Markdown specification)

Includes documented intentional contradictions:
- Contradiction 1 (Overtime Rate): PRD specifies 1.5x regular pay after 40 hours; Business Rules specifies 2.0x for holiday shifts.
- Contradiction 2 (Probation Period): PRD requires 90 days probation for leave eligibility; SRS specifies 30 days probation.
- Contradiction 3 (Session Timeout): SRS specifies 15 minutes session inactivity timeout; API spec specifies 30 minutes timeout.
"""
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "dayforce_sample_docs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def create_dayforce_prd_pdf():
    pdf_path = OUT_DIR / "Dayforce_PRD_v1.2.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "DocH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1E40AF"),
        spaceBefore=14,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
    )
    callout_style = ParagraphStyle(
        "DocCallout",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8,
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Dayforce Enterprise Product Requirements Document (PRD)", title_style))
    story.append(Paragraph("<b>Version:</b> 1.2 | <b>Date:</b> Nov 5, 2026 | <b>Author:</b> Product Management (Enterprise QE)", body_style))
    story.append(Paragraph("<b>Scope:</b> Core HR, Time & Attendance, Leave Management, and Gross-to-Net Payroll Verification", callout_style))
    story.append(Spacer(1, 10))

    # Section 1
    story.append(Paragraph("1. Executive Summary & Product Overview", h1_style))
    story.append(Paragraph("The Dayforce Platform delivers an unified enterprise Human Capital Management (HCM) solution. The system shall centralize employee records, automate punch pairing, track shift attendance, and orchestrate compliant gross-to-net payroll execution.", body_style))
    story.append(Paragraph("The system must maintain high data integrity across all employee status transitions and prevent unauthorized record access.", body_style))

    # Section 2
    story.append(Paragraph("2. Employee Lifecycle Management", h1_style))
    story.append(Paragraph("2.1 Onboarding and Profile Maintenance", h2_style))
    story.append(Paragraph("The system shall record new employee hires with mandatory legal name, tax identification number, date of birth, and assigned work location.", body_style))
    story.append(Paragraph("The system must validate that employee email addresses are unique across the active organization directory.", body_style))
    story.append(Paragraph("The system shall enforce role-based permissions prohibiting non-administrative personnel from viewing unmasked tax identification numbers.", body_style))
    story.append(Paragraph("The system will support asynchronous employee document upload with virus scanning and automated audit logging.", body_style))

    # Section 3
    story.append(Paragraph("3. Time and Attendance Tracking", h1_style))
    story.append(Paragraph("3.1 Clock In and Clock Out Workflows", h2_style))
    story.append(Paragraph("The system shall allow registered employees to record digital clock-in and clock-out punches via web portal and mobile clients.", body_style))
    story.append(Paragraph("The system must capture geolocation coordinates and server timestamps for every clock event.", body_style))
    story.append(Paragraph("The system shall enforce a 5-minute grace period before tagging an arrival as late relative to scheduled shift start time.", body_style))
    story.append(Paragraph("The system rejects duplicate punch events submitted within 60 seconds of a previous event to prevent accidental double-tap recording.", body_style))
    story.append(Paragraph("The system shall notify shift managers automatically when an employee fails to clock in within 15 minutes of shift start.", body_style))
    story.append(Paragraph("The system must maintain immutable historical audit logs of all manager punch adjustments and reason codes.", body_style))

    story.append(PageBreak())

    # Section 4
    story.append(Paragraph("4. Overtime Calculation & FLSA Compliance", h1_style))
    story.append(Paragraph("4.1 Regular and Overtime Hours Determination", h2_style))
    story.append(Paragraph("The system shall calculate overtime at 1.5x regular pay after 40 hours worked in a single workweek.", body_style))
    story.append(Paragraph("The system must track non-exempt employee daily hours and flag daily shifts exceeding 12 hours for mandatory rest break review.", body_style))
    story.append(Paragraph("The system shall allow payroll administrators to configure jurisdiction-specific overtime thresholds at the legal entity level.", body_style))
    story.append(Paragraph("The system validates that calculated overtime hours match approved timesheet records before committing to payroll batch.", body_style))

    # Section 5
    story.append(Paragraph("5. Leave Management & Accruals", h1_style))
    story.append(Paragraph("5.1 Leave Eligibility and Approvals", h2_style))
    story.append(Paragraph("The system shall enforce a mandatory 90-day probationary period before newly hired employees become eligible for paid annual leave accrual.", body_style))
    story.append(Paragraph("The system must allow employees to submit planned time-off requests with date ranges and leave type classifications.", body_style))
    story.append(Paragraph("The system shall route leave requests exceeding 3 consecutive days to department managers for formal approval.", body_style))
    story.append(Paragraph("The system prohibits negative leave balances unless explicit overdraft authorization is configured for the employee group.", body_style))
    story.append(Paragraph("The system will support automated bereavement, jury duty, and parental leave workflows according to statutory policies.", body_style))

    # Section 6
    story.append(Paragraph("6. Payroll Calculation & Deductions", h1_style))
    story.append(Paragraph("6.1 Gross-to-Net Engine", h2_style))
    story.append(Paragraph("The system shall compute gross pay by aggregating regular hours, overtime hours, and approved premium differentials.", body_style))
    story.append(Paragraph("The system must apply statutory tax withholdings including federal, state, and social security deductions prior to net pay disbursement.", body_style))
    story.append(Paragraph("The system shall enforce cutoff deadlines for timesheet approvals prior to executing final payroll generation.", body_style))
    story.append(Paragraph("The system stores final pay statements in encrypted PDF format accessible through employee self-service.", body_style))

    # Section 7
    story.append(Paragraph("7. Role-Based Security & Non-Functional Specifications", h1_style))
    story.append(Paragraph("The system shall enforce multi-factor authentication for all users possessing HR Administrator or Payroll Administrator roles.", body_style))
    story.append(Paragraph("The system must encrypt all sensitive employee PII at rest using AES-256 and in transit using TLS 1.3.", body_style))
    story.append(Paragraph("The system shall maintain 99.9% platform availability during core business hours (06:00 to 22:00 local time).", body_style))
    story.append(Paragraph("The system will support concurrent attendance clock events up to 5,000 requests per minute with p95 latency under 500ms.", body_style))

    doc.build(story)
    print(f"Generated PDF PRD: {pdf_path} ({pdf_path.stat().st_size} bytes)")


def create_dayforce_srs_docx():
    docx_path = OUT_DIR / "Dayforce_SRS_v1.0.docx"
    doc = docx.Document()

    # Title
    t = doc.add_paragraph()
    r = t.add_run("Dayforce Software Requirements Specification (SRS)")
    r.font.name = "Arial"
    r.font.size = Pt(18)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    meta = doc.add_paragraph("Version 1.0 • Enterprise HR & Workforce Engineering • Status: Approved")
    meta.runs[0].font.size = Pt(9.5)
    meta.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    # Section 1
    doc.add_heading("1. System Functional Requirements", level=1)
    doc.add_paragraph("1.1 Identity & Authentication Gateway")
    doc.add_paragraph("The system shall validate user credentials against the corporate identity provider using OAuth2 with PKCE.")
    doc.add_paragraph("The system must reject session authentication tokens after 15 minutes of user inactivity and terminate active sessions.")
    doc.add_paragraph("The system shall lock user accounts after 5 consecutive failed authentication attempts for a lockout duration of 30 minutes.")

    # Section 2
    doc.add_heading("2. Employee Data Governance", level=1)
    doc.add_paragraph("The system shall enforce mandatory employee fields including Employee ID, Legal First Name, Legal Last Name, Hire Date, and Department Code.")
    doc.add_paragraph("The system rejects employee record creation when Department Code does not map to an active organizational department.")
    doc.add_paragraph("The system must publish audit events to the centralized event bus whenever employee compensation or bank details are modified.")

    # Section 3
    doc.add_heading("3. Leave Policy Rules and Probationary Constraints", level=1)
    doc.add_paragraph("The system shall enforce standard leave policies based on tenure and job grade.")
    doc.add_paragraph("The system requires a standard probationary period of 30 days before full-time staff can request paid vacation days.")
    doc.add_paragraph("The system must calculate pro-rated leave accruals for employees joining mid-accrual cycle.")
    doc.add_paragraph("The system allows managers to delegate approval authority to designated delegates during planned manager absence.")

    # Section 4: Table
    doc.add_heading("4. Leave Entitlement Specifications", level=1)
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Leave Code"
    hdr_cells[1].text = "Description"
    hdr_cells[2].text = "Probation Period"
    hdr_cells[3].text = "Annual Accrual"

    data = [
        ("VAC", "Paid Annual Vacation", "30 days", "15 days"),
        ("SCK", "Paid Medical / Sick Leave", "0 days (immediate)", "10 days"),
        ("PER", "Personal Floating Holiday", "60 days", "3 days"),
        ("BER", "Bereavement Leave", "0 days (immediate)", "5 days"),
    ]
    for row in data:
        r = table.add_row().cells
        for idx, val in enumerate(row):
            r[idx].text = val

    # Section 5
    doc.add_heading("5. Performance & Reliability Non-Functional Requirements", level=1)
    doc.add_paragraph("The system shall complete timesheet batch calculation for 10,000 employees within 300 seconds.")
    doc.add_paragraph("The system must retain employee audit trails in compliant immutable storage for a minimum period of 7 years.")
    doc.add_paragraph("The system shall achieve Recovery Point Objective (RPO) under 5 minutes and Recovery Time Objective (RTO) under 60 minutes.")

    doc.save(str(docx_path))
    print(f"Generated DOCX SRS: {docx_path} ({docx_path.stat().st_size} bytes)")


def create_dayforce_business_rules_xlsx():
    xlsx_path = OUT_DIR / "Business_Rules.xlsx"
    wb = openpyxl.Workbook()

    # Style definitions
    hdr_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    hdr_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    border_side = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)

    # Sheet 1: Attendance_Policies
    ws1 = wb.active
    ws1.title = "Attendance_Policies"
    headers1 = ["Rule_ID", "Category", "Policy_Statement", "Grace_Period_Minutes", "Threshold_Action", "Enforcement_Level"]
    ws1.append(headers1)
    rows1 = [
        ["ATT-001", "Clock In", "Employees must record attendance within 5 minutes of scheduled shift start.", 5, "Flag Late Arrival", "Mandatory"],
        ["ATT-002", "Clock Out", "Employees shall not clock out earlier than 5 minutes before scheduled shift end without manager approval.", 5, "Require Early Departure Reason", "Mandatory"],
        ["ATT-003", "Meal Break", "Employees working shifts exceeding 6 hours must record a meal break of at least 30 consecutive minutes.", 30, "System Alert on Missed Break", "Statutory"],
        ["ATT-004", "Rest Break", "Employees are entitled to one paid 15-minute rest break for each 4-hour work interval.", 15, "Non-deductible from total hours", "Mandatory"],
        ["ATT-005", "Missed Punch", "When an employee forgets to clock out, the system shall prompt for manager timesheet adjustment.", 0, "Hold Timesheet Approval", "Mandatory"],
    ]
    for r in rows1:
        ws1.append(r)

    # Sheet 2: Overtime_Rules
    ws2 = wb.create_sheet(title="Overtime_Rules")
    headers2 = ["Rule_ID", "Shift_Type", "Threshold_Hours", "Multiplier_Rate", "Jurisdiction", "Description"]
    ws2.append(headers2)
    rows2 = [
        ["OT-001", "Weekly Standard", "40 hours / week", "1.5x", "Federal / FLSA", "Standard overtime paid at 1.5x regular pay after 40 hours worked in a week."],
        ["OT-002", "Daily California", "8 hours / day", "1.5x", "State - California", "Daily overtime paid at 1.5x for hours worked beyond 8 up to 12 in a single day."],
        ["OT-003", "Sunday Holiday", "Statutory Holiday / Sunday", "2.0x", "Statutory Collective Bargaining", "Overtime paid at 2.0x regular pay for Sunday and recognized statutory holiday shifts."],
        ["OT-004", "Double Time Daily", "12 hours / day", "2.0x", "State - California", "Double time paid at 2.0x for hours worked beyond 12 in a single day."],
    ]
    for r in rows2:
        ws2.append(r)

    # Sheet 3: Leave_Entitlements
    ws3 = wb.create_sheet(title="Leave_Entitlements")
    headers3 = ["Leave_Code", "Leave_Type", "Probation_Days", "Annual_Days", "Carryover_Max", "Approval_Required"]
    ws3.append(headers3)
    rows3 = [
        ["VAC-STD", "Annual Vacation", 90, 15, 5, "Direct Manager"],
        ["SCK-STD", "Sick Leave", 0, 10, 0, "Auto-Approved up to 2 days"],
        ["PRN-MAT", "Maternity Leave", 180, 84, 0, "HR Administrator"],
        ["PRN-PAT", "Paternity Leave", 180, 28, 0, "HR Administrator"],
        ["BER-FAM", "Bereavement (Immediate)", 0, 5, 0, "Manager Notification"],
    ]
    for r in rows3:
        ws3.append(r)

    # Format sheets
    for ws in [ws1, ws2, ws3]:
        for cell in ws[1]:
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.font = data_font
                cell.border = cell_border
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(str(xlsx_path))
    print(f"Generated XLSX Business Rules: {xlsx_path} ({xlsx_path.stat().st_size} bytes)")


def create_dayforce_api_markdown():
    md_path = OUT_DIR / "Dayforce_API_Integration.md"
    content = """# Dayforce REST API & Integration Specification

**Version:** 1.0  
**Target Environment:** Development / Staging / Production  
**Protocol:** HTTPS / TLS 1.3  
**Auth Scheme:** Bearer JWT (OAuth2.0 Token)  

---

## 1. Authentication & Security Expectations

The system shall require valid Bearer JWT tokens on all REST API invocations under `/api/v1/*`.

The system shall reject expired or unauthorized API requests with `HTTP 401 Unauthorized` and an error payload conforming to RFC 7807.

The system will enforce a session inactivity timeout of 30 minutes for API bearer tokens before mandatory refresh.

The system must log every client request IP address, client ID, and HTTP verb in centralized audit telemetry.

---

## 2. Employee Management Endpoints

### 2.1 Retrieve Employee Profile
- **Endpoint:** `GET /api/v1/employees/{employee_id}`
- **Permissions Required:** `employee.read`
- **Success Response (200 OK):**
```json
{
  "employee_id": "EMP1001",
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane.doe@dayforce-demo.com",
  "department": "Engineering",
  "job_title": "Senior Quality Engineer",
  "status": "active",
  "hire_date": "2024-03-15"
}
```
- **Error Responses:**
  - `401 Unauthorized`: Missing or malformed authentication header.
  - `403 Forbidden`: Authenticated user lacks permission to view requested profile.
  - `404 Not Found`: Employee record does not exist.

### 2.2 Register Clock In Event
- **Endpoint:** `POST /api/v1/attendance/clock-in`
- **Permissions Required:** `attendance.write`
- **Request Payload:**
```json
{
  "employee_id": "EMP1001",
  "punch_timestamp": "2026-11-07T08:58:30Z",
  "location": "HQ_Building_A",
  "device_id": "KIOSK-04"
}
```
- **Success Response (201 Created):**
```json
{
  "punch_id": "PCH-98421",
  "employee_id": "EMP1001",
  "status": "on_time",
  "recorded_at": "2026-11-07T08:58:30Z",
  "message": "Clock-in recorded successfully"
}
```
- **Error Responses:**
  - `400 Bad Request`: Missing mandatory employee ID or punch timestamp.
  - `409 Conflict`: Duplicate clock-in punch recorded within 60 seconds.

---

## 3. Leave Management Endpoints

### 3.1 Submit Leave Request
- **Endpoint:** `POST /api/v1/leave/requests`
- **Permissions Required:** `leave.submit`
- **Request Payload:**
```json
{
  "employee_id": "EMP1001",
  "leave_type": "VAC",
  "start_date": "2026-12-20",
  "end_date": "2026-12-24",
  "notes": "Year-end vacation"
}
```
- **Success Response (202 Accepted):**
```json
{
  "request_id": "LVE-55410",
  "status": "pending_manager_approval",
  "days_requested": 5,
  "remaining_balance": 10
}
```
- **Validation Rules:**
  - The system shall validate that start date occurs before or equal to end date.
  - The system rejects leave requests exceeding available accrued balance.
"""
    md_path.write_text(content, encoding="utf-8")
    print(f"Generated Markdown API Integration: {md_path} ({md_path.stat().st_size} bytes)")


if __name__ == "__main__":
    create_dayforce_prd_pdf()
    create_dayforce_srs_docx()
    create_dayforce_business_rules_xlsx()
    create_dayforce_api_markdown()
    print("All 4 Dayforce sample requirement documents generated successfully.")
