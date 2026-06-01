from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.db_manager import DatabaseManager
from services.analytics_engine import AnalyticsEngine


class ReportingService:
    def __init__(self, db: DatabaseManager, analytics: AnalyticsEngine) -> None:
        self.db = db
        self.analytics = analytics

    def generate_pdf_report(self, output_path: str) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(str(output), pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph("Ultra Advanced Record System - Executive Report", styles["Title"]), Spacer(1, 12)]

        items = [dict(row) for row in self.db.list_items()]
        if items:
            table_data = [["Identifier", "Title", "Category", "Available"]]
            for row in items[:30]:
                table_data.append([row["identifier"], row["title"], row["category"], "Yes" if row["available"] else "No"])
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a3447")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 16))

        charts = self.analytics.build_dashboard_charts()
        for name, chart_path in charts.items():
            story.append(Paragraph(name.replace("_", " ").title(), styles["Heading2"]))
            story.append(Image(str(chart_path), width=440, height=220))
            story.append(Spacer(1, 10))

        doc.build(story)
        return output

    def export_excel_report(self, output_path: str) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        items = pd.DataFrame([dict(row) for row in self.db.list_items()])
        tx = pd.DataFrame([dict(row) for row in self.db.analytics_dataframe()])
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            items.to_excel(writer, sheet_name="Items", index=False)
            tx.to_excel(writer, sheet_name="Transactions", index=False)
        return output
