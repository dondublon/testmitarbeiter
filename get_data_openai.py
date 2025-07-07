import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json

from openai import OpenAI

with open("openai_key.txt", "r") as f:
    line = f.readline()
    client = OpenAI(api_key=line)

CONTACT_PATTERNS = ["kontakt", "contact", "impressum", "unternehmen", "about"]

PROMPT_TEMPLATE = """
Ниже HTML страницы. Извлеки и верни в JSON:
- "company_name": название компании
- "email": email
- "phone": телефон
- "country": страна (название или код)
- "description": краткое описание деятельности (1-2 предложения)
Если не нашёл телефон или email, ищи ссылку на страницу с контактами. В этом случае в ִּJSON добавь поле "contact_link".
Если на понял краткое описание деятельности, ищи раздел типа "about us". В этом случае добавь в JSON поле "about_link".
   
Ориентируйся на немецкий язык.
 
Вернуть только JSON, без пояснений.

HTML:
{}
"""
CONTACT_PROMPT_TEMLATE = """
Ниже HTML страницы. Извлеки и верни в JSON:
- "company_name": название компании
- "email": email
- "phone": телефон
Если на понял краткое описание деятельности, ищи раздел типа "about us". В этом случае добавь в JSON поле "about_link".

Ориентируйся на немецкий язык.

Вернуть только JSON, без пояснений.

HTML:
{}
"""
ABOUT_PROMPT_TEMPLATE =  """
Ниже HTML страницы. Извлеки и верни в JSON:
- "company_name": название компании
- "country": страна (название или код)
- "description": краткое описание деятельности (1-2 предложения)
Если не нашёл телефон или email, ищи ссылку на страницу с контактами. В этом случае в ִּJSON добавь поле "contact_link".
Если на понял краткое описание деятельности, ищи раздел типа "about us". В этом случае добавь в JSON поле "about_link".
   
Ориентируйся на немецкий язык.
 
Вернуть только JSON, без пояснений.

HTML:
{}
"""

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

def query_openai(html):
    prompt = PROMPT_TEMPLATE.format(html[:10000])  # ограничиваем размер
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # или "gpt-4"
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0,
    )
    content = response.choices[0].message.content
    json_obj = json.loads(content)

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
        home_page_result = query_internal(PROMPT_TEMPLATE, site)
        if "contact_link" in home_page_result:
            contact_link = urljoin(site, home_page_result["contact_link"])
            contact_result = query_internal(CONTACT_PROMPT_TEMLATE, contact_link)
        if "about" in home_page_result:
            about = urljoin(site, home_page_result["about_link"])
            about_result = query_internal(ABOUT_PROMPT_TEMPLATE, about)
        pass

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
