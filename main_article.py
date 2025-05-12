import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser
from fuzzywuzzy import fuzz
from ndtv_module import get_from_ndtv
from ndtv_time_desc import get_article_time
from rapidfuzz import fuzz
import hashlib

# Define IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


KEYWORDS = ["india", "pakistan", "war", "conflict"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def normalize_datetime(dt):
    """Parses datetime input to a timezone-aware IST datetime. If invalid, returns current IST time."""
    if dt is None:
        return datetime.today().replace(tzinfo=IST)

    if not isinstance(dt, datetime):
        try:
            dt = parser.parse(str(dt))
        except Exception:
            return datetime.today().replace(tzinfo=IST)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)

    return dt


def extract_publish_time(soup):
    meta = soup.find("meta", attrs={"property": "article:published_time"})
    if meta and meta.get("content"):
        return meta["content"]

    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        return time_tag["datetime"]
    if time_tag:
        return time_tag.get_text(strip=True)

    for tag in soup.find_all(["span", "div"]):
        cls = " ".join(tag.get("class", []))
        if any(k in cls.lower() for k in ["date", "time", "publish"]):
            return tag.get_text(strip=True)

    return "Unknown"


def fetch_article_text(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text() for p in paragraphs)
        publish_time = extract_publish_time(soup)
        return text, publish_time, url
    except:
        return "", "Unknown", url


def get_ndtv_news():
    url = "https://special.ndtv.com/operation-sindoor-200/news"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    articles = []
    link_and_headlines: dict = get_from_ndtv(soup)
    for headline, link in link_and_headlines.items():
        article, time, final_url = get_article_time(link)
        if time is not None and "IST" in time:
            time = time[:18]
        if article and any(word in article.lower() for word in KEYWORDS):
            articles.append((headline, article, time, "NDTV", final_url))
    return articles


def get_toi_time(link):
    response = requests.get(link)
    soup = BeautifulSoup(response.text, "html.parser")
    time_class = soup.find_all("span")
    for time in time_class:
        if "Updated: " in (time_text := time.get_text(strip=True)):
            # print(time_text[9:])
            return time_text[9:]
    return None


def get_toi():
    url = "https://timesofindia.indiatimes.com/india/operation-sindoor"
    articles = []
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    captions = soup.find_all("a", class_="Hn2z7")
    for caption in captions:
        link = caption.get("href")
        headline = "NA"
        headline_class = caption.find_all("figcaption", class_="sNF1c")
        headline_blank = caption.find_all("figcaption")
        if headline_class:
            headline = headline_class[0].get_text()
        if headline_blank:
            headline = headline_blank[0].get_text()
        # print(headline)
        article, time, final_url = fetch_article_text(link)
        time = get_toi_time(link)
        if time is not None:
            # print(f"{time=}")
            articles.append((headline, article, time, "TOI", final_url))
    return articles


def get_indianexpress_news():
    url = "https://indianexpress.com/latest-news/"
    articles = []
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    for article_tag in soup.select(".articles a"):
        link = article_tag.get("href")
        headline = article_tag.get_text(strip=True)
        if not link.startswith("http"):
            link = urljoin(url, link)
        article, time, final_url = fetch_article_text(link)
        if article and any(word in article.lower() for word in KEYWORDS):
            articles.append((headline, article, time, "Indian Express", final_url))
    return articles


def filter_headline(headline: str, thold: int) -> bool:
    headline_lower = re.findall(r"\b\w+\b", headline.lower())
    if not headline_lower:
        return False
    filter_words = [
        "pakistan",
        "shelling",
        "blackout",
        "drones",
        "ceasefire",
        "war",
        "conflict",
        "pak",
        "jammu",
        "kashmir",
        "army",
        "forces",
        "attack",
        "sindoor",
        "terror",
        "terrorist",
        "china",
        "indo-pak",
        "border",
        "pok",
        "retaliation"
    ]
    for word in filter_words:
        score = max(fuzz.ratio(word, w) for w in headline_lower)
        if score > thold:
            return True
    return False


def filter_all_headlines(articles):
    return [
        article
        for article in articles
        if filter_headline(article[0], 80) or filter_headline(article[1][:300], 70)
    ]




def normalize_text(text):
    return " ".join(text.lower().strip().split())

def fuzzy_group_articles(articles):
    hash_to_group = {}

    for headline, content, time, source, url in articles:
        summary = content[:300]
        pub_dt = normalize_datetime(time)

        # Normalize and hash the summary for grouping
        norm_summary = normalize_text(summary)
        summary_key = hashlib.md5(norm_summary.encode()).hexdigest()

        if summary_key in hash_to_group:
            group = hash_to_group[summary_key]
            group["headlines"].append(headline)
            group["urls"].append(url)
            group["sources"].append(source)
            if pub_dt > group["time"]:
                group["time"] = pub_dt
        else:
            hash_to_group[summary_key] = {
                "summary": summary,
                "headlines": [headline],
                "urls": [url],
                "sources": [source],
                "time": pub_dt,
            }

    # Prepare final dict with readable keys
    final_output = {}
    for group in hash_to_group.values():
        display_headline = group["headlines"][0]  # Pick the first headline for display
        final_output[display_headline] = {
            "summary": group["summary"],
            "urls": group["urls"],
            "sources": group["sources"],
            "time": group["time"],
        }

    return final_output

def main_fetch():
    all_articles = get_indianexpress_news() + get_ndtv_news() + get_toi()
    # print(all_articles)
    filtered_articles = filter_all_headlines(all_articles)
    grouped = fuzzy_group_articles(filtered_articles)
    # print(grouped)
    sorted_grouped = dict(
        sorted(grouped.items(), key=lambda x: x[1]["time"], reverse=True)[:20]
    )
    # print(dict(sorted_grouped))
    for value in sorted_grouped.values():
        time = datetime.strftime(value["time"], "%Y-%m-%d %H:%M:%S")
        value["time"] = time
        value["sources"] = set(value["sources"])
        value["urls"] = set(value["urls"])
    print("Hello")
    # print(sorted_grouped)
    return sorted_grouped
    # print(result)
    # return result
    # print(sorted_grouped)
    # return sorted_grouped


"""    for key, value in sorted_grouped:
        print(
            f"\nHeadline: {key}\nReported by: {value['sources']}\nTime: {value['time']}\nURLs: {value['urls']}\nSummary: {value['summary']}\n"
        )"""
