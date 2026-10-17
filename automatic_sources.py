"""Ricerca Amazon tramite un fornitore dati configurato, senza scraping nell'app."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


MARKETPLACES = {
    "IT": ("amazon.it", "EUR"),
    "US": ("amazon.com", "USD"),
    "UK": ("amazon.co.uk", "GBP"),
    "DE": ("amazon.de", "EUR"),
    "FR": ("amazon.fr", "EUR"),
    "ES": ("amazon.es", "EUR"),
    "CA": ("amazon.ca", "CAD"),
    "AU": ("amazon.com.au", "AUD"),
    "NL": ("amazon.nl", "EUR"),
    "BR": ("amazon.com.br", "BRL"),
    "JP": ("amazon.co.jp", "JPY"),
}
ROOT_RANK_NAMES = {
    "books", "kindle store", "libri", "negozio kindle", "bücher",
    "kindle-shop", "livres", "boutique kindle", "libros", "tienda kindle",
    "boeken", "livros", "書籍",
}
BOOK_FORMATS = {
    "paperback", "hardcover", "kindle", "ebook", "e-book",
    "copertina flessibile", "copertina rigida", "broché", "relié",
    "taschenbuch", "gebundene ausgabe", "tapa blanda", "tapa dura",
}
SOURCE_URL = "https://api.rainforestapi.com/request"


class SourceError(RuntimeError):
    """Errore presentabile all'utente, senza dati riservati."""


def estimated_provider_credits(count: int) -> int:
    if count not in (5, 10, 20):
        raise ValueError("Numero di risultati non supportato")
    return 1 + count


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _positive_number(value: Any) -> int | None:
    try:
        number = int(value)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def _price(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def _author_name(result: dict, product: dict) -> str:
    author = product.get("author")
    if isinstance(author, dict) and author.get("name"):
        return str(author["name"])
    if isinstance(author, str) and author.strip():
        return author.strip()
    for item in result.get("authors") or []:
        if isinstance(item, dict) and item.get("name"):
            return str(item["name"])
    return "N/D"


def _rank_values(product: dict) -> tuple[int | None, str]:
    root = None
    categories = []
    for entry in product.get("bestsellers_rank") or []:
        if not isinstance(entry, dict):
            continue
        rank = _positive_number(entry.get("rank"))
        category = str(entry.get("category") or "").strip()
        if not rank:
            continue
        if category.casefold() in ROOT_RANK_NAMES and root is None:
            root = rank
        else:
            categories.append(f"{category}: {rank}" if category else str(rank))
    return root, " | ".join(categories)


def _indie_status(publisher: str) -> str:
    if publisher.casefold().strip() in {
        "independently published", "pubblicazione indipendente",
        "auto-publié", "autopublicado", "selbst veröffentlicht",
    }:
        return "Indipendente: indicato nella scheda"
    return "Da verificare"


def _is_book_product(result: dict, product: dict) -> bool:
    if result.get("authors"):
        return True
    if str(product.get("publisher") or "").strip():
        return True
    book_format = str(product.get("format") or "").casefold()
    if any(name in book_format for name in BOOK_FORMATS):
        return True
    alias = _mapping(product.get("search_alias"))
    if str(alias.get("title") or "").casefold() in ROOT_RANK_NAMES:
        return True
    for rank in product.get("bestsellers_rank") or []:
        if str(_mapping(rank).get("category") or "").casefold() in ROOT_RANK_NAMES:
            return True
    return False


def normalize_search_results(payload: dict, marketplace: str) -> pd.DataFrame:
    """Conserva solo dati osservati; non stima vendite o status editoriali."""
    if marketplace not in MARKETPLACES:
        raise ValueError("Marketplace non supportato")
    metadata = _mapping(payload.get("request_metadata"))
    observed_at = str(metadata.get("created_at") or datetime.now(timezone.utc).isoformat())
    domain, default_currency = MARKETPLACES[marketplace]
    rows = []
    seen_asins = set()
    for result in payload.get("search_results") or []:
        if not isinstance(result, dict):
            continue
        asin = str(result.get("asin") or "").strip().upper()
        title = str(result.get("title") or "").strip()
        if not asin or not title or asin in seen_asins:
            continue
        product = _mapping(result.get("product"))
        if not _is_book_product(result, product):
            continue
        seen_asins.add(asin)
        rank, category_ranks = _rank_values(product)
        price_data = _mapping(result.get("price")) or _mapping(product.get("price"))
        publisher = str(product.get("publisher") or "").strip()
        image = product.get("main_image") or result.get("image") or ""
        if isinstance(image, dict):
            image = image.get("link") or ""
        rows.append({
            "Copertina": image,
            "Titolo": title,
            "BSR": rank,
            "BSR categorie": category_ranks,
            "Prezzo": _price(price_data.get("value")),
            "Valuta": str(price_data.get("currency") or default_currency),
            "Autore": _author_name(result, product),
            "Editore": publisher or "N/D",
            "Indipendente": _indie_status(publisher),
            "Formato": str(product.get("format") or "N/D"),
            "Recensioni": _positive_number(product.get("reviews_total")),
            "Valutazioni": _positive_number(result.get("ratings_total")),
            "ASIN": asin,
            "URL": f"https://www.{domain}/dp/{asin}",
            "Sponsorizzato": bool(result.get("sponsored", False)),
            "Posizione ricerca": _positive_number(result.get("position")),
            "Fonte": "Rainforest API (dati Amazon)",
            "Rilevato il": observed_at,
        })
    return pd.DataFrame(rows)


def _request_payload(params: dict, opener: Any) -> dict:
    try:
        with opener(f"{SOURCE_URL}?{urlencode(params)}", timeout=150) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        # Non concatenare l'eccezione originale: l'URL contiene la chiave API.
        raise SourceError("La fonte dati non è raggiungibile o ha risposto in modo non valido") from None
    return payload if isinstance(payload, dict) else {}


def _credits_used(payload: dict, fallback: int) -> int:
    value = _mapping(payload.get("request_info")).get("credits_used_this_request")
    try:
        return max(0, int(value)) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def search_amazon_books(
    *, keyword: str, marketplace: str, count: int, api_key: str,
    include_sponsored: bool = False, opener: Any = urlopen,
) -> tuple[pd.DataFrame, int]:
    """Una richiesta Search + Product; restituisce righe e crediti effettivi."""
    keyword = keyword.strip()
    if not keyword or len(keyword) > 160:
        raise ValueError("Inserisci una nicchia di 1-160 caratteri")
    if marketplace not in MARKETPLACES:
        raise ValueError("Marketplace non supportato")
    estimated_provider_credits(count)
    if not api_key.strip():
        raise SourceError("Configura la chiave Rainforest API prima della ricerca")

    params = {
        "api_key": api_key.strip(),
        "type": "search",
        "amazon_domain": MARKETPLACES[marketplace][0],
        "search_term": keyword,
        "number_of_results": count,
        "include_products_count": count,
        "exclude_sponsored": str(not include_sponsored).lower(),
    }
    payload = _request_payload(params, opener)
    if not _mapping(payload.get("request_info")).get("success"):
        raise SourceError("La fonte dati ha rifiutato la richiesta: verifica chiave, saldo e limiti del servizio")

    frame = normalize_search_results(payload, marketplace)
    return frame, _credits_used(payload, estimated_provider_credits(count))


def fetch_review_sample(
    *, marketplace: str, asins: list[str], api_key: str,
    opener: Any = urlopen,
) -> tuple[list[dict], int, int]:
    """Legge una pagina positiva e una critica per massimo tre libri."""
    if marketplace not in MARKETPLACES:
        raise ValueError("Marketplace non supportato")
    if not api_key.strip():
        raise SourceError("Configura la chiave Rainforest API prima di leggere le recensioni")
    selected = []
    for raw_asin in asins:
        asin = str(raw_asin).strip().upper()
        if re.fullmatch(r"[A-Z0-9]{10}", asin) and asin not in selected:
            selected.append(asin)
        if len(selected) == 3:
            break
    if not selected:
        raise ValueError("Nessun ASIN valido per la lettura delle recensioni")

    reviews = []
    credits = 0
    unavailable = 0
    seen = set()
    for asin in selected:
        for group, filter_name in (("positiva", "all_positive"), ("critica", "all_critical")):
            params = {
                "api_key": api_key.strip(),
                "type": "reviews",
                "amazon_domain": MARKETPLACES[marketplace][0],
                "asin": asin,
                "review_stars": filter_name,
                "sort_by": "most_recent",
            }
            try:
                payload = _request_payload(params, opener)
            except SourceError:
                unavailable += 1
                continue
            if not _mapping(payload.get("request_info")).get("success"):
                unavailable += 1
                continue
            credits += _credits_used(payload, 1)
            accepted = 0
            for item in payload.get("reviews") or []:
                if accepted == 5:
                    break
                if not isinstance(item, dict):
                    continue
                body = str(item.get("body") or "").strip()[:700]
                title = str(item.get("title") or "").strip()[:160]
                if not body:
                    continue
                try:
                    rating = float(item.get("rating"))
                except (TypeError, ValueError):
                    rating = None
                if rating is not None and (rating < 4 if group == "positiva" else rating > 2):
                    continue
                identity = f"{asin}:{item.get('id') or body}"
                if identity in seen:
                    continue
                seen.add(identity)
                reviews.append({
                    "asin": asin,
                    "group": group,
                    "rating": rating,
                    "title": title,
                    "body": body,
                })
                accepted += 1
    return reviews, credits, unavailable
