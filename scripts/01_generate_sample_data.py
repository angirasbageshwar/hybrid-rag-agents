"""STEP 1 — Generate two realistic sample enterprise PDFs (a financial report
with a nested table + a legal agreement) so the pipeline is testable without
any private data. Safe to re-run."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parents[1] / "data" / "sample_docs"
OUT.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()


def financial_report() -> None:
    doc = SimpleDocTemplate(str(OUT / "acme_q3_2025_financial_report.pdf"), pagesize=LETTER)
    story = [
        Paragraph("ACME Robotics Inc. — Q3 2025 Financial Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Management Discussion", styles["Heading2"]),
        Paragraph(
            "ACME Robotics reported total revenue of $482.3 million in Q3 2025, "
            "up 18.4% year-over-year, driven primarily by the Industrial Automation "
            "segment. Gross margin expanded to 61.2% from 58.9% in Q3 2024. "
            "Operating expenses rose 11% to $186.4 million due to expanded R&D "
            "headcount in the Autonomous Systems division. Net income was "
            "$74.1 million, or $1.32 per diluted share.", styles["BodyText"]),
        Spacer(1, 10),
        Paragraph("Revenue by Segment and Region (USD millions)", styles["Heading2"]),
    ]
    data = [
        ["Segment", "Region", "Q3 2025", "Q3 2024", "YoY %"],
        ["Industrial Automation", "North America", "148.2", "121.5", "+22.0%"],
        ["Industrial Automation", "EMEA", "96.7", "84.3", "+14.7%"],
        ["Autonomous Systems", "North America", "88.4", "70.1", "+26.1%"],
        ["Autonomous Systems", "APAC", "62.9", "58.8", "+7.0%"],
        ["Service & Support", "Global", "86.1", "72.7", "+18.4%"],
        ["TOTAL", "", "482.3", "407.4", "+18.4%"],
    ]
    t = Table(data, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e5e7eb")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story += [t, Spacer(1, 12),
              Paragraph("Risk Factors", styles["Heading2"]),
              Paragraph(
                  "The company notes continued supply-chain exposure for precision "
                  "actuators sourced from two suppliers, and foreign-exchange headwinds "
                  "of approximately $6.2 million in EMEA. Full-year 2025 revenue "
                  "guidance is raised to $1.92–$1.96 billion.", styles["BodyText"])]
    doc.build(story)
    print("wrote", OUT / "acme_q3_2025_financial_report.pdf")


def legal_agreement() -> None:
    doc = SimpleDocTemplate(str(OUT / "acme_master_services_agreement.pdf"), pagesize=LETTER)
    story = [
        Paragraph("Master Services Agreement — ACME Robotics Inc. & Orbital Logistics LLC",
                  styles["Title"]),
        Spacer(1, 12),
        Paragraph("Clause 4. Term and Renewal", styles["Heading2"]),
        Paragraph(
            "This Agreement commences on 1 February 2025 and continues for an "
            "initial term of thirty-six (36) months, renewing automatically for "
            "successive twelve (12) month periods unless either party gives ninety "
            "(90) days written notice of non-renewal.", styles["BodyText"]),
        Paragraph("Clause 9. Limitation of Liability", styles["Heading2"]),
        Paragraph(
            "Except for breaches of Clause 12 (Confidentiality), each party's "
            "aggregate liability is capped at the fees paid in the twelve (12) "
            "months preceding the claim, and in no event exceeds $5,000,000.",
            styles["BodyText"]),
        Paragraph("Clause 14. Service Credits", styles["Heading2"]),
        Paragraph("Monthly uptime below 99.9% entitles Client to the credits below:",
                  styles["BodyText"]),
    ]
    data = [["Monthly Uptime", "Credit (% of monthly fee)"],
            ["99.0% – 99.89%", "5%"], ["97.0% – 98.99%", "10%"], ["Below 97.0%", "25%"]]
    t = Table(data, hAlign="LEFT")
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(t)
    doc.build(story)
    print("wrote", OUT / "acme_master_services_agreement.pdf")


if __name__ == "__main__":
    financial_report()
    legal_agreement()
