import os
import time
import psycopg2
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from typing import List, Dict

app = FastAPI()

# ✅ TEMPORARY CORS FIX (Allow All Requests for Debugging)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Replace this with your frontend URL after debugging
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ✅ Function to establish a new database connection
def get_db_connection():
    try:
        return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None

# ✅ Ensure database connection is always active
def get_cursor():
    global conn, cur
    if conn is None or conn.closed:
        print("🔄 Reconnecting to the database...")
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
        else:
            return None
    return cur

# ✅ Initial database connection
conn = get_db_connection()
cur = conn.cursor() if conn else None

# ✅ Function to set up Selenium with ChromeDriver
def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

# ✅ Function to scrape job news using Selenium & BeautifulSoup
def scrape_job_news(category: str) -> List[Dict[str, str]]:
    url = f"https://news.google.com/search?q={category}+jobs&hl=en&gl=US&ceid=US:en"

    driver = setup_selenium()
    driver.get(url)
    time.sleep(5)  # ✅ Wait for JavaScript to load

    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source, "html.parser")
    articles = soup.find_all("article")[:10]  

    if articles:
        print("🔍 Debug: Full HTML of First Article:")
        print(articles[0].prettify())  # ✅ Force printing first article's full HTML
    else:
        print("❌ No articles found! Debugging Full Page HTML...")
        print(soup.prettify())  # ✅ Print full page source if no articles are found

    job_news = []
    for article in articles:
        title_tag = (article.select_one("h3") or 
                     article.select_one("a") or 
                     article.select_one("div[role='heading']") or 
                     article.select_one("span"))
        link_tag = article.find("a", href=True)

        if not title_tag or not link_tag:
            print("⚠️ Skipping article due to missing title or link.")
            continue  

        title = title_tag.get_text(strip=True)
        link = "https://news.google.com" + link_tag["href"][1:]
        job_news.append({"title": title, "link": link})

    print(f"✅ Scraped {len(job_news)} job news articles.")
    return job_news

# ✅ Route to handle `/news` (Prevents 404 Error)
@app.get("/news")
def get_all_news():
    return {
        "message": "Please use /news/{category} to fetch job news.",
        "example": "/news/software"
    }

# ✅ Route to get job news by category
@app.get("/news/{category}")
def get_news(category: str):
    try:
        cur = get_cursor()  # ✅ Ensure connection is active
        if not cur:
            return {"error": "Database connection unavailable."}

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
        if conn:
            try:
                conn.rollback()  # ✅ Only rollback if an active transaction exists
                print("🔄 Database transaction rolled back due to error.")
            except psycopg2.Error:
                print("⚠️ Rollback failed (no active transaction).")
        return {"error": str(e)}

# ✅ Root route to check if the API is running
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}

# ✅ Ensures FastAPI keeps running on Render
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
