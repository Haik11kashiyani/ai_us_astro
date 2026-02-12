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

    # Standard "How to Find Your Sign" Guide (Western Astrology)
    FIND_SIGN_GUIDE = """
🌟 HOW TO FIND YOUR ZODIAC SIGN (Western Astrology):
📅 Aries: Mar 21 - Apr 19
📅 Taurus: Apr 20 - May 20
📅 Gemini: May 21 - Jun 20
📅 Cancer: Jun 21 - Jul 22
📅 Leo: Jul 23 - Aug 22
📅 Virgo: Aug 23 - Sep 22
📅 Libra: Sep 23 - Oct 22
📅 Scorpio: Oct 23 - Nov 21
📅 Sagittarius: Nov 22 - Dec 21
📅 Capricorn: Dec 22 - Jan 19
📅 Aquarius: Jan 20 - Feb 18
📅 Pisces: Feb 19 - Mar 20
"""
    
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
        
        # Google AI key (PRIMARY provider - free & reliable)
        self.google_ai_key = os.getenv("GOOGLE_AI_API_KEY")
        if self.google_ai_key and GOOGLE_AI_AVAILABLE:
            genai.configure(api_key=self.google_ai_key)
            self.google_model = genai.GenerativeModel('gemini-2.0-flash')
            logging.info("🌟 Google AI Studio (Gemini) PRIMARY provider enabled")
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

    def _generate_with_google_ai(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> dict:
        """Primary provider: Google AI Studio (Gemini). Free with 15 RPM limit. ENFORCES 1 CALL PER MINUTE STRICTLY."""
        import time
        if not self.google_model:
            return None
            
        # STRICT RATE LIMIT: 60 seconds sleep to ensure max 1 RPM per instance
        # This allows multiple workflows to run (up to 15) without hitting the global 15 RPM limit
        logging.info("⏳ STRICT RATE LIMIT: Sleeping 60s before Google AI call to prevent 429s...")
        time.sleep(60)
            
        for attempt in range(1, max_retries + 1):
            logging.info(f"🌟 Google AI Studio (Gemini) - Attempt {attempt}/{max_retries}...")
            try:
                # Rate limit: 15 RPM = 1 request per 4 seconds (use 5s to be safe)
                if attempt > 1:
                    wait_time = 10 * attempt  # 20s, 30s backoff
                    logging.info(f"⏳ Rate limit guard: waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                
                full_prompt = f"{system_prompt}\n\nIMPORTANT: Return ONLY valid JSON. No markdown formatting, no preambles, no extra text.\n\n{user_prompt}"
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
                error_str = str(e)
                logging.warning(f"⚠️ Google AI attempt {attempt} failed: {e}")
                
                # If rate limited, wait longer and retry
                if "429" in error_str or "Resource" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries:
                        wait_time = 60 * attempt  # 60s, 120s
                        logging.info(f"⏳ Google AI rate limited. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                if attempt >= max_retries:
                    logging.error(f"❌ Google AI Studio exhausted all {max_retries} retries.")
                    return None
        
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
        """Generates content using priority: Google AI → OpenRouter → Mock Data."""
        import time
        
        # ========================================
        # PRIORITY 1: Google AI (FREE, reliable)
        # ========================================
        if self.google_model:
            logging.info(f"🌟 PRIORITY 1: Using Google AI (Gemini) for {sign} {period_type}...")
            google_result = self._generate_with_google_ai(system_prompt, user_prompt)
            if google_result:
                return google_result
            logging.warning("⚠️ Google AI failed. Falling back to OpenRouter...")
        
        # ========================================
        # PRIORITY 2: OpenRouter (backup)
        # ========================================
        if self.client and self.models:
            errors = []
            tried_backup = False
            
            while True:
                for model in self.models:
                    # Short wait between attempts (30s instead of 2 min)
                    logging.info(f"⏳ Rate Limit Guard: Waiting 30s before OpenRouter call...")
                    time.sleep(30)
                    
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
        
        # ========================================
        # PRIORITY 3: Mock Data (SAFETY NET)
        # ========================================
        logging.warning(f"⚠️ ALL APIs failed for {sign}. Using mock data to ensure video is still produced!")
        return self._get_mock_data(sign, period_type)

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
        You are 'Stella', a wise and empathetic friend who knows astrology deeply.
        
        Your task: Talk to the user about their day as if you are sitting right next to them.
        
        TONE & STYLE:
        1. **HUMAN & CONVERSATIONAL**: Do not sound like a robot or a news anchor. Sound like a best friend giving advice.
        2. **EMPATHETIC**: Use phrases like "I know it feels heavy...", "You might be wondering...", "Here is the good news..."
        3. **DIRECT "YOU"**: Speak directly to the person. Connect deeply.
        4. **NO ASTRO-JARGON OVERLOAD**: Explain the transit like you are talking to a normal person. "Mars is making you feisty" instead of "Mars square Pluto causes aggression".
        5. **REAL TALK**: Be honest. If it's a hard day, say "Look, today might be tough, but here is how you handle it."
        
        FORMATTING:
        - Add EMOTION TAGS at the start of sections if helpful: (Warmly), (Honestly), (Excited).
        - Use simple, punchy English.
        """,
        
        user_prompt = f"""
        Generate a **Daily Horoscope** for **{sign}** for **{date}**.
        
        Sign Details:
        - Element: {element}
        - Ruling Planet: {ruler}
        
        **MANDATORY REQUIREMENT**:
        - Analyze the ACTUAL planetary positions for {date}.
        - If the forecast is tough, say it. If it's lucky, say it. The user wants the TRUTH.
        - Connect the 'astrological cause' (the transit) to the 'real-world effect' (the event).
        
        Return ONLY valid JSON:
        {{
            "hook": "A short, punchy, truth-telling opening. Can be a warning or a celebration. (Max 15 words)",
            "intro": "The core astrological weather report. What transits are hitting {sign} today?",
            "love": "Specific relationship advice. Mention if it's a day for passion or a day for distance/conflict.",
            "career": "Work dynamics. Any power struggles? Breakthroughs? Boredom?",
            "money": "Financial reality check. Spending spree or tightening belt?",
            "health": "Physical & mental state. Energy levels, stress points.",
            "remedy": "A specific, actionable remedy to improve the day's energy (e.g., color to wear, mantra, action to avoid).",
            "advice": "The single most important action to take today to navigate these energies.",
            "lucky_color": "A color that balances today's specific energy",
            "lucky_number": "A numerologically significant number for today",
            "best_time": "Precise time window for peak performance",
            "metadata": {{
                "title": "Urgent/Exciting Title for {sign} {date} (under 80 chars) ⭐ #shorts #viral",
                "description": "Summary of the key prediction + hashtags",
                "tags": "viral, astrology, {sign.lower()}, horoscope, truth, 100% accurate, shorts"
            }}
        }}
        """
        result = self._generate_script(sign, date, "Daily", system_prompt, user_prompt)
        
        # Enhance Description with Guide if missing
        if "metadata" in result and "description" in result["metadata"]:
            desc = result["metadata"]["description"]
            if "HOW TO FIND YOUR ZODIAC SIGN" not in desc:
                 result["metadata"]["description"] = desc + "\n" + self.FIND_SIGN_GUIDE
                 
        return result

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
        7. Use (Happy), (Excited), (Serious), (Caution), (Warm) tags to indicate tone.
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
        result = self._generate_script(sign, month_year, "Monthly", system_prompt, user_prompt)

        # Enhance Description with Guide if missing
        if "metadata" in result and "description" in result["metadata"]:
            desc = result["metadata"]["description"]
            if "HOW TO FIND YOUR ZODIAC SIGN" not in desc:
                 result["metadata"]["description"] = desc + "\n" + self.FIND_SIGN_GUIDE

        return result

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
        result = self._generate_script(sign, year, "Yearly", system_prompt, user_prompt)

        # Enhance Description with Guide if missing
        if "metadata" in result and "description" in result["metadata"]:
            desc = result["metadata"]["description"]
            if "HOW TO FIND YOUR ZODIAC SIGN" not in desc:
                 result["metadata"]["description"] = desc + "\n" + self.FIND_SIGN_GUIDE

        return result

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
        result = self._generate_script(sign, date, "Daily_Insight", system_prompt, user_prompt)

        # Enhance Description with Guide if missing
        if "metadata" in result and "description" in result["metadata"]:
            desc = result["metadata"]["description"]
            if "HOW TO FIND YOUR ZODIAC SIGN" not in desc:
                 result["metadata"]["description"] = desc + "\n" + self.FIND_SIGN_GUIDE
                 
        return result

    def generate_viral_metadata(self, sign: str, date_str: str, period_type: str, script_data) -> dict:
        """
        Generates MEGA Viral YouTube Metadata (Title, Desc, Tags) using the LLM.
        Includes trending tags from every relevant niche for maximum discoverability.
        """
        logging.info(f"🚀 Astrologer: Generating MEGA Viral Metadata for {sign} ({period_type})...")
        
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
        You are a YouTube Growth Expert specializing in viral astrology content.
        
        TITLE RULES:
        1. Under 80 characters
        2. Include the zodiac sign name
        3. Create EXTREME curiosity or urgency ("You WON'T believe...", "SHOCKING truth...")
        4. Use 1 emoji at the end (⭐, 🔮, ✨, 💫)
        5. End with #shorts #viral
        
        DESCRIPTION RULES (MAXIMIZE SEO):
        1. Clickbait hook in first line (this shows in search results)
        2. Mention: love, career, money, health, lucky numbers
        3. LONG description (2000-4000 chars) with:
           - "Deep Dive" section expanding on the hook
           - "Why Astrology Works" mini-essay
           - "General Traits" section
           - "How to Find Your Sign" guide
        4. End with 40+ hashtags mixing: sign-specific, general astrology, trending viral, manifestation, spiritual, self-help
        
        TAG RULES (50+ TAGS for maximum reach):
        1. Sign-specific: "{sign} horoscope", "{sign} today", "{sign} 2026"
        2. General astrology: horoscope, zodiac, daily horoscope, astrology
        3. VIRAL/TRENDING: shorts, viral, fyp, trending, explore, foryou
        4. Spiritual: manifestation, law of attraction, universe, angel numbers, 1111
        5. Self-help: motivation, self care, healing, mindset, positivity
        6. Cross-niche trending: asmr, satisfying, storytime, grwm, aesthetic
        7. Engagement: must watch, don't skip, watch till end
        """
        
        user_prompt = f"""
        Generate YouTube Metadata for a **{period_type}** horoscope video.
        **Sign**: {sign}
        **Date**: {date_str}
        **Content Highlight**: {context}
        
        Return ONLY valid JSON:
        {{
            "title": "Catchy title under 80 chars ending with ⭐ #shorts #viral",
            "description": "EXTREMELY DETAILED description. Include: Hook, Deep Dive (300 words), {sign} Traits (200 words), Spiritual Meaning, How to Find Your Sign guide, and 40+ Hashtags. MUST be > 2000 characters.",
            "tags": ["list", "of", "50+", "relevant", "tags", "including", "viral", "trending", "cross-niche"]
        }}
        """
        
        result = self._generate_script(sign, date_str, f"Metadata_{period_type}", system_prompt, user_prompt)
        
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]
            else:
                logging.warning("⚠️ LLM metadata generation failed. Will use uploader fallback.")
                return None
        
        if not isinstance(result, dict) or 'title' not in result:
            logging.warning("⚠️ Invalid metadata structure. Will use uploader fallback.")
            return None
        
        # Ensure hashtags are present
        title = result.get('title', '')
        if '#shorts' not in title.lower():
            if len(title) > 80:
                title = title[:77] + "..."
            title = title.rstrip() + " #shorts #viral"
        elif '#viral' not in title.lower():
            title = title.rstrip() + " #viral"
        
        description = result.get('description', '')
        
        # Append "How to Find Your Sign" guide if not present
        if "HOW TO FIND YOUR ZODIAC SIGN" not in description:
            result['description'] = description + "\n" + self.FIND_SIGN_GUIDE
        
        # FORCE-INJECT mega viral tags into the tags list
        sign_lower = sign.lower().split()[0]
        import re
        year_match = re.search(r'\b(20\d{2})\b', date_str)
        dynamic_year = year_match.group(1) if year_match else "2026"
        
        # 300+ KEYWORDS BLOCK for Description (Max SEO)
        keywords_block = [
            f"{sign_lower} horoscope", f"{sign_lower} today", f"{sign_lower} daily", f"{sign_lower} {dynamic_year}",
            "horoscope", "astrology", "zodiac", "fortune", "tarot", "manifestation", "spirituality", "love", "career", "money",
            "shorts", "viral", "trending", "fyp", "foryou", "explore", "aesthetic", "satisfying", "peaceful", "calm",
            "healing", "meditation", "yoga", "mindfulness", "positive vibes", "motivation", "inspiration", "self care",
            "lawofattraction", "abundance", "wealth", "success", "growth", "mindset", "energy", "vibration", "frequency",
            "528hz", "432hz", "binaural beats", "asmr", "relaxing", "sleep music", "focus", "study", "work",
            "mercury retrograde", "full moon", "new moon", "eclipse", "solar eclipse", "lunar eclipse", "retrograde",
            "mars", "venus", "jupiter", "saturn", "uranus", "neptune", "pluto", "sun", "moon", "rising",
            "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
            "fire sign", "earth sign", "air sign", "water sign", "cardinal", "fixed", "mutable",
            "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "weekend", "week", "month", "year",
            "2024", "2025", "2026", "prediction", "forecast", "reading", "psychic reading", "tarot reading", "angel cards",
            "angel numbers", "111", "222", "333", "444", "555", "666", "777", "888", "999", "1111", "1212",
            "soulmate", "twin flame", "karmic", "partner", "ex", "crush", "marriage", "divorce", "breakup", "reconciliation",
            "job", "promotion", "raise", "business", "entrepreneur", "investment", "crypto", "stocks", "lottery", "luck",
            "health", "wellness", "fitness", "diet", "nutrition", "mental health", "anxiety", "stress", "depression", "therapy",
            "happy", "joy", "blessed", "grateful", "thankful", "love you", "peace", "hope", "faith", "believe",
            "magic", "witch", "wicca", "spells", "crystals", "herbs", "candles", "rituals", "moon water", "sage",
            "funny", "comedy", "meme", "relatable", "truth", "facts", "did you know", "life hacks", "tips", "tricks",
            "how to", "tutorial", "guide", "explained", "education", "learning", "school", "college", "university",
            "usa", "uk", "canada", "australia", "india", "philippines", "europe", "asia", "africa", "world",
            "must watch", "watch till end", "don't skip", "wait for it", "omg", "wow", "crazy", "shocking", "scary",
            "mystery", "conspiracy", "secret", "hidden", "unknown", "truth revealed", "exposed", "leak", "news",
            "update", "alert", "warning", "urgent", "important", "breaking", "live", "stream", "video",
        ]
        
        # Multiply to reach "300 is must" count if needed, but 100+ high quality is better. 
        # Let's just create a massive string of tags for the description.
        mega_tag_string = " ".join([f"#{k.replace(' ', '')}" for k in keywords_block])
        
        # Append to description if space allows (YouTube desc limit is 5000 chars)
        current_len = len(result['description'])
        if current_len < 4500:
            result['description'] += f"\n\n🔎 **INCOMING SEARCH TERMS:**\n{mega_tag_string}"[:(4800 - current_len)]
        
        # Verify tags for the "tags" field (Max 500 chars limit by YouTube)
        mega_viral_tags = keywords_block[:50] # Take top 50 for tags list
        
        # Merge LLM tags + mega viral tags (deduplicate)
        existing_tags = result.get('tags', [])
        if isinstance(existing_tags, str):
            existing_tags = [t.strip() for t in existing_tags.split(',')]
        
        all_tags = list(dict.fromkeys(existing_tags + mega_viral_tags))  # dedupe preserving order
        
        # YouTube Tag Limit logic: Must be < 500 characters TOTAL. 
        # If we just dump 50 tags, it will likely exceed 500 chars.
        # So we filter to fit.
        final_tags = []
        current_char_count = 0
        for t in all_tags:
            t_clean = t.replace("#", "").strip()[:30] # Limit individual tag length
            if current_char_count + len(t_clean) + 1 < 490: # buffer
                final_tags.append(t_clean)
                current_char_count += len(t_clean) + 1
            else:
                break
                
        result['tags'] = final_tags
        
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
