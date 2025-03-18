from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")  # Fetch from environment variable
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

@app.get("/news/{category}")
def get_news(category: str):
    cur.execute("SELECT title, link FROM news WHERE category=%s ORDER BY published_at DESC LIMIT 10", (category,))
    news = cur.fetchall()
    return [{"title": row[0], "link": row[1]} for row in news]
