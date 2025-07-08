import unittest
from unittest.mock import patch
import json
import os

from src.get_data_openai import get_all, CompanyDB, sites  # замените your_module на имя модуля

class TestGetAll(unittest.TestCase):
    def setUp(self):
        self.db = CompanyDB()  # ":memory:" для in-memory базы

    def tearDown(self):
        self.db.close()

    def mock_process_site(self, site):
        domain_filename = site.replace("https://", "").replace("http://", "").replace(".", "_").strip("/")
        filepath = os.path.join("oai_results", f"{domain_filename}.json")
        if not os.path.isfile(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @patch("your_module.process_site")
    def test_get_all_with_mocked_data(self, mock_process_site):
        mock_process_site.side_effect = self.mock_process_site
        get_all()

        db = CompanyDB()  # подключаемся к реальной базе, если не in-memory
        db.cursor.execute("SELECT COUNT(*) FROM companies")
        count = db.cursor.fetchone()[0]
        db.close()

        self.assertGreater(count, 0, "Должны быть добавлены хотя бы некоторые записи из oai_results/")

if __name__ == "__main__":
    unittest.main()
