import json
import unittest
from urllib.error import URLError

from automatic_sources import (
    MARKETPLACES,
    SourceError,
    estimated_provider_credits,
    fetch_review_sample,
    normalize_search_results,
    search_amazon_books,
)


PAYLOAD = {
    "request_info": {"success": True, "credits_used_this_request": 6},
    "request_metadata": {"created_at": "2026-10-17T10:00:00Z"},
    "search_results": [
        {
            "position": 1,
            "asin": "B012345678",
            "title": "Guida alla scrittura",
            "image": "https://example.test/cover.jpg",
            "price": {"value": 14.9, "currency": "EUR"},
            "ratings_total": 42,
            "authors": [{"name": "Maria Rossi"}],
            "sponsored": False,
            "product": {
                "publisher": "Independently published",
                "format": "Paperback",
                "reviews_total": 25,
                "bestsellers_rank": [
                    {"rank": 12000, "category": "Libri"},
                    {"rank": 15, "category": "Scrittura creativa"},
                ],
            },
        },
        {"asin": "B012345678", "title": "Duplicato"},
        {
            "position": 2,
            "asin": "B012345679",
            "title": "Manuale editoriale",
            "price": {"value": 12.0, "currency": "EUR"},
            "product": {
                "publisher": "Editore Sconosciuto",
                "bestsellers_rank": [
                    {"rank": 7, "category": "Scrittura creativa"},
                ],
            },
        },
        {
            "position": 3,
            "asin": "B099999999",
            "title": "Batteria per fotocamera",
            "product": {"search_alias": {"title": "Electronics"}},
        },
    ],
}


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(PAYLOAD).encode("utf-8")


class SourceTests(unittest.TestCase):
    def test_marketplaces_are_supported(self):
        for code in ("IT", "US", "UK", "DE", "FR", "ES", "CA", "AU", "NL", "BR", "JP"):
            self.assertIn(code, MARKETPLACES)

    def test_additional_market_uses_its_own_domain_and_currency(self):
        frame = normalize_search_results(PAYLOAD, "CA")
        self.assertEqual(frame.iloc[0]["URL"], "https://www.amazon.ca/dp/B012345678")

    def test_cost_is_explicit(self):
        self.assertEqual(estimated_provider_credits(5), 6)
        self.assertEqual(estimated_provider_credits(10), 11)
        with self.assertRaises(ValueError):
            estimated_provider_credits(500)

    def test_rank_and_independent_evidence_are_separate(self):
        frame = normalize_search_results(PAYLOAD, "IT")
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.iloc[0]["BSR"], 12000)
        self.assertIn("Scrittura creativa: 15", frame.iloc[0]["BSR categorie"])
        self.assertIn("Indipendente", frame.iloc[0]["Indipendente"])
        self.assertEqual(frame.iloc[0]["Recensioni"], 25)
        self.assertEqual(frame.iloc[0]["Valutazioni"], 42)
        self.assertTrue(frame.iloc[1]["BSR"] != frame.iloc[1]["BSR"])
        self.assertEqual(frame.iloc[1]["Indipendente"], "Da verificare")

    def test_request_and_actual_cost(self):
        observed_urls = []

        def opener(url, timeout):
            observed_urls.append((url, timeout))
            return FakeResponse()

        frame, credits = search_amazon_books(
            keyword="scrittura creativa", marketplace="IT", count=5,
            api_key="personal-test-key", opener=opener,
        )
        self.assertEqual(len(frame), 2)
        self.assertEqual(credits, 6)
        self.assertIn("exclude_sponsored=true", observed_urls[0][0])
        self.assertIn("include_products_count=5", observed_urls[0][0])

    def test_missing_key_never_calls_provider(self):
        def opener(_url, _timeout):
            self.fail("Network call must not happen")

        with self.assertRaises(SourceError):
            search_amazon_books(
                keyword="nicchia", marketplace="IT", count=5,
                api_key="", opener=opener,
            )

    def test_network_error_does_not_expose_key(self):
        def opener(url, timeout):
            raise URLError(f"Failed: {url}")

        with self.assertRaises(SourceError) as caught:
            search_amazon_books(
                keyword="nicchia", marketplace="IT", count=5,
                api_key="private-secret", opener=opener,
            )
        self.assertNotIn("private-secret", str(caught.exception))

    def test_reviews_are_filtered_and_credit_counted(self):
        observed_urls = []

        class ReviewResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        def opener(url, timeout):
            observed_urls.append(url)
            positive = "all_positive" in url
            return ReviewResponse({
                "request_info": {"success": True, "credits_used_this_request": 1},
                "reviews": [{
                    "id": "positive" if positive else "critical",
                    "rating": 5 if positive else 1,
                    "title": "Good" if positive else "Missing detail",
                    "body": "Helpful examples" if positive else "I wanted more examples",
                    "profile": {"name": "Do not store this"},
                }],
            })

        reviews, credits, unavailable = fetch_review_sample(
            marketplace="DE", asins=["B012345678"], api_key="private-secret", opener=opener,
        )
        self.assertEqual((len(reviews), credits, unavailable), (2, 2, 0))
        self.assertEqual({item["group"] for item in reviews}, {"positiva", "critica"})
        self.assertNotIn("profile", reviews[0])
        self.assertTrue(all("amazon.de" in url for url in observed_urls))

    def test_reviews_reject_missing_key_without_network_call(self):
        def opener(_url, _timeout):
            self.fail("Network call must not happen")

        with self.assertRaises(SourceError):
            fetch_review_sample(
                marketplace="IT", asins=["B012345678"], api_key="", opener=opener,
            )


if __name__ == "__main__":
    unittest.main()
