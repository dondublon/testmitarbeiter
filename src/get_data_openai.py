import os
import logging
import json
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

from src.database import CompanyDB

logging.basicConfig(
    level=logging.INFO,  # Показывает debug и выше
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

with open("openai_key.txt", "r") as f:
    line = f.readline()
    client = OpenAI(api_key=line)

CONTACT_PATTERNS = ["kontakt", "contact", "impressum", "unternehmen", "about"]

with open('prompts/general.txt') as fpg:
    PROMPT_TEMPLATE = fpg.read()

with open('prompts/contact.txt') as fpc:
    CONTACT_PROMPT_TEMLATE = fpc.read()

with open('prompts/about.txt') as fpa:
    ABOUT_PROMPT_TEMPLATE =  fpa.read()

model="gpt-3.5-turbo"


# def find_contact_link(base_url, html):
#     soup = BeautifulSoup(html, "lxml")
#     for a in soup.find_all("a", href=True):
#         href = a["href"].lower()
#         if any(p in href for p in CONTACT_PATTERNS):
#             return urljoin(base_url, a["href"])
#     return None

def get_clean_html_text(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    return str(soup)

# def query_openai(html):
#     prompt = PROMPT_TEMPLATE.format(html[:10000])  # ограничиваем размер
#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",  # или "gpt-4"
#         messages=[
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0,
#     )
#     content = response.choices[0].message.content
#     json_obj = json.loads(content)

def query_internal(prompt, url):
    r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    html = r.text
    clean_html = get_clean_html_text(html)
    to_propmt = prompt.format(clean_html[:10000])
    response = client.chat.completions.create(
        model=model,  # или "gpt-4"
        messages=[
            {"role": "user", "content": to_propmt}
        ],
        temperature=0,
    )
    content = response.choices[0].message.content
    json_obj = json.loads(content)
    return json_obj

def process_site(site):
    try:
        logger.info("Getting %s", site)
        home_page_result = query_internal(PROMPT_TEMPLATE, site)
        logger.info("\tHomepage result %s", site)
        contact_result = about_result = {}
        if "contact_link" in home_page_result:
            contact_link = urljoin(site, home_page_result["contact_link"])
            contact_result = query_internal(CONTACT_PROMPT_TEMLATE, contact_link)
            logger.info("\tContact result %s", contact_result)
        if "about" in home_page_result:
            about = urljoin(site, home_page_result["about_link"])
            about_result = query_internal(ABOUT_PROMPT_TEMPLATE, about)
            logger.info("\t'About' result %s", contact_result)
        final_result = home_page_result.copy()
        final_result["phone"] = home_page_result.get("phone") or contact_result.get("phone")
        final_result["email"] = home_page_result.get("email") or contact_result.get("email")
        final_result['description'] = home_page_result.get("description") or about_result.get("description")
        return final_result

    except Exception as e:
        print(f"[!] Ошибка для {site}: {e}")
        return None

os.makedirs("results", exist_ok=True)

with open("sites.txt", "r") as f:
    sites = [line.strip() for line in f if line.strip()]

def get_all():
    db = CompanyDB()
    for site in sites:
        result = process_site(site)
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
    get_all()