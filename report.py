"""
Professional PDF report generation for CareerOps AI.

build_pdf() converts an agent's Markdown output (headings, bullet lists,
numbered lists, tables, bold/italic/code, quotes) into a branded A4 PDF
with a title banner, details strip, optional match-score card, running
header, and "Page X of Y" footer.

Only the standard PDF fonts are used, so no font files are needed on the
server. Emoji and characters outside Latin-1/Windows-1252 are removed.
"""

import io
import re
import textwrap
import unicodedata
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# THEME
# ============================================================

NAVY = colors.HexColor("#1f2a44")
TEXT = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
LIGHT = colors.HexColor("#f3f4f6")
BORDER = colors.HexColor("#d1d5db")
GREEN = colors.HexColor("#059669")
AMBER = colors.HexColor("#d97706")
RED = colors.HexColor("#dc2626")

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 2.0 * cm
MARGIN_TOP = 1.9 * cm
MARGIN_BOTTOM = 2.2 * cm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

DISCLAIMER = (
    "AI-generated guidance. Please verify all details before using "
    "them in an application."
)


# ============================================================
# TEXT CLEANING
# ============================================================

_REPLACEMENTS = {
    "\u2192": "->",
    "\u2190": "<-",
    "\u21d2": "=>",
    "\u2713": "+",
    "\u2714": "+",
    "\u2717": "x",
    "\u2718": "x",
    "\u2264": "<=",
    "\u2265": ">=",
    "\u2212": "-",
    "\u2011": "-",
    "\u00a0": " ",
    "\u200b": "",
    "\u2605": "*",
    "\u25cf": "\u2022",
    "\u25aa": "\u2022",
    "\u25e6": "\u2022",
}


def clean(text):
    """Make text safe for the standard PDF fonts (Windows-1252)."""

    text = str(text)

    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)

    text = unicodedata.normalize("NFC", text)
    text = text.encode("cp1252", "ignore").decode("cp1252")

    return text


def strip_markdown(text):
    """Plain-text fallback if a line of Markdown cannot be rendered."""

    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    return escape(text)


# ============================================================
# INLINE MARKDOWN -> REPORTLAB MARKUP
# ============================================================

def _format_plain(segment):
    segment = escape(segment)

    segment = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<link href="\2" color="#1d4ed8">\1</link>',
        segment,
    )
    segment = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", segment)
    segment = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", segment)
    segment = re.sub(r"(?<!\w)__(.+?)__(?!\w)", r"<b>\1</b>", segment)
    segment = re.sub(
        r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])",
        r"<i>\1</i>",
        segment,
    )
    segment = re.sub(
        r"(?<!\w)_(?![\s_])(.+?)(?<![\s_])_(?!\w)",
        r"<i>\1</i>",
        segment,
    )

    return segment


def inline(text):
    """Convert inline Markdown to ReportLab paragraph markup."""

    text = clean(text)
    parts = text.split("`")
    output = []

    for index, part in enumerate(parts):
        if index % 2 == 1:
            output.append(
                '<font face="Courier" color="#9a3412">'
                f"{escape(part)}</font>"
            )
        else:
            output.append(_format_plain(part))

    return "".join(output)


def safe_paragraph(text, style, **kwargs):
    """Paragraph that never crashes the whole report on bad markup."""

    try:
        return Paragraph(inline(text), style, **kwargs)
    except Exception:
        return Paragraph(strip_markdown(clean(text)), style, **kwargs)


# ============================================================
# STYLES
# ============================================================

def build_styles(accent):
    base = dict(fontName="Helvetica", textColor=TEXT, alignment=TA_LEFT)

    return {
        "body": ParagraphStyle(
            "body", fontSize=9.6, leading=14.2, spaceAfter=5, **base
        ),
        "h1": ParagraphStyle(
            "h1", fontName="Helvetica-Bold", fontSize=16, leading=20,
            textColor=NAVY, spaceBefore=12, spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "h2", fontName="Helvetica-Bold", fontSize=13, leading=17,
            textColor=accent, spaceBefore=14, spaceAfter=2,
        ),
        "h3": ParagraphStyle(
            "h3", fontName="Helvetica-Bold", fontSize=10.8, leading=14,
            textColor=NAVY, spaceBefore=9, spaceAfter=3,
        ),
        "h4": ParagraphStyle(
            "h4", fontName="Helvetica-Bold", fontSize=9.8, leading=13,
            textColor=MUTED, spaceBefore=7, spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontSize=9.6, leading=14, spaceAfter=2.5, **base
        ),
        "quote": ParagraphStyle(
            "quote", fontName="Helvetica-Oblique", fontSize=9.4,
            leading=13.5, textColor=MUTED, leftIndent=12,
            borderPadding=(2, 2, 2, 8), spaceAfter=6,
        ),
        "code": ParagraphStyle(
            "code", fontName="Courier", fontSize=8, leading=10.5,
            textColor=colors.HexColor("#111827"), backColor=LIGHT,
            borderPadding=6, leftIndent=6, rightIndent=6, spaceAfter=8,
        ),
        "cell": ParagraphStyle(
            "cell", fontSize=8.4, leading=11.2, **base
        ),
        "cell_head": ParagraphStyle(
            "cell_head", fontName="Helvetica-Bold", fontSize=8.4,
            leading=11.2, textColor=colors.white,
        ),
        "meta_label": ParagraphStyle(
            "meta_label", fontName="Helvetica-Bold", fontSize=7,
            leading=9, textColor=MUTED,
        ),
        "meta_value": ParagraphStyle(
            "meta_value", fontName="Helvetica-Bold", fontSize=9.5,
            leading=12, textColor=NAVY,
        ),
        "banner_kicker": ParagraphStyle(
            "banner_kicker", fontName="Helvetica-Bold", fontSize=8,
            leading=10, textColor=colors.HexColor("#e5e7eb"),
        ),
        "banner_title": ParagraphStyle(
            "banner_title", fontName="Helvetica-Bold", fontSize=23,
            leading=28, textColor=colors.white, spaceBefore=3,
        ),
        "banner_sub": ParagraphStyle(
            "banner_sub", fontName="Helvetica", fontSize=10.5,
            leading=14, textColor=colors.HexColor("#f3f4f6"),
            spaceBefore=3,
        ),
        "score_big": ParagraphStyle(
            "score_big", fontName="Helvetica-Bold", fontSize=34,
            leading=38, textColor=colors.white, alignment=1,
        ),
        "score_cap": ParagraphStyle(
            "score_cap", fontName="Helvetica-Bold", fontSize=8.5,
            leading=11, textColor=colors.white, alignment=1,
        ),
        "section_label": ParagraphStyle(
            "section_label", fontName="Helvetica-Bold", fontSize=8,
            leading=10, textColor=MUTED, spaceAfter=3,
        ),
        "request": ParagraphStyle(
            "request", fontName="Helvetica-Oblique", fontSize=9,
            leading=13, textColor=colors.HexColor("#374151"),
        ),
    }


# ============================================================
# BLOCKS: BANNER, DETAILS, SCORE CARD, REQUEST
# ============================================================

def banner(title, subtitle, accent, styles):
    cell = [
        Paragraph("CAREEROPS AI", styles["banner_kicker"]),
        Paragraph(clean(title), styles["banner_title"]),
        Paragraph(clean(subtitle), styles["banner_sub"]),
    ]

    table = Table([[cell]], colWidths=[CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 20),
                ("RIGHTPADDING", (0, 0), (-1, -1), 20),
                ("TOPPADDING", (0, 0), (-1, -1), 20),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
            ]
        )
    )

    return table


def details_strip(items, accent, styles):
    labels = [Paragraph(clean(k).upper(), styles["meta_label"]) for k, _ in items]
    values = [Paragraph(clean(v), styles["meta_value"]) for _, v in items]
    width = CONTENT_WIDTH / len(items)

    table = Table([labels, values], colWidths=[width] * len(items))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("LINEBELOW", (0, -1), (-1, -1), 1.2, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
                ("TOPPADDING", (0, 1), (-1, 1), 2),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    return table


def request_box(request_text, accent, styles):
    request_text = clean(request_text).strip()

    if not request_text:
        return None

    if len(request_text) > 700:
        request_text = request_text[:700].rstrip() + "..."

    content = [
        Paragraph("YOUR CAREER REQUEST", styles["section_label"]),
        Paragraph(escape(request_text).replace("\n", "<br/>"), styles["request"]),
    ]

    table = Table([[content]], colWidths=[CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    return table


def _score_color(value):
    if value >= 75:
        return GREEN
    if value >= 50:
        return AMBER
    return RED


def _score_label(value):
    if value >= 80:
        return "STRONG MATCH"
    if value >= 60:
        return "GOOD MATCH"
    if value >= 40:
        return "PARTIAL MATCH"
    return "WEAK MATCH"


def score_card(match_score, styles):
    """Big percentage on the left, one bar per category on the right."""

    overall = match_score["overall"]
    color = _score_color(overall)

    big = [
        Paragraph(f"{overall}%", styles["score_big"]),
        Paragraph(_score_label(overall), styles["score_cap"]),
    ]

    breakdown = match_score.get("breakdown") or {}
    bars_width = CONTENT_WIDTH - 4.4 * cm - 24
    row_height = 24
    height = max(row_height * max(len(breakdown), 1), 40)
    drawing = Drawing(bars_width, height)

    label_width = 118
    track_width = bars_width - label_width - 34

    for index, (category, value) in enumerate(breakdown.items()):
        y = height - (index + 1) * row_height + 8
        drawing.add(
            String(0, y + 2, clean(category), fontName="Helvetica",
                   fontSize=8, fillColor=TEXT)
        )
        drawing.add(
            Rect(label_width, y, track_width, 8, rx=4, ry=4,
                 fillColor=colors.HexColor("#e5e7eb"), strokeColor=None)
        )
        fill = max(track_width * value / 100.0, 0)
        if fill > 0:
            drawing.add(
                Rect(label_width, y, fill, 8, rx=4, ry=4,
                     fillColor=_score_color(value), strokeColor=None)
            )
        drawing.add(
            String(label_width + track_width + 6, y + 1, str(value),
                   fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY)
        )

    table = Table([[big, drawing]], colWidths=[4.4 * cm, CONTENT_WIDTH - 4.4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), color),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f9fafb")),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING", (1, 0), (1, 0), 16),
            ]
        )
    )

    return table


# ============================================================
# MARKDOWN -> FLOWABLES
# ============================================================

_TABLE_SEPARATOR = re.compile(
    r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$"
)
_BULLET = re.compile(r"^(\s*)([-*+\u2022])\s+(.*)$")
_NUMBERED = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")


def _split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _build_table(rows, accent, styles):
    columns = max(len(row) for row in rows)
    rows = [row + [""] * (columns - len(row)) for row in rows]

    weights = []
    minimums = []

    for column in range(columns):
        cells = [clean(row[column]) for row in rows]
        average = sum(len(cell) for cell in cells) / len(cells)
        weights.append(min(max(average, 9), 55))

        # never narrower than the longest single word (plus padding)
        longest_word = max(
            (len(word) for cell in cells for word in cell.split()),
            default=4,
        )
        minimums.append(min(longest_word * 4.9 + 14, CONTENT_WIDTH * 0.4))

    total = sum(weights)
    widths = [CONTENT_WIDTH * weight / total for weight in weights]

    # raise too-narrow columns to their minimum, taking the space
    # from the columns that have room to spare
    for _ in range(columns):
        short = [i for i in range(columns) if widths[i] < minimums[i]]
        if not short:
            break
        deficit = sum(minimums[i] - widths[i] for i in short)
        donors = [i for i in range(columns) if widths[i] > minimums[i]]
        spare = sum(widths[i] - minimums[i] for i in donors)
        if spare <= 0:
            break
        scale = min(1.0, deficit / spare)
        for i in donors:
            widths[i] -= (widths[i] - minimums[i]) * scale
        for i in short:
            widths[i] = minimums[i]

    data = []
    for row_index, row in enumerate(rows):
        style = styles["cell_head"] if row_index == 0 else styles["cell"]
        data.append([safe_paragraph(cell, style) for cell in row])

    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), accent),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#f6f7f9")]),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    return [table, Spacer(1, 8)]


def markdown_to_flowables(text, accent, styles):
    lines = clean(text).replace("\r\n", "\n").replace("\t", "    ").split("\n")
    flow = []
    paragraph = []
    index = 0

    def flush():
        if paragraph:
            flow.append(safe_paragraph(" ".join(paragraph), styles["body"]))
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        # ---- fenced code block ----
        if stripped.startswith("```"):
            flush()
            index += 1
            block = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            wrapped = []
            for code_line in block or [""]:
                wrapped.extend(textwrap.wrap(code_line, 92) or [""])
            flow.append(Preformatted("\n".join(wrapped), styles["code"]))
            continue

        # ---- blank line ----
        if not stripped:
            flush()
            index += 1
            continue

        # ---- horizontal rule ----
        if _RULE.match(stripped):
            flush()
            flow.append(
                HRFlowable(width="100%", thickness=0.6, color=BORDER,
                           spaceBefore=6, spaceAfter=6)
            )
            index += 1
            continue

        # ---- heading ----
        heading = _HEADING.match(stripped)
        if heading:
            flush()
            level = min(len(heading.group(1)), 4)
            title = heading.group(2).strip()
            if title:
                paragraph_obj = safe_paragraph(title, styles[f"h{level}"])
                if level <= 2:
                    rule = HRFlowable(
                        width="100%",
                        thickness=1.1 if level == 2 else 0.6,
                        color=accent if level == 2 else BORDER,
                        spaceBefore=1, spaceAfter=6,
                    )
                    flow.append(KeepTogether([paragraph_obj, rule]))
                else:
                    flow.append(paragraph_obj)
            index += 1
            continue

        # ---- table ----
        if (
            stripped.startswith("|")
            and index + 1 < len(lines)
            and _TABLE_SEPARATOR.match(lines[index + 1])
        ):
            flush()
            rows = [_split_row(stripped)]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(_split_row(lines[index]))
                index += 1
            flow.extend(_build_table(rows, accent, styles))
            continue

        # ---- block quote ----
        if stripped.startswith(">"):
            flush()
            quote = stripped.lstrip("> ").strip()
            flow.append(safe_paragraph(quote, styles["quote"]))
            index += 1
            continue

        # ---- bullet list ----
        bullet = _BULLET.match(line)
        if bullet:
            flush()
            level = min(len(bullet.group(1)) // 2, 3)
            left = 16 + 14 * level
            style = ParagraphStyle(
                f"bullet{level}", parent=styles["bullet"],
                leftIndent=left, bulletIndent=left - 11,
            )
            marker = "\u2022" if level == 0 else "-"
            flow.append(
                safe_paragraph(bullet.group(3), style, bulletText=marker)
            )
            index += 1
            continue

        # ---- numbered list ----
        numbered = _NUMBERED.match(line)
        if numbered:
            flush()
            level = min(len(numbered.group(1)) // 2, 3)
            left = 20 + 14 * level
            style = ParagraphStyle(
                f"number{level}", parent=styles["bullet"],
                leftIndent=left, bulletIndent=left - 17,
            )
            flow.append(
                safe_paragraph(
                    numbered.group(3), style,
                    bulletText=f"{numbered.group(2)}.",
                )
            )
            index += 1
            continue

        # ---- normal text ----
        paragraph.append(stripped)
        index += 1

    flush()
    return flow


# ============================================================
# PAGE DECORATION (header, footer, page numbers)
# ============================================================

def _canvas_factory(accent, agent, task):
    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_states = []

        def showPage(self):
            self._saved_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_states)
            for state in self._saved_states:
                self.__dict__.update(state)
                self._decorate(total)
                super().showPage()
            super().save()

        def _decorate(self, total_pages):
            page = self._pageNumber
            self.saveState()

            # top accent bar
            self.setFillColor(accent)
            self.rect(0, PAGE_HEIGHT - 9, PAGE_WIDTH, 9, fill=1, stroke=0)

            # running header (not on the first page: the banner is there)
            if page > 1:
                self.setFont("Helvetica-Bold", 8)
                self.setFillColor(NAVY)
                self.drawString(MARGIN_X, PAGE_HEIGHT - 28, "CareerOps AI")
                self.setFont("Helvetica", 8)
                self.setFillColor(MUTED)
                self.drawRightString(
                    PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 28,
                    clean(f"{agent}  |  {task}"),
                )
                self.setStrokeColor(BORDER)
                self.setLineWidth(0.5)
                self.line(MARGIN_X, PAGE_HEIGHT - 34, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 34)

            # footer
            self.setStrokeColor(BORDER)
            self.setLineWidth(0.5)
            self.line(MARGIN_X, 38, PAGE_WIDTH - MARGIN_X, 38)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(MUTED)
            self.drawString(MARGIN_X, 26, DISCLAIMER)
            self.drawRightString(
                PAGE_WIDTH - MARGIN_X, 26, f"Page {page} of {total_pages}"
            )

            self.restoreState()

    return NumberedCanvas


# ============================================================
# PUBLIC API
# ============================================================

def _hex_to_color(value, default):
    try:
        return colors.HexColor(value)
    except Exception:
        return default


def build_pdf(
    agent,
    task,
    markdown_text,
    generated_at="",
    career_request="",
    accent_hex="#4f46e5",
    match_score=None,
):
    """
    Build the PDF and return it as bytes.

    match_score: optional dict from features.parse_match_score(); when
    given, a score card is placed at the top of the report.
    """

    accent = _hex_to_color(accent_hex, colors.HexColor("#4f46e5"))
    styles = build_styles(accent)

    title = f"{task} Report"
    subtitle = f"Prepared by the {agent} agent"

    story = [
        banner(title, subtitle, accent, styles),
        Spacer(1, 10),
        details_strip(
            [
                ("Agent", agent),
                ("Report type", task),
                ("Generated", generated_at or "-"),
            ],
            accent,
            styles,
        ),
        Spacer(1, 12),
    ]

    request = request_box(career_request, accent, styles)
    if request is not None:
        story.extend([request, Spacer(1, 12)])

    if match_score:
        story.extend([score_card(match_score, styles), Spacer(1, 10)])

    story.extend(markdown_to_flowables(markdown_text or "", accent, styles))

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title=clean(f"{task} Report - CareerOps AI"),
        author="CareerOps AI",
        subject=clean(f"{agent}: {task}"),
    )
    document.build(
        story, canvasmaker=_canvas_factory(accent, clean(agent), clean(task))
    )

    return buffer.getvalue()
