"""Render report/report.md to report/report.pdf (A4) with a headless Edge or Chrome.

  pip install markdown
  python report/build_pdf.py
"""
import re
import subprocess
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",  # Edge here exits 0 without writing the PDF
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "/usr/bin/google-chrome", "/usr/bin/chromium"]
CSS = """
@page { size: A4; margin: 13mm 14mm; }
body { font: 9.6pt/1.38 "Segoe UI", "Nirmala UI", Arial, sans-serif; color: #1a1a1a; }
h1 { font-size: 16pt; margin: 0 0 4px; }
h2 { font-size: 12pt; margin: 12px 0 4px; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
p, ul { margin: 4px 0; }
li { margin: 1px 0; }
table { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 8.6pt; page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 2px 5px; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
code { font: 8.6pt Consolas, monospace; background: #f4f4f4; padding: 0 2px; }
"""

def github_lists(text):
    """Python-Markdown needs a blank line before a list and 4-space nesting; GitHub needs neither."""
    out, prev = [], ""
    for line in text.splitlines():
        line = re.sub(r"^((?:  )+)(- )", lambda m: "    " * (len(m[1]) // 2) + m[2], line)
        if re.match(r"\s*- ", line) and prev.strip() and not re.match(r"\s*- ", prev):
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


body = markdown.markdown(github_lists((HERE / "report.md").read_text(encoding="utf-8")),
                         extensions=["tables", "fenced_code"])
out = HERE / "report.pdf"
out.unlink(missing_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    page = Path(tmp) / "report.html"
    page.write_text(f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>{body}", encoding="utf-8")
    browser = next(b for b in BROWSERS if Path(b).exists())
    # own profile dir: otherwise an already-open browser takes the job and the PDF never appears
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tmp}/profile",
                    f"--print-to-pdf={out}", page.as_uri()], check=True, capture_output=True, timeout=120)
if not out.exists():
    raise SystemExit("PDF was not written; check the browser path")
print("wrote", out)
