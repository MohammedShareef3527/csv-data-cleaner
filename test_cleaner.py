import pandas as pd
import pytest

from cleaner import (clean_dataframe, clean_phone, clean_text, main,
                     parse_dates, snake_columns, to_numbers)


def S(values):
    return pd.Series(values, dtype="string")


def test_snake_columns_and_duplicates():
    assert snake_columns([" Customer Name ", "E-mail", "Name", "name"]) == [
        "customer_name", "e_mail", "name", "name_2"]


def test_clean_text_trims_and_blanks_placeholders():
    out = clean_text(S(["  hello   world ", "N/A", "null", "--", "ok"]))
    assert out.tolist()[0] == "hello world"
    assert out.isna().tolist() == [False, True, True, True, False]


def test_numbers_with_currency():
    out = to_numbers(S(["₹1,200", "Rs. 2,500.50", "(300)", "abc"]))
    assert out.tolist()[:3] == [1200, 2500.5, -300]
    assert pd.isna(out.iloc[3])


def test_phone_cleanup():
    assert clean_phone(S(["+91 98765 43210", "098765-43210", "9876543210"])).tolist() == [
        "9876543210"] * 3


def test_iso_dates_are_never_swapped():
    # regression: with dayfirst=True, 2024-03-05 was once read as 3 May
    out = parse_dates(S(["2024-03-05"]), dayfirst=True)
    assert out.iloc[0] == pd.Timestamp("2024-03-05")


def test_ambiguous_dates_follow_dayfirst_flag():
    assert parse_dates(S(["05/03/2024"]), dayfirst=True).iloc[0] == pd.Timestamp("2024-03-05")
    assert parse_dates(S(["05/03/2024"]), dayfirst=False).iloc[0] == pd.Timestamp("2024-05-03")


def test_mixed_date_formats():
    out = parse_dates(S(["12-Mar-2024", "March 20 2024", "15/03/2024"]), dayfirst=True)
    assert out.dt.strftime("%Y-%m-%d").tolist() == ["2024-03-12", "2024-03-20", "2024-03-15"]


def messy():
    return pd.DataFrame({
        "Name ": ["john smith", "JOHN SMITH", None, "amit kumar"],
        "Join Date": ["05/03/2024", "2024-03-05", None, "15/03/2024"],
        "Amount": ["₹1,200", "1200", None, "n/a"],
        "Pincode": ["0560001", "0560001", None, "580020"],
    })


def test_duplicates_found_after_standardising():
    df, report = clean_dataframe(messy())
    assert report["duplicates_removed"] == 1
    assert report["empty_rows_dropped"] == 1
    assert len(df) == 2


def test_ids_with_leading_zeros_are_kept_as_text():
    df, _ = clean_dataframe(messy())
    assert df["pincode"].iloc[0] == "0560001"


def test_empty_columns_removed():
    df = pd.DataFrame({"a": ["1", "2"], "b": [None, "n/a"]})
    cleaned, report = clean_dataframe(df)
    assert list(cleaned.columns) == ["a"]
    assert report["empty_columns_dropped"] == ["b"]


def test_invalid_email_is_kept_but_reported():
    df = pd.DataFrame({"Email": ["a@b.com", "oops"]})
    cleaned, report = clean_dataframe(df)
    assert "oops" in cleaned["email"].tolist()
    assert any("emails" in p for p in report["problems"])


def test_text_column_is_not_turned_into_numbers():
    df = pd.DataFrame({"notes": ["call back", "interested", "5"]})
    cleaned, _ = clean_dataframe(df)
    assert cleaned["notes"].tolist() == ["call back", "interested", "5"]


def test_cli_csv_roundtrip(tmp_path):
    src = tmp_path / "in.csv"
    messy().to_csv(src, index=False)
    out = tmp_path / "out.csv"
    rep = tmp_path / "rep.txt"
    main([str(src), "-o", str(out), "--report", str(rep)])
    result = pd.read_csv(out, dtype=str)
    assert len(result) == 2
    assert "DATA CLEANING REPORT" in rep.read_text(encoding="utf-8")


def test_cli_excel_roundtrip(tmp_path):
    src = tmp_path / "in.xlsx"
    messy().to_excel(src, index=False)
    out = tmp_path / "out.xlsx"
    main([str(src), "-o", str(out)])
    assert len(pd.read_excel(out)) == 2


def test_cli_missing_file_exits():
    with pytest.raises(SystemExit):
        main(["does_not_exist.csv"])
