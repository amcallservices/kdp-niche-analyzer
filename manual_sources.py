"""Importazione prudente dei CSV strutturati di prodotti Amazon."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import pandas as pd

from automatic_sources import MARKETPLACES, ROOT_RANK_NAMES


REQUIRED_COLUMNS = {"asin", "title", "product_url"}
CURRENCY_CODES = {"€": "EUR", "$": "USD", "£": "GBP", "¥": "JPY", "R$": "BRL"}
DOMAIN_MARKETS = {domain: market for market, (domain, _) in MARKETPLACES.items()}


def is_products_csv(frame: pd.DataFrame) -> bool:
    columns = {str(column).strip().lstrip("\ufeff").strip('"').casefold() for column in frame.columns}
    return REQUIRED_COLUMNS <= columns


def _value(row: pd.Series, column: str) -> str:
    value = row.get(column)
    return "" if pd.isna(value) else str(value).strip()


def _positive_number(raw: str) -> float | None:
    text = re.sub(r"[^\d,.-]", "", raw)
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(",", "") if text.rfind(".") > text.rfind(",") else text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".") if len(text.rsplit(",", 1)[-1]) <= 2 else text.replace(",", "")
    try:
        number = float(text)
        return number if number > 0 else None
    except ValueError:
        return None


def _whole_number(raw: str, *, allow_zero: bool = False) -> int | None:
    text = raw.strip().lstrip("#").strip()
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    elif re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", text):
        text = text.replace(".", "").replace(",", "")
    if not re.fullmatch(r"\d+", text):
        return None
    number = int(text)
    return number if number > 0 or (allow_zero and number == 0) else None


def _market_from_url(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return DOMAIN_MARKETS.get(host)


def normalize_products_csv(
    frame: pd.DataFrame, selected_market: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Mappa solo valori presenti e non mescola BSR di mercati diversi."""
    if selected_market not in MARKETPLACES:
        raise ValueError("Marketplace non supportato")
    if not is_products_csv(frame):
        raise ValueError("CSV prodotti non riconosciuto")

    source = frame.copy()
    source.columns = [str(column).strip().lstrip("\ufeff").strip('"').casefold() for column in source.columns]
    rows = []
    skipped_market = 0
    skipped_invalid = 0
    for _, item in source.iterrows():
        asin = _value(item, "asin").upper()
        title = _value(item, "title")
        url = _value(item, "product_url")
        if not re.fullmatch(r"[A-Z0-9]{10}", asin) or not title:
            skipped_invalid += 1
            continue
        market = _market_from_url(url)
        if market and market != selected_market:
            skipped_market += 1
            continue

        category = _value(item, "bsr_category")
        rank = _whole_number(_value(item, "bsr_rank"))
        root_rank = rank if category.casefold() in ROOT_RANK_NAMES else None
        category_rank = f"{category}: {rank}" if rank and category and root_rank is None else ""
        raw_currency = _value(item, "currency")
        currency = CURRENCY_CODES.get(raw_currency, raw_currency.upper()) or MARKETPLACES[selected_market][1]
        price = _positive_number(_value(item, "price"))
        rating = _positive_number(_value(item, "rating"))
        reviews = _whole_number(_value(item, "review_count"), allow_zero=True)
        publisher = _value(item, "publisher")
        rows.append({
            "Copertina": _value(item, "image_url") or None,
            "Titolo": title,
            "BSR": root_rank,
            "BSR categorie": category_rank,
            "Prezzo": price,
            "Valuta": currency,
            "Autore": _value(item, "author") or "N/D",
            "Editore": publisher or "N/D",
            "Indipendente": "Da verificare",
            "Formato": _value(item, "format") or "N/D",
            "Recensioni": reviews,
            "Valutazione media": rating,
            "ASIN": asin,
            "URL": url,
            "Mercato fonte": market or "Da verificare",
            "Tipo venditore": _value(item, "seller_type") or "N/D",
            "Venditore": _value(item, "seller_name") or "N/D",
            "Acquisti mese dichiarati": _value(item, "bought_past_month") or "N/D",
        })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.drop_duplicates(subset=["ASIN"], keep="first").reset_index(drop=True)
    return result, {
        "read": len(source),
        "included": len(result),
        "other_market": skipped_market,
        "invalid": skipped_invalid,
    }
