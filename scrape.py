#!/usr/bin/env python3
"""
scrape.py — Pulls birthday records from the Franciscan e-Care API
and exports them as sorted CSV files into a versioned session folder.

Usage:
    python3 scrape.py
    python3 scrape.py --year 2027
    python3 scrape.py --code YOUR_SCHOOL_CODE
"""

import os
import sys
import json
import csv
import urllib.request
import argparse
from datetime import datetime

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULTS = {
    "school_code":   "",
    "api_key":       "",
    "api_base_url":  "https://android.franciscan.in/api",
    "session_year":  None,
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULTS
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not read config.json ({e}), using defaults.")
        return DEFAULTS


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "okhttp/4.9.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fmt_date(raw):
    """'2017-07-05T00:00:00'  ->  '05 July 2017'"""
    try:
        return datetime.strptime(raw.split("T")[0], "%Y-%m-%d").strftime("%d %B %Y")
    except (ValueError, AttributeError):
        return raw


def parse_name_class(raw):
    """'AYAN KHAN|5-B'  ->  ('AYAN KHAN', '5-B')"""
    if "|" in raw:
        name, cls = raw.split("|", 1)
        return name.strip(), cls.strip()
    return raw.strip(), ""


def resolve_passout(class_sec, year):
    """
    Returns (clean_class, passout_label).
    Students whose section is missing or '.' are treated as passouts.
    e.g. '10-.'  ->  ('10', 'Yes (2026)')
         '10-A'  ->  ('10-A', 'No')
    """
    if "-" in class_sec:
        cls, sec = class_sec.split("-", 1)
        if sec.strip() in (".", "") or not sec.strip().isalpha():
            return cls.strip(), f"Yes ({year})"
        return class_sec, "No"
    return (class_sec or "N/A"), f"Yes ({year})"


def scrape_students(base_url, school_code, api_key, year):
    url  = f"{base_url}/birthday/lst?SchCode={school_code}&key={api_key}&UserType=1"
    data = fetch(url)

    rows = []
    for month in data.get("MonthWise", []):
        for item in month.get("ThisMonth", []):
            name, class_sec = parse_name_class(item.get("Name", ""))
            clean_class, passout = resolve_passout(class_sec, year)
            rows.append({
                "Name":    name,
                "Class":   clean_class,
                "Birthday": fmt_date(item.get("DOB", "")),
                "Passout": passout,
            })
    return sorted(rows, key=lambda r: r["Name"])


def scrape_teachers(base_url, school_code, api_key):
    url  = f"{base_url}/birthday/lst?SchCode={school_code}&key={api_key}&UserType=3"
    data = fetch(url)

    rows = []
    for month in data.get("MonthWise", []):
        for item in month.get("ThisMonth", []):
            name, role = parse_name_class(item.get("Name", ""))
            rows.append({
                "Name":    name,
                "Role":    role or "Staff",
                "Birthday": fmt_date(item.get("DOB", "")),
            })
    return sorted(rows, key=lambda r: r["Name"])


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def drop_session_bday(records_dir, year):
    """Write a ./bday launcher into the records folder, scoped to that year only."""
    path = os.path.join(records_dir, "bday")
    search_py = os.path.join(os.path.dirname(records_dir), "search.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "#!/usr/bin/env bash\n"
            f"# Scoped to birthday-records-{year} only\n"
            'SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
            f'BDAY_RECORDS_DIR="$SELF_DIR" python3 "{search_py}" "$@"\n'
        )
    os.chmod(path, 0o755)


def main():
    parser = argparse.ArgumentParser(description="Scrape birthday records from the Franciscan e-Care API")
    parser.add_argument("--year", type=int, help="Session year (default: current year)")
    parser.add_argument("--code", type=str, help="School code (default: from config.json)")
    args = parser.parse_args()

    cfg          = load_config()
    school_code  = args.code or cfg["school_code"]
    api_key      = cfg["api_key"]
    base_url     = cfg["api_base_url"]
    year         = args.year or cfg["session_year"] or datetime.now().year

    if not school_code or not api_key:
        print("Error: school_code or api_key is missing.")
        print("Please configure config.json (copy from config.example.json).")
        sys.exit(1)

    records_dir  = os.path.join(BASE_DIR, f"birthday-records-{year}")
    os.makedirs(records_dir, exist_ok=True)

    print(f"\nSchool : {school_code}  |  Session : {year}")
    print(f"Output : {records_dir}\n")

    print("Fetching students...", end=" ", flush=True)
    try:
        students = scrape_students(base_url, school_code, api_key, year)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    passouts = sum(1 for s in students if s["Passout"] != "No")
    write_csv(
        os.path.join(records_dir, "students_birthdays.csv"),
        ["Name", "Class", "Birthday", "Passout"],
        students,
    )
    print(f"{len(students)} records ({passouts} passouts)")

    print("Fetching staff...  ", end=" ", flush=True)
    try:
        teachers = scrape_teachers(base_url, school_code, api_key)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    write_csv(
        os.path.join(records_dir, "teachers_birthdays.csv"),
        ["Name", "Role", "Birthday"],
        teachers,
    )
    print(f"{len(teachers)} records")

    drop_session_bday(records_dir, year)

    with open(os.path.join(BASE_DIR, ".active_session"), "w", encoding="utf-8") as f:
        f.write(f"birthday-records-{year}\n")

    print(f"\nDone. Run './bday' from the project root, or './bday' inside birthday-records-{year}/\n")


if __name__ == "__main__":
    main()
