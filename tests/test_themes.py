import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import analyze  # noqa: E402
import clean  # noqa: E402
import themes as th  # noqa: E402


def tagged(*texts):
    return th.tag(pd.DataFrame({"text_clean": list(texts)}))


@pytest.mark.parametrize("text,theme", [
    ("I sent money and the transfer failed but I was debited", "Failed or delayed transactions"),
    ("Still waiting for my reversal after three days", "Failed or delayed transactions"),
    ("OTP never arrives so I cannot login", "Login, OTP and verification"),
    ("They keep asking for BVN and face verification", "Login, OTP and verification"),
    ("The charges and stamp duty are too high", "Fees and charges"),
    ("Customer care never responds to my complaint", "Customer support"),
    ("The app keeps crashing and the server is slow", "App performance and downtime"),
    ("My account was restricted and put on PND", "Account restriction or freeze"),
    ("Fraudsters hacked my wallet", "Fraud and security"),
    ("I took a loan and the repayment harassment is terrible", "Loans and credit"),
    ("My data bundle expired quickly after I did the recharge", "Data, airtime and bundles"),
])
def test_theme_fires(text, theme):
    assert tagged(text)[theme].iloc[0]


@pytest.mark.parametrize("text", [
    "Lovely app, very easy to use and fast",
    "Great experience, I recommend it to everybody",
])
def test_neutral_praise_triggers_no_complaint_theme(text):
    row = tagged(text).iloc[0]
    assert not any(row[t] for t in th.THEME_NAMES)
    assert row["Praise"]


def test_scrub_removes_personal_identifiers():
    s = th.scrub("call me on 08031234567 or +2348091234567, mail ade@example.com acct 0123456789")
    assert "0803" not in s and "8091234567" not in s and "ade@" not in s and "0123456789" not in s
    assert "[phone]" in s and "[email]" in s and "[number]" in s


def test_scrub_keeps_ordinary_numbers():
    assert th.scrub("I waited 3 days and lost 5000 naira") == "I waited 3 days and lost 5000 naira"


def test_clean_drops_short_duplicate_and_personal_data():
    raw = pd.DataFrame({
        "app": ["A", "A", "A", "A"], "sector": ["Bank"] * 4,
        "date": ["2026-01-02"] * 4, "rating": [1, 1, 5, 5],
        "text": ["ok", "Transfer failed call 08031234567", "Transfer failed call 08031234567", "Smooth and fast app"],
        "thumbs_up": [0] * 4, "app_version": ["1.0"] * 4})
    out = clean.clean(raw)
    assert len(out) == 2                                  # short review and the duplicate are gone
    assert not out.text_clean.str.contains("0803").any()
    assert "text" not in out.columns


def test_penalty_and_prevalence_on_known_data():
    rows = ([{"app": "A", "sector": "Bank", "rating": 1, "text_clean": "transfer failed"}] * 40
            + [{"app": "A", "sector": "Bank", "rating": 5, "text_clean": "smooth app"}] * 40)
    d = th.tag(pd.DataFrame(rows).assign(date=pd.Timestamp("2026-01-01"), month=pd.Timestamp("2026-01-01")))
    pen = analyze.penalty(d).set_index("theme")
    assert pen.loc["Failed or delayed transactions", "rating_penalty"] == pytest.approx(4.0)
    prev = analyze.prevalence(d).set_index("theme")
    assert prev.loc["Failed or delayed transactions", "share_of_negative_pct"] == pytest.approx(100.0)
