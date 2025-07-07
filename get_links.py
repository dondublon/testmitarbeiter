import requests
from lxml import html

url = "https://eurobike.com/frankfurt/de.html"
headers = {"User-Agent": "Mozilla/5.0"}

r = requests.get(url, headers=headers)
tree = html.fromstring(r.content)

# XPath к нужным ссылкам
# links = tree.xpath('//a[contains(@class, "a-link--external")]/@href')
links = tree.xpath('/html/body/main/footer//a[contains(@class, "a-link--external")]/@href')


for link in links:
    print(link)
