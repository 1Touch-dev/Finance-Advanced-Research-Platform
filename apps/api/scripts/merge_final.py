"""Merge the best base report with all appendix supplements into final PDF."""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

report_dir = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "reports"

# Use 165707 as base (better company coverage - 12 companies)
base_file = report_dir / "PayPal_Mafia_EXPANDED_v2_20260804_165707.md"
base = base_file.read_text(encoding="utf-8")
print(f"Base (165707): {len(base.split())} words")

# Extract charts from 163106 (has 5 embedded charts)
import re
charts_file = report_dir / "PayPal_Mafia_EXPANDED_v2_20260804_163106.md"
charts_md = charts_file.read_text(encoding="utf-8")
chart_section_start = charts_md.find("## 9. Network Visualizations")
chart_section_end = charts_md.find("## 10. Methodology")
if chart_section_start > 0 and chart_section_end > chart_section_start:
    charts_content = charts_md[chart_section_start:chart_section_end]
    print(f"Charts section: {len(charts_content)} chars (with base64 images)")
else:
    charts_content = ""
    print("WARNING: Could not extract charts")

# Read FINAL which has the appendices (A through G)
final_file = report_dir / "PayPal_Mafia_FINAL_20260804_170907.md"
final = final_file.read_text(encoding="utf-8")

# Extract appendix content
appendix_start = final.find("## Appendix A:")
methodology_in_final = final.rfind("## 10. Methodology")
if appendix_start > 0 and methodology_in_final > appendix_start:
    appendix_content = final[appendix_start:methodology_in_final]
    print(f"Appendix content: {len(appendix_content.split())} words")
else:
    print("ERROR: Could not extract appendix content")
    appendix_content = ""

# Merge: base + charts + appendices, then methodology
marker = "## 10. Methodology"
if marker in base:
    parts = base.split(marker, 1)
    merged = parts[0] + "\n\n" + charts_content + "\n\n" + appendix_content + "\n\n" + marker + parts[1]
else:
    merged = base + "\n\n" + charts_content + "\n\n" + appendix_content

print(f"Merged: {len(merged.split())} words")

# Save
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
md_path = report_dir / f"PayPal_Mafia_COMPLETE_{ts}.md"
pdf_path = report_dir / f"PayPal_Mafia_COMPLETE_{ts}.pdf"
md_path.write_text(merged, encoding="utf-8")
print(f"Markdown saved: {md_path.name}")

# Render PDF
try:
    import markdown as md_lib
    from weasyprint import HTML
    import fitz

    html_body = md_lib.markdown(merged, extensions=["tables", "fenced_code", "toc"])
    css = """
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:40px;font-size:9.5px;line-height:1.45;color:#1a1a1a;}
h1{font-size:22px;border-bottom:3px solid #1e40af;padding-bottom:10px;color:#1e3a5f;page-break-before:always;}
h1:first-child{page-break-before:avoid;}
h2{font-size:15px;color:#1e40af;margin-top:22px;border-bottom:1.5px solid #dbeafe;padding-bottom:5px;page-break-after:avoid;}
h3{font-size:12px;color:#374151;margin-top:16px;page-break-after:avoid;}
h4{font-size:10.5px;color:#4b5563;margin-top:10px;}
table{border-collapse:collapse;width:100%;margin:6px 0;font-size:8.5px;page-break-inside:auto;}
th{background:#1e40af;color:white;padding:4px 6px;text-align:left;}
td{padding:3px 6px;border:1px solid #e5e7eb;}
tr:nth-child(even){background:#f9fafb;}
tr{page-break-inside:avoid;}
hr{border:none;border-top:2px solid #1e40af;margin:18px 0;}
img{max-width:100%;height:auto;margin:8px 0;page-break-inside:avoid;}
li{margin:2px 0;}
strong{color:#1e3a5f;}
p{margin:4px 0;}
@page{size:A4;margin:1.5cm;@bottom-center{content:counter(page);font-size:8px;color:#6b7280;}}
"""
    full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{html_body}</body></html>"
    HTML(string=full_html).write_pdf(str(pdf_path))
    doc = fitz.open(str(pdf_path))
    print(f"PDF: {pdf_path.name} ({doc.page_count} pages)")
    doc.close()
except Exception as e:
    print(f"PDF error: {e}")
    import traceback
    traceback.print_exc()

print("DONE")
