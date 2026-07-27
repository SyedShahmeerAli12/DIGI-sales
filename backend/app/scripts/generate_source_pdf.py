"""
Generates backend/data/source_questions_qa.pdf from source_questions_qa.json —
exactly one page per Q&A entry, in the same order as the JSON array, so entry
index N (0-based) always lands on PDF page N+1. This lets the UI open the PDF
straight to the page an answer was grounded in via a #page=N URL fragment.

Run from backend/: python -m app.scripts.generate_source_pdf
"""

import json
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
QA_PATH = DATA_DIR / "source_questions_qa.json"
PDF_PATH = DATA_DIR / "source_questions_qa.pdf"

PERSONA_STYLE = ParagraphStyle(
    name="Persona", fontSize=10, textColor="#B3161E", spaceAfter=4, fontName="Helvetica-Bold"
)
CATEGORY_STYLE = ParagraphStyle(
    name="Category", fontSize=9, textColor="#666666", spaceAfter=16, fontName="Helvetica-Oblique"
)
QUESTION_STYLE = ParagraphStyle(
    name="Question", fontSize=14, textColor="#1a1a1a", spaceAfter=12, fontName="Helvetica-Bold", leading=18
)
ANSWER_STYLE = ParagraphStyle(
    name="Answer", fontSize=11, textColor="#222222", leading=16
)


def build_pdf() -> int:
    entries = json.loads(QA_PATH.read_text(encoding="utf-8"))

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=LETTER,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
    )

    story = []
    for i, entry in enumerate(entries):
        story.append(Paragraph(entry["persona"], PERSONA_STYLE))
        story.append(Paragraph(entry["category"], CATEGORY_STYLE))
        story.append(Paragraph(f"Q: {entry['question']}", QUESTION_STYLE))
        story.append(Paragraph(f"A: {entry['answer']}", ANSWER_STYLE))
        if i < len(entries) - 1:
            from reportlab.platypus import PageBreak

            story.append(PageBreak())

    doc.build(story)
    print(f"Wrote {len(entries)} pages to {PDF_PATH.name}")
    return len(entries)


if __name__ == "__main__":
    build_pdf()
