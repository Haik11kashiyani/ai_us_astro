import os
import json
import logging
import random
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class YouTubeUploader:
    """
    Handles YouTube Authentication and Video Uploads.
    Uses Refresh Token flow for headless automation.
    Generates VIRAL-OPTIMIZED metadata dynamically.
    """
    
    # Viral hook phrases for titles
    VIRAL_HOOKS = [
        "MAJOR SHIFT",
        "BIG NEWS",
        "You Won't Believe",
        "Watch This NOW",
        "URGENT Message",
        "Something HUGE",
        "SHOCKING Prediction",
        "Life-Changing",
        "MUST WATCH",
        "Don't Miss This",
        "FINALLY",
        "The Universe Says",
        "Stars Reveal",
        "Cosmic Alert",
        "BREAKTHROUGH"
    ]
    
    # Emotional triggers
    EMOTIONAL_TRIGGERS = [
        "💫 CHANGES COMING",
        "🔮 BIG ENERGY",
        "⚡ POWERFUL DAY",
        "✨ MAGIC AWAITS",
        "🌟 YOUR TIME NOW",
        "💥 MAJOR MOVES",
        "🚀 LEVEL UP",
        "💎 GOLDEN OPPORTUNITY"
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client_id = os.getenv("YOUTUBE_CLIENT_ID")
        self.client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
        self.service = None
        
        if self.client_id and self.client_secret and self.refresh_token:
            self._authenticate()
        else:
            self.logger.warning("⚠️ YouTube Credentials missing! Uploads will fail.")

    def _authenticate(self):
        """Authenticates using the refresh token."""
        try:
            creds = Credentials(
                None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.service = build('youtube', 'v3', credentials=creds)
            self.logger.info("✅ YouTube Authenticated Successfully.")
        except Exception as e:
            self.logger.error(f"❌ YouTube Auth Failed: {e}")

    def generate_metadata(self, sign_name: str, date_str: str, period_type: str = "Daily") -> dict:
        """
        Generates VIRAL-OPTIMIZED Title, Description, and Tags.
        Ensures #shorts is ALWAYS in title. 100% dynamic, never static.
        """
        # Clean sign name
        clean_sign = sign_name.split('(')[0].strip() if '(' in sign_name else sign_name
        sign_lower = clean_sign.lower()
        sign_upper = clean_sign.upper()
        
        # Extract year/month dynamically
        import re
        year_match = re.search(r'\b(20\d{2})\b', date_str)
        dynamic_year = year_match.group(1) if year_match else "2026"
        
        # Random viral elements
        hook = random.choice(self.VIRAL_HOOKS)
        trigger = random.choice(self.EMOTIONAL_TRIGGERS)
        
        # --- DYNAMIC VIRAL TITLE STRATEGY ---
        title_templates = {
            "Daily": [
                f"{sign_upper}: {hook}! {date_str} ⭐ #shorts",
                f"🔮 {clean_sign} TODAY - {hook} {date_str} #shorts",
                f"{trigger} {clean_sign} {date_str} #shorts",
                f"{clean_sign} Daily Horoscope | {hook}! ⭐ #shorts",
                f"⚡ {sign_upper} {date_str} - The Stars Say THIS #shorts",
            ],
            "Monthly": [
                f"{sign_upper} {date_str}: {hook}! 🌙 #shorts",
                f"🔮 {clean_sign} Monthly - {hook} #shorts",
                f"{trigger} {clean_sign} This Month! #shorts",
                f"{clean_sign} {date_str} Horoscope | GAME CHANGER ⭐ #shorts",
            ],
            "Yearly": [
                f"{sign_upper} {dynamic_year}: Your YEAR! {hook} 🌟 #shorts",
                f"🔮 {clean_sign} {dynamic_year} - {hook}! #shorts",
                f"{clean_sign} Yearly Horoscope {dynamic_year} | {trigger} #shorts",
                f"⭐ {sign_upper} {dynamic_year} - THE STARS HAVE SPOKEN #shorts",
            ],
            "Daily_Insight": [
                f"✨ {clean_sign} Cosmic Message - {hook}! #shorts",
                f"{sign_upper}: The Universe Speaks {date_str} 🔮 #shorts",
                f"{trigger} {clean_sign} Today! #shorts",
            ]
        }
        
        # Select random title from appropriate list
        titles = title_templates.get(period_type, title_templates["Daily"])
        title = random.choice(titles)
        
        # Ensure title is under 100 chars and has #shorts
        if len(title) > 100:
            title = title[:85] + "... #shorts"
        if "#shorts" not in title.lower():
            title = title.rstrip() + " #shorts"

        # --- VIRAL DESCRIPTION STRATEGY ---
        # "How to find check" is already here, but let's make it more robust and add more "filler" viral text to use space.
        
        desc = f"""🔮 {clean_sign} {period_type} Horoscope - {date_str}

{trigger}

The cosmos has a powerful message for {clean_sign} today! 🌌
Are you ready to embrace your destiny? This reading reveals the hidden energies influencing your life right now. 
Watch till the end to discover what the stars have in store for you! ⭐

👇 **TIME STAMPS & HIGHLIGHTS** 👇
0:00 - {hook}
0:15 - Love & Relationships 💖
0:30 - Career & Money 💰
0:45 - Health & Wellness 🌿
0:55 - Lucky Numbers & Colors 🍀

📅 **HOW TO FIND YOUR ZODIAC SIGN (Western / Tropical):**
♈ Aries: Mar 21 - Apr 19
♉ Taurus: Apr 20 - May 20
♊ Gemini: May 21 - Jun 20
♋ Cancer: Jun 21 - Jul 22
♌ Leo: Jul 23 - Aug 22
♍ Virgo: Aug 23 - Sep 22
♎ Libra: Sep 23 - Oct 22
♏ Scorpio: Oct 23 - Nov 21
♐ Sagittarius: Nov 22 - Dec 21
♑ Capricorn: Dec 22 - Jan 19
♒ Aquarius: Jan 20 - Feb 18
♓ Pisces: Feb 19 - Mar 20

🌟 **WHY WATCH DAILY?**
Astrology helps you align with the cosmic flow. By understanding the daily energies, you can make better decisions, improve your relationships, and manifest your desires with greater ease.
This channel is dedicated to bringing you the most accurate, uplifting, and clear western astrology forecasts.

✨ **MANIFESTATION AFFIRMATION FOR {clean_sign.upper()}:**
"I am aligned with the universe. I attract abundance, love, and joy into my life effortlessly. My path is clear."

👆 LIKE if this resonates!
💬 COMMENT "{clean_sign}" to claim this energy!
🔔 SUBSCRIBE for your daily cosmic guidance!

━━━━━━━━━━━━━━━━━━━━━━━
** FOLLOW THE STARS **
Don't miss out on important planetary shifts!
Mercury Retrograde updates, Full Moon rituals, and New Moon intentions.

#shorts #viral #{sign_lower} #{sign_lower}horoscope #horoscope #astrology #zodiac #zodiacsigns #horoscopetoday #dailyhoroscope #{sign_lower}{dynamic_year} #tarot #starsigns #universe #manifestation #spirituality #cosmicenergy #psychic #fortune #destiny #fyp #foryou #trending #explore #viralshorts #lawofattraction #witchesofyoutube #astrologylovers #zodiacfacts
━━━━━━━━━━━━━━━━━━━━━━━
""".strip()

        # --- MEGA TAGS STRATEGY ---
        tags = [
            # Sign-specific (high intent)
            f"{sign_lower} horoscope",
            f"{sign_lower} horoscope today",
            f"{sign_lower} daily horoscope",
            f"{sign_lower} {dynamic_year}",
            f"{sign_lower} horoscope {dynamic_year}",
            f"{sign_lower} zodiac",
            f"{sign_lower} prediction",
            f"{sign_lower} today",
            # General astrology (high volume)
            "horoscope",
            "horoscope today", 
            "daily horoscope",
            "astrology",
            "zodiac",
            "zodiac signs",
            "star signs",
            "horoscope predictions",
            # Viral tags (algorithm boost)
            "shorts",
            "viral",
            "trending",
            "fyp",
            "foryou",
            "explore",
            "viralshorts",
            # Spiritual/Manifestation (growing niche)
            "manifestation",
            "universe",
            "cosmic energy",
            "spiritual",
            "tarot",
            "psychic",
            "fortune",
            "destiny",
            # Year-specific
            f"horoscope {dynamic_year}",
            f"astrology {dynamic_year}",
        ]
        
        return {
            "title": title,
            "description": desc,
            "tags": tags,
            "categoryId": "24"  # Entertainment
        }

    def upload_video(self, file_path: str, metadata: dict, privacy_status: str = "public", publish_at: datetime = None):
        """Uploads the video. Supports scheduled publishing."""
        if not self.service:
            self.logger.error("❌ Cannot upload: Not Authenticated.")
            return False

        if not os.path.exists(file_path):
            self.logger.error(f"❌ File not found: {file_path}")
            return False

        self.logger.info(f"🚀 Uploading {file_path}...")
        self.logger.info(f"   Title: {metadata['title']}")
        
        status_body = {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
        
        # Handle Scheduling
        if publish_at:
            status_body["privacyStatus"] = "private"
            status_body["publishAt"] = publish_at.isoformat() + "Z" 
            self.logger.info(f"   📅 Scheduled for: {status_body['publishAt']}")

        body = {
            "snippet": {
                "title": metadata['title'],
                "description": metadata['description'],
                "tags": metadata['tags'],
                "categoryId": metadata['categoryId']
            },
            "status": status_body
        }

        try:
            media = MediaFileUpload(file_path, chunksize=1024*1024, resumable=True)
            request = self.service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"      📤 Uploading... {progress}%")
            
            video_id = response.get("id")
            self.logger.info(f"✅ Upload Complete! Video ID: {video_id}")
            self.logger.info(f"   URL: https://youtube.com/shorts/{video_id}")
            return True
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Upload Failed: {e}")
            self.logger.error(f"   Full traceback:\n{traceback.format_exc()}")
            return False
