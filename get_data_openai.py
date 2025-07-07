import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import openai
import json

with open("openai_key.txt", "r") as f:
    line = f.readline()
    openai.api_key = line

CONTACT_PATTERNS = ["kontakt", "contact", "impressum", "unternehmen", "about"]

PROMPT_TEMPLATE = """
Ниже HTML страницы. Извлеки и верни в JSON:
- "company_name": название компании
- "email": email
- "phone": телефон
- "country": страна (название или код)
- "description": краткое описание деятельности (1-2 предложения)

Только JSON, без пояснений.

HTML:
{}
"""

def find_contact_link(base_url, html):
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(p in href for p in CONTACT_PATTERNS):
            return urljoin(base_url, a["href"])
    return None

def get_clean_html_text(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    return str(soup)

def query_openai(html):
    prompt = PROMPT_TEMPLATE.format(html[:10000])  # ограничиваем размер
    response = openai.ChatCompletion.create(
        model="gpt-4",  # можно заменить на gpt-3.5-turbo
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    content = response["choices"][0]["message"]["content"]
    return json.loads(content)

def process_site(site):
    try:
        r = requests.get(site, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        html = r.text

        contact_url = find_contact_link(site, html)
        if contact_url:
            r = requests.get(contact_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            html = r.text

        clean_html = get_clean_html_text(html)
        return query_openai(clean_html)

    except Exception as e:
        print(f"[!] Ошибка для {site}: {e}")
        return None

os.makedirs("results", exist_ok=True)

with open("sites.txt", "r") as f:
    sites = [line.strip() for line in f if line.strip()]

for site in sites:
    result = process_site(site)
    if result:
        domain = urlparse(site).netloc.replace(".", "_")
        with open(f"results/{domain}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
