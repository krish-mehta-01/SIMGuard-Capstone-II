# Report generator

Builds `SIMGuard Capstone Report.docx` / `.pdf` in the Sem 4 format (Times New Roman 14 pt, 1.5 spacing, CHAPTER | TITLE | PAGE NO
contents table, FIG. NO list, blue-grey code boxes). Every number in the text is read from `../prototype/results/*.json`.

```bash
python drawio_figs.py      # redraw the 8 diagrams: writes drawio/*.drawio (editable in diagrams.net) and figures/*.png
python build_report.py     # build the .docx, let Word measure page numbers for the contents / figure list, export the PDF
```

* Needs Microsoft Word (used through COM to measure page numbers and export the PDF) and Chrome (draw.io renders in headless Chrome).
* Placeholders (highlighted yellow in the document): `[MONTH YEAR]`, `[COURSE CODE]`, `[LEVEL]`, `[HOD NAME]`, `[SUPERVISOR NAME]`,
  `[QUALIFICATIONS]`, `[GUIDE NAME]`, `[PROJECT COORDINATOR NAME]`, `[DD-MM-YYYY]`. Edit them in `content_front.py` or directly in Word.
* If you edit text in Word, the contents table and figure list are plain tables, so renumber their page column by hand or re-run the build.
* To refresh the results: run the prototype's experiments (`python run_pipeline.py --all` in `../prototype`), then rebuild.
