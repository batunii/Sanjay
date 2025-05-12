import requests
from bs4 import BeautifulSoup
from newspaper import Article

from ndtv_module import get_from_ndtv

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def get_article_time(link):
    resp = requests.get(link, headers=HEADERS)
    new_soup = BeautifulSoup(resp.text, 'html.parser')
    content = new_soup.find("meta", {'name':'description'})
    desc = content['content']
    published_date = new_soup.find("meta",{'name':'publish-date'})
    if not published_date:
        published_date = new_soup.find("div", {'class': "pst-by_lnk-dt"})
    date = published_date.get('content', published_date.get_text()) if published_date is not None else None
    print(date)
    return desc, date, link 


