import os
import time
import psycopg2
import uvicorn
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict

app = FastAPI()

# ✅ Allow frontend requests from Vercel (CORS Fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://job-news-frontend.vercel.app"],  # ✅ Replace with your actual frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # ✅ Allow GET & POST requests
    allow_headers=["*"],  # ✅ Allow all headers
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

# ✅ Function to set up Selenium with ChromeDriver
def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Use webdriver_manager to automatically download ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

# ✅ Function to scrape job news using Selenium & BeautifulSoup
def scrape_job_news(category: str) -> List[Dict[str, str]]:
    url = f"https://news.google.com/search?q={category}+jobs&hl=en&gl=US&ceid=US:en"

    # ✅ Start Selenium WebDriver
    driver = setup_selenium()
    driver.get(url)
    time.sleep(5)  # ✅ Wait for JavaScript to load

    # ✅ Get fully rendered page source
    page_source = driver.page_source
    driver.quit()  # ✅ Close browser after loading page

    soup = BeautifulSoup(page_source, "html.parser")
    articles = soup.find_all("article")[:10]  # Get top 10 job-related articles

    job_news = []
    for article in articles:
        title_tag = article.find("h3") or article.find("div", {"role": "heading"}) or article.find("span") or article.select_one("div.MBeuO")
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
