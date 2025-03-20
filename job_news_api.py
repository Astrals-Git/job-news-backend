import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from typing import List, Dict

app = FastAPI()

def scrape_job_news(category: str) -> List[Dict[str, str]]:
    url = f"https://news.google.com/search?q={category}+jobs&hl=en&gl=US&ceid=US:en"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return [{"title": "Error fetching news", "link": "#"}]

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article")[:10]  # Get top 10 job-related articles

    job_news = []
    for article in articles:
        title_tag = article.find("a")
        if title_tag:
            title = title_tag.text
            link = "https://news.google.com" + title_tag["href"][1:]  # Fix relative link
            job_news.append({"title": title, "link": link})

    return job_news

@app.get("/news/{category}")
def get_news(category: str):
    return scrape_job_news(category)
