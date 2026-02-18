#!/usr/bin/env python3
"""
CV Build Script
Preprocesses CSV and .bib data files into JSON for Typst consumption.
Then compiles the Typst document to PDF.

Usage:
    python3 build.py              # Full CV
    python3 build.py --years 5    # Last 5 years only
    python3 build.py --output cv-short.pdf --years 5
"""

import csv
import json
import re
import os
import sys
import argparse
import shutil
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# BibTeX parser (simple, handles the .bib format we produce)
# ---------------------------------------------------------------------------

def parse_bib(path):
    """Parse a .bib file into a list of dicts."""
    text = Path(path).read_text(encoding="utf-8")
    entries = []

    # Match each @type{key, ... } block
    # We track brace depth to find the matching close brace
    i = 0
    while i < len(text):
        m = re.search(r"@(\w+)\s*\{", text[i:])
        if not m:
            break
        entry_type = m.group(1).lower()
        start = i + m.end()  # position right after the opening {

        # Find key (everything up to first comma)
        try:
            key_end = text.index(",", start)
        except ValueError:
            line_num = text[:start].count("\n") + 1
            raise ValueError(
                f"{path}: malformed entry near line {line_num} — "
                f"expected a comma after @{entry_type}{{key"
            )
        key = text[start:key_end].strip()

        # Find matching closing brace
        depth = 1
        j = key_end + 1
        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1

        if depth != 0:
            raise ValueError(
                f"{path}: unmatched braces in entry @{entry_type}{{{key}}}"
            )

        body = text[key_end + 1 : j - 1]
        try:
            entry = parse_bib_fields(body)
        except Exception as exc:
            raise ValueError(
                f"{path}: error parsing fields of @{entry_type}{{{key}}}: {exc}"
            ) from exc
        entry["_type"] = entry_type
        entry["_key"] = key
        entries.append(entry)
        i = j

    return entries


def parse_bib_fields(body):
    """Extract field = {value} pairs from bib entry body."""
    fields = {}
    # Match field = {value} or field = "value"
    # Handle nested braces in values
    pattern = re.compile(r"(\w+)\s*=\s*")
    pos = 0
    while pos < len(body):
        m = pattern.search(body, pos)
        if not m:
            break
        field_name = m.group(1).lower()
        val_start = m.end()

        # Skip whitespace
        while val_start < len(body) and body[val_start] in " \t\n":
            val_start += 1

        if val_start >= len(body):
            break

        if body[val_start] == "{":
            # Find matching }
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
            # Find matching "
            k = body.index('"', val_start + 1)
            value = body[val_start + 1 : k]
            pos = k + 1
        else:
            # Bare value (number or macro)
            end = body.find(",", val_start)
            if end == -1:
                end = len(body)
            value = body[val_start:end].strip()
            pos = end

        # Clean up LaTeX commands in value
        value = clean_latex(value)
        fields[field_name] = value

    # Convert BibTeX page ranges -- to en-dash –
    if "pages" in fields:
        fields["pages"] = fields["pages"].replace("--", "–")

    return fields


def clean_latex(s):
    """Remove common LaTeX markup from a string."""
    # \textit{...} -> ...
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    # \textbf{...} -> ...
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    # \emph{...} -> ...
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    # \href{url}{text} -> text
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    # Special chars: \~{n} -> ñ, \'{e} -> é, \"{u} -> ü
    s = re.sub(r"\\~\{([^}])\}", lambda m: m.group(1) + "\u0303", s)  # tilde
    s = s.replace("\\~{n}", "ñ").replace("\\~n", "ñ")
    s = re.sub(r"\\'\{([^}])\}", lambda m: m.group(1) + "\u0301", s)  # acute
    s = re.sub(r'\\"\{([^}])\}', lambda m: m.group(1) + "\u0308", s)  # umlaut
    # \& -> &
    s = s.replace("\\&", "&")
    # Remove remaining braces (used for capitalization protection)
    s = s.replace("{", "").replace("}", "")
    return s.strip()


def format_authors(entry):
    """Format author string for display."""
    # If there's a custom display string, use it
    if "authordisplay" in entry:
        return entry["authordisplay"]

    raw = entry.get("author", "")
    # Split on " and "
    authors = [a.strip() for a in re.split(r"\s+and\s+", raw)]

    formatted = []
    for a in authors:
        if a.lower() == "others":
            # This shouldn't happen if authordisplay is set, but just in case
            formatted.append("others")
            continue
        # "Last, First" format — keep as-is for CV style
        formatted.append(a)

    if len(formatted) == 1:
        return formatted[0]
    elif len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    else:
        return ", ".join(formatted[:-1]) + ", and " + formatted[-1]


def normalize_author_list(raw):
    """Normalize 'First Last' -> 'Last, First' unless already comma-formatted."""
    if not raw:
        return ""
    authors = [a.strip() for a in re.split(r"\s+and\s+", raw)]
    normalized = []
    for a in authors:
        if "," in a:
            normalized.append(a)
            continue
        parts = a.split()
        if len(parts) >= 2:
            normalized.append(parts[-1] + ", " + " ".join(parts[:-1]))
        else:
            normalized.append(a)
    return " and ".join(normalized)




def format_pub_url(entry):
    """Get the best URL for a publication."""
    if "doi" in entry and entry["doi"]:
        return f"https://doi.org/{entry['doi']}"
    return entry.get("url", "")


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------

def read_csv_file(path):
    """Read a CSV file into a list of dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _coerce_int(val, allow_commas=False, allow_dollar=False):
    """Normalize a numeric string and return int, or raise ValueError."""
    if allow_commas:
        val = val.replace(",", "")
    if allow_dollar:
        val = val.replace("$", "")
    return int(val)


def validate_numeric_fields(rows, filepath, field_specs):
    """Validate that specified fields contain numeric values (or are blank).

    field_specs: list of (field_name, allow_blank, opts) tuples.
    opts: dict with parsing options (e.g., allow_commas, allow_dollar).
    Raises ValueError with file, row number, and field name on failure.
    """
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        for field_name, allow_blank, opts in field_specs:
            val = row.get(field_name, "")
            if val == "" and allow_blank:
                continue
            if val == "":
                raise ValueError(
                    f"{filepath} row {i}: '{field_name}' is blank but a value is required"
                )
            try:
                _coerce_int(val, **opts)
            except ValueError:
                raise ValueError(
                    f"{filepath} row {i}: '{field_name}' must be numeric, got '{val}'"
                )


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_data(data_dir):
    """Read all data files and return a combined dict for JSON export."""
    data = {}

    # Simple CSV sections
    csv_files = {
        "positions": "positions.csv",
        "education": "education.csv",
        "roles": "roles.csv",
        "teaching": "teaching.csv",
        "grants": "grants.csv",
        "admin_positions": "admin_positions.csv",
        "service": "service.csv",
        "presentations": "presentations.csv",
        "peer_reviews": "peer_reviews.csv",
    }

    for key, filename in csv_files.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            data[key] = read_csv_file(filepath)
        else:
            data[key] = []

    # Validate numeric fields in CSVs
    numeric_checks = {
        "positions": [("start_year", False, {}), ("end_year", True, {})],
        "education": [("start_year", False, {}), ("end_year", False, {})],
        "roles": [("start_year", False, {}), ("end_year", True, {})],
        "teaching": [("start_year", False, {}), ("end_year", True, {})],
        "grants": [("year", False, {}), ("amount", True, {"allow_commas": True, "allow_dollar": True})],
        "admin_positions": [("start_year", False, {}), ("end_year", True, {})],
        "presentations": [("year", False, {})],
    }
    for key, specs in numeric_checks.items():
        if data[key]:
            filepath = os.path.join(data_dir, csv_files[key])
            validate_numeric_fields(data[key], filepath, specs)

    # Publications from .bib
    bib_path = os.path.join(data_dir, "publications.bib")
    if os.path.exists(bib_path):
        raw_entries = parse_bib(bib_path)
        publications = []
        wip_items = []
        for entry in raw_entries:
            entry_type = entry.get("_type", "")
            status = entry.get("status", "")

            # Route works-in-progress entries to a separate list.
            if entry_type in {"unpublished", "manuscript", "workingpaper", "inprogress"} or status == "wip":
                wip_items.append({
                    "authors": format_authors(entry),
                    "year": entry.get("year", ""),
                    "title": entry.get("title", ""),
                    "url": format_pub_url(entry),
                    "note": entry.get("note", ""),
                })
                continue

            pub = {
                "key": entry.get("_key", ""),
                "type": entry_type,
                "authors_display": format_authors(entry),
                "year": entry.get("year", ""),
                "title": entry.get("title", ""),
                "journal": entry.get("journal", ""),
                "booktitle": entry.get("booktitle", ""),
                "editor": entry.get("editor", ""),
                "volume": entry.get("volume", ""),
                "number": entry.get("number", ""),
                "pages": entry.get("pages", ""),
                "doi": entry.get("doi", ""),
                "url": format_pub_url(entry),
                "status": status,
                "note": entry.get("note", ""),
            }
            publications.append(pub)
        data["publications"] = publications
        data["wip"] = wip_items
    else:
        data["publications"] = []
        data["wip"] = []

    # Other writing from .bib
    other_bib_path = os.path.join(data_dir, "other_writing.bib")
    if os.path.exists(other_bib_path):
        raw_entries = parse_bib(other_bib_path)
        other_writing = []
        for entry in raw_entries:
            # Normalize author order for consistent display
            if "author" in entry and entry["author"]:
                entry["author"] = normalize_author_list(entry["author"])
            other_writing.append({
                "key": entry.get("_key", ""),
                "authors_display": format_authors(entry),
                "year": entry.get("year", ""),
                "title": entry.get("title", ""),
                "venue": entry.get("note", ""),
                "url": format_pub_url(entry),
            })
        data["other_writing"] = other_writing
    else:
        data["other_writing"] = []

    return data


def main():
    parser = argparse.ArgumentParser(description="Build CV PDF")
    parser.add_argument("--years", type=int, default=None,
                        help="Include only the last N years (omit for full CV)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output PDF filename (default: cv.pdf or cv-Nyear.pdf)")
    parser.add_argument("--data-only", action="store_true",
                        help="Only generate JSON data, don't compile PDF")
    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent.resolve()
    data_dir = script_dir / "data"
    gen_dir = script_dir / "_generated"
    output_dir = script_dir / "output"

    # Create directories
    gen_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # Build data
    print("Reading data files...")
    data = build_data(str(data_dir))

    # Write JSON
    json_path = gen_dir / "cv-data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Generated {json_path}")

    if args.data_only:
        return

    # Compile with Typst (CLI via Homebrew)
    print("Compiling PDF...")

    typst_bin = shutil.which("typst")
    if not typst_bin:
        print("ERROR: typst CLI not found on PATH. Install with: brew install typst")
        sys.exit(1)

    input_path = str(script_dir / "cv.typ")

    # Determine output filename
    if args.output:
        out_name = args.output
    elif args.years:
        out_name = f"cv-{args.years}year.pdf"
    else:
        out_name = "cv.pdf"
    output_path = str(output_dir / out_name)

    cmd = [typst_bin, "compile", input_path, output_path, "--root", str(script_dir)]

    # Pass sys.inputs (Typst CLI: --input key=value)
    if args.years is not None:
        cmd += ["--input", f"years={args.years}"]

    try:
        subprocess.run(cmd, check=True)
        print(f"PDF written to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Typst compilation error:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
