<div align="center">

# Data Cleaner

**A Python command-line tool that cleans messy CSV and Excel files and explains every fix in a plain-English report.**

![Python](https://img.shields.io/badge/Python-0d1117?style=flat-square&logo=python&logoColor=3776AB)
![pandas](https://img.shields.io/badge/pandas-0d1117?style=flat-square&logo=pandas&logoColor=E70488)
![pytest](https://img.shields.io/badge/tests-15%20passing-3fb950?style=flat-square&logo=pytest&logoColor=white&labelColor=0d1117)

</div>

---

## Overview

Data Cleaner takes a messy spreadsheet (a customer list, sales sheet or enquiry log) and produces a clean copy: tidy column names, consistent dates, real numbers, standardised phone numbers and emails, and no duplicates. It also writes a report of what it changed and what still needs a human to check.

## Problem Statement

Small businesses constantly deal with spreadsheets full of typos, duplicates and inconsistent formats: the same customer typed twice in different capitalisation, dates in three formats, amounts written as `₹1,200` or `Rs. 2,500.50`. Cleaning this by hand is slow and error-prone, and silent "auto-fixes" can damage data. This tool fixes what it safely can and clearly flags the rest.

## Features

- **Column names** are tidied (`' Customer Name '` becomes `customer_name`)
- **Extra spaces** are trimmed, and placeholders such as `N/A`, `null` and `--` become blank
- **Empty rows and empty columns** are removed
- **Dates** in mixed formats (`05/03/2024`, `2024-03-05`, `12-Mar-2024`, `March 20 2024`) all become `YYYY-MM-DD`
- **Amounts** like `₹1,200`, `Rs. 2,500.50` and `(300)` become real numbers
- **Phone numbers** lose spaces, symbols and the `+91` prefix
- **Emails** are trimmed and lower-cased
- **Names and cities** get consistent capitalisation
- **Duplicates** are removed *after* everything is standardised, so `JOHN SMITH` with `05/03/2024` matches `john smith` with `2024-03-05`
- **IDs and pincodes** with leading zeros stay as text, so `0560002` is never turned into `560002`
- **CSV and Excel** input and output, with automatic handling of UTF-8 and Latin-1 files

Problems it can't safely fix (invalid emails, bad phone numbers, unreadable dates) are listed under "Needs your attention" in the report instead of being silently changed.

## Before and After

`messy_customers.csv` (input):

```
Customer Name , E-mail,Phone,Join Date,Amount Paid,City,Pincode
  john smith,John@Example.com ,9876543210,05/03/2024,"₹1,200",bengaluru,560001
JOHN SMITH,john@example.com,+91 98765 43210,2024-03-05,1200,Bengaluru,560001
priya  sharma,priya@mail.com,98765 43211,12-Mar-2024,"Rs. 2,500.50",MYSORE,570001
,,,,,,
amit kumar,amit@example.com,N/A,15/03/2024,n/a,hubli,580020
...
```

`messy_customers_cleaned.csv` (output):

```
customer_name,e_mail,phone,join_date,amount_paid,city,pincode
John Smith,john@example.com,9876543210,2024-03-05,1200.0,Bengaluru,560001
Priya Sharma,priya@mail.com,9876543211,2024-03-12,2500.5,Mysore,570001
Amit Kumar,amit@example.com,,2024-03-15,,Hubli,580020
...
```

The full report is in [`cleaning_report.txt`](cleaning_report.txt).

## Tech Stack

- **Language:** Python 3
- **Data processing:** pandas
- **Excel support:** openpyxl
- **Testing:** pytest
- **CLI:** argparse

## Project Structure

```text
csv-data-cleaner/
├── cleaner.py                    # the cleaning engine and command-line interface
├── test_cleaner.py               # 15 automated tests
├── messy_customers.csv           # sample messy input
├── messy_customers_cleaned.csv   # output produced from the sample
├── cleaning_report.txt           # report produced from the sample
├── requirements.txt
└── .gitignore
```

## Installation and Setup

```bash
git clone https://github.com/MohammedShareef3527/csv-data-cleaner.git
cd csv-data-cleaner
pip install -r requirements.txt
python cleaner.py messy_customers.csv
```

Options:

```bash
python cleaner.py data.csv -o clean.csv --report report.txt   # choose output and save the report
python cleaner.py sales.xlsx -o sales_clean.xlsx              # Excel in, Excel out
python cleaner.py data.csv --us-dates                         # read 03/05/2024 as March 5
```

## Configuration

No API keys or settings files are needed. Behaviour is controlled with command-line options:

| Option | Default | Meaning |
|---|---|---|
| `-o`, `--output` | `<input>_cleaned.csv` | output file; use `.xlsx` for Excel |
| `--report` | not saved | also save the report to a text file |
| `--us-dates` | off | read ambiguous dates as month/day/year |

Ambiguous dates such as `05/03/2024` are read as day/month/year by default, which is the usual format in India.

## How It Works

1. `snake_columns()` renames columns, and `clean_text()` trims text and blanks out placeholders
2. Empty rows and columns are dropped
3. Each column is checked by name and by content: emails, phones, dates, names and numbers each get their own rule. A column is converted only if at least 80% of its values fit the type, so a notes column is never turned into numbers by accident
4. Duplicates are detected on the standardised values
5. A report is generated from counters collected along the way

## Run the Tests

```bash
pytest
```

The 15 tests cover column renaming, placeholders, currency parsing, phone cleanup, date handling in both day-first and month-first modes, duplicate detection, leading-zero IDs, invalid emails, and full CSV and Excel round trips through the command line.

## Future Improvements

These are planned ideas, not current features:

- Choose which columns to clean from the command line
- Fill missing values (for example, with the column average)
- A simple drag-and-drop web interface

## Learning Outcomes

- Data cleaning and type inference with pandas
- Writing rules that are safe by default: convert only when most values match, and report instead of guessing
- Handling real-world formats: Indian currency, phone numbers and day-first dates
- Building a command-line tool with argparse
- Test-driven development with pytest, including end-to-end CLI tests

## Author

**Mohammed Shamsul Qhadri Shareef**
GitHub: [@MohammedShareef3527](https://github.com/MohammedShareef3527)
