"""
Data Cleaner
------------
Cleans messy CSV / Excel files and writes a tidy file plus a plain-English report.

Usage:
    python cleaner.py messy_customers.csv
    python cleaner.py messy_customers.csv -o clean.csv --report report.txt
    python cleaner.py sales.xlsx -o sales_clean.xlsx
    python cleaner.py data.csv --us-dates        # read 03/05/2024 as March 5
"""

import argparse
import os
import re
import sys
import warnings

import pandas as pd

# Cell values that really mean "empty"
NULL_TOKENS = {"", "na", "n/a", "nan", "null", "none", "nil", "-", "--", "?", "not available"}

# Column-name hints (matched against the cleaned snake_case names)
EMAIL_HINT = re.compile(r"e_?mail", re.I)
PHONE_HINT = re.compile(r"(phone|mobile|contact|whatsapp)", re.I)
DATE_HINT = re.compile(r"(date|dob|birth|joined|created|updated)", re.I)
NAME_HINT = re.compile(r"(^|_)(name|city|state|country)$", re.I)
ID_HINT = re.compile(r"(^|_)(id|code|pin|pincode|zip|postal|sku|number|no)$", re.I)

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
MIN_MATCH = 0.8  # a column is converted only if at least 80% of its values fit the type


# ------------------------------------------------------------------ small helpers
def snake_columns(columns):
    """' Customer Name ' -> 'customer_name'. Duplicate names get _2, _3 ..."""
    seen, out = {}, []
    for col in columns:
        name = re.sub(r"[^0-9a-zA-Z]+", "_", str(col).strip()).strip("_").lower() or "column"
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return out


def clean_text(series):
    """Trim, collapse repeated spaces, turn placeholder values (N/A, null, -) into blanks."""
    s = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    return s.mask(s.str.casefold().isin(NULL_TOKENS))


def parse_dates(series, dayfirst=True):
    """Parse mixed date formats. Year-first dates (2024-03-05) are always read as
    YYYY-MM-DD; only the ambiguous ones (05/03/2024) follow the dayfirst setting."""
    iso_mask = series.str.match(r"^\d{4}-\d{1,2}-\d{1,2}").fillna(False).astype(bool)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        iso = pd.to_datetime(series.where(iso_mask), errors="coerce", format="mixed", dayfirst=False)
        other = pd.to_datetime(series.where(~iso_mask), errors="coerce", format="mixed", dayfirst=dayfirst)
    return iso.fillna(other)


def to_numbers(series):
    """'₹1,200' / 'Rs. 2,500.50' / '(300)' -> numbers. Unparseable values become NaN."""
    cleaned = series.str.replace(r"(?i)\brs\.?|inr|[₹$€£,\s]", "", regex=True)
    cleaned = cleaned.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def clean_phone(series):
    """Keep digits only and drop a leading 91 / 0 country or trunk prefix."""
    digits = series.str.replace(r"\D", "", regex=True)
    digits = digits.str.replace(r"^(91|0)(?=\d{10}$)", "", regex=True)
    return digits.mask(digits == "")


# ---------------------------------------------------------------------- main logic
def clean_dataframe(df, dayfirst=True):
    """Clean a DataFrame. Returns (clean_df, report_dict)."""
    report = {
        "rows_in": len(df), "cols_in": len(df.columns), "renamed": [],
        "empty_rows_dropped": 0, "empty_columns_dropped": [], "duplicates_removed": 0,
        "actions": [], "problems": [],
    }

    df = df.copy()
    new_cols = snake_columns(df.columns)
    report["renamed"] = [(o, n) for o, n in zip(df.columns, new_cols) if str(o) != n]
    df.columns = new_cols

    # 1. text cleanup + placeholders -> blank
    for col in df.columns:
        df[col] = clean_text(df[col])

    # 2. remove empty rows / columns
    before = len(df)
    df = df.dropna(how="all")
    report["empty_rows_dropped"] = before - len(df)
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    report["empty_columns_dropped"] = empty_cols
    df = df.drop(columns=empty_cols)

    # 3. fix each column according to what it holds
    for col in df.columns:
        s = df[col]
        filled = int(s.notna().sum())

        if EMAIL_HINT.search(col):
            s = s.str.lower()
            valid = s.str.match(EMAIL_RE).fillna(True)
            bad = int((~valid).sum())
            df[col] = s
            report["actions"].append(f"'{col}': trimmed and lower-cased emails")
            if bad:
                report["problems"].append(f"'{col}': {bad} value(s) do not look like valid emails (kept, please review)")

        elif PHONE_HINT.search(col):
            s = clean_phone(s)
            valid = s.str.match(r"^[6-9]\d{9}$").fillna(True)
            bad = int((~valid).sum())
            df[col] = s
            report["actions"].append(f"'{col}': stripped spaces/symbols and +91 prefix from phone numbers")
            if bad:
                report["problems"].append(f"'{col}': {bad} value(s) are not valid 10-digit Indian mobile numbers (kept, please review)")

        elif DATE_HINT.search(col):
            parsed = parse_dates(s, dayfirst)
            if parsed.notna().sum() >= MIN_MATCH * filled:
                bad = filled - int(parsed.notna().sum())
                df[col] = parsed.dt.strftime("%Y-%m-%d").astype("string")
                report["actions"].append(f"'{col}': converted mixed date formats to YYYY-MM-DD")
                if bad:
                    report["problems"].append(f"'{col}': {bad} value(s) could not be read as dates (left blank)")

        elif NAME_HINT.search(col):
            df[col] = s.str.title()
            report["actions"].append(f"'{col}': fixed capitalisation")

        elif not ID_HINT.search(col) and not s.str.match(r"^0\d").fillna(False).any():
            nums = to_numbers(s)
            if filled and nums.notna().sum() >= MIN_MATCH * filled:
                bad = filled - int(nums.notna().sum())
                if (nums.dropna() % 1 == 0).all():
                    nums = nums.astype("Int64")
                else:
                    nums = nums.round(2)
                df[col] = nums
                report["actions"].append(f"'{col}': removed currency symbols/commas and converted to numbers")
                if bad:
                    report["problems"].append(f"'{col}': {bad} value(s) were not numbers (left blank)")

    # 4. remove duplicates AFTER standardising, so 'John' / 'john' and 05/03 / 2024-03-05 match
    key = df.apply(lambda c: c.astype("string").str.casefold())
    dup = key.duplicated(keep="first")
    report["duplicates_removed"] = int(dup.sum())
    df = df[~dup].reset_index(drop=True)

    report["rows_out"] = len(df)
    report["cols_out"] = len(df.columns)
    report["missing"] = {c: int(n) for c, n in df.isna().sum().items() if n}
    return df, report


def format_report(report, source, output):
    lines = [
        "DATA CLEANING REPORT", "=" * 44,
        f"Input file : {source}", f"Output file: {output}", "",
        f"Rows    : {report['rows_in']} -> {report['rows_out']}",
        f"Columns : {report['cols_in']} -> {report['cols_out']}", "",
        f"Empty rows removed   : {report['empty_rows_dropped']}",
        f"Duplicate rows removed: {report['duplicates_removed']}",
    ]
    if report["empty_columns_dropped"]:
        lines.append("Empty columns removed: " + ", ".join(report["empty_columns_dropped"]))
    if report["renamed"]:
        lines += ["", "Column names tidied:"] + [f"  {o!r} -> {n}" for o, n in report["renamed"]]
    if report["actions"]:
        lines += ["", "What was fixed:"] + [f"  - {a}" for a in report["actions"]]
    if report["missing"]:
        lines += ["", "Missing values left in the data:"] + [f"  - {c}: {n}" for c, n in report["missing"].items()]
    if report["problems"]:
        lines += ["", "Needs your attention:"] + [f"  ! {p}" for p in report["problems"]]
    return "\n".join(lines)


# ------------------------------------------------------------------------ file I/O
def read_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, dtype=str)
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not read the file's text encoding")


def write_file(df, path):
    if path.lower().endswith((".xlsx", ".xlsm")):
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clean a messy CSV or Excel file.")
    parser.add_argument("input", help="CSV or Excel file to clean")
    parser.add_argument("-o", "--output", help="Output file (default: <input>_cleaned.csv)")
    parser.add_argument("--report", help="Also save the report to this text file")
    parser.add_argument("--us-dates", action="store_true", help="Read ambiguous dates as MM/DD/YYYY (default is DD/MM/YYYY)")
    args = parser.parse_args(argv)

    try:
        df = read_file(args.input)
    except FileNotFoundError:
        sys.exit(f"File not found: {args.input}")
    except pd.errors.EmptyDataError:
        sys.exit("The file is empty.")
    if df.empty:
        sys.exit("The file has no data rows.")

    stem = os.path.splitext(args.input)[0]
    output = args.output or f"{stem}_cleaned.csv"
    cleaned, report = clean_dataframe(df, dayfirst=not args.us_dates)
    write_file(cleaned, output)

    text = format_report(report, args.input, output)
    print(text)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
