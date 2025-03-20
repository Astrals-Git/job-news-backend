import os
import psycopg2
import uvicorn
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict

app = FastAPI()

# ✅ Allow requests from your frontend (CORS settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⬅️ Allows all frontend origins (change to specific domain for security)
    allow_credentials=True,
    allow_methods=["*"],  # ⬅️ Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # ⬅️ Allows all headers
)

print("✅ Checking environment variables...")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL is missing! Check Render environment variables.")
    raise ValueError("DATABASE_URL environment variable is missing!")

print(f"✅ DATABASE_URL detected: {DATABASE_URL[:30]}... (truncated for security)")

# Establish database connection
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ✅ Function to scrape job news from Google News
def scrape_job_news(category: str) -> List[Dict[str, str]]:
    url = f"https://news.google.com/search?q={category}+jobs&hl=en&gl=US&ceid=US:en"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching news: {e}")
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

# ✅ API route to get job news by category (Checks Database First)
@app.get("/news/{category}")
def get_news(category: str):
    try:
        cur.execute("SELECT title, link FROM news WHERE category=%s ORDER BY published_at DESC LIMIT 10", (category,))
        news = cur.fetchall()

        if news:
            print(f"✅ Found {len(news)} articles in database.")
            return [{"title": row[0], "link": row[1]} for row in news]

        print("🔍 No recent data found. Scraping Google News...")
        scraped_news = scrape_job_news(category)

        for item in scraped_news:
            cur.execute("INSERT INTO news (title, link, category, published_at) VALUES (%s, %s, %s, NOW())",
                        (item["title"], item["link"], category))
        conn.commit()

        return scraped_news

    except psycopg2.Error as e:
        conn.rollback()
        return {"error": str(e)}

# ✅ Root route to check if the API is running
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}

# ✅ Ensures FastAPI keeps running on Render
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
