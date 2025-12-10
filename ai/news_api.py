import os
import json
import feedparser
import urllib.parse
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Use the same GENAI_KEY as pattern_api
GENAI_KEY = os.getenv("GENAI_KEY")
if GENAI_KEY:
    genai.configure(api_key=GENAI_KEY)

class NewsAnalyzer:
    def __init__(self):
        # Gemini 1.5 Flash is highly efficient and free-tier friendly
        # Using alias found in model list
        self.model = genai.GenerativeModel('gemini-flash-latest')

    def fetch_news(self, symbol):
        # Construct search query
        # Remove /USDT or similar if present
        coin = symbol.split('/')[0]
        query = f"{coin} crypto news"
        encoded_query = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        feed = feedparser.parse(rss_url)
        
        # Take top 5 headlines
        headlines = []
        for entry in feed.entries[:5]:
            headlines.append(f"- {entry.title} ({entry.published})")
        
        return "\n".join(headlines)

    async def get_news_score(self, symbol):
        headlines = self.fetch_news(symbol)
        if not headlines:
            return {"news_driven": False, "news_score": 0, "sentiment": "neutral"}
        
        prompt = f"""
        Analyze these news headlines for {symbol}:
        {headlines}
        
        Is the recent price pump news-driven? 
        Determine Sentiment: bullish/neutral/bearish.
        Risk Score (0-100): High score means high risk of sustained pump (bad for shorting). 0 means purely technical pump (good for exhaustion short).
        
        Return STRICT JSON:
        {{
            "news_driven": true/false,
            "news_score": <int 0-100>,
            "sentiment": "string"
        }}
        """
        
        try:
            # Gemini async generation or synchronous run in executor
            # google.generativeai supports async generate_content_async since roughly 0.3.0
            # If not available, we wrap sync call.
            # Assuming recent library version.
            response = await self.model.generate_content_async(prompt)
            
            text = response.text
            # Clean markdown
            text = text.replace("```json", "").replace("```", "")
            return json.loads(text)
                
        except Exception as e:
            print(f"News Analysis Error (Gemini): {e}")
            return {"news_driven": False, "news_score": 50, "sentiment": "neutral"}

