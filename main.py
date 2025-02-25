import os
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer
from atproto import Client
import torch
import re

# Load environment variables
load_dotenv()

# Bluesky credentials
BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

if not all([BLUESKY_USERNAME, BLUESKY_PASSWORD, HUGGINGFACE_TOKEN]):
    print("❌ Error: Missing environment variables!")
    exit(1)

# Model setup
MODEL_NAME = "distilgpt2"

# Check GPU (won’t use GPU on GitHub Actions, runs on CPU)
print(f"⚠️ Running on CPU (GitHub Actions)")

# Load model and tokenizer
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    print("✅ DistilGPT-2 loaded on CPU!")
except Exception as e:
    print(f"❌ Error loading DistilGPT-2 model: {e}")
    exit(1)

# Initialize Bluesky API
try:
    bluesky_client = Client()
    bluesky_client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)
    print("✅ Bluesky API initialized successfully!")
except Exception as e:
    print(f"❌ Error initializing Bluesky API: {e}")
    exit(1)

# Fetch news from Times of India RSS
INDIA_NEWS_RSS = "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"

def fetch_trending_india_news():
    try:
        response = requests.get(INDIA_NEWS_RSS)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "lxml-xml")
            news_items = [item.title.text for item in soup.find_all("item")]
            return news_items[:5]
        else:
            print(f"⚠️ Failed to fetch news, status code: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error fetching India news: {e}")
    return [
        "Big changes in Indian politics today!",
        "Tech boom hits India with new startups.",
        "Cricket fever grips the nation again!",
        "Monsoon updates: What’s the forecast?",
        "Bollywood’s latest blockbuster drops!"
    ]

def generate_post():
    try:
        trending_news = fetch_trending_india_news()
        # topic = random.choice(trending_news)
        topic="Happening in Cricket "
        print(f"📌 Selected News Topic: {topic}")

        prompt = f"Give latest updates about {topic} (max 150 chars): "
        input_ids = tokenizer.encode(prompt, return_tensors="pt")

        output = model.generate(
            input_ids,
            max_new_tokens=40,
            min_new_tokens=5,
            do_sample=True,
            temperature=0.6,
            top_p=0.95,
            top_k=50,
            repetition_penalty=1.2,
            pad_token_id=tokenizer.eos_token_id
        )
        generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
        raw_post = generated_text.replace(prompt, "").strip()
        
        raw_post = re.sub(r'^[^a-zA-Z0-9#]+', '', raw_post)
        raw_post = ''.join(c for c in raw_post if c.isascii() and c.isprintable())
        if len(raw_post) > 120 or not raw_post.endswith(('.', '!', '?')):
            sentences = re.split(r'(?<=[.!?])\s+', raw_post)
            truncated = []
            char_count = 0
            for sentence in sentences:
                if char_count + len(sentence) + (1 if char_count > 0 else 0) <= 120:
                    truncated.append(sentence)
                    char_count += len(sentence) + (1 if char_count > 0 else 0)
                else:
                    break
            raw_post = ' '.join(truncated) if truncated else "News rocks!"
        if not raw_post:
            raw_post = "Wild stuff!"
        print(f"📜 Raw Model Output: '{raw_post}'")

        if "law" in topic.lower() or "court" in topic.lower():
            hashtag = "#JusticeMatters"
        elif "monsoon" in topic.lower() or "rain" in topic.lower():
            hashtag = "#MonsoonMania"
        elif "politics" in topic.lower():
            hashtag = "#PollsAndPower"
        elif "tech" in topic.lower() or "startup" in topic.lower():
            hashtag = "#TechIndia"
        else:
            hashtag = "#TrendingNow"

        max_topic_len = 300 - len(raw_post) - len(hashtag) - len("#IndiaNews") - 3
        truncated_topic = topic[:max_topic_len] if len(topic) > max_topic_len else topic
        post = f"{truncated_topic}: {raw_post} {hashtag} #IndiaNews"

        if len(post) > 300:
            excess = len(post) - 300
            raw_post = raw_post[:-excess] if len(raw_post) > excess else raw_post
            post = f"{truncated_topic}: {raw_post} {hashtag} #IndiaNews"

        print(f"📝 Final Post: {post}")
        print(f"📏 Length: {len(post)} characters")
        return post
    except Exception as e:
        print(f"⚠️ Error generating post: {e}")
        return f"Hot scoop: {topic}! #TrendingNow #IndiaNews"

def post_to_bluesky():
    try:
        post = generate_post()
        bluesky_client.send_post(text=post)
        print("✅ Post published successfully!")
    except Exception as e:
        print(f"❌ Failed to publish post: {e}")

# Run once (GitHub Actions will handle scheduling)
post_to_bluesky()
