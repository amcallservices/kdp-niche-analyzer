import unittest

import pandas as pd

from manual_sources import is_products_csv, normalize_products_csv


class ManualSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = pd.DataFrame([
            {
                "ASIN": "B0H9X7LYN2",
                "Title": "La Badante: Guida per le Famiglie",
                "Price": 6.99,
                "Currency": "€",
                "BSR_Rank": None,
                "BSR_Category": None,
                "Rating": None,
                "Review_Count": None,
                "Seller_Type": "UNKNOWN",
                "Seller_Name": None,
                "Bought_Past_Month": None,
                "Product_URL": "https://www.amazon.it/dp/B0H9X7LYN2",
            },
            {
                "ASIN": "B0H65Y3GLQ",
                "Title": "Genitori anziani e badante",
                "Price": 0,
                "Currency": "€",
                "BSR_Rank": 149976.0,
                "BSR_Category": "Kindle Store",
                "Rating": None,
                "Review_Count": 0,
                "Seller_Type": "UNKNOWN",
                "Seller_Name": None,
                "Bought_Past_Month": None,
                "Product_URL": "https://www.amazon.com/dp/B0H65Y3GLQ",
            },
        ])

    def test_two_title_file_is_recognized_and_market_is_separated(self):
        self.assertTrue(is_products_csv(self.source))
        italian, info = normalize_products_csv(self.source, "IT")
        self.assertEqual(len(italian), 1)
        self.assertEqual(info["other_market"], 1)
        self.assertEqual(italian.iloc[0]["Titolo"], "La Badante: Guida per le Famiglie")
        self.assertEqual(italian.iloc[0]["Prezzo"], 6.99)
        self.assertEqual(italian.iloc[0]["Valuta"], "EUR")
        self.assertTrue(pd.isna(italian.iloc[0]["BSR"]))
        self.assertEqual(italian.iloc[0]["Indipendente"], "Da verificare")

    def test_rank_is_not_multiplied_and_zero_price_is_missing(self):
        us, info = normalize_products_csv(self.source, "US")
        self.assertEqual(info["other_market"], 1)
        self.assertEqual(us.iloc[0]["BSR"], 149976)
        self.assertTrue(pd.isna(us.iloc[0]["Prezzo"]))
        self.assertEqual(us.iloc[0]["Recensioni"], 0)
        self.assertEqual(us.iloc[0]["Valuta"], "EUR")

    def test_category_rank_is_not_merged_into_general_bsr(self):
        source = self.source.iloc[[0]].copy()
        source["BSR_Rank"] = source["BSR_Rank"].astype(object)
        source.loc[source.index[0], "BSR_Rank"] = "#1.234"
        source.loc[source.index[0], "BSR_Category"] = "Assistenza anziani"
        italian, _ = normalize_products_csv(source, "IT")
        self.assertTrue(pd.isna(italian.iloc[0]["BSR"]))
        self.assertEqual(italian.iloc[0]["BSR categorie"], "Assistenza anziani: 1234")


if __name__ == "__main__":
    unittest.main()
