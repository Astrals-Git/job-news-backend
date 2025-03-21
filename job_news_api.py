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

# ✅ CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://job-news-frontend.vercel.app"],  # ✅ Replace with your actual frontend URL
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
    articles = soup.find_all("article")[:5]  # ✅ Get first 5 articles for debugging

    if articles:
        print("🔍 Debug: Full HTML of First Article:")
        print(articles[0].prettify())  # ✅ Print first article's full HTML

    job_news = []
    for article in articles:
        title_tag = article.select_one("h3") or article.select_one("a") or article.select_one("span")  # ✅ Extract title from multiple elements
        link_tag = article.find("a", href=True)

        if not title_tag or not link_tag:
            print("⚠️ Skipping article due to missing title or link.")
            continue  

        title = title_tag.get_text(strip)

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
