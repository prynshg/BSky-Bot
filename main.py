import os
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load environment variables
load_dotenv()

# API Keys & Credentials
BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not all([BLUESKY_USERNAME, BLUESKY_PASSWORD, GEMINI_API_KEY]):
    print("❌ Error: Missing environment variables!")
    exit(1)

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# Bluesky API (Replace with your actual implementation)
from atproto import Client
bluesky_client = Client()
bluesky_client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)

# Fetch trending India news
INDIA_NEWS_RSS = "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"

def fetch_trending_india_news():
    try:
        response = requests.get(INDIA_NEWS_RSS)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "xml")
            news_items = [item.title.text for item in soup.find_all("item")]
            return news_items[:5]
    except Exception as e:
        print(f"⚠️ Error fetching news: {e}")
    
    return [
        "Big changes in Indian politics today!",
        "Tech boom hits India with new startups.",
        "Cricket fever grips the nation again!",
        "Monsoon updates: What’s the forecast?",
        "Bollywood’s latest blockbuster drops!"
    ]

def clean_and_truncate(text, max_length=120):
    """Ensures the post is clean and truncated at the last full sentence."""
    text = re.sub(r"\s+", " ", text).strip()  # Remove excessive spaces

    if len(text) <= max_length:
        return text

    # Find the last full sentence within the limit
    sentences = re.split(r"(?<=[.!?])\s+", text)
    truncated_text = ""
    for sentence in sentences:
        if len(truncated_text) + len(sentence) <= max_length:
            truncated_text += sentence + " "
        else:
            break

    return truncated_text.strip() if truncated_text else text[:max_length]  # Fallback to simple truncation

# Generate post using Gemini AI with better error handling
def generate_post():
    try:
        trending_news = fetch_trending_india_news()
        topic = random.choice(trending_news)
        print(f"📌 Selected News Topic: {topic}")

        prompt = f"Create a short, engaging social media post about '{topic}'. Keep it professional and non-controversial. Maximum length: 120 characters."

        response = model.generate_content(prompt)

        if not response.candidates or not response.candidates[0].content.parts:
            print("⚠️ Gemini refused to generate a response. Retrying with different phrasing...")
            prompt = f"Write a friendly and neutral tweet about '{topic}' within 120 characters."
            response = model.generate_content(prompt)

        if not response.candidates or not response.candidates[0].content.parts:
            print("❌ Failed again! Defaulting to a backup message.")
            return f"Breaking News: {topic}! Stay informed. #TrendingNow #IndiaNews"

        generated_text = response.candidates[0].content.parts[0].text.strip()

        # Truncate properly to avoid cut-off words
        clean_text = clean_and_truncate(generated_text, max_length=120)

        hashtag = "#TrendingNow #IndiaNews"
        post = f"{topic}: {clean_text} {hashtag}"

        print(f"📝 Final Post: {post}")
        return post
    except Exception as e:
        print(f"⚠️ Error generating post: {e}")
        return "Breaking news! Stay tuned for updates. #TrendingNow #IndiaNews"

# Post to Bluesky
def post_to_bluesky():
    try:
        post = generate_post()
        print(post)
        bluesky_client.send_post(text=post)
        print("✅ Post published successfully!")
    except Exception as e:
        print(f"❌ Failed to publish post: {e}")

# Run the script
post_to_bluesky()
