import os
import json
import mplfinance as mpf
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import pathlib

load_dotenv()

GENAI_KEY = os.getenv("GENAI_KEY")
if GENAI_KEY:
    genai.configure(api_key=GENAI_KEY)

class PatternAnalyzer:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro-vision') 
        # Pattern Analysis (Vision)
        # Switching to Gemini 2.0 Flash for better multimodal support
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def generate_chart_image(self, symbol, df, output_path="chart.png"):
        # Configure mplfinance style
        # We need a clear chart for AI
        df.index = pd.to_datetime(df['time'], unit='ms')
        
        # Plot last 50 candles for clarity
        subset = df.tail(50)
        
        mpf.plot(
            subset, 
            type='candle',
            style='yahoo',
            volume=True,
            savefig=dict(fname=output_path, dpi=100)
        )
        return output_path

    async def analyze_chart(self, symbol, df_1h, df_15m):
        # We will combine both charts or just send 1H? User said "Take chart screenshot (1H+15m)"
        # Let's generate one image or two. Multi-image prompt is supported.
        
        img_1h = self.generate_chart_image(symbol, df_1h, "chart_1h.png")
        img_15m = self.generate_chart_image(symbol, df_15m, "chart_15m.png")

        prompt = """
        Analyze these crypto charts (1H and 15m) for a "Blow-off Top" or "Reversal" setup.
        
        Look for SPECIFIC confirmation signals:
        1. Blow-off top wick (Long upper wick indicating rejection)
        2. Shooting Star or Doji candle at the highs
        3. Bearish Engulfing candle
        4. Structure Shift (Higher High -> Lower High in 15m)
        
        We are looking for a SHORT opportunity on an overextended pump.
        
        Return STRICT JSON:
        {
            "pattern_score": <float between 0 and 1, higher is better short candidate>,
            "reversal_detected": <bool>,
            "tags": ["blow-off-top", "bearish-engulfing", "rejection-wick", "structure-break"],
            "reasoning": "brief explanation"
        }
        """

        try:
            # Load images
            # Gemini API accepts path or data
            # Using genai file API or just simple PIL
            import PIL.Image
            p_img_1h = PIL.Image.open(img_1h)
            p_img_15m = PIL.Image.open(img_15m)
            
            response = self.model.generate_content([prompt, p_img_1h, p_img_15m])
            
            # Clean up
            os.remove(img_1h)
            os.remove(img_15m)
            
            # Extract JSON
            text = response.text
            # Simple cleanup for markdown code blocks if present
            text = text.replace("```json", "").replace("```", "")
            
            return json.loads(text)
            
        except Exception as e:
            print(f"Pattern Analysis Error: {e}")
            return {"pattern_score": 0, "tags": [], "reasoning": "Error"}

# Helper specific for redis data structure
    async def get_pattern_score(self, symbol, redis_client):
        # Fetch data
        import json
        k_1h = await redis_client.get(f"klines:{symbol}:1h")
        k_15m = await redis_client.get(f"klines:{symbol}:15m")
        
        if not k_1h or not k_15m:
            return {"pattern_score": 0}
            
        df_1h = pd.DataFrame(json.loads(k_1h), columns=['time','open','high','low','close','volume'])
        df_15m = pd.DataFrame(json.loads(k_15m), columns=['time','open','high','low','close','volume'])
        
        return await self.analyze_chart(symbol, df_1h, df_15m)
