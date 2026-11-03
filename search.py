#!/usr/bin/env python3
"""
search.py — Interactive and CLI birthday search tool.

Searches students and staff by name, class, month, day, or passout status.
Reads from the active session folder (or the one set via BDAY_RECORDS_DIR).

Usage:
    python3 search.py                    # interactive
    python3 search.py "Aarav"           # quick query
    python3 search.py "Ayan Khan" --exact
"""

import os
import sys
import csv
import glob
import signal

if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MONTHS = {
    "1": "january",  "01": "january",  "jan": "january",  "january": "january",
    "2": "february", "02": "february", "feb": "february", "february": "february",
    "3": "march",    "03": "march",    "mar": "march",    "march": "march",
    "4": "april",    "04": "april",    "apr": "april",    "april": "april",
    "5": "may",      "05": "may",      "may": "may",
    "6": "june",     "06": "june",     "jun": "june",     "june": "june",
    "7": "july",     "07": "july",     "jul": "july",     "july": "july",
    "8": "august",   "08": "august",   "aug": "august",   "august": "august",
    "9": "september","09": "september","sep": "september","september": "september",
    "10": "october",                   "oct": "october",  "october": "october",
    "11": "november",                  "nov": "november", "november": "november",
    "12": "december",                  "dec": "december", "december": "december",
}


# ── Data loading ───────────────────────────────────────────────────────────────

def resolve_records_dir():
    """
    Priority:
      1. BDAY_RECORDS_DIR env var  (set by per-session ./bday scripts)
      2. .active_session file
      3. Latest birthday-records-* folder
      4. BASE_DIR as fallback
    """
    env = os.environ.get("BDAY_RECORDS_DIR", "").strip()
    if env and os.path.isdir(env):
        return env

    active = os.path.join(BASE_DIR, ".active_session")
    if os.path.exists(active):
        with open(active, encoding="utf-8") as f:
            target = os.path.join(BASE_DIR, f.read().strip())
            if os.path.isdir(target):
                return target

    candidates = sorted(glob.glob(os.path.join(BASE_DIR, "birthday-records-*")), reverse=True)
    return candidates[0] if candidates else BASE_DIR


def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Matching ──────────────────────────────────────────────────────────────────

def _term_matches(term, row):
    t       = term.lower()
    name    = row.get("Name", "").lower()
    cat     = row.get("Class", row.get("Role", "")).lower()
    bday    = row.get("Birthday", "").lower()
    passout = row.get("Passout", "").lower()

    if t in name or t in cat or t in bday or t in passout:
        return True
    if t in ("passout", "passouts", "passed", "graduated") and "yes" in passout:
        return True
    if t in ("active", "current") and passout == "no":
        return True
    if t in MONTHS and MONTHS[t] in bday:
        return True
    if t.isdigit() and 1 <= int(t) <= 31:
        day = f"{int(t):02d} "
        return bday.startswith(day) or f" {int(t):02d} " in bday

    return False


def matches(row, query, exact=False):
    q = query.strip()
    if not q:
        return False

    name = row.get("Name", "").strip()
    cat  = row.get("Class", row.get("Role", "")).strip()
    bday = row.get("Birthday", "").strip()

    if exact:
        ql = q.lower()
        return ql == name.lower() or ql == cat.lower() or ql == bday.lower()

    ql = q.lower()
    if ql in name.lower() or ql in cat.lower() or ql in bday.lower():
        return True

    return all(_term_matches(t, row) for t in q.split())


def parse_flags(raw):
    """Strip --exact / -e from the query string and return (clean_query, exact_bool)."""
    exact  = False
    tokens = []
    for part in raw.split():
        if part.lower() in ("--exact", "-exact", "-e"):
            exact = True
        else:
            tokens.append(part)
    return " ".join(tokens).strip(), exact


# ── Output ────────────────────────────────────────────────────────────────────

W = 80

def _print_students(rows):
    print(f"Students ({len(rows)}):")
    print(f"  {'Name':<30} {'Class':<10} {'Birthday':<20} Passout")
    print("  " + "-" * (W - 2))
    for r in rows:
        print(f"  {r['Name']:<30} {r['Class']:<10} {r['Birthday']:<20} {r.get('Passout','')}")
    print()


def _print_teachers(rows):
    print(f"Staff ({len(rows)}):")
    print(f"  {'Name':<30} {'Role':<20} Birthday")
    print("  " + "-" * (W - 2))
    for r in rows:
        print(f"  {r['Name']:<30} {r['Role']:<20} {r['Birthday']}")
    print()


def run_search(raw_query, students, teachers):
    query, exact = parse_flags(raw_query)
    if not query:
        return

    s_res = [r for r in students if matches(r, query, exact)]
    t_res = [r for r in teachers if matches(r, query, exact)]
    total = len(s_res) + len(t_res)

    tag   = "  [exact]" if exact else ""
    print(f"\n> '{query}'{tag}  —  {total} result(s)\n" + "=" * W)

    if s_res:
        _print_students(s_res)
    if t_res:
        _print_teachers(t_res)
    if total == 0:
        print("  No records found.")
    print("=" * W + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    records_dir = resolve_records_dir()
    students    = load_csv(os.path.join(records_dir, "students_birthdays.csv"))
    teachers    = load_csv(os.path.join(records_dir, "teachers_birthdays.csv"))
    session     = os.path.basename(records_dir)

    if len(sys.argv) > 1:
        run_search(" ".join(sys.argv[1:]), students, teachers)
        return

    print(f"\n  Birthday Search  [{session}]")
    print(f"  {len(students)} students  |  {len(teachers)} staff")
    print(f"  Search by name, class, month, day, or 'passout'")
    print(f"  Append --exact for exact-name matching\n")

    while True:
        try:
            q = input("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if q.lower() in ("exit", "q", "quit"):
            break
        if q:
            run_search(q, students, teachers)


if __name__ == "__main__":
    main()
