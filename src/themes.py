"""Rule-based theme tagging for Nigerian fintech, banking and telecom app reviews.

Each theme is a regular expression over lower-cased text. A review can carry several themes.
Rules are intentionally transparent (no black-box model) so a reader can audit and edit them;
tests/test_themes.py pins their behaviour and README.md reports an audit of precision.
"""
from __future__ import annotations

import re
import warnings

import pandas as pd

_TXN = r"(?:transaction|transfer|payment|withdraw\w*|deposit|purchase|top ?up|bill)s?"
_BAD = r"(?:fail\w*|pending|declin\w*|stuck|delay\w*)"

THEMES: dict[str, str] = {
    "Failed or delayed transactions": (
        r"\b(?:reversal|refund(?:ed)?|debit(?:ed)? (?:me )?(?:but|without)|deduct(?:ed|ion)? (?:but|without)|"
        r"money (?:not|never|no) (?:reach|arriv|reflect|credit)\w*|lost (?:my )?money|missing money|"
        + _TXN + r"(?: \w+){0,4} (?:" + _BAD[3:-1] + r"|not (?:go|goes|went|reflect|credit|receiv)\w*|revers\w*)|"
        + _BAD + r" (?:\w+ ){0,3}" + _TXN + r")\b"
    ),
    "Login, OTP and verification": (
        r"\b(?:otp|log ?in|sign ?in|verif(?:y|ied|ication|ying)|bvn|nin|kyc|face (?:id|scan|recognition|verification)|"
        r"password|biometric|locked out|can'?t (?:log|sign|access)|cannot (?:log|sign|access)|"
        r"new device|sim (?:swap|registration))\b"
    ),
    "Fees and charges": (
        r"\b(?:charge[sd]?|fees?|stamp duty|vat|commission|expensive|overcharg\w*|"
        r"too much (?:money|deduct\w*)|high rate|exorbitant)\b"
    ),
    "Customer support": (
        r"\b(?:customer (?:care|service|support|centre|center)|support team|no (?:response|reply)|"
        r"respond(?:ed|ing)?|complain(?:t|ed|ing)?s?|call ?cent(?:re|er)|chat ?bot|help ?desk|ticket|"
        r"nobody (?:answers|responds|replies))\b"
    ),
    "App performance and downtime": (
        r"\b(?:slow(?:ly)?|crash(?:es|ed|ing)?|not working|doesn'?t work|glitch(?:es|y)?|bugs?|buggy|loading|"
        r"freez(?:e|es|ing)|hang(?:s|ing)?|network (?:error|issue|problem)|server|downtime|keeps (?:closing|stopping)|"
        r"error|timeout|time out|maintenance|unavailable)\b"
    ),
    "Account restriction or freeze": (
        r"\b(?:restrict(?:ed|ion|ions)?|froze(?:n)?|freez(?:e|ing) (?:my )?account|block(?:ed|ing)? (?:my )?account|"
        r"suspend(?:ed|sion)?|pnd|post no debit|lien|deactivat(?:ed|ion)|account (?:closed|disabled|limit)|banned?|"
        r"tier (?:1|2|3|one|two|three)|transaction limit|daily limit)\b"
    ),
    "Fraud and security": (
        r"\b(?:fraud(?:ster|sters|ulent)?|scam(?:s|med|mer|mers)?|hack(?:ed|er|ers|ing)?|stole(?:n)?|"
        r"unauthori[sz]ed|thie(?:f|ves)|theft|phishing|impersonat\w+|compromised)\b"
    ),
    "Loans and credit": (
        r"\b(?:loans?|borrow(?:ed|ing)?|repay(?:ment|ments|ed)?|credit score|overdraft|debt|interest|"
        r"loan app|defaulter|harass(?:ed|ing|ment)?)\b"
    ),
    "Data, airtime and bundles": (
        r"\b(?:airtime|data (?:bundle|plan|subscription|expire\w*|finish\w*)|bundles?|recharge|top ?up|"
        r"mb|gb|gigs?|subscription|renew(?:al)?)\b"
    ),
}

PRAISE = (r"\b(?:great|good|nice|best|love|loved|easy|fast|quick|smooth|reliable|excellent|awesome|"
          r"amazing|helpful|satisfied|perfect|seamless|convenient)\b")

_PHONE = re.compile(r"(?<!\d)(?:\+?234|0)[789][01]\d{8}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONGNUM = re.compile(r"(?<!\d)\d{8,}(?!\d)")


def scrub(text: str) -> str:
    """Remove phone numbers, emails and account-like digit runs from a review."""
    t = _EMAIL.sub("[email]", str(text))
    t = _PHONE.sub("[phone]", t)
    return _LONGNUM.sub("[number]", t)


def tag(df: pd.DataFrame, text_col: str = "text_clean") -> pd.DataFrame:
    """Add one boolean column per theme, plus Praise."""
    low = df[text_col].str.lower()
    out = df.copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        for name, rx in THEMES.items():
            out[name] = low.str.contains(rx, regex=True)
        out["Praise"] = low.str.contains(PRAISE, regex=True)
    return out


THEME_NAMES = list(THEMES)
