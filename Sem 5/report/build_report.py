"""Builds the Sem 5 capstone report (.docx) in the Sem 4 format and exports a PDF.

The contents table and list of figures are filled with page numbers measured by Microsoft Word: each heading / caption is
bookmarked, Word reports its page, and the document is rebuilt until the numbers stop changing.

    python build_report.py             full build
    python build_report.py --no-word   build the .docx only (page numbers left blank)
"""

import importlib
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from data import Data  # noqa: E402
from docx_kit import Report, roman  # noqa: E402

OUT_DIR = HERE / "output"
DOCX = OUT_DIR / "SIMGuard_Capstone_Report.docx"
PDF = OUT_DIR / "SIMGuard_Capstone_Report.pdf"
CHAPTERS = ["content_front", "content_ch1", "content_ch2", "content_ch3", "content_ch4", "content_ch5", "content_back"]


def build(prev, refs):
    r = Report(refs=refs, prev=prev)
    r.crest = HERE / "figures" / "crest.png"
    r.figdir = HERE / "figures"
    r.protodir = HERE.parent / "prototype"
    D = Data()
    for name in CHAPTERS:
        mod = importlib.import_module(name)
        importlib.reload(mod)
        mod.build(r, D)
    return r


class Word:
    def __enter__(self):
        import win32com.client as w32
        self.app = w32.Dispatch("Word.Application")
        self.app.Visible = False
        self.app.DisplayAlerts = 0
        return self

    def __exit__(self, *exc):
        self.app.Quit()

    def measure(self, docx_path, entries, pdf_path=None):
        doc = self.app.Documents.Open(str(docx_path))
        try:
            doc.Repaginate()
            out = []
            for e in entries:
                rng = doc.Bookmarks(e["bm"]).Range
                sec = rng.Sections(1).Index
                n = int(rng.Information(1))          # wdActiveEndAdjustedPageNumber
                out.append({**e, "page": "" if sec == 1 else roman(n) if sec == 2 else str(n)})
            pages = int(doc.ComputeStatistics(2))
            if pdf_path:
                doc.ExportAsFixedFormat(str(pdf_path), 17)
            return out, pages
        finally:
            doc.Close(False)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    no_word = "--no-word" in sys.argv
    prev, refs = [], {}
    pages = 0
    word = None if no_word else Word().__enter__()
    try:
        for it in range(1, 7):
            t = time.time()
            r = build(prev, refs)
            r.save(DOCX)
            if no_word:
                print("saved (no Word measurement)")
                return
            entries, pages = word.measure(DOCX, r.entries)
            stable = (it > 1 and [e["page"] for e in entries] == [e["page"] for e in prev]
                      and r.new_refs == refs and len(entries) == len(prev))
            print(f"pass {it}: {len(entries)} entries, {pages} pages, stable={stable} ({time.time() - t:.0f}s)")
            prev, refs = entries, r.new_refs
            if stable:
                break
        _, pages = word.measure(DOCX, prev, pdf_path=PDF)
        print(f"saved {DOCX}\nPDF   {PDF}  ({pages} pages)")
    finally:
        if word:
            word.__exit__()


if __name__ == "__main__":
    main()
