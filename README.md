# Data Cleaner

A Python command-line tool that cleans messy CSV and Excel files and gives you a plain-English report of what it fixed. It is the kind of job small businesses constantly need: customer lists, sales sheets and enquiry logs full of typos, duplicates and inconsistent formats.

## Before and after

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

## What it fixes

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

Problems it can't safely fix (invalid emails, bad phone numbers, unreadable dates) are listed under "Needs your attention" in the report instead of being silently changed.

## How to run

```bash
pip install -r requirements.txt
python cleaner.py messy_customers.csv
```

Options:

```bash
python cleaner.py data.csv -o clean.csv --report report.txt   # choose output and save the report
python cleaner.py sales.xlsx -o sales_clean.xlsx              # Excel in, Excel out
python cleaner.py data.csv --us-dates                         # read 03/05/2024 as March 5
```

Ambiguous dates such as `05/03/2024` are read as day/month/year by default, which is the usual format in India.

## How it works

1. `snake_columns()` renames columns, and `clean_text()` trims text and blanks out placeholders
2. Empty rows and columns are dropped
3. Each column is checked by name and by content: emails, phones, dates, names and numbers each get their own rule. A column is converted only if at least 80% of its values fit the type, so a notes column is never turned into numbers by accident
4. Duplicates are detected on the standardised values
5. A report is generated from counters collected along the way

## Run the tests

```bash
pytest
```

## Tech Stack

Python 3, pandas, openpyxl, pytest

## Possible Future Improvements

- Choose which columns to clean from the command line
- Fill missing values (for example, with the column average)
- A simple drag-and-drop web interface
