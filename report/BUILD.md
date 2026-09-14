# Build the technical report

The complete editable source is `report.tex`. It uses standard LaTeX packages and does not need a separate `.bib` file.

## Easiest option: Overleaf

1. Create a **Blank Project** in Overleaf.
2. Upload `report.tex` and name it `main.tex`, or change the project's main document to `report.tex`.
3. Select **pdfLaTeX** as the compiler and click **Recompile**. Compile twice so the contents page and cross-references update.
4. Download the resulting PDF and inspect every page before printing.

## Local option (Kali Linux)

Install a LaTeX distribution if one is not already present, then from this folder run:

```bash
pdflatex -interaction=nonstopmode -halt-on-error report.tex
pdflatex -interaction=nonstopmode -halt-on-error report.tex
```

If `pdflatex` reports a missing package, install the matching TeX Live package through your distribution's package manager or use Overleaf.

## Mandatory checks before hard-copy submission

- Verify the title-page roster with the actual team. This revised source includes all four members, including the project owner, and shows only roll numbers (not student-status labels).
- Confirm the course code: the course-outline slide says CSE-307, while the report instruction says CSE-308 Sessional. The source follows the requested CSE-308 title.
- Confirm the contribution statements against the team log; the supplied materials do not prove who did each task.
- The results table uses session `c4482580ced8`. Retain its CSV/JSON exports and screenshots. A later Kali terminal screenshot shows commit `235e343`, kernel `6.19.14+kali-amd64`, 3.8 GiB total RAM, and 33 passing tests, but the exports do not independently tie that checkout to the earlier session. The CSV and JSON row counts differ by a few records.
- Review the references and add access dates if your department requires them.
- Confirm that group names appear only on the title page in the generated PDF.
- Print A4, double-sided only if your department permits it, and check that tables and code remain readable.
