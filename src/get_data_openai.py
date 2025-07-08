import os
import logging
import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

from src.database import CompanyDB

logging.basicConfig(
    level=logging.INFO,  # Показывает debug и выше
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

class Scrapper:
    def get_client(self):
        with open("src/openai_key.txt", "r") as f:
            line = f.readline()
            client = OpenAI(api_key=line)
        return client

    def init(self):
        with open('src/prompts/general.txt') as fpg:
            self.PROMPT_TEMPLATE = fpg.read()

        with open('src/prompts/contact.txt') as fpc:
            self.CONTACT_PROMPT_TEMLATE = fpc.read()

        with open('src/prompts/about.txt') as fpa:
            self.ABOUT_PROMPT_TEMPLATE =  fpa.read()

        self.ai_model="gpt-3.5-turbo"

        os.makedirs("results", exist_ok=True)

    def get_clean_html_text(cls, html):
        soup = BeautifulSoup(html, "lxml")
        #for tag in soup(["script", "style", "noscript"]):
        #    tag.extract()
        #return str(soup)
        textonly = soup.get_text()
        return textonly


    def query_internal(self, client, prompt, url):
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        html = r.text
        clean_html = self.get_clean_html_text(html)
        to_propmt = prompt.format(clean_html[:20000])
        response = client.chat.completions.create(
            model=self.ai_model,  # или "gpt-4"
            messages=[
                {"role": "user", "content": to_propmt}
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        json_obj = json.loads(content)
        return json_obj

    def process_site(self, client, site):
        try:
            logger.info("Getting %s", site)
            home_page_result = self.query_internal(client, self.PROMPT_TEMPLATE, site)
            logger.info("\tHomepage result %s", site)
            contact_result = about_result = {}
            if "contact_link" in home_page_result:
                contact_link = urljoin(site, home_page_result["contact_link"])
                contact_result = self.query_internal(client, self.CONTACT_PROMPT_TEMLATE, contact_link)
                logger.info("\tContact result %s", contact_result)
            if "about" in home_page_result:
                about = urljoin(site, home_page_result["about_link"])
                about_result = self.query_internal(client, self.ABOUT_PROMPT_TEMPLATE, about)
                logger.info("\t'About' result %s", contact_result)
            final_result = home_page_result.copy()
            final_result["phone"] = home_page_result.get("phone") or contact_result.get("phone")
            final_result["email"] = home_page_result.get("email") or contact_result.get("email")
            final_result['description'] = home_page_result.get("description") or about_result.get("description")
            return final_result

        except Exception as e:
            print(f"[!] Ошибка для {site}: {e}")
            return None

    def get_all(self):
        with open("src/sites.txt", "r") as f:
            sites = [line.strip() for line in f if line.strip()]

        db = CompanyDB()
        client = self.get_client()
        for site in sites:
            result = self.process_site(client, site)
            if result:
                # to dump results:
                # domain_filename = urlparse(site).netloc.replace(".", "_")
                # with open(f"oai_results/{domain_filename}.json", "w", encoding="utf-8") as f:
                #     json.dump(result, f, ensure_ascii=False, indent=2)  # noqa
                db.add(name=result.get('company_name'),
                       website=site,
                       country=result.get('country'),
                       description=result.get('description'),
                       phone=result.get('phone'),
                       email=result.get('email')
                       )
        db.close()

if __name__ == "__main__":
    scrapper = Scrapper()
    scrapper.init()
    scrapper.get_all()
