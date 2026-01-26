import os
import json
import logging
import requests
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Try to import Google AI
try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AstrologerAgent:
    """
    The Astrologer Agent uses LLMs to generate authentic Western Astrology content.
    It acts like a professional Western Astrologer with deep knowledge of:
    - Sun Signs, Moon Signs, Rising Signs
    - Planetary Transits (Mercury Retrograde, Saturn Return, etc.)
    - Aspects (Conjunctions, Squares, Trines, Oppositions)
    - Houses and their meanings
    Supports multiple API keys with automatic failover on rate limits.
    Falls back to Google AI Studio (Gemini) when OpenRouter is exhausted.
    """
    
    # Western Zodiac Signs (English only)
    ZODIAC_SIGNS = {
        "aries": "Aries",
        "taurus": "Taurus", 
        "gemini": "Gemini",
        "cancer": "Cancer",
        "leo": "Leo",
        "virgo": "Virgo",
        "libra": "Libra",
        "scorpio": "Scorpio",
        "sagittarius": "Sagittarius",
        "capricorn": "Capricorn",
        "aquarius": "Aquarius",
        "pisces": "Pisces"
    }
    
    # Zodiac Elements
    ZODIAC_ELEMENTS = {
        "aries": "Fire", "leo": "Fire", "sagittarius": "Fire",
        "taurus": "Earth", "virgo": "Earth", "capricorn": "Earth",
        "gemini": "Air", "libra": "Air", "aquarius": "Air",
        "cancer": "Water", "scorpio": "Water", "pisces": "Water"
    }
    
    # Ruling Planets
    RULING_PLANETS = {
        "aries": "Mars", "taurus": "Venus", "gemini": "Mercury",
        "cancer": "Moon", "leo": "Sun", "virgo": "Mercury",
        "libra": "Venus", "scorpio": "Pluto/Mars", "sagittarius": "Jupiter",
        "capricorn": "Saturn", "aquarius": "Uranus/Saturn", "pisces": "Neptune/Jupiter"
    }
    
    def __init__(self, api_key: str = None, backup_key: str = None):
        """Initialize with OpenRouter API Keys (primary + backup) + Google AI fallback."""
        self.api_keys = []
        
        # Primary key
        primary = api_key or os.getenv("OPENROUTER_API_KEY")
        if primary:
            self.api_keys.append(primary)
        
        # Backup key 1
        backup = backup_key or os.getenv("OPENROUTER_API_KEY_BACKUP")
        if backup:
            self.api_keys.append(backup)
        
        # Backup key 2 (3rd key for extra capacity)
        backup2 = os.getenv("OPENROUTER_API_KEY_BACKUP_2")
        if backup2:
            self.api_keys.append(backup2)
        
        # Google AI key (fallback)
        self.google_ai_key = os.getenv("GOOGLE_AI_API_KEY")
        if self.google_ai_key and GOOGLE_AI_AVAILABLE:
            genai.configure(api_key=self.google_ai_key)
            self.google_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            logging.info("🌟 Google AI Studio (Gemini) fallback enabled")
        else:
            self.google_model = None
        
        if not self.api_keys and not self.google_model:
            raise ValueError("No API keys found! Need OPENROUTER_API_KEY or GOOGLE_AI_API_KEY")
        
        logging.info(f"🔑 Loaded {len(self.api_keys)} OpenRouter key(s)")
        
        self.current_key_index = 0
        if self.api_keys:
            self._init_client()
            self.models = self.get_best_free_models()
        else:
            self.client = None
            self.models = []

    def _init_client(self):
        """Initialize OpenAI client with current key."""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_keys[self.current_key_index],
        )

    def _switch_to_backup_key(self):
        """Switch to backup key if available."""
        if self.current_key_index < len(self.api_keys) - 1:
            self.current_key_index += 1
            logging.info(f"🔄 Switching to backup key #{self.current_key_index + 1}")
            self._init_client()
            return True
        return False

    def _generate_with_google_ai(self, system_prompt: str, user_prompt: str) -> dict:
        """Fallback to Google AI Studio (Gemini) when OpenRouter fails."""
        if not self.google_model:
            return None
            
        logging.info("🌟 Trying Google AI Studio (Gemini) as fallback...")
        try:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self.google_model.generate_content(full_prompt)
            
            # Extract JSON from response
            text = response.text
            # Clean up markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text.strip())
            logging.info("✅ Google AI Studio succeeded!")
            return result
            
        except Exception as e:
            logging.error(f"❌ Google AI Studio failed: {e}")
            return None

    def get_best_free_models(self) -> list:
        """
        Fetches available models from OpenRouter, filters for free ones,
        and ranks them based on heuristics (e.g. 'gemini', 'llama', '70b').
        """
        try:
            logging.info("🔎 Discovering best free models on OpenRouter...")
            response = requests.get("https://openrouter.ai/api/v1/models")
            if response.status_code != 200:
                logging.warning("⚠️ Failed to fetch models list. Using defaults.")
                return ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct:free"]
            
            all_models = response.json().get("data", [])
            free_models = []
            
            for m in all_models:
                pricing = m.get("pricing", {})
                if pricing.get("prompt") == "0" and pricing.get("completion") == "0":
                    free_models.append(m["id"])
            
            # Smart Ranking Heuristics
            scored_models = []
            for mid in free_models:
                score = 0
                mid_lower = mid.lower()
                
                if "gemini" in mid_lower: score += 10
                if "llama-3" in mid_lower: score += 8
                if "deepseek" in mid_lower: score += 7
                if "phi-4" in mid_lower: score += 6
                
                if "flash" in mid_lower: score += 3
                if "exp" in mid_lower: score += 2
                if "70b" in mid_lower: score += 2
                
                if "nano" in mid_lower or "1b" in mid_lower or "3b" in mid_lower: score -= 20
                
                scored_models.append((score, mid))
            
            scored_models.sort(key=lambda x: x[0], reverse=True)
            best_models = [m[1] for m in scored_models[:5]]
            
            logging.info(f"✅ Selected Top Free Models: {best_models}")
            if not best_models:
                 return ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct:free"]
                 
            return best_models
            
        except Exception as e:
            logging.error(f"⚠️ Model discovery failed: {e}")
            return ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct:free"]

    def _generate_script(self, sign: str, date: str, period_type: str, system_prompt: str, user_prompt: str) -> dict:
        """Helper to try models in rotation with key failover on rate limits."""
        errors = []
        tried_backup = False
        
        while True:
            for model in self.models:
                # Rate Limit Protection: Wait 2 mins between calls
                import time
                logging.info(f"⏳ Rate Limit Guard: Waiting 2 minutes before API call...")
                time.sleep(120)
                
                logging.info(f"🤖 Generating {period_type} horoscope using: {model}")
                try:
                    # Try standard JSON mode first
                    try:
                        response = self.client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            response_format={"type": "json_object"}
                        )
                        raw_content = response.choices[0].message.content
                    except Exception as e:
                        if "400" in str(e):
                            logging.warning(f"⚠️ Model {model} rejected JSON mode. Retrying with Plain Text...")
                            response = self.client.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": system_prompt + "\n\nIMPORTANT: Return ONLY valid JSON. No markdown, no preambles."},
                                    {"role": "user", "content": user_prompt}
                                ]
                            )
                            raw_content = response.choices[0].message.content
                        else:
                            raise e

                    # Robust JSON cleanup
                    clean_json = raw_content.replace('```json', '').replace('```', '').strip()
                    return json.loads(clean_json)
                    
                except Exception as e:
                    error_str = str(e)
                    logging.warning(f"⚠️ Model {model} failed: {e}")
                    errors.append(f"{model}: {error_str}")
                    
                    if "429" in error_str or "rate limit" in error_str.lower():
                        if not tried_backup and self._switch_to_backup_key():
                            logging.info("🔄 Rate limit hit! Retrying with backup key...")
                            tried_backup = True
                            errors = []
                            break
                    continue
            else:
                break
        
        # FINAL FALLBACK: Try Google AI Studio
        logging.warning("⚠️ All OpenRouter models/keys exhausted. Trying Google AI fallback...")
        google_result = self._generate_with_google_ai(system_prompt, user_prompt)
        if google_result:
            return google_result
        
        raise Exception(f"❌ API Quota Exceeded for ALL keys. Cannot generate valid content for {sign}.")

    def _get_mock_data(self, sign, period_type):
        """Returns safe, pre-written content for testing when APIs are down."""
        logging.warning(f"⚠️ RETURNING MOCK DATA FOR {sign} ({period_type})")
        
        sign_clean = sign.split('(')[0].strip() if '(' in sign else sign
        
        if period_type.startswith("Metadata_"):
            import pytz
            est = pytz.timezone('America/New_York')
            today_str = datetime.now(est).strftime("%B %d, %Y")
            
            return {
                "title": f"{sign_clean} Horoscope {today_str} ⭐ #shorts #viral",
                "description": f"""⭐ {sign_clean} Daily Horoscope - {today_str}

Discover what the stars have in store for you today!

🌟 Topics Covered:
- Love & Relationships
- Career & Money
- Health & Wellness

#shorts #viral #horoscope #astrology #{sign_clean.lower()} #dailyhoroscope #zodiac #trending""",
                "tags": [
                    f"{sign_clean.lower()} horoscope",
                    "horoscope",
                    "astrology",
                    "shorts",
                    "viral",
                    "daily horoscope",
                    "zodiac",
                    "trending"
                ],
                "categoryId": "24"
            }
        
        if period_type == "Daily":
            return {
                "hook": f"{sign_clean}, the stars are aligning in your favor today! Here's what the universe has planned for you.",
                "intro": "With the Moon's energy supporting your endeavors, today brings opportunities for growth and positive change.",
                "love": "Romance is in the air! If you're in a relationship, expect deeper connections. Singles may encounter someone special.",
                "career": "Your professional life gets a boost today. New opportunities may arise, and your hard work will be recognized.",
                "money": "Financial prospects look stable. It's a good day to review your budget, but avoid impulsive purchases.",
                "health": "Focus on self-care today. A balanced approach to diet and exercise will serve you well.",
                "advice": "Trust your intuition today. The universe is guiding you toward your highest good.",
                "lucky_color": "Blue",
                "lucky_number": "7"
            }
        return {
            "hook": "Mock Data generated due to API Rate Limits.",
            "intro": "Systems are currently offline, please check API quotas.",
            "love": "Unavailable.", "career": "Unavailable.", "money": "Unavailable.",
            "health": "Unavailable.", "advice": "Check logs.", "lucky_number": "N/A"
        }

    def generate_daily_horoscope(self, sign: str, date: str) -> dict:
        """Generates Daily Horoscope using authentic Western Astrology."""
        logging.info(f"⭐ Astrologer: Generating Daily Horoscope for {sign}...")
        
        sign_key = sign.lower().split()[0]
        element = self.ZODIAC_ELEMENTS.get(sign_key, "Unknown")
        ruler = self.RULING_PLANETS.get(sign_key, "Unknown")
        
        system_prompt = """
        You are 'Stella Nova', a renowned Western Astrologer with 30+ years of experience.
        You specialize in authentic Western/Tropical Astrology, NOT Vedic/Sidereal astrology.
        
        Your expertise includes:
        - Sun Sign, Moon Sign, and Rising Sign interpretations
        - Planetary transits and their effects (Mercury Retrograde, Venus in signs, etc.)
        - Aspects between planets (Conjunctions, Squares, Trines, Sextiles, Oppositions)
        - House placements and their meanings in daily life
        - Current celestial events affecting all zodiac signs
        
        RULES:
        1. Write in ENGLISH only - clear, engaging, and professional
        2. Base predictions on ACTUAL planetary positions and transits for the given date
        3. Be specific and actionable - give real advice, not vague statements
        4. Reference planetary influences (e.g., "With Mars in your 10th house...")
        5. Keep the tone warm, hopeful, but honest - acknowledge challenges when present
        6. Make predictions feel PERSONAL and RELEVANT to the specific sign
        7. Include timing guidance (morning vs evening energy, etc.)
        8. DO NOT use Hindu/Vedic terms - use Western astrology terminology only
        """
        
        user_prompt = f"""
        Generate a **Daily Horoscope** for **{sign}** for {date}.
        
        Sign Details:
        - Element: {element}
        - Ruling Planet: {ruler}
        
        Consider current planetary transits and how they specifically affect {sign}.
        Make it feel authentic, insightful, and different from generic horoscopes.
        
        Return ONLY valid JSON:
        {{
            "hook": "Attention-grabbing opening line (exciting, intriguing, or dramatic)",
            "intro": "Brief astrological context - mention specific planetary influences affecting {sign} today",
            "love": "Love and relationship prediction - be specific to {sign}'s traits",
            "career": "Career and professional life prediction",
            "money": "Financial outlook and money advice",
            "health": "Health and wellness guidance",
            "advice": "Key wisdom or action to take today (specific and actionable)",
            "lucky_color": "A color that resonates with today's energy",
            "lucky_number": "A meaningful number for today",
            "best_time": "Best time of day for important activities",
            "metadata": {{
                "title": "Catchy YouTube Shorts title with {sign} name and date (under 80 chars). End with ⭐ #shorts #viral",
                "description": "Engaging 2-3 line summary with relevant hashtags",
                "tags": "Comma separated viral tags including {sign.lower()}, horoscope, zodiac, astrology, shorts, viral"
            }}
        }}
        """
        return self._generate_script(sign, date, "Daily", system_prompt, user_prompt)

    def generate_monthly_forecast(self, sign: str, month_year: str) -> dict:
        """Generates Monthly Horoscope with detailed Western Astrology analysis."""
        logging.info(f"⭐ Astrologer: Generating Monthly Horoscope for {sign} ({month_year})...")
        
        sign_key = sign.lower().split()[0]
        element = self.ZODIAC_ELEMENTS.get(sign_key, "Unknown")
        ruler = self.RULING_PLANETS.get(sign_key, "Unknown")
        
        system_prompt = """
        You are 'Stella Nova', a master Western Astrologer creating in-depth monthly forecasts.
        
        Your monthly readings include:
        - Major planetary transits through the month
        - New Moon and Full Moon effects on the sign
        - Mercury Retrograde periods (if applicable)
        - Venus and Mars movements affecting love and energy
        - Jupiter and Saturn influences on growth and responsibilities
        - Key dates to watch
        
        RULES:
        1. Write in clear, engaging ENGLISH
        2. Provide WEEK-BY-WEEK guidance when relevant
        3. Highlight the BEST and CHALLENGING days
        4. Give specific dates for important events
        5. Be detailed but accessible - explain astrological terms simply
        6. Use WESTERN astrology terminology only (no Vedic terms)
        """
        
        user_prompt = f"""
        Generate a **Monthly Horoscope** for **{sign}** for **{month_year}**.
        
        Sign Details:
        - Element: {element}
        - Ruling Planet: {ruler}
        
        Return ONLY valid JSON:
        {{
            "hook": "Powerful opening about the month's major theme",
            "intro": "Overview of the month - key planetary movements and their overall effect",
            "love": "Detailed relationship forecast - singles and couples",
            "career": "Career opportunities, challenges, and timing",
            "money": "Financial forecast - best times for investments, caution periods",
            "health": "Health focus areas and self-care recommendations",
            "key_dates": "3-5 important dates with brief descriptions",
            "advice": "Overall guidance for navigating the month successfully",
            "metadata": {{
                "title": "Engaging YouTube title for {sign} {month_year} (under 80 chars)",
                "description": "SEO-optimized description with hashtags",
                "tags": "Relevant viral tags"
            }}
        }}
        """
        return self._generate_script(sign, month_year, "Monthly", system_prompt, user_prompt)

    def generate_yearly_forecast(self, sign: str, year: str) -> dict:
        """Generates comprehensive Yearly Horoscope."""
        logging.info(f"⭐ Astrologer: Generating Yearly Horoscope for {sign} ({year})...")
        
        sign_key = sign.lower().split()[0]
        element = self.ZODIAC_ELEMENTS.get(sign_key, "Unknown")
        ruler = self.RULING_PLANETS.get(sign_key, "Unknown")
        
        system_prompt = """
        You are 'Stella Nova', creating the definitive yearly astrology forecast.
        
        Your yearly readings analyze:
        - Major outer planet transits (Jupiter, Saturn, Uranus, Neptune, Pluto)
        - Eclipse seasons and their transformative effects
        - Retrograde periods throughout the year
        - Best months for love, career, money, and personal growth
        - Challenges to prepare for and how to navigate them
        - The overall theme and lesson of the year
        
        RULES:
        1. This is a COMPREHENSIVE forecast - be thorough but organized
        2. Month-by-month highlights for key areas
        3. Include SPECIFIC predictions, not just general advice
        4. Balance optimism with realistic challenges
        5. Use only WESTERN astrology principles
        6. Make it feel like a valuable, insightful reading worth watching
        """
        
        user_prompt = f"""
        Generate a **Yearly Horoscope** for **{sign}** for the year **{year}**.
        
        Sign Details:
        - Element: {element}
        - Ruling Planet: {ruler}
        
        Return ONLY valid JSON:
        {{
            "hook": "The biggest theme/prediction for {sign} in {year}",
            "intro": "Year overview - what makes {year} special for {sign}",
            "love": "Full year love forecast - key periods, predictions",
            "career": "Career trajectory - opportunities, promotions, changes",
            "money": "Financial year outlook - wealth building, caution periods",
            "health": "Health trends and focus areas throughout the year",
            "best_months": "Top 3 luckiest months and why",
            "challenging_months": "Months requiring extra care and how to handle them",
            "yearly_advice": "The key lesson and growth opportunity for {sign} in {year}",
            "metadata": {{
                "title": "{sign} {year} Yearly Horoscope ⭐ (under 80 chars)",
                "description": "Comprehensive yearly forecast description",
                "tags": "Yearly horoscope tags"
            }}
        }}
        """
        return self._generate_script(sign, year, "Yearly", system_prompt, user_prompt)

    def generate_daily_insight_script(self, sign: str, date: str) -> dict:
        """Generates a detailed Daily Insight deep-dive (Evening Content)."""
        logging.info(f"⭐ Astrologer: Generating Daily Cosmic Insight for {sign}...")
        
        sign_key = sign.lower().split()[0]
        element = self.ZODIAC_ELEMENTS.get(sign_key, "Unknown")
        ruler = self.RULING_PLANETS.get(sign_key, "Unknown")
        
        system_prompt = """
        You are 'Stella Nova', providing deep cosmic insights for personal growth.
        
        This is a REFLECTIVE, SPIRITUAL content piece focusing on:
        - How today's planetary energy affects inner growth
        - Manifestation and intention-setting guidance
        - Crystal, color, and element recommendations
        - Affirmations aligned with today's energy
        - Meditation or journaling prompts
        
        Tone: Warm, wise, nurturing, empowering.
        Write in clear, beautiful ENGLISH.
        """
        
        user_prompt = f"""
        Generate a **Daily Cosmic Insight** for **{sign}** for **{date}**.
        
        Sign Details:
        - Element: {element}
        - Ruling Planet: {ruler}
        
        Return ONLY valid JSON:
        {{
            "hook": "Inspiring opening about today's cosmic energy",
            "intro": "The spiritual theme of today for {sign}",
            "cosmic_message": "A personal message from the universe to {sign}",
            "affirmation": "A powerful affirmation to repeat today",
            "crystal": "Recommended crystal for today and why",
            "meditation_focus": "Brief guided visualization or focus point",
            "journal_prompt": "A reflective question to explore",
            "closing": "Empowering closing message",
            "metadata": {{
                "title": "{sign} Cosmic Insight {date} ✨ #shorts #viral",
                "description": "Spiritual guidance description",
                "tags": "Spiritual, cosmic, manifestation tags"
            }}
        }}
        """
        return self._generate_script(sign, date, "Daily_Insight", system_prompt, user_prompt)

    def generate_viral_metadata(self, sign: str, date_str: str, period_type: str, script_data) -> dict:
        """
        Generates Viral YouTube Metadata (Title, Desc, Tags) using the LLM.
        """
        logging.info(f"🚀 Astrologer: Generating Viral Metadata for {sign} ({period_type})...")
        
        # Handle script_data being a list
        if isinstance(script_data, list):
            if len(script_data) > 0 and isinstance(script_data[0], dict):
                script_data = script_data[0]
            else:
                script_data = {}
        
        # Safely extract context
        if isinstance(script_data, dict):
            context = f"Hook: {script_data.get('hook', '')}. Theme: {script_data.get('intro', '')}"
        else:
            context = "Daily horoscope prediction"
        
        system_prompt = """
        You are a YouTube Growth Expert specializing in astrology content.
        
        TITLE RULES:
        1. Under 80 characters
        2. Include the zodiac sign name
        3. Create curiosity or urgency
        4. Use 1 emoji at the end (⭐, 🔮, ✨, 💫)
        5. End with #shorts #viral
        
        DESCRIPTION RULES:
        1. Hook in first line
        2. Mention what's covered (love, career, money)
        3. Include 15-20 hashtags mixing broad and specific
        
        TAG RULES:
        1. Include sign name + horoscope
        2. Include: shorts, viral, zodiac, astrology
        3. Include trending astrology terms
        """
        
        user_prompt = f"""
        Generate YouTube Metadata for a **{period_type}** horoscope video.
        **Sign**: {sign}
        **Date**: {date_str}
        **Content Highlight**: {context}
        
        Return ONLY valid JSON:
        {{
            "title": "Catchy title under 80 chars ending with ⭐ #shorts #viral",
            "description": "Engaging description with hashtags",
            "tags": ["list", "of", "25+", "relevant", "tags"]
        }}
        """
        
        result = self._generate_script(sign, date_str, f"Metadata_{period_type}", system_prompt, user_prompt)
        
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]
            else:
                raise Exception(f"Metadata generation failed for {sign}.")
        
        if not isinstance(result, dict) or 'title' not in result:
            raise Exception("Invalid metadata generated.")
        
        # Ensure hashtags are present
        title = result.get('title', '')
        if '#shorts' not in title.lower():
            if len(title) > 80:
                title = title[:77] + "..."
            title = title.rstrip() + " #shorts #viral"
        elif '#viral' not in title.lower():
            title = title.rstrip() + " #viral"
        result['title'] = title
        
        if 'categoryId' not in result:
            result['categoryId'] = '24'
            
        return result


# Backward compatibility alias
def generate_daily_rashifal(self, rashi: str, date: str) -> dict:
    """Alias for backward compatibility."""
    return self.generate_daily_horoscope(rashi, date)

# Test Run
# if __name__ == "__main__":
#     agent = AstrologerAgent()
#     print(json.dumps(agent.generate_daily_horoscope("Aries", "January 26, 2026"), indent=2))
