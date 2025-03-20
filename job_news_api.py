import uvicorn
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from typing import List, Dict

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")  # Ensure this is set correctly
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing!")
    
# Establish database connection
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

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
<<<<<<< HEAD
    return scrape_job_news(category)

# ✅ Root route to check if the API is running
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}

# ✅ Ensures FastAPI keeps running on Render
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
=======
    try:
        cur.execute("SELECT title, link FROM news WHERE category=%s ORDER BY published_at DESC LIMIT 10", (category,))
        news = cur.fetchall()
        return [{"title": row[0], "link": row[1]} for row in news]
    except psycopg2.Error as e:
        conn.rollback()  # Reset the transaction to avoid blocking future queries
        return {"error": str(e)}
>>>>>>> 3b17c5c (Updated job_news_api)
