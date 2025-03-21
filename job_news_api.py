import os
import psycopg2
import uvicorn
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict

app = FastAPI()

# ✅ Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from any frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

print("✅ Checking environment variables...")  # Debugging output

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL is missing! Check Render environment variables.")
    raise ValueError("DATABASE_URL environment variable is missing!")

print(f"✅ DATABASE_URL detected: {DATABASE_URL[:30]}... (truncated for security)")

# Establish database connection
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ✅ Function to scrape job news from Google News (Fixes Empty Titles)
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

    # ✅ Debugging: Print only the first 500 characters of the HTML (Prevent log overflow)
    print(f"🔍 HTML Preview: {soup.prettify()[:500]}...")  

    articles = soup.find_all("article")[:10]

    job_news = []
    for article in articles:
        print("🔍 Article HTML Preview:", article.prettify()[:200])  # ✅ Prevent log overflow

        # ✅ Extracting title from multiple possible tags
        title_tag = article.find("h3") or article.find("a") or article.find("span") or article.find("div")
        link_tag = article.find("a")

        if title_tag and link_tag and link_tag.has_attr("href"):
            title = title_tag.get_text(strip=True)  
            link = "https://news.google.com" + link_tag["href"][1:]
            job_news.append({"title": title, "link": link})

    print(f"✅ Scraped {len(job_news)} job news articles.")
    return job_news

# ✅ API route to get job news by category (Checks Database First)
@app.get("/news/{category}")
def get_news(category: str):
    try:
        # ✅ Check if news exists in the database
        cur.execute("SELECT title, link FROM news WHERE category=%s ORDER BY published_at DESC LIMIT 10", (category,))
        news = cur.fetchall()

        if news:
            print(f"✅ Found {len(news)} articles in database.")
            return [{"title": row[0], "link": row[1]} for row in news]

        # ❌ No recent data found → Scrape Google News
        print(f"🔍 No recent data found for {category}. Scraping Google News...")
        scraped_news = scrape_job_news(category)

        # ✅ Store scraped news in the database
        for item in scraped_news:
            cur.execute("INSERT INTO news (title, link, category, published_at) VALUES (%s, %s, %s, NOW())",
                        (item["title"], item["link"], category))
        conn.commit()

        return scraped_news

    except psycopg2.Error as e:
        conn.rollback()  # Prevent database lock if an error occurs
        return {"error": str(e)}

# ✅ Root route to check if the API is running
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}

# ✅ Ensures FastAPI keeps running on Render
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
