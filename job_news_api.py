import uvicorn
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from typing import List, Dict

app = FastAPI()

# ✅ Function to scrape job news from Google News
def scrape_job_news(category: str) -> List[Dict[str, str]]:
    url = f"https://news.google.com/search?q={category}+jobs&hl=en&gl=US&ceid=US:en"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article")[:10]

    job_news = []
    for article in articles:
        title_tag = article.find("a")
        if title_tag:
            title = title_tag.text.strip()
            link = "https://news.google.com" + title_tag["href"][1:]
            job_news.append({"title": title, "link": link})

    return job_news

# ✅ API route to get job news by category
@app.get("/news/{category}")
def get_news(category: str):
    return scrape_job_news(category)

# ✅ Root route to check if the API is running
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}

# ✅ Ensures FastAPI keeps running on Render
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
