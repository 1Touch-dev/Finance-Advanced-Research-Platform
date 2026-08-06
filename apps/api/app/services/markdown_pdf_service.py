"""
Markdown to PDF converter with beautiful styling.

Uses WeasyPrint to convert markdown to beautifully formatted PDF reports
with professional styling suitable for enterprise intelligence reports.
"""
import io
import re
import markdown
from datetime import datetime
from typing import Optional

try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_OK = True
except ImportError:
    WEASYPRINT_OK = False

# Print stylesheet for the intelligence report.
#
# The design target is an institutional research note rather than a web page:
# a dark cover, a contents page with real page references, numbered sections,
# and dense rule-separated tables with right-aligned figures. The previous
# stylesheet used web conventions — heavy filled table headers, generous row
# padding, left-aligned numbers — which read as a dashboard and wasted roughly
# half of each page.
REPORT_CSS = """
:root {
    --navy: #12283F;
    --navy-deep: #0B1A2B;
    --ink: #14202E;
    --body: #253546;
    --muted: #64748B;
    --accent: #B45309;
    --rule: #D7DEE6;
    --rule-light: #EBEFF4;
    --tint: #F6F8FA;
    --neg: #A32020;
}

/* ── Page furniture ──────────────────────────────────────────────────── */
@page {
    size: letter;
    margin: 20mm 18mm 18mm 18mm;

    @top-left {
        content: string(doctitle);
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 7pt;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #8494A5;
        vertical-align: bottom;
        padding-bottom: 3mm;
    }
    @top-right {
        content: string(section);
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 7pt;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #8494A5;
        vertical-align: bottom;
        padding-bottom: 3mm;
    }
    @bottom-left {
        content: "Public records and open sources · Research only";
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 6.5pt;
        color: #9AA7B4;
    }
    @bottom-right {
        content: counter(page) " / " counter(pages);
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 7pt;
        font-weight: 600;
        color: var(--navy);
    }
}

/* The cover carries no running heads or folio. */
@page cover {
    margin: 0;
    @top-left { content: none; }
    @top-right { content: none; }
    @bottom-left { content: none; }
    @bottom-right { content: none; }
}

@page contents {
    @top-right { content: "Contents"; }
}

/* ── Base typography ─────────────────────────────────────────────────── */
body {
    font-family: Charter, Georgia, 'Times New Roman', serif;
    font-size: 9.4pt;
    line-height: 1.52;
    color: var(--body);
    margin: 0;
    padding: 0;
    -weasy-hyphens: auto;
    hyphens: auto;
    /* Break only long words, and never leave a stub of one or two letters. */
    -weasy-hyphenate-limit-chars: 8 4 4;
    hyphenate-limit-chars: 8 4 4;
    text-align: justify;
}

p { margin: 0 0 7pt 0; orphans: 2; widows: 2; }

a { color: var(--navy); text-decoration: none; border-bottom: 0.4pt solid #C3CEDA; }

strong { color: var(--ink); font-weight: 600; }

em { color: var(--muted); }

code {
    font-family: Menlo, Consolas, monospace;
    font-size: 8pt;
    background: var(--tint);
    padding: 0 2pt;
}

/* ── Figures ─────────────────────────────────────────────────────────── */
/* A chart is set to the text measure so it aligns with the tables around it,
   and is kept with its caption: a figure separated from its caption by a page
   break is unreadable, and both are unreadable if the chart splits. */
figure {
    margin: 11pt 0 13pt 0;
    page-break-inside: avoid;
    break-inside: avoid;
}

figure img {
    display: block;
    width: 100%;
    height: auto;
}

figure figcaption {
    margin-top: 4pt;
    padding-top: 3pt;
    border-top: 0.4pt solid var(--rule-light);
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 7pt;
    line-height: 1.4;
    color: var(--muted);
    text-align: left;
}

figure figcaption .fig-label {
    color: var(--accent);
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-right: 4pt;
}

/* ── Cover ───────────────────────────────────────────────────────────── */
.cover {
    page: cover;
    page-break-after: always;
    background: var(--navy-deep);
    color: #FFFFFF;
    height: 279.4mm;
    width: 215.9mm;
    padding: 26mm 22mm;
    box-sizing: border-box;
    text-align: left;
}
.cover-rule {
    width: 34mm;
    height: 2.4pt;
    background: var(--accent);
    margin-bottom: 9mm;
}
.cover-org {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 8pt;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #7E93A8;
    margin-bottom: 24mm;
}
.cover-entity {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 30pt;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: -0.015em;
    color: #FFFFFF;
    margin: 0 0 4mm 0;
}
.cover-ticker {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    font-weight: 500;
    letter-spacing: 0.10em;
    color: var(--accent);
    margin-bottom: 14mm;
}
.cover-kind {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 13pt;
    font-weight: 300;
    letter-spacing: 0.03em;
    color: #C8D4E0;
    padding-top: 5mm;
    border-top: 0.6pt solid #2C4257;
    margin-bottom: 16mm;
}
.cover-facts {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    margin-bottom: 8mm;
}
.cover-facts td {
    border: none;
    padding: 2.1mm 0;
    border-bottom: 0.4pt solid #24384B;
    vertical-align: baseline;
}
.cover-facts .k {
    font-size: 7.5pt;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: #7E93A8;
    width: 42mm;
}
.cover-facts .v {
    font-size: 9.5pt;
    color: #F2F6FA;
    font-weight: 500;
    text-align: left;
}
.cover-foot {
    position: absolute;
    bottom: 22mm;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 7.5pt;
    line-height: 1.6;
    color: #6D8296;
    text-align: left;
}
.cover-class {
    display: inline-block;
    font-size: 7pt;
    font-weight: 600;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--accent);
    border: 0.7pt solid var(--accent);
    padding: 1.6mm 3.4mm;
    margin-bottom: 5mm;
}

/* ── Contents ────────────────────────────────────────────────────────── */
.contents {
    page: contents;
    page-break-after: always;
}
.contents h2 {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 15pt;
    font-weight: 700;
    color: var(--navy);
    letter-spacing: -0.01em;
    margin: 0 0 8mm 0;
    padding: 0 0 3mm 0;
    border-bottom: 1.4pt solid var(--navy);
    counter-increment: none;
}
.contents h2::before { content: none; }
.contents ol { list-style: none; margin: 0; padding: 0; counter-reset: toc; }
.contents li {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 9.2pt;
    padding: 2.5mm 0;
    border-bottom: 0.4pt solid var(--rule-light);
    counter-increment: toc;
}
.contents li a {
    color: var(--ink);
    border: none;
    text-decoration: none;
}
.contents li a::before {
    content: counter(toc, decimal-leading-zero);
    color: var(--accent);
    font-weight: 700;
    font-size: 8pt;
    margin-right: 5mm;
}
.contents li a::after {
    content: target-counter(attr(href), page);
    float: right;
    color: var(--navy);
    font-weight: 600;
}

/* ── Headings ────────────────────────────────────────────────────────── */
h1 { display: none; }

h2 {
    string-set: section content();
    counter-increment: sec;
    counter-reset: sub;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 15pt;
    font-weight: 700;
    letter-spacing: -0.012em;
    color: var(--navy);
    margin: 11mm 0 5mm 0;
    padding-bottom: 2.6mm;
    border-bottom: 1.4pt solid var(--navy);
    page-break-after: avoid;
    page-break-before: auto;
    text-align: left;
}
h2::before {
    content: counter(sec) ". ";
    color: var(--accent);
}

h3 {
    counter-increment: sub;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 10.2pt;
    font-weight: 600;
    color: var(--ink);
    margin: 7mm 0 2.6mm 0;
    page-break-after: avoid;
    text-align: left;
}
h3::before {
    content: counter(sec) "." counter(sub) "  ";
    color: var(--muted);
    font-weight: 500;
}

h4 {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--muted);
    margin: 5mm 0 2mm 0;
    page-break-after: avoid;
    text-align: left;
}

/* A paragraph that is only bold text acts as a sub-label (director names,
   matter captions). Keep it with the prose that follows it. */
p.label {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 9.4pt;
    font-weight: 600;
    color: var(--ink);
    margin: 5mm 0 1.4mm 0;
    page-break-after: avoid;
    text-align: left;
}

/* ── Tables ──────────────────────────────────────────────────────────── */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 3.5mm 0 6mm 0;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 8.2pt;
    font-variant-numeric: tabular-nums;
    page-break-inside: auto;
    /* Column headings are short phrases; hyphenating them produced
       "REVEN-UE" and "NET IN-COME". */
    -weasy-hyphens: none;
    hyphens: none;
    text-align: left;
}

thead { display: table-header-group; }

th {
    font-size: 6.9pt;
    font-weight: 700;
    letter-spacing: 0.085em;
    text-transform: uppercase;
    color: var(--navy);
    background: transparent;
    text-align: left;
    padding: 0 3mm 1.8mm 0;
    border-bottom: 1pt solid var(--navy);
    vertical-align: bottom;
}

td {
    padding: 1.7mm 3mm 1.7mm 0;
    border-bottom: 0.35pt solid var(--rule-light);
    color: var(--body);
    vertical-align: top;
    text-align: left;
}

th:last-child, td:last-child { padding-right: 0; }

tbody tr:last-child td { border-bottom: 0.7pt solid var(--rule); }

/* Figures read down a column, so they are right-aligned and set in
   tabular figures. Detected per column at build time. */
th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; }
td.neg { color: var(--neg); }

/* A row whose first cell is bold is a total. */
tr.total td {
    font-weight: 700;
    color: var(--ink);
    border-top: 0.7pt solid var(--navy);
    border-bottom: none;
    background: var(--tint);
}

table.compact td { padding-top: 1.1mm; padding-bottom: 1.1mm; }

/* Keep short tables whole; let long ones break across pages. */
table.short { page-break-inside: avoid; }

/* ── Lists ───────────────────────────────────────────────────────────── */
ul, ol { margin: 0 0 6pt 0; padding-left: 5mm; }
li { margin-bottom: 2.4pt; padding-left: 1mm; }
ul li::marker { color: var(--accent); }
ol li::marker { color: var(--accent); font-weight: 600; font-size: 8.5pt; }

/* ── Rules and callouts ──────────────────────────────────────────────── */
hr {
    border: none;
    border-top: 0.5pt solid var(--rule);
    margin: 7mm 0;
}

blockquote {
    margin: 4mm 0;
    padding: 3mm 0 3mm 5mm;
    border-left: 2pt solid var(--accent);
    color: var(--ink);
    font-style: normal;
}

/* Source attributions set in italics at the end of a block. */
em.source, p em:only-child {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 7.6pt;
    color: var(--muted);
    font-style: normal;
}

/* Accession numbers, docket numbers and award identifiers are provenance,
   not argument: they should be findable without interrupting the sentence. */
span.ref {
    font-family: Menlo, Consolas, monospace;
    font-size: 7pt;
    color: #8494A5;
    -weasy-hyphens: none;
    hyphens: none;
}
"""


_NUMERIC_CELL = re.compile(
    r"^[\s]*[-+(]?\s*(?:US)?\$?\s*\d[\d,\.]*\s*"
    r"(?:%|x|bn|m|k|M|B|T|K|days?)?\s*\)?[\s]*$"
)
_DASH = {"—", "-", "–", "n/m", "N/A", ""}


def _looks_numeric(text: str) -> bool:
    text = (text or "").strip()
    if text in _DASH:
        return True          # a gap in a figure column is still a figure column
    return bool(_NUMERIC_CELL.match(text))


def _style_tables(soup) -> None:
    """Right-align figure columns and mark total rows.

    Markdown carries no column alignment, so it is inferred: a column whose
    data cells are predominantly numeric is a figure column. Left-aligned
    figures are the single clearest sign of a document that was laid out by a
    web template rather than typeset.
    """
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        body_rows = [r for r in rows if r.find_all("td")]
        headers = rows[0].find_all(["th", "td"])
        width = len(headers)

        for col in range(width):
            values, filled = [], 0
            for row in body_rows:
                cells = row.find_all("td")
                if col < len(cells):
                    text = cells[col].get_text(strip=True)
                    values.append(text)
                    if text.strip() not in _DASH:
                        filled += 1
            if not values or not filled:
                continue
            numeric = sum(1 for v in values if _looks_numeric(v))
            # The first column is the row label even when it holds a year.
            if col > 0 and numeric / len(values) >= 0.8:
                if col < len(headers):
                    headers[col]["class"] = headers[col].get("class", []) + ["num"]
                for row in body_rows:
                    cells = row.find_all("td")
                    if col < len(cells):
                        cells[col]["class"] = cells[col].get("class", []) + ["num"]

        # A row whose label is entirely bold is a total or subtotal.
        for row in body_rows:
            first = row.find("td")
            if first and first.find("strong") and first.get_text(strip=True):
                if first.get_text(strip=True) == first.find("strong").get_text(strip=True):
                    row["class"] = row.get("class", []) + ["total"]

        # Short tables are kept whole; longer ones may break, with the header
        # repeating. Holding a large table together pushed it to the next page
        # and left a third of the previous one empty.
        if len(body_rows) <= 7:
            table["class"] = table.get("class", []) + ["short"]


def _mark_labels(soup) -> None:
    """Tag paragraphs that are wholly bold so they set as sub-headings."""
    for p in soup.find_all("p"):
        strong = p.find("strong")
        if not strong:
            continue
        if p.get_text(strip=True) == strong.get_text(strip=True):
            p["class"] = p.get("class", []) + ["label"]


_REFERENCE = re.compile(
    r"\b(\d{10}-\d{2}-\d{6}"          # EDGAR accession number
    # Federal docket number, including the judge initials a court appends to
    # it — 4:18-cv-07669-HSG is one identifier and breaks if split.
    r"|\d{1,2}:\d{2}-[a-z]{2}-\d{3,6}(?:-[A-Z]{2,4})?"
    r"|\d{4}-\d{3,4}-[A-Z]{3,4}"        # Delaware Chancery case number
    r"|[A-Z0-9]{6,}-\d{2}-[A-Z0-9-]{4,})\b"  # federal award identifier
)


def _style_references(soup) -> None:
    """Set identifiers in monospace so they read as citations, not prose."""
    from bs4 import NavigableString
    for node in list(soup.find_all(string=_REFERENCE.search)):
        if node.parent.name in ("code", "a", "span", "th"):
            continue
        pieces, last = [], 0
        for match in _REFERENCE.finditer(node):
            if match.start() > last:
                pieces.append(NavigableString(node[last:match.start()]))
            span = soup.new_tag("span")
            span["class"] = "ref"
            span.string = match.group(0)
            pieces.append(span)
            last = match.end()
        if last < len(node):
            pieces.append(NavigableString(node[last:]))
        node.replace_with(*pieces)


def _build_figures(soup, doc) -> int:
    """Wrap each chart and the italic line under it in a numbered <figure>.

    Markdown has no figure syntax, so the report emits an image paragraph
    followed by an italic caption paragraph. Pairing them here is what lets the
    two be kept on one page — a caption stranded at the top of the next page
    describes a chart the reader can no longer see.
    """
    count = 0
    for image in soup.find_all("img"):
        holder = image.parent
        if holder is None or holder.name != "p":
            continue
        count += 1
        figure = doc.new_tag("figure")
        holder.insert_before(figure)
        figure.append(image.extract())

        caption = holder.find_next_sibling()
        text = ""
        if caption is not None and caption.name == "p":
            only_child = caption.find("em")
            if only_child is not None and caption.get_text(strip=True) == \
                    only_child.get_text(strip=True):
                text = only_child.get_text()
                caption.decompose()

        figcaption = doc.new_tag("figcaption")
        label = doc.new_tag("span")
        label["class"] = "fig-label"
        label.string = f"Figure {count}"
        figcaption.append(label)
        figcaption.append(text)
        figure.append(figcaption)
        holder.decompose()
    return count


def _build_contents(soup, doc):
    """Contents page listing every section with its real page number.

    Page references resolve at layout time through target-counter, so they stay
    correct as content shifts between runs.
    """
    sections = [h for h in soup.find_all("h2") if h.get("id")]
    if len(sections) < 3:
        return None
    nav = doc.new_tag("div")
    nav["class"] = "contents"
    heading = doc.new_tag("h2")
    heading.string = "Contents"
    nav.append(heading)
    ordered = doc.new_tag("ol")
    for h in sections:
        li = doc.new_tag("li")
        link = doc.new_tag("a", href=f"#{h['id']}")
        link.string = h.get_text()
        li.append(link)
        ordered.append(li)
    nav.append(ordered)
    return nav


def _build_cover(soup, doc, entity: str, ticker: str, subtitle: str):
    """Cover page assembled from the report's own front matter.

    The identity table and the classification line are lifted out of the body
    so they are not repeated once they appear on the cover.
    """
    cover = doc.new_tag("div")
    cover["class"] = "cover"

    rule = doc.new_tag("div"); rule["class"] = "cover-rule"; cover.append(rule)
    org = doc.new_tag("div"); org["class"] = "cover-org"
    org.string = "Enterprise Intelligence Platform"
    cover.append(org)

    name = doc.new_tag("div"); name["class"] = "cover-entity"
    name.string = entity
    cover.append(name)

    if ticker:
        tick = doc.new_tag("div"); tick["class"] = "cover-ticker"
        tick.string = ticker
        cover.append(tick)

    kind = doc.new_tag("div"); kind["class"] = "cover-kind"
    kind.string = subtitle or "Intelligence Report"
    cover.append(kind)

    # The entity identity table is the first table in the document.
    identity = soup.find("table")
    facts = []
    if identity:
        for row in identity.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key.lower() not in ("field", "") and value:
                    facts.append((key, value))
        identity.decompose()
    if facts:
        table = doc.new_tag("table"); table["class"] = "cover-facts"
        for key, value in facts:
            tr = doc.new_tag("tr")
            k = doc.new_tag("td"); k["class"] = "k"; k.string = key
            v = doc.new_tag("td"); v["class"] = "v"; v.string = value
            tr.append(k); tr.append(v); table.append(tr)
        cover.append(table)

    foot = doc.new_tag("div"); foot["class"] = "cover-foot"
    badge = doc.new_tag("div"); badge["class"] = "cover-class"
    badge.string = "Internal use only — not for distribution"
    foot.append(badge)
    note = doc.new_tag("div")
    note.string = (
        f"Prepared {datetime.now().strftime('%d %B %Y')} from public records and "
        f"open sources. Research use only — not legal, investment, or tax advice."
    )
    foot.append(note)
    cover.append(foot)
    return cover


def _strip_front_matter(soup) -> tuple:
    """Remove the markdown front matter the cover now carries.

    Returns the entity name, ticker and report kind read out of it.
    """
    entity, ticker, subtitle = "", "", ""
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        for sep in ("—", "–", "-"):
            if sep in text:
                entity, subtitle = [p.strip() for p in text.split(sep, 1)]
                break
        else:
            entity = text
        h1.decompose()

    # The classification block is a single paragraph of bold key/value pairs.
    for p in soup.find_all("p")[:3]:
        text = p.get_text(" ", strip=True)
        if "Classification:" in text or "Report Date:" in text:
            match = re.search(r"Ticker:\s*([A-Za-z:\. ]+)", text)
            if match:
                ticker = match.group(1).strip()
            p.decompose()
            break

    # A horizontal rule closed the front matter.
    first_hr = soup.find("hr")
    if first_hr and not first_hr.find_previous("h2"):
        first_hr.decompose()

    return entity, ticker, subtitle


def convert_markdown_to_pdf(
    markdown_content: str,
    output_path: Optional[str] = None,
    title: str = "Intelligence Report"
) -> bytes:
    """
    Render report markdown as a typeset PDF.

    The markdown is the single source of truth for content; everything here is
    presentation. A cover and contents page are synthesised from the document's
    own front matter, sections are numbered, and figure columns are detected
    and right-aligned.

    Args:
        markdown_content: The markdown text to convert
        output_path: Optional path to save the PDF file
        title: Document title for metadata and the running head

    Returns:
        PDF bytes
    """
    if not WEASYPRINT_OK:
        raise RuntimeError("WeasyPrint is not installed. Run: pip install weasyprint")

    md = markdown.Markdown(
        extensions=['tables', 'fenced_code', 'codehilite', 'toc', 'attr_list',
                    'md_in_html']
    )
    body_html = md.convert(markdown_content)

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(body_html, "html.parser")
        entity, ticker, subtitle = _strip_front_matter(soup)
        cover = _build_cover(soup, soup, entity or title, ticker, subtitle)
        contents = _build_contents(soup, soup)
        _build_figures(soup, soup)
        _style_tables(soup)
        _mark_labels(soup)
        _style_references(soup)
        parts = [str(cover)]
        if contents:
            parts.append(str(contents))
        parts.append(str(soup))
        body_html = "".join(parts)
        running_title = entity or title
    except ImportError:
        running_title = title

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        html {{ counter-reset: sec; }}
        body {{ string-set: doctitle "{running_title}"; }}
    </style>
</head>
<body>
{body_html}
</body>
</html>"""

    font_config = FontConfiguration()
    html = HTML(string=full_html)
    css = CSS(string=REPORT_CSS, font_config=font_config)

    if output_path:
        html.write_pdf(output_path, stylesheets=[css], font_config=font_config)
        with open(output_path, 'rb') as f:
            return f.read()
    return html.write_pdf(stylesheets=[css], font_config=font_config)

def _clean_news_text(text: str) -> str:
    """Clean news text by removing JSON metadata and URLs."""
    import re
    if not text:
        return ''
    # Remove JSON array/dict at the end (e.g., [{'name': 'Mashable', ...}])
    clean = re.sub(r"\s*\[\{['\"]name['\"].*$", "", text, flags=re.DOTALL)
    # Remove trailing URLs
    clean = re.sub(r"\s*https?://\S+\s*$", "", clean)
    # Remove [DOCUMENTED] etc tags
    clean = re.sub(r"\[(DOCUMENTED|REPORTED|ANALYTICAL)\]\s*", "", clean)
    return clean.strip()


def _parse_news_headline(text: str) -> tuple:
    """Parse news headline, source, and date from text."""
    import re
    if not text:
        return '', 'Unknown', ''

    # First clean the text of JSON metadata and trailing URLs
    clean_text = _clean_news_text(text)

    # Pattern 1: "Headline - Source (ISO datetime)" e.g., "Title - CNN (2026-07-19T22:40:14.000Z)"
    match = re.match(r'^(.+?) - ([^(]+) \((\d{4}-\d{2}-\d{2})(?:T[\d:.]+Z?)?\)', clean_text)
    if match:
        headline = match.group(1).strip()
        source = match.group(2).strip()
        date = match.group(3)  # Just the YYYY-MM-DD part
        return headline, source, date

    # Pattern 2: "Headline - Source (simple date)" e.g., "Title - CNN (2026-07-19)"
    match = re.match(r'^(.+?) - ([^(]+) \((\d{4}-\d{2}-\d{2})\)', clean_text)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3)

    # Pattern 3: Just "Headline - Source" without date
    match = re.match(r'^(.+?) - (.+)$', clean_text)
    if match:
        return match.group(1).strip(), match.group(2).strip(), ''

    # Fallback: return cleaned text as headline
    return clean_text[:100] if clean_text else text[:100], 'Unknown', ''


def generate_enhanced_markdown_report(report_data: dict) -> str:
    """
    Generate a comprehensive markdown report from enhanced intelligence data.

    Args:
        report_data: The enhanced report dictionary

    Returns:
        Markdown formatted string
    """
    import re
    md = []

    # Use `or` (not dict.get's default arg) — these keys are often present
    # with an explicit None value (e.g. non-enhanced reports, older reports),
    # and .get(key, default) only falls back when the key is MISSING entirely.
    entity_name = report_data.get('entity_name') or 'Unknown Entity'
    ticker = report_data.get('ticker') or ''
    report_id = report_data.get('report_id') or ''
    gen_at = report_data.get('generated_at') or datetime.utcnow().isoformat()

    # Title
    ticker_str = f" ({ticker})" if ticker else ""
    md.append(f"# {entity_name}{ticker_str} — Enhanced Intelligence Report")
    md.append("")
    md.append(f"**Generated:** {gen_at[:19].replace('T', ' ')} UTC")
    md.append(f"**Report ID:** {report_id}")
    md.append(f"**Classification:** CONFIDENTIAL — Enterprise Intelligence Platform")
    md.append("")
    md.append("---")
    md.append("")

    # Executive Dashboard
    summary = report_data.get('summary') or {}
    investment_thesis = report_data.get('investment_thesis') or {}
    risk_matrix = report_data.get('risk_matrix') or {}
    financial_health = report_data.get('financial_health') or {}

    md.append("## Executive Dashboard")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")

    if investment_thesis:
        rec = investment_thesis.get('recommendation', 'N/A')
        conv = investment_thesis.get('conviction', 'N/A')
        md.append(f"| **Investment Recommendation** | **{rec}** ({conv} conviction) |")

    if financial_health:
        grade = financial_health.get('grade', 'N/A')
        md.append(f"| **Financial Health Grade** | **{grade}** |")

    if risk_matrix:
        score = risk_matrix.get('overall_score', 'N/A')
        md.append(f"| **Overall Risk Score** | **{score}/100** |")

    md.append(f"| SEC Filings Analyzed | {summary.get('sec_filings', 0)} |")
    md.append(f"| Government Contracts | {summary.get('contracts_found', 0)} (${summary.get('total_obligated_usd', 0):,.0f}) |")
    md.append(f"| Lobbying Filings | {summary.get('lobbying_filings', 0)} |")
    md.append(f"| News Articles | {summary.get('news_articles', 0)} |")
    md.append("")
    md.append("---")
    md.append("")

    # Process sections
    sections = report_data.get('sections') or []

    # Extract key sections
    section_map = {sec.get('name', ''): sec for sec in sections}

    # Investment Thesis
    if 'Investment Thesis' in section_map:
        sec = section_map['Investment Thesis']
        text = sec.get('claims', [{}])[0].get('text', '')
        if text:
            md.append("## Investment Thesis")
            md.append("")
            md.append(text)
            md.append("")
            md.append("---")
            md.append("")

    # Executive Summary
    if 'Executive Summary' in section_map:
        sec = section_map['Executive Summary']
        text = sec.get('claims', [{}])[0].get('text', '')
        if text:
            md.append("## Executive Summary")
            md.append("")
            md.append(text)
            md.append("")
            md.append("---")
            md.append("")

    # SWOT Analysis
    swot = report_data.get('swot_analysis') or {}
    if swot:
        md.append("## SWOT Analysis")
        md.append("")

        md.append("### Strengths")
        md.append("")
        for i, s in enumerate(swot.get('strengths', [])[:7], 1):
            if isinstance(s, dict):
                desc = s.get('description', '')
                if desc:
                    md.append(f"{i}. **{desc}**")
                    if s.get('evidence'):
                        md.append(f"   - Evidence: {s['evidence'][:150]}...")
                    if s.get('impact'):
                        md.append(f"   - Impact: {s['impact']}/5")
                    md.append("")

        md.append("### Weaknesses")
        md.append("")
        for i, w in enumerate(swot.get('weaknesses', [])[:7], 1):
            if isinstance(w, dict) and w.get('description'):
                md.append(f"{i}. **{w['description']}**")
                md.append("")

        md.append("### Opportunities")
        md.append("")
        for i, o in enumerate(swot.get('opportunities', [])[:7], 1):
            if isinstance(o, dict) and o.get('description'):
                md.append(f"{i}. **{o['description']}**")
                md.append("")

        md.append("### Threats")
        md.append("")
        for i, t in enumerate(swot.get('threats', [])[:7], 1):
            if isinstance(t, dict) and t.get('description'):
                md.append(f"{i}. **{t['description']}**")
                md.append("")

        if swot.get('synthesis'):
            md.append("### Strategic Synthesis")
            md.append("")
            md.append(swot['synthesis'])
            md.append("")

        md.append("---")
        md.append("")

    # Risk Matrix
    if risk_matrix:
        md.append("## Risk Assessment Matrix")
        md.append("")
        md.append(f"**Overall Risk Score:** {risk_matrix.get('overall_score', 0)}/100")
        md.append("")
        md.append("### Risk Distribution")
        md.append("")
        md.append(f"- **Critical Risks:** {len(risk_matrix.get('critical_risks', []))}")
        md.append(f"- **High Risks:** {len(risk_matrix.get('high_risks', []))}")
        md.append(f"- **Medium Risks:** {len(risk_matrix.get('medium_risks', []))}")
        md.append(f"- **Low Risks:** {len(risk_matrix.get('low_risks', []))}")
        md.append("")

        top_risks = risk_matrix.get('top_priority_risks', [])
        if top_risks:
            md.append("### Top Priority Risks")
            md.append("")
            md.append("| ID | Risk | Category | Severity | Likelihood | Score |")
            md.append("|:--:|------|----------|:--------:|:----------:|:-----:|")
            for risk in top_risks[:5]:
                desc = risk.get('description', '')[:60]
                md.append(f"| {risk.get('id', '-')} | {desc}... | {risk.get('category', '')} | {risk.get('severity', '')}/5 | {risk.get('likelihood', '')}/5 | **{risk.get('score', '')}** |")
            md.append("")

        md.append("---")
        md.append("")

    # Financial Health
    if 'Financial Health Summary' in section_map:
        sec = section_map['Financial Health Summary']
        text = sec.get('claims', [{}])[0].get('text', '')
        if text:
            md.append("## Financial Health Summary")
            md.append("")
            if financial_health:
                md.append(f"### Overall Grade: {financial_health.get('grade', 'N/A')}")
                md.append("")
            md.append(text)
            md.append("")
            md.append("---")
            md.append("")

    # Competitive Analysis
    if 'Competitive Analysis' in section_map:
        sec = section_map['Competitive Analysis']
        text = sec.get('claims', [{}])[0].get('text', '')
        if text:
            md.append("## Competitive Analysis")
            md.append("")
            md.append(text)
            md.append("")
            md.append("---")
            md.append("")

    # Government Contracts
    for sec in sections:
        if 'Government Contracts' in sec.get('name', ''):
            data = sec.get('data', {})
            claims = sec.get('claims', [])

            md.append("## Government Contracts & Procurement")
            md.append("")
            md.append(f"**Total Obligated:** ${data.get('total_obligated_usd', 0):,.0f}")
            md.append(f"**Award Count:** {data.get('award_count', 0)}")
            md.append("")
            md.append("### Contract Details")
            md.append("")

            for claim in claims[:12]:
                text = claim.get('text', '')
                if text:
                    md.append(f"- {text[:200]}")
            md.append("")
            md.append("---")
            md.append("")
            break

    # Lobbying Activity
    for sec in sections:
        if 'Lobbying' in sec.get('name', ''):
            data = sec.get('data', {})

            md.append("## Lobbying Activity")
            md.append("")
            md.append(f"**Total Filings:** {data.get('total_lobbying_filings', 0)}")
            md.append(f"**As Registrant:** {data.get('as_registrant_count', 0)}")
            md.append("")
            md.append("### Issue Areas")
            md.append("")
            for area in data.get('issue_areas', [])[:10]:
                md.append(f"- {area}")
            md.append("")
            md.append("---")
            md.append("")
            break

    # News - with clean formatting
    for sec in sections:
        if 'News' in sec.get('name', ''):
            claims = sec.get('claims', [])
            if claims:
                md.append("## Recent News & Media Coverage")
                md.append("")
                md.append("| Date | Headline | Source |")
                md.append("|------|----------|--------|")
                for claim in claims[:12]:
                    text = claim.get('text', '')
                    if text:
                        headline, source, date = _parse_news_headline(text)
                        if headline:
                            md.append(f"| {date} | {headline[:70]}... | {source} |")
                md.append("")
                md.append("---")
                md.append("")
            break

    # Social Media
    for sec in sections:
        if 'Social Media' in sec.get('name', ''):
            data = sec.get('data', {})
            twitter = data.get('twitter', {})
            instagram = data.get('instagram', {})
            youtube = data.get('youtube', {})

            md.append("## Social Media Footprint")
            md.append("")
            md.append("| Platform | Handle | Followers | Posts/Videos |")
            md.append("|----------|--------|----------:|-------------:|")
            if twitter:
                md.append(f"| Twitter/X | @{twitter.get('username', 'N/A')} | {(twitter.get('followers') or 0):,} | {twitter.get('tweets_count', 'N/A')} |")
            if instagram:
                md.append(f"| Instagram | @{instagram.get('username', 'N/A')} | {(instagram.get('followers') or 0):,} | {instagram.get('posts_count', 'N/A')} |")
            if youtube:
                md.append(f"| YouTube | {youtube.get('channel_name', 'N/A')} | {(youtube.get('subscribers') or 0):,} | {youtube.get('video_count', 'N/A')} |")
            md.append("")
            md.append("---")
            md.append("")
            break

    # Data Sources
    ds = report_data.get('data_sources') or {}
    md.append("## Data Sources & Methodology")
    md.append("")
    md.append("This report was generated using the following data sources:")
    md.append("")

    sources = []
    if ds.get('wikipedia'): sources.append("Wikipedia REST API")
    if ds.get('sec_investors'): sources.append(f"SEC EDGAR ({ds.get('sec_investors', 0)} investor filings)")
    if ds.get('yfinance'): sources.append("Yahoo Finance (fundamentals)")
    if ds.get('valuation'): sources.append("DCF Valuation Model")
    if ds.get('technicals'): sources.append("Technical Analysis Indicators")
    if ds.get('apify_news'): sources.append(f"Google News via Apify ({ds.get('apify_news', 0)} articles)")
    if ds.get('enhanced_narrative'): sources.append("GPT-4o-mini (AI analysis)")

    for src in sources:
        md.append(f"- {src}")
    md.append("")

    # Footer
    md.append("---")
    md.append("")
    md.append("## Classification & Disclaimer")
    md.append("")
    md.append("**CONFIDENTIAL** — This document contains proprietary intelligence analysis.")
    md.append("")
    md.append("*Generated by Enterprise Intelligence Platform*")
    md.append(f"*Report ID: {report_id} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*")

    return '\n'.join(md)
