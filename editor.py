import os
import logging
import json
import asyncio
import nest_asyncio
from playwright.async_api import async_playwright
from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeAudioClip, vfx, CompositeVideoClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Allow nested asyncio loops (required for Playwright in some envs)
nest_asyncio.apply()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Western Zodiac Sign to filename mapping
SIGN_IMAGE_MAP = {
    "aries": "aries",
    "taurus": "taurus",
    "gemini": "gemini",
    "cancer": "cancer",
    "leo": "leo",
    "virgo": "virgo",
    "libra": "libra",
    "scorpio": "scorpio",
    "sagittarius": "sagittarius",
    "capricorn": "capricorn",
    "aquarius": "aquarius",
    "pisces": "pisces",
}

# Cosmic Western Astrology Color Schemes
# Deep space purples, cosmic blues, and stellar golds
SIGN_STYLES = {
    # Fire Signs - Warm cosmic (Deep reds, oranges, gold nebulas)
    "aries": {
        "grad": ("#1a0a0a", "#3d1515", "#ff6b35"),
        "glow": "#ff4500",
        "element": "fire"
    },
    "leo": {
        "grad": ("#1a1005", "#3d2a10", "#ffd700"),
        "glow": "#ffc107",
        "element": "fire"
    },
    "sagittarius": {
        "grad": ("#1a0520", "#3d1040", "#ff8c00"),
        "glow": "#ff7043",
        "element": "fire"
    },
    
    # Earth Signs - Deep forest and emerald cosmos
    "taurus": {
        "grad": ("#050f08", "#0d2818", "#4caf50"),
        "glow": "#66bb6a",
        "element": "earth"
    },
    "virgo": {
        "grad": ("#0a1a0a", "#1a3a1a", "#8bc34a"),
        "glow": "#9ccc65",
        "element": "earth"
    },
    "capricorn": {
        "grad": ("#0a0a0a", "#1a1a1a", "#78909c"),
        "glow": "#90a4ae",
        "element": "earth"
    },

    # Air Signs - Ethereal lavenders and cosmic pastels
    "gemini": {
        "grad": ("#0f0a1a", "#201535", "#ffeb3b"),
        "glow": "#fff176",
        "element": "air"
    },
    "libra": {
        "grad": ("#150520", "#2a0a40", "#e1bee7"),
        "glow": "#ce93d8",
        "element": "air"
    },
    "aquarius": {
        "grad": ("#050a1a", "#0a1535", "#4fc3f7"),
        "glow": "#29b6f6",
        "element": "air"
    },

    # Water Signs - Deep ocean and mystic blues
    "cancer": {
        "grad": ("#050810", "#0a1020", "#90caf9"),
        "glow": "#64b5f6",
        "element": "water"
    },
    "scorpio": {
        "grad": ("#150508", "#2a0a10", "#ef5350"),
        "glow": "#e53935",
        "element": "water"
    },
    "pisces": {
        "grad": ("#051015", "#0a2030", "#80deea"),
        "glow": "#4dd0e1",
        "element": "water"
    },
}

# Dynamic Lucky Color Themes (Overrides Sign defaults)
COLOR_STYLES = {
    "red": {
        "grad": ("#150505", "#2a0a0a", "#ef5350"),
        "glow": "#f44336",
        "element": "fire"
    },
    "blue": {
        "grad": ("#050510", "#0a0a20", "#42a5f5"),
        "glow": "#2196f3",
        "element": "water"
    },
    "green": {
        "grad": ("#051005", "#0a200a", "#66bb6a"),
        "glow": "#4caf50",
        "element": "earth"
    },
    "yellow": {
        "grad": ("#101005", "#201a0a", "#ffee58"),
        "glow": "#ffeb3b",
        "element": "air"
    },
    "white": {
        "grad": ("#101010", "#1a1a1a", "#e0e0e0"),
        "glow": "#ffffff",
        "element": "air"
    },
    "black": {
        "grad": ("#000000", "#0a0a0a", "#424242"),
        "glow": "#757575",
        "element": "earth"
    },
    "pink": {
        "grad": ("#150510", "#2a0a20", "#f48fb1"),
        "glow": "#ec407a",
        "element": "fire"
    },
    "orange": {
        "grad": ("#150a05", "#2a140a", "#ffb74d"),
        "glow": "#ff9800",
        "element": "fire"
    },
    "purple": {
        "grad": ("#0a0515", "#140a2a", "#ba68c8"),
        "glow": "#9c27b0",
        "element": "air"
    },
    "brown": {
        "grad": ("#0a0805", "#1a100a", "#8d6e63"),
        "glow": "#795548",
        "element": "earth"
    },
    "gold": {
        "grad": ("#151005", "#2a1a0a", "#ffd54f"),
        "glow": "#ffc107",
        "element": "fire"
    },
    "silver": {
        "grad": ("#080a10", "#101520", "#b0bec5"),
        "glow": "#cfd8dc",
        "element": "water"
    },
}

# New cosmic animation styles
COSMIC_ANIM_STYLES = ['cosmic', 'stellar', 'nebula', 'constellation', 'aurora']


class EditorEngine:
    """
    Premium COSMIC Video Engine for Western Astrology.
    Uses Playwright (Headless Chrome) to render HTML5 animations to video frames.
    Features: Starfield, nebulas, constellation lines, cosmic effects.
    """
    
    def __init__(self):
        self.width = 1080
        self.height = 1920
        self.template_path = os.path.abspath("templates/scene.html")
        os.makedirs("assets/temp", exist_ok=True)

    def _get_sign_key(self, sign_name: str) -> str:
        """Extract sign key from name like 'Aries' or 'Aries (fire)'."""
        sign_key = sign_name.lower().split()[0].split("(")[0].strip()
        return sign_key

    def get_sign_image_path(self, sign_name: str, period_type: str = "Daily") -> str:
        """
        Finds the appropriate zodiac sign image using fuzzy matching.
        """
        sign_key = self._get_sign_key(sign_name)

        # Folders to search in order
        folders = ["12_photos"]
        if period_type == "Monthly": folders.insert(0, "monthly_12_photos")
        elif period_type == "Yearly": folders.insert(0, "yearly_12_photos")
        
        # Translate using map if available
        mapped_key = SIGN_IMAGE_MAP.get(sign_key, sign_key)
        
        search_keys = [mapped_key, sign_key]
        search_keys = list(dict.fromkeys(filter(None, search_keys)))
        
        for folder in folders:
            folder_path = os.path.join("assets", folder)
            if not os.path.exists(folder_path): continue
            
            try:
                files = os.listdir(folder_path)
                for f in files:
                    fname_lower = f.lower()
                    for key in search_keys:
                        if key and key in fname_lower:
                             return os.path.abspath(os.path.join(folder_path, f))
            except Exception as e:
                logging.warning(f"Error scanning folder {folder}: {e}")
                
        return None

    async def _render_html_scene(self, sign_name, text, duration, subtitle_data, theme_override=None, header_text="", period_type="Daily", anim_style="cosmic"):
        """
        Renders the cosmic scene using Playwright.
        Captures screenshots at 30 FPS.
        """
        frames_dir = f"assets/temp/frames_{hash(text)}"
        os.makedirs(frames_dir, exist_ok=True)
        
        sign_img = self.get_sign_image_path(sign_name, period_type) or ""
        sign_key = self._get_sign_key(sign_name)
        
        # Get style: COLOR_THEME > SIGN_STYLES > Fallback
        style = None
        if theme_override and theme_override in COLOR_STYLES:
            style = COLOR_STYLES[theme_override]
        
        if not style:
             style = SIGN_STYLES.get(sign_key)
             
        if not style:
             # Default cosmic purple theme
             style = {
                 "grad": ("#0a0515", "#140a2a", "#9c27b0"),
                 "glow": "#ce93d8",
                 "element": "neutral"
             }
        
        grad = style["grad"]
        glow = style["glow"]
        element = style["element"]
        
        # Convert local path to file URL for browser
        if sign_img:
            sign_img_url = f"file:///{sign_img.replace(os.sep, '/')}"
        else:
            sign_img_url = ""
            
        # Construct URL with params
        import urllib.parse
        encoded_text = urllib.parse.quote(text)
        encoded_header = urllib.parse.quote(header_text)
        
        url = (f"file:///{self.template_path.replace(os.sep, '/')}?text={encoded_text}&header={encoded_header}&img={sign_img_url}"
               f"&c1={grad[0].replace('#', '%23')}&c2={grad[1].replace('#', '%23')}&c3={grad[2].replace('#', '%23')}"
               f"&glow={glow.replace('#', '%23')}&elem={element}&anim={anim_style}")
        
        logging.info(f"   🌌 Launching Playwright ({anim_style.upper()}) for cosmic scene ({duration}s)...")
        
        frames = []
        fps = 30
        total_frames = int(duration * fps)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page(viewport={"width": 1080, "height": 1920})
            
            await page.goto(url)
            await page.wait_for_selector(f"#text-container") 
            
            logging.info(f"   ✨ Capturing {total_frames} cosmic frames...")
            
            for i in range(total_frames):
                current_time = i / fps
                
                # 1. Update Karaoke Highlight
                if subtitle_data:
                    active_idx = -1
                    for idx, sub in enumerate(subtitle_data):
                        end_time = sub.get('end', sub['start'] + sub.get('duration', 0.5))
                        if sub['start'] <= current_time < end_time:
                            active_idx = idx
                            break
                    
                    if active_idx != -1:
                         await page.evaluate(f"window.setWordActive({active_idx})")
                
                # 2. Update Animations (GSAP seek)
                await page.evaluate(f"window.seek({current_time})")
                
                # 3. Capture Frame
                frame_path = os.path.join(frames_dir, f"frame_{i:04d}.png")
                await page.screenshot(path=frame_path, type='png')
                frames.append(frame_path)
            
            await browser.close()
            
        return frames

    def create_scene(self, sign_name: str, text: str, duration: float, subtitle_data: list = None, theme_override: str = None, header_text: str = "", period_type: str = "Daily"):
        """Wrapper to run async render synchronously. Uses cosmic animation styles."""
        import random
        # Use new cosmic animation styles
        chosen_style = random.choice(COSMIC_ANIM_STYLES)
        
        try:
            frames = asyncio.run(self._render_html_scene(sign_name, text, duration, subtitle_data, theme_override, header_text, period_type, chosen_style))
            
            if not frames:
                raise Exception("No frames captured")
                
            clip = ImageSequenceClip(frames, fps=30)
            return clip
            
        except Exception as e:
            logging.error(f"❌ Playwright Render Error: {e}")
            return None

    def assemble_final(self, scenes: list, output_path: str, mood: str = "peaceful", sign_name: str = None):
        """Assembles all scenes into final cosmic video with background music."""
        if not scenes:
            logging.error("No scenes to assemble!")
            return
            
        scenes = [s for s in scenes if s is not None]
        if not scenes:
            logging.error("All scenes failed to render.")
            return

        logging.info(f"🌟 Assembling {len(scenes)} cosmic scenes...")
        final_video = run_concatenate(scenes) 
        
        # --- ADD BACKGROUND MUSIC ---
        music_path = self._select_music_by_mood(mood, sign_name)
        if music_path:
            try:
                logging.info(f"   🎵 Adding background music: {os.path.basename(music_path)}")
                music = AudioFileClip(music_path)
                
                # Loop music if shorter than video
                if music.duration < final_video.duration:
                    music = vfx.loop(music, duration=final_video.duration)
                else:
                    music = music.subclip(0, final_video.duration)
                
                # Lower content volume slightly, music volume low
                music = music.volumex(0.12)  # Background level
                
                # Mix audio
                original_audio = final_video.audio
                final_audio = CompositeAudioClip([original_audio, music])
                final_video = final_video.set_audio(final_audio)
                
            except Exception as e:
                logging.warning(f"   ⚠️ Could not add background music: {e}")

        # --- STRICT 59 SECOND LIMIT ---
        MAX_DURATION = 59.0
        if final_video.duration > MAX_DURATION:
            logging.warning(f"⚠️ Video duration {final_video.duration}s exceeds {MAX_DURATION}s. Trimming...")
            final_video = final_video.subclip(0, MAX_DURATION)
            final_video = final_video.fadeout(0.2)
        
        # Write final video
        logging.info(f"   📹 Rendering cosmic video to {output_path}...")
        final_video.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            threads=4,
            preset="medium"
        )
        logging.info(f"   ✅ Cosmic video saved: {output_path}")

    def _select_music_by_mood(self, mood: str, sign_name: str = None) -> str:
        """Selects background music based on mood and sign."""
        import random
        
        base_music_folder = os.path.join("assets", "music")
        
        # 1. Try Sign-Specific Music Folder first
        target_list = []
        if sign_name:
            sign_key = self._get_sign_key(sign_name) # e.g. "aries"
            # Try to match folder (case-insensitive)
            # Music folders are now "Aries", "Taurus", etc.
            
            # CHECK: Does assets/music/music exist?
            sign_music_base = os.path.join(base_music_folder, "music")
            if os.path.exists(sign_music_base) and os.path.isdir(sign_music_base):
                try:
                    music_subdirs = [d for d in os.listdir(sign_music_base) 
                                     if os.path.isdir(os.path.join(sign_music_base, d))]
                    
                    matching_dir = next((d for d in music_subdirs if d.lower() == sign_key.lower()), None)
                    
                    if matching_dir:
                        sign_music_path = os.path.join(sign_music_base, matching_dir)
                        sign_tracks = [f for f in os.listdir(sign_music_path) if f.endswith(('.mp3', '.wav', '.m4a'))]
                        if sign_tracks:
                            logging.info(f"   ✅ Using sign-specific music for {sign_name}")
                            target_list = [os.path.join(sign_music_path, t) for t in sign_tracks]
                except Exception as e:
                    logging.warning(f"   ⚠️ Could not access sign music folder: {e}")

        # 2. If no sign specific music, use generic folder
        if not target_list:
            if not os.path.exists(base_music_folder):
                os.makedirs(base_music_folder, exist_ok=True)
                self._ensure_music_assets(base_music_folder)
            
            all_music = [f for f in os.listdir(base_music_folder) if f.endswith(('.mp3', '.wav', '.m4a'))]
            if not all_music:
                self._ensure_music_assets(base_music_folder)
                all_music = [f for f in os.listdir(base_music_folder) if f.endswith(('.mp3', '.wav', '.m4a'))]
            
            if not all_music: return None
            
            # Filter by mood
            mood_lower = mood.lower()
            matching_music = [f for f in all_music if mood_lower in f.lower()]
            
            if not matching_music:
                if "energetic" in mood_lower: matching_music = [f for f in all_music if "upbeat" in f.lower()]
                elif "peaceful" in mood_lower: matching_music = [f for f in all_music if "ambient" in f.lower()]
            
            target_list = [os.path.join(base_music_folder, f) for f in (matching_music if matching_music else all_music)]

        return random.choice(target_list)

    def _ensure_music_assets(self, music_folder):
        """Downloads default royalty-free music."""
        tracks = {
            "peaceful_ambient.mp3": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Clean%20Soul.mp3",
            "energetic_upbeat.mp3": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Life%20of%20Riley.mp3",
            "mysterious_deep.mp3": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Private%20Reflection.mp3"
        }
        try:
            import requests
            for f, u in tracks.items():
                p = os.path.join(music_folder, f)
                if not os.path.exists(p):
                    logging.info(f"   ⬇️ Fetching {f}...")
                    r = requests.get(u, verify=False, timeout=30)
                    with open(p, 'wb') as file: file.write(r.content)
        except Exception as e:
            logging.warning(f"   ⚠️ Could not download music: {e}")


# Helper for concatenate
def run_concatenate(clips):
    from moviepy.editor import concatenate_videoclips
    return concatenate_videoclips(clips, method="compose")
