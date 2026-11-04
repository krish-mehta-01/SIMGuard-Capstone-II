"""python-docx toolkit that reproduces the Sem 4 report format exactly:
Times New Roman 14 pt body, 1.5 line spacing, justified; centred 'CHAPTER n / TITLE' headings; bold-caps section headings;
borderless 'CHAPTER | TITLE | PAGE NO' contents table and 'FIG. NO | FIGURE NAME | PAGE' list; roman front matter and arabic
body numbering; blue-grey code boxes. Contents / figure-list page numbers are measured in Word and fed back on the next pass."""

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

FONT = "Times New Roman"
BODY_PT = 14
TOKEN = re.compile(r"(\*\*.+?\*\*|`.+?`|__.+?__|\[[A-Z][A-Z0-9 /_.,()-]*\])")


def roman(n):
    out = ""
    for v, s in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"),
                 (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out += s
            n -= v
    return out


def set_font(run_or_style, name=FONT, size=None, bold=None, italic=None, color=None):
    f = run_or_style.font
    f.name = name
    el = run_or_style._element
    rpr = el.get_or_add_rPr() if hasattr(el, "get_or_add_rPr") else el.rPr
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rfonts.get(qn(a)) is not None:
            del rfonts.attrib[qn(a)]
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color is not None:
        f.color.rgb = RGBColor.from_string(color)


def shade(pr, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def add_field(paragraph, instr, placeholder="", size=None, bold=None):
    def run_with(child):
        r = paragraph.add_run()
        set_font(r, size=size, bold=bold)
        r._r.append(child)
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin")
    i = OxmlElement("w:instrText"); i.set(qn("xml:space"), "preserve"); i.text = f" {instr} "
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate")
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end")
    run_with(b); run_with(i); run_with(s)
    r = paragraph.add_run(placeholder)
    set_font(r, size=size, bold=bold)
    run_with(e)


class Report:
    def __init__(self, refs=None, prev=None):
        self.doc = Document()
        self.refs = refs or {}          # label -> "Fig. 2.3" / "Table 4.1" from the previous pass
        self.new_refs = {}
        self.prev = prev or []          # entries (with measured pages) from the previous pass
        self.entries = []               # headings / figures recorded in this pass (bookmarked)
        self.ch = 0
        self.ch_prefix = ""
        self.fig_n = 0
        self.tab_n = 0
        self._bm_id = 100
        self._setup_styles()
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)   # A4, as the Sem 4 body pages
        sec.left_margin, sec.right_margin = Inches(1.0), Inches(0.88)
        sec.top_margin, sec.bottom_margin = Inches(1.0), Inches(1.0)
        sec.footer_distance = Inches(0.58)

    # ───────────────────────── styles ─────────────────────────
    def _setup_styles(self):
        st = self.doc.styles
        n = st["Normal"]
        set_font(n, size=BODY_PT)
        pf = n.paragraph_format
        pf.space_before = Pt(0); pf.space_after = Pt(6)
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        for name, size, align in (("Heading 1", 14, WD_ALIGN_PARAGRAPH.CENTER), ("Heading 2", 14, WD_ALIGN_PARAGRAPH.LEFT),
                                  ("Heading 3", 14, WD_ALIGN_PARAGRAPH.LEFT)):
            h = st[name]
            set_font(h, size=size, bold=True, italic=False, color="000000")
            h.paragraph_format.alignment = align
            h.paragraph_format.keep_with_next = True
            h.paragraph_format.space_before = Pt(10 if name != "Heading 1" else 0)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        for name in ("Figure Caption", "Table Caption"):
            c = st.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            c.base_style = n
            set_font(c, size=14, bold=True)
            c.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            c.paragraph_format.space_before = Pt(4)
            c.paragraph_format.space_after = Pt(10)
        st["Table Caption"].paragraph_format.keep_with_next = True
        st["Table Caption"].paragraph_format.space_after = Pt(4)
        for name in ("List Bullet", "List Number"):
            lb = st[name]
            set_font(lb, size=BODY_PT)
            lb.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            lb.paragraph_format.line_spacing = 1.25
            lb.paragraph_format.space_after = Pt(3)
        front = st.add_style("Front Heading", WD_STYLE_TYPE.PARAGRAPH)
        front.base_style = n
        set_font(front, size=14, bold=True)
        front.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        front.paragraph_format.space_after = Pt(14)
        front.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    # ───────────────────────── bookmarks / entries ─────────────────────────
    def _record(self, kind, num, title, para):
        idx = len(self.entries)
        name = f"_e{idx}"
        self._bm_id += 1
        start = OxmlElement("w:bookmarkStart")
        start.set(qn("w:id"), str(self._bm_id)); start.set(qn("w:name"), name)
        end = OxmlElement("w:bookmarkEnd")
        end.set(qn("w:id"), str(self._bm_id))
        p = para._p
        ppr = p.find(qn("w:pPr"))
        if ppr is not None:
            ppr.addnext(start)
        else:
            p.insert(0, start)
        p.append(end)
        self.entries.append({"kind": kind, "num": num, "title": title, "bm": name})

    # ───────────────────────── text ─────────────────────────
    def _runs(self, p, text, size=None, bold=False, italic=False, color=None):
        for part in TOKEN.split(text):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                r = p.add_run(part[2:-2]); set_font(r, size=size, bold=True, italic=italic, color=color)
            elif part.startswith("__") and part.endswith("__"):
                r = p.add_run(part[2:-2]); set_font(r, size=size, bold=bold, italic=True, color=color)
            elif part.startswith("[") and part.endswith("]"):
                r = p.add_run(part); set_font(r, size=size, bold=bold, italic=italic, color=color)
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            elif part.startswith("`") and part.endswith("`"):
                r = p.add_run(part[1:-1]); set_font(r, name="Courier New", size=(size or BODY_PT) - 2, bold=bold)
            else:
                r = p.add_run(part); set_font(r, size=size, bold=bold, italic=italic, color=color)

    def p(self, text, indent=True, align="justify", size=None, bold=False, italic=False, after=None, keep_next=False,
          spacing=None):
        para = self.doc.add_paragraph()
        pf = para.paragraph_format
        para.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                          "center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        if indent and align == "justify":
            pf.first_line_indent = Inches(0.5)
        if after is not None:
            pf.space_after = Pt(after)
        if spacing:
            pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            pf.line_spacing = spacing
        pf.keep_with_next = keep_next
        self._runs(para, text, size=size, bold=bold, italic=italic)
        return para

    def lead(self, text):
        return self.p(text, indent=True)

    def bullets(self, items, style="List Bullet"):
        for it in items:
            para = self.doc.add_paragraph(style=style)
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            self._runs(para, it)

    def numbered(self, items):
        for i, it in enumerate(items, 1):
            para = self.doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf = para.paragraph_format
            pf.left_indent = Inches(0.5); pf.first_line_indent = Inches(-0.3)
            pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE; pf.line_spacing = 1.25; pf.space_after = Pt(3)
            self._runs(para, f"{i}.  " + it)

    def equation(self, text, label=None):
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        para.paragraph_format.space_before = Pt(4); para.paragraph_format.space_after = Pt(8)
        r = para.add_run(text); set_font(r, size=13, italic=True)
        if label:
            r2 = para.add_run(f"        ({label})"); set_font(r2, size=13)

    # ───────────────────────── headings ─────────────────────────
    def chapter(self, number, title):
        self.ch = number
        self.ch_prefix = str(number)
        self.fig_n = 0
        self.tab_n = 0
        para = self.doc.add_paragraph(style="Heading 1")
        para.paragraph_format.page_break_before = True
        para.paragraph_format.space_after = Pt(22)
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY      # Sem 4 spaces 'CHAPTER n' and the title ~26 pt apart
        para.paragraph_format.line_spacing = Pt(26)
        r = para.add_run(f"CHAPTER {number}"); set_font(r, size=14, bold=True, color="000000")
        r.add_break()
        r2 = para.add_run(title.upper()); set_font(r2, size=14, bold=True, color="000000")
        self._record("chapter", str(number), title.upper(), para)

    def unnumbered(self, title, prefix="", page_break=True, align="center"):
        self.ch = 0
        self.ch_prefix = prefix
        self.fig_n = 0
        self.tab_n = 0
        para = self.doc.add_paragraph(style="Heading 1")
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER if align == "center" else WD_ALIGN_PARAGRAPH.LEFT
        para.paragraph_format.page_break_before = page_break
        para.paragraph_format.space_after = Pt(14)
        r = para.add_run(title.upper()); set_font(r, size=14, bold=True, color="000000")
        self._record("plain", "", title.upper(), para)
        return para

    def h2(self, text):
        para = self.doc.add_paragraph(style="Heading 2")
        r = para.add_run(text.upper()); set_font(r, size=14, bold=True, color="000000")
        num, title = text.split(" ", 1)
        self._record("h2", num, title, para)

    def h3(self, text, caps=True):
        para = self.doc.add_paragraph(style="Heading 3")
        r = para.add_run(text.upper() if caps else text); set_font(r, size=14, bold=True, color="000000")
        num, title = text.split(" ", 1)
        self._record("h3", num, title, para)

    def h4(self, text):
        """Bold stand-alone label (as used for the enhancement names and layer names in the Sem 4 report)."""
        para = self.doc.add_paragraph()
        para.paragraph_format.keep_with_next = True
        para.paragraph_format.space_before = Pt(6)
        para.paragraph_format.space_after = Pt(2)
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        r = para.add_run(text); set_font(r, size=14, bold=True)

    def front_heading(self, text, page_break=False, size=14):
        para = self.doc.add_paragraph(style="Front Heading")
        para.paragraph_format.page_break_before = page_break
        r = para.add_run(text.upper()); set_font(r, size=size, bold=True)
        return para

    # ───────────────────────── cross references ─────────────────────────
    def ref(self, key):
        return self.refs.get(key, "Fig. ?")

    def _number(self, kind):
        if kind == "fig":
            self.fig_n += 1
            n = self.fig_n
        else:
            self.tab_n += 1
            n = self.tab_n
        return f"{self.ch_prefix}.{n}"

    # ───────────────────────── figures ─────────────────────────
    def figure(self, path, caption, key, width=6.0, max_height=None, center_caption=False, label=None):
        path = Path(path)
        num = self._number("fig")
        label = label or f"Fig. {num}"
        self.new_refs[key] = label
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.keep_with_next = True
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        para.paragraph_format.space_before = Pt(6)
        para.paragraph_format.space_after = Pt(2)
        run = para.add_run()
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
        width_in = width
        if max_height and width * h / w > max_height:
            width_in = max_height * w / h
        run.add_picture(str(path), width=Inches(width_in))
        cap = self.doc.add_paragraph(style="Figure Caption")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER if center_caption else WD_ALIGN_PARAGRAPH.LEFT
        r = cap.add_run(f"{label} – {caption}"); set_font(r, size=14, bold=True)
        self._record("fig", label, caption, cap)
        return label

    # ───────────────────────── tables ─────────────────────────
    def table(self, headers, rows, widths, caption=None, key=None, font=11, align=None, bold_last=False,
              highlight_row=None, header_fill="D9D9D9"):
        if caption:
            num = self._number("tab")
            label = f"Table {num}"
            if key:
                self.new_refs[key] = label
            cp = self.doc.add_paragraph(style="Table Caption")
            r = cp.add_run(f"{label} – {caption}"); set_font(r, size=12, bold=True)
        t = self.doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tblPr = t._tbl.tblPr
        lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
        mar = OxmlElement("w:tblCellMar")
        for side, w in (("top", 40), ("left", 90), ("bottom", 40), ("right", 90)):
            e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), str(w)); e.set(qn("w:type"), "dxa"); mar.append(e)
        tblPr.append(mar)
        align = align or ["left"] * len(headers)

        def fill(cell, text, bold=False, al="left", width=None, fillc=None):
            cell.width = Inches(width)
            para = cell.paragraphs[0]
            para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            para.paragraph_format.space_after = Pt(1); para.paragraph_format.space_before = Pt(1)
            para.paragraph_format.first_line_indent = Inches(0)
            para.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
                              "right": WD_ALIGN_PARAGRAPH.RIGHT}[al]
            self._runs(para, str(text), size=font, bold=bold)
            if fillc:
                shade(cell._tc.get_or_add_tcPr(), fillc)

        for i, h in enumerate(headers):
            fill(t.rows[0].cells[i], h, bold=True, al="center" if align[i] != "left" else "left", width=widths[i],
                 fillc=header_fill)
        trPr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            last = bold_last and ri == len(rows) - 1
            hl = highlight_row is not None and ri == highlight_row
            for i, v in enumerate(row):
                fill(cells[i], v, bold=last or hl, al=align[i], width=widths[i], fillc="EAF1FB" if hl else None)
            cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true")
            t.rows[-1]._tr.get_or_add_trPr().append(cs)
        if len(rows) <= 16:                      # keep short tables on one page
            for row in t.rows[:-1]:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        para.paragraph_format.keep_with_next = True
        gap = self.doc.add_paragraph()
        gap.paragraph_format.space_after = Pt(4)
        gap.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        return t

    # ───────────────────────── Sem 4 style contents and figure lists ─────────────────────────
    def _borderless(self, widths, rows, size, header=None, aligns=None, spacing_after=5, header_aligns=None):
        t = self.doc.add_table(rows=0, cols=len(widths))
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        t.autofit = False
        aligns = aligns or [WD_ALIGN_PARAGRAPH.LEFT] * len(widths)
        header_aligns = header_aligns or aligns
        allrows = ([header] if header else []) + rows
        for ri, row in enumerate(allrows):
            cells = t.add_row().cells
            for ci, spec in enumerate(row):
                text, bold, indent = spec
                cells[ci].width = Inches(widths[ci])
                para = cells[ci].paragraphs[0]
                para.alignment = header_aligns[ci] if (header and ri == 0) else aligns[ci]
                pf = para.paragraph_format
                pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
                pf.space_after = Pt(spacing_after)
                pf.space_before = Pt(0)
                pf.first_line_indent = Inches(0)
                pf.left_indent = Inches(indent)
                r = para.add_run(text)
                set_font(r, size=size, bold=bold)
            if header and ri == 0:
                trPr = t.rows[0]._tr.get_or_add_trPr()
                th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
            cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true")
            t.rows[-1]._tr.get_or_add_trPr().append(cs)
        return t

    def contents_table(self):
        """CHAPTER | TITLE | PAGE NO, filled from the previous pass's measured entries (positions measured on the Sem 4 report)."""
        C, L = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT
        rows = []
        for e in self.prev:
            pg = e.get("page", "")
            if e["kind"] == "plain":
                rows.append([("", False, 0), (e["title"], False, 0), (pg, False, 0)])
            elif e["kind"] == "chapter":
                rows.append([(e["num"], True, 0), (e["title"], True, 0), (pg, False, 0)])
            elif e["kind"] == "h2":
                rows.append([("", False, 0), (f"{e['num']} {e['title']}", False, 0.14), (pg, False, 0)])
        header = [("CHAPTER", True, 0), ("TITLE", True, 0), ("PAGE NO", True, 0)]
        self._borderless([0.98, 4.4, 0.85], rows, 11, header=header, aligns=[C, L, C], spacing_after=11.8,
                         header_aligns=[C, C, C])

    def figures_table(self):
        """FIG. NO | FIGURE NAME | PAGE."""
        C, L = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT
        rows = [[(e["num"], False, 0), (e["title"], False, 0), (e.get("page", ""), False, 0)]
                for e in self.prev if e["kind"] == "fig"]
        header = [("FIG. NO", True, 0), ("FIGURE NAME", True, 0), ("PAGE", True, 0)]
        self._borderless([1.04, 4.4, 0.85], rows, 11, header=header, aligns=[L, L, C], spacing_after=11.8,
                         header_aligns=[C, C, C])

    # ───────────────────────── code ─────────────────────────
    def code(self, text, size=10):
        para = self.doc.add_paragraph()
        pf = para.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.space_after = Pt(8)
        pf.keep_together = len(text.splitlines()) < 28
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pPr = para._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        for side in ("top", "left", "bottom", "right"):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "4"); e.set(qn("w:color"), "8F9CAB")
            bdr.append(e)
        pPr.append(bdr)
        shade(pPr, "EEF3F8")
        lines = text.rstrip("\n").split("\n")
        for i, line in enumerate(lines):
            r = para.add_run(line.replace("\t", "    "))
            set_font(r, name="Courier New", size=size)
            if i < len(lines) - 1:
                r.add_break()

    # ───────────────────────── sections / numbering ─────────────────────────
    def new_section(self, number_format=None, start=1, footer=False):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        sect = sec._sectPr
        for old in sect.findall(qn("w:pgNumType")):
            sect.remove(old)
        if number_format:
            pg = OxmlElement("w:pgNumType")
            pg.set(qn("w:fmt"), number_format)
            pg.set(qn("w:start"), str(start))
            sect.append(pg)
        sec.footer.is_linked_to_previous = not footer
        if footer:
            fp = sec.footer.paragraphs[0]
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in list(fp.runs):
                r._r.getparent().remove(r._r)
            add_field(fp, "PAGE", "1", size=9)
        return sec

    def save(self, path):
        self.doc.save(str(path))
