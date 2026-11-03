# 🎂 Franciscan e-Care Birthday Scraper

A command-line tool to **scrape, archive, and search** school birthday directories on the **Franciscan e-Care** platform — including data that the app's frontend doesn't fully show (like the full birth year).

> A lightweight tool for offline school birthday directory access and fast terminal search.

---

## 🚀 Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/kyokomico/ecare-birthday-scraper.git
cd ecare-birthday-scraper

# 2. Set up your config
cp config.example.json config.json
# Edit config.json — enter your school code and API key

# 3. Scrape live data
python3 scrape.py

# 4. Search
./bday "Aarav"
```

**Requirements:** Python 3.6+ only. No external dependencies — uses Python standard library (`urllib`, `json`, `csv`).

---

## 📁 Project Structure

```
ecare-birthday-scraper/
├── birthday-records-2026/          ← Session database (git-ignored)
│   ├── students_birthdays.csv      ← Name, Class, Birthday, Passout
│   ├── teachers_birthdays.csv      ← Name, Role, Birthday
│   └── bday                        ← Run from here to search this session only
├── config.json                     ← Local config (git-ignored, create from example)
├── config.example.json             ← Template — copy to config.json
├── scrape.py                       ← Live data fetcher from school API
├── search.py                       ← Search engine (used by all bday scripts)
├── bday                            ← Run from root for active session search
└── README.md                       ← This file
```

---

## ⚙️ Configuration (`config.json`)

Copy `config.example.json` to `config.json` and fill in your details:

```json
{
  "school_code": "YOUR_SCHOOL_CODE",
  "api_key": "YOUR_API_KEY",
  "api_base_url": "https://android.franciscan.in/api",
  "session_year": null
}
```

- **`school_code`** — Your school's code.
- **`api_key`** — The API key used by the e-Care client.
- **`session_year`** — Leave as `null` to auto-detect current year, or set manually (e.g. `2027`).

---

## 🔄 Scraping Live Data (`scrape.py`)

Fetches the latest birthday records directly from the school's API and creates a new session folder.

```bash
cd ecare-birthday-scraper
python3 scrape.py
```

### What it does:
1. Connects live to the Franciscan e-Care API server.
2. Fetches all **student records** (UserType=1) and **staff records** (UserType=3).
3. Creates `birthday-records-<year>/` (e.g., `birthday-records-2027`).
4. Detects **passout students** automatically:
   - Students with an active section (e.g. `10-A`, `4-B`) → `Passout: No`
   - Students whose section is missing or replaced with `.` (e.g. `10-.`, `12-.`) → `Passout: Yes (2026)`
5. Exports two clean, sorted CSV files.
6. Drops a `./bday` shortcut inside the new session folder.
7. Sets the new session as the active default.

### Optional flags:

```bash
python3 scrape.py --year 2027         # Force a specific session year
python3 scrape.py --code YOUR_SCHOOL_CODE       # Override school code
```

---

## 🔍 Searching Birthdays (`./bday`)

The search tool works at two levels:

### Root-level `bday` (active session)
Searches whichever session is currently active (latest scraped year):
```bash
cd ecare-birthday-scraper
./bday "Aarav"
```

### Per-session `bday` (specific year only)
Searches only that year's records regardless of active session:
```bash
cd ecare-birthday-scraper/birthday-records-2026
./bday "Aarav"
```

---

## 🔎 Search Examples

### By Name (substring — finds all containing matches)
```bash
./bday "Aarav"
./bday "Singh"
```

### By Exact Name (case-insensitive, no partial matches)
```bash
./bday "Ayan Khan" --exact
./bday "Priya Sharma" --exact
# --exact can go anywhere in the command
./bday --exact "Ayan Khan"
```

### By Class & Section
```bash
./bday "10-A"         # Specific section
./bday "10"           # All of class 10 (all sections)
./bday "LKG"          # LKG section
```

### By Month
```bash
./bday "April"        # Full month name
./bday "apr"          # Short form works too
./bday "4"            # Month number
```

### By Day of Month
```bash
./bday "25"           # Everyone born on the 25th of any month
```

### Combining Filters
```bash
./bday "25 April"     # Born on 25th April specifically
./bday "Passout 12"   # 12th grade passout students
```

### Passout Students
```bash
./bday "Passout"      # All passout students (any grade)
./bday "Passout 10"   # Only 10th grade passouts
./bday "Passout 12"   # Only 12th grade passouts
```

### Active Students Only
```bash
./bday "active"       # All currently enrolled students
```

### Interactive Mode (no argument)
```bash
./bday                # Opens interactive prompt — search repeatedly
```
Type `exit` or `q` to quit.

---

## 📊 CSV File Format

### `students_birthdays.csv`
| Column | Example | Notes |
|--------|---------|-------|
| `Name` | `AYAN KHAN` | Uppercase |
| `Class` | `5-B` or `10` | Passout students show class only (no section) |
| `Birthday` | `10 January 2016` | Full date including birth year |
| `Passout` | `No` / `Yes (2026)` | Year indicates which batch they passed out |

### `teachers_birthdays.csv`
| Column | Example |
|--------|---------|
| `Name` | `NIKHIL KUMAR` |
| `Role` | `OFFICE STAFF` |
| `Birthday` | `25 April 1993` |

---

## 💡 How It Works (Technical)

The Franciscan e-Care app communicates with its backend server via plain HTTPS API calls. These calls were discovered by intercepting the app's network traffic using an Android emulator. The scraper replicates those exact same calls directly from Python, bypassing the app entirely.

### Key discovery — data hidden from the frontend:
The app's birthday calendar displays only the **day and month** (e.g., `15 Aug`). However, the raw API response contains the **full date including the birth year** (e.g., `2010-08-15T00:00:00`). This scraper captures and stores the complete date.

### API endpoints used:
| Endpoint | Data |
|----------|------|
| `/api/birthday/lst?SchCode=YOUR_SCHOOL_CODE&key=...&UserType=1` | All student birthdays |
| `/api/birthday/lst?SchCode=YOUR_SCHOOL_CODE&key=...&UserType=3` | All staff birthdays |

---

## 📅 Yearly Maintenance

At the start of each new academic session:

1. Open terminal in `ecare-birthday-scraper`
2. Run `python3 scrape.py`
3. A new `birthday-records-<year>/` folder is created automatically
4. Previous year's data is preserved — nothing is deleted
5. The new session becomes the active default for `./bday` at root level
6. Old sessions are still searchable via their own `./bday` inside their folder

---

## ⚠️ Disclaimer

- This tool is intended for personal offline directory lookup and educational purposes within your own institution.
- Do not use this tool to access unauthorized systems or data.
