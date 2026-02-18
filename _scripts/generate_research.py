#!/usr/bin/env python3
"""
Generate research.qmd from the CV data files (publications.bib, other_writing.bib).

This script reuses the same .bib data that feeds the Typst CV, so adding a paper
to publications.bib automatically updates both the CV PDF and the website.

Run: python3 _scripts/generate_research.py
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# BibTeX parser (copied from cv/build.py to keep this standalone)
# ---------------------------------------------------------------------------

def parse_bib(path):
    """Parse a .bib file into a list of dicts."""
    text = Path(path).read_text(encoding="utf-8")
    entries = []
    i = 0
    while i < len(text):
        m = re.search(r"@(\w+)\s*\{", text[i:])
        if not m:
            break
        entry_type = m.group(1).lower()
        start = i + m.end()
        try:
            key_end = text.index(",", start)
        except ValueError:
            break
        key = text[start:key_end].strip()

        depth = 1
        j = key_end + 1
        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        if depth != 0:
            break

        body = text[key_end + 1 : j - 1]
        entry = parse_bib_fields(body)
        entry["_type"] = entry_type
        entry["_key"] = key
        entries.append(entry)
        i = j
    return entries


def parse_bib_fields(body):
    """Extract field = {value} pairs from bib entry body."""
    fields = {}
    pattern = re.compile(r"(\w+)\s*=\s*")
    pos = 0
    while pos < len(body):
        m = pattern.search(body, pos)
        if not m:
            break
        field_name = m.group(1).lower()
        val_start = m.end()
        while val_start < len(body) and body[val_start] in " \t\n":
            val_start += 1
        if val_start >= len(body):
            break

        if body[val_start] == "{":
            depth = 1
            k = val_start + 1
            while k < len(body) and depth > 0:
                if body[k] == "{":
                    depth += 1
                elif body[k] == "}":
                    depth -= 1
                k += 1
            value = body[val_start + 1 : k - 1]
            pos = k
        elif body[val_start] == '"':
            k = body.index('"', val_start + 1)
            value = body[val_start + 1 : k]
            pos = k + 1
        else:
            end = body.find(",", val_start)
            if end == -1:
                end = len(body)
            value = body[val_start:end].strip()
            pos = end

        value = clean_latex(value)
        if field_name == "pages":
            value = value.replace("--", "–")
        fields[field_name] = value
    return fields


def clean_latex(s):
    """Remove common LaTeX markup from a string."""
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\~\{([^}])\}", lambda m: m.group(1) + "\u0303", s)
    s = s.replace("\\~{n}", "ñ").replace("\\~n", "ñ")
    s = re.sub(r"\\'\{([^}])\}", lambda m: m.group(1) + "\u0301", s)
    s = re.sub(r'\\"\{([^}])\}', lambda m: m.group(1) + "\u0308", s)
    s = s.replace("\\&", "&")
    s = s.replace("{", "").replace("}", "")
    return s.strip()


def format_authors(entry):
    """Format author string for display."""
    if "authordisplay" in entry:
        return entry["authordisplay"]
    raw = entry.get("author", "")
    authors = [a.strip() for a in re.split(r"\s+and\s+", raw)]
    formatted = []
    for a in authors:
        if a.lower() == "others":
            formatted.append("others")
            continue
        formatted.append(a)
    if len(formatted) == 1:
        return formatted[0]
    elif len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    else:
        return ", ".join(formatted[:-1]) + ", and " + formatted[-1]


def get_url(entry):
    """Get the best URL for a publication.

    Prefers a local file (for the website) over DOI/URL links.
    """
    if "file" in entry and entry["file"]:
        return entry["file"]
    if "doi" in entry and entry["doi"]:
        return f"https://doi.org/{entry['doi']}"
    return entry.get("url", "")


def ends_punct(s):
    return s and s[-1] in ".?!–-"


def with_period(s):
    return s if ends_punct(s) else s + "."


# ---------------------------------------------------------------------------
# Categorization: driven by the `keywords` field in each .bib entry
# ---------------------------------------------------------------------------

# Mapping from keywords value -> internal category key
KEYWORD_TO_CATEGORY = {
    "methodology": "methodology",
    "aid-dev": "aid_development",
    "african-politics": "african_politics",
    "other": "other",
}


def categorize_article(entry):
    """Categorize an article by its `keywords` field. Falls back to aid_development."""
    kw = entry.get("keywords", "").strip().lower()
    return KEYWORD_TO_CATEGORY.get(kw, "aid_development")


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def format_article_md(entry):
    """Format a single article as markdown."""
    authors = format_authors(entry)
    year = entry.get("year", "")
    status = entry.get("status", "")
    title = entry.get("title", "")
    journal = entry.get("journal", "")
    volume = entry.get("volume", "")
    number = entry.get("number", "")
    pages = entry.get("pages", "")
    url = get_url(entry)
    note = entry.get("note", "")

    if status == "accepted":
        year_display = "(accepted)"
    else:
        year_display = f"({year})"

    # Build venue string
    venue_parts = []
    if journal:
        venue_parts.append(f"*{journal}*")
    if volume:
        vol_str = volume
        if number:
            vol_str += f"({number})"
        venue_parts.append(vol_str)
    if pages:
        venue_parts.append(pages)
    venue = ", ".join(venue_parts)

    # Title with link
    if url:
        title_md = f"[{title}]({url})"
    else:
        title_md = title

    line = f"{with_period(authors)} {year_display}. {title_md}. {with_period(venue)}"

    if note:
        line += f"\\\n*{note}*"

    return line


def format_chapter_md(entry):
    """Format a book chapter as markdown."""
    authors = format_authors(entry)
    year = entry.get("year", "")
    title = entry.get("title", "")
    booktitle = entry.get("booktitle", "")
    editor = entry.get("editor", "")
    pages = entry.get("pages", "")
    url = get_url(entry)

    if url:
        title_md = f"[{title}]({url})"
    else:
        title_md = title

    parts = [f"{with_period(authors)} ({year}). {title_md}"]
    if booktitle:
        book_str = f"in *{booktitle}*"
        if editor:
            book_str += f", edited by {editor}"
        if pages:
            book_str += f", pp. {pages}"
        parts.append(book_str)

    return with_period(" ".join(parts))


def format_wip_md(entry):
    """Format a work-in-progress entry."""
    authors = format_authors(entry)
    title = entry.get("title", "")
    url = get_url(entry)

    if url:
        title_md = f"[{title}]({url})"
    else:
        title_md = title

    return f"{with_period(authors)} {with_period(title_md)}"


def format_other_writing_md(entry):
    """Format an other writing entry."""
    authors = format_authors(entry)
    year = entry.get("year", "")
    title = entry.get("title", "")
    venue = entry.get("note", "")
    url = get_url(entry)

    if url:
        title_md = f"[{title}]({url})"
    else:
        title_md = title

    line = f"{with_period(authors)} ({year}). {title_md}."
    if venue:
        line += f" *{venue}*."
    return line


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    data_dir = project_root / "cv" / "data"
    output_path = project_root / "research.qmd"

    # Parse publications
    pub_bib = data_dir / "publications.bib"
    if not pub_bib.exists():
        print(f"ERROR: {pub_bib} not found", file=sys.stderr)
        sys.exit(1)

    entries = parse_bib(str(pub_bib))

    # Separate by type
    articles = [e for e in entries if e["_type"] == "article"]
    chapters = [e for e in entries if e["_type"] == "incollection"]
    wip = [e for e in entries if e["_type"] in ("unpublished", "manuscript", "workingpaper", "inprogress")
           or e.get("status") == "wip"]

    # Sort articles: accepted first, then by year descending
    def article_sort_key(e):
        y = int(e.get("year", "9999")) if e.get("year") else 9999
        return -y
    articles.sort(key=article_sort_key)

    # Categorize articles
    methodology = [a for a in articles if categorize_article(a) == "methodology"]
    aid_dev = [a for a in articles if categorize_article(a) == "aid_development"]
    african_pol = [a for a in articles if categorize_article(a) == "african_politics"]
    other_articles = [a for a in articles if categorize_article(a) == "other"]

    # Parse other writing — only include entries tagged with keywords = {website}
    other_bib = data_dir / "other_writing.bib"
    other_writing = []
    if other_bib.exists():
        other_entries = parse_bib(str(other_bib))
        other_writing = [e for e in other_entries if "website" in e.get("keywords", "").lower()]
        other_writing = sorted(other_writing, key=lambda e: -int(e.get("year", "0")))

    # Build the markdown
    lines = []
    lines.append("---")
    lines.append("title: \"Research\"")
    lines.append("---")
    lines.append("")
    lines.append("## Peer Reviewed Research")
    lines.append("")

    # Methodology
    lines.append("### Methodology")
    lines.append("")
    for a in methodology:
        lines.append(format_article_md(a))
        lines.append("")

    # Foreign Aid & Development Studies
    lines.append("### Foreign Aid & Development Studies")
    lines.append("")
    for a in aid_dev:
        lines.append(format_article_md(a))
        lines.append("")

    # African Politics
    lines.append("### African Politics")
    lines.append("")
    for a in african_pol:
        lines.append(format_article_md(a))
        lines.append("")

    # Other
    lines.append("### Other")
    lines.append("")
    for a in other_articles:
        lines.append(format_article_md(a))
        lines.append("")

    # Book Chapters
    if chapters:
        lines.append("### Book Chapters")
        lines.append("")
        for c in chapters:
            lines.append(format_chapter_md(c))
            lines.append("")

    # Work in Progress
    if wip:
        lines.append("## Work in Progress")
        lines.append("")
        for w in wip:
            lines.append(format_wip_md(w))
            lines.append("")

    # Other Writing
    if other_writing:
        lines.append("## Selected Other Writing")
        lines.append("")
        for w in other_writing:
            lines.append(format_other_writing_md(w))
            lines.append("")

    # Write output
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
