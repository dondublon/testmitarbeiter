import unittest
from unittest.mock import patch
import json
import os

# from src.database import CompanyDB

with patch("src.get_data_openai.Scrapper.get_client"):
    from src.get_data_openai import Scrapper  # замените your_module на имя модуля


class TestGetAll(unittest.TestCase):
    def setUp(self):
        self.scrapper = Scrapper()  # ":memory:" для in-memory базы
        self.scrapper.init('test_companies.db')

    def tearDown(self):
        self.scrapper.close()

    def mock_process_site(self, site):
        domain_filename = site.replace("https://", "").replace("http://", "").replace(".", "_").strip("/")
        filepath = os.path.join("oai_results", f"{domain_filename}.json")
        if not os.path.isfile(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @patch("src.get_data_openai.Scrapper.process_site")
    def test_get_all_with_mocked_data(self, mock_process_site):
        mock_process_site.side_effect = self.mock_process_site
        self.scrapper.get_all()

        db = self.scrapper.db
        db.cursor.execute("SELECT COUNT(*) FROM companies")
        count = db.cursor.fetchone()[0]

        self.assertGreater(count, 0, "Должны быть добавлены хотя бы некоторые записи из oai_results/")


if __name__ == "__main__":
    unittest.main()
