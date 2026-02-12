import os
import sys
import argparse
import json
import logging
from datetime import datetime
import pytz
import re

from agents.astrologer import AstrologerAgent
from agents.director import DirectorAgent
from agents.narrator import NarratorAgent
from agents.uploader import YouTubeUploader
from editor import EditorEngine
from moviepy.editor import AudioFileClip

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Western Zodiac Signs
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Sign Index for scheduling (1-12)
SIGN_INDEX_MAP = {
    "aries": 1, "taurus": 2, "gemini": 3, "cancer": 4,
    "leo": 5, "virgo": 6, "libra": 7, "scorpio": 8,
    "sagittarius": 9, "capricorn": 10, "aquarius": 11, "pisces": 12
}


def process_immediate_upload(agents, video_path, script_data, sign, date_str, period_type):
    """
    Handles immediate upload logic with smart scheduling check.
    If past 6 AM EST, uploads PUBLIC immediately.
    If before 6 AM EST, schedules for 6 AM Today.
    """
    uploader = agents['uploader']
    astrologer = agents['astrologer']
    
    if not uploader.service:
         print("❌ Upload skipped: No Auth.")
         return

    if not os.path.exists(video_path):
        print(f"❌ Video file not found for upload: {video_path}")
        return

    # Scheduling Logic (EST)
    from datetime import timedelta
    est = pytz.timezone('America/New_York')
    now_est = datetime.now(est)
    
    # Target: 6:00 AM EST Today
    target_time = now_est.replace(hour=6, minute=0, second=0, microsecond=0)
    
    privacy_status = "public"
    publish_at = None
    
    # If it is currently BEFORE 5 AM (Buffer for 6 AM runs), schedule for today 6 AM
    cutoff_time = now_est.replace(hour=5, minute=0, second=0, microsecond=0)
    if now_est < cutoff_time:
        # Add random delay (0-45 mins) for organic feel
        import random
        delay_minutes = random.randint(0, 45) 
        target_time = target_time + timedelta(minutes=delay_minutes)
        
        # Convert to UTC for API
        target_utc = target_time.astimezone(pytz.utc)
        publish_at = target_utc.replace(tzinfo=None)
        privacy_status = "private" # Must be private for scheduled
        print(f"   📅 Early Morning! Scheduled for: {target_time.strftime('%H:%M')} EST (Delay: {delay_minutes}m)")
    else:
        # If it is AFTER 6 AM, upload IMMEDIATELY as PUBLIC
        print(f"   🚀 Past 6 AM EST. Uploading IMMEDIATELY (Public).")
        privacy_status = "public"
        publish_at = None

    print(f"\n🚀 Initiating Upload for {period_type}...")
    try:
        # ALWAYS try to generate Mega Viral Metadata (300+ keywords) via Astrologer
        print("🚀 Generating MEGA Viral Metadata (300+ keywords)...")
        meta = astrologer.generate_viral_metadata(sign, date_str, period_type, script_data)
        
        if not meta or "title" not in meta:
            print("⚠️ Advanced metadata generation failed. Falling back to simple...")
            meta = uploader.generate_metadata(sign, date_str, period_type)
        else:
            print("✅ MEGA Metadata Generated Successfully!")
            
    except Exception as e:
        print(f"⚠️ Metadata extraction failed: {e}. Using fallback.")
        meta = uploader.generate_metadata(sign, date_str, period_type)
    
    if "categoryId" not in meta: meta["categoryId"] = "24"
    
    # Ensure tags is a list (LLM sometimes returns comma-separated string)
    if isinstance(meta.get("tags"), str):
        meta["tags"] = [t.strip() for t in meta["tags"].split(",")]
    
    uploader.upload_video(video_path, meta, privacy_status=privacy_status, publish_at=publish_at)


def produce_video_from_script(agents, sign, title_suffix, script, date_str, theme_override=None, period_type="Daily", header_text=""):
    """
    Orchestrates the production of a single video from a script.
    Uses gradient sign-themed backgrounds with karaoke text.
    """
    narrator, editor, director = agents['narrator'], agents['editor'], agents['director']
    
    print(f"\n🎬 STARTING PRODUCTION: {title_suffix} ({header_text})...")


    scenes = []
    
    # Debug: Show what script format we received
    print(f"   📋 Script type: {type(script).__name__}")
    if isinstance(script, dict):
        print(f"   📋 Script keys: {list(script.keys())}")
    elif isinstance(script, list):
        print(f"   📋 Script has {len(script)} items")
        if len(script) == 1 and isinstance(script[0], dict):
            print("   ✅ Unwrapping single-item list -> dict")
            script = script[0]
        else:
            script = {"content": " ".join(str(s) for s in script)}
    
    # Use Director to analyze script and get mood for music
    print(f"   🎬 Director analyzing content mood...")
    screenplay = director.create_screenplay(script)
    content_mood = screenplay.get("mood", "peaceful") if isinstance(screenplay, dict) else "peaceful"
    print(f"   🎵 Detected mood: {content_mood}")
    
    # Define order of sections to ensure flow
    priority_order = ["hook", "intro", "love", "career", "money", "health", "advice", "lucky_color", "lucky_number", "best_time", "key_dates", "affirmation"]
    
    # Identify relevant sections from script
    active_sections = []
    for section in priority_order + [k for k in script.keys() if k not in priority_order]:
        if section in script and script[section] and len(str(script[section])) >= 5:
            # Skip metadata section
            if section == "metadata":
                continue
            active_sections.append(section)

    print(f"   📋 Processing {len(active_sections)} active sections...")
    
    # --- PHASE 1: GENERATE ALL AUDIO & MEASURE DURATION ---
    section_audios = {}
    total_duration = 0.0
    
    os.makedirs(f"assets/temp/{title_suffix}", exist_ok=True)
    
    for section in active_sections:
        original_text = str(script[section])
        
        # Clean text for display and speech
        speech_text = original_text
        
        # Remove emotion tags from display text only (Narrator handles speech text cleaning internally)
        # Using regex to remove (Happy), (Excited), etc. and any extra spaces
        display_text = re.sub(r'\s*\((Happy|Excited|Serious|Caution|Warm)\)\s*', ' ', original_text, flags=re.IGNORECASE).strip()
        
        # Format section-specific content
        if section == "lucky_color":
            speech_text = f"Your lucky color today is {original_text}."
            display_text = f"Lucky Color: {original_text}"
        elif section == "lucky_number":
            speech_text = f"Your lucky number today is {original_text}."
            display_text = f"Lucky Number: {original_text}"
        elif section == "best_time":
            speech_text = f"The best time for important activities is {original_text}."
            display_text = f"Best Time: {original_text}"
        
        # Validate text isn't a stringified dict/list
        text_stripped = speech_text.strip()
        if (text_stripped.startswith("{") and "}" in text_stripped) or (text_stripped.startswith("[") and "]" in text_stripped):
            print(f"         ⚠️ WARNING: Section '{section}' appears to be a raw object. Skipping.")
            continue
             
        audio_path = f"assets/temp/{title_suffix}/{section}.mp3"
        subtitle_path = audio_path.replace(".mp3", ".json")
        
        narrator.speak(speech_text, audio_path)
        
        if os.path.exists(audio_path):
            try:
                clip = AudioFileClip(audio_path)
                dur = clip.duration + 0.3  # Buffer
                section_audios[section] = {
                    "path": audio_path,
                    "duration": dur,
                    "subtitle_path": subtitle_path,
                    "text": display_text,
                    "audio_object": clip 
                }
                clip.close()
                total_duration += dur
            except Exception as e:
                print(f"         ⚠️ Audio read error for {section}: {e}")
        else:
            print(f"         ⚠️ Generation failed for {section}")

    print(f"   ⏱️  Total Pre-Render Duration: {total_duration:.2f}s")

    # --- PHASE 2: SMART TRIMMING (Target based on type) ---
    if period_type == "Daily":
        TARGET_DURATION = 58.0
    else:
        TARGET_DURATION = 600.0  # 10 mins for Monthly/Yearly

    if total_duration > TARGET_DURATION:
        print(f"   ⚠️ Duration {total_duration:.2f}s > {TARGET_DURATION}s. Initiating SMART TRIMMING.")
        
        # Strategy: Drop sections in order of "least impact"
        drop_candidates = ["intro", "health", "lucky_number", "lucky_color", "best_time", "money"]
        
        for candidate in drop_candidates:
            if total_duration <= TARGET_DURATION:
                break
            
            if candidate in section_audios:
                dropped_dur = section_audios[candidate]["duration"]
                print(f"      ✂️ Dropping '{candidate.upper()}' (-{dropped_dur:.2f}s)")
                del section_audios[candidate]
                if candidate in active_sections:
                    active_sections.remove(candidate)
                total_duration -= dropped_dur
                
        print(f"   ✅ New Duration: {total_duration:.2f}s")
    
    # --- PHASE 3: CREATE SCENES ---
    
    # NEW: Add "Find Your Sign" Intro Scene for Western Astrology context
    print("   📍 Rendering Intro Scene...")
    try:
        intro_text = "Unsure of your Sign? Check the Description below! ⬇️"
        # Use a neutral header or the standard one
        intro_clip = editor.create_scene(
            sign, 
            intro_text, 
            duration=4.0, 
            theme_override=theme_override, 
            header_text="Find Your Sign",
            period_type=period_type
        )
        if intro_clip:
            scenes.append(intro_clip)
            print("      ✅ Intro scene added.")
    except Exception as e:
        print(f"      ⚠️ Failed to add intro scene: {e}")

    for section in active_sections:
        if section not in section_audios:
            continue
            
        data = section_audios[section]
        audio_path = data["path"]
        duration = data["duration"]
        subtitle_path = data["subtitle_path"]
        text = data["text"]
        
        print(f"\n   📍 Rendering Scene: {section.upper()} ({duration:.1f}s)")
        
        # Load subtitles
        subtitle_data = None
        if os.path.exists(subtitle_path):
            try:
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    subtitle_data = json.load(f)
            except: pass
            
        # Create Scene
        clean_sign_name = sign.split('(')[0].strip() if '(' in sign else sign
        clip = editor.create_scene(
            clean_sign_name, 
            text, 
            duration, 
            subtitle_data=subtitle_data, 
            theme_override=theme_override,
            header_text=header_text,
            period_type=period_type
        )
        
        # Attach Audio
        if clip:
            try:
                audio_clip = AudioFileClip(audio_path)
                clip = clip.set_audio(audio_clip)
                scenes.append(clip)
                print(f"      ✅ Scene ready.")
            except Exception as e:
                print(f"      ❌ Audio attach error: {e}")
        else:
             print(f"      ❌ Scene render failed.")
        
    if not scenes:
        print("❌ No scenes created.")
        raise Exception("No scenes created.")

    # Final Assembly
    print(f"\n🎞️ Assembling Final Master: {title_suffix}")
    output_filename = f"outputs/{sign.split()[0]}_{title_suffix}.mp4"
    os.makedirs("outputs", exist_ok=True)
    
    editor.assemble_final(scenes, output_filename, mood=content_mood, sign_name=sign)
    print(f"\n✅ CREATED: {output_filename}")


def main():
    parser = argparse.ArgumentParser(description="AI Video Studio - Western Astrology Automation")
    parser.add_argument("--sign", type=str, default="Aries", help="Target Zodiac Sign")
    # Keep --rashi for backward compatibility
    parser.add_argument("--rashi", type=str, default=None, help="(Deprecated) Use --sign instead")
    parser.add_argument("--type", type=str, default="shorts", choices=["shorts", "detailed"], help="Video Type: shorts (Morning) or detailed (Evening)")
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube after generation")
    args = parser.parse_args()
    
    # Handle backward compatibility
    target_sign = args.rashi if args.rashi else args.sign
    
    # Initialize Agents
    agents = {
        'astrologer': AstrologerAgent(),
        'director': DirectorAgent(),
        'narrator': NarratorAgent(),
        'editor': EditorEngine(),
        'uploader': YouTubeUploader()
    }
    
    # Use US Eastern timezone for American audience
    est = pytz.timezone('America/New_York')
    today = datetime.now(est)
    date_str = today.strftime("%B %d, %Y")  # e.g., "January 26, 2026"
    month_year = today.strftime("%B %Y")
    year_str = today.strftime("%Y")
    
    # --- Sign Index for Drip Scheduling ---
    sign_key_clean = target_sign.lower().split()[0]
    sign_idx = SIGN_INDEX_MAP.get(sign_key_clean, 1)
        
    print("\n" + "="*60)
    print(f"🌟 STELLAR HOROSCOPES: Automation Engine")
    print(f"   Target: {target_sign} (Index: {sign_idx})")
    print(f"   Date: {date_str}")
    print(f"   Type: {args.type.upper()}")
    print("="*60 + "\n")
    
    
    # ==========================
    # MODE 1: SHORTS (MORNING)
    # ==========================
    if args.type == "shorts":
        try:
            print("⭐ Generating DAILY Horoscope (Shorts)...")
            daily_script = agents['astrologer'].generate_daily_horoscope(target_sign, date_str)
            
            # EXTRACT LUCKY COLOR FOR THEME
            theme_color = None
            if "lucky_color" in daily_script:
                l_text = str(daily_script["lucky_color"]).lower()
                valid_colors = ["red", "blue", "green", "yellow", "white", "black", "pink", "orange", "purple", "brown", "gold", "silver"]
                for c in valid_colors:
                    if c in l_text:
                        theme_color = c
                        break
            
            daily_header = f"Daily Horoscope: {date_str}"
            
            suffix = f"Daily_{today.strftime('%Y%m%d')}"
            produce_video_from_script(
                agents, 
                target_sign, 
                suffix, 
                daily_script, 
                date_str,
                theme_override=theme_color,
                period_type="Daily",
                header_text=daily_header
            )
            

            
            # IMMEDIATE UPLOAD
            if args.upload:
                sign_clean = target_sign.split()[0]
                path = f"outputs/{sign_clean}_{suffix}.mp4"
                process_immediate_upload(agents, path, daily_script, target_sign, date_str, "Daily")
            

        except Exception as e:
            print(f"❌ Daily Video Failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)  # Exit with error so GitHub Actions marks this as FAILED

    # ==========================
    # MODE 2: DETAILED (EVENING)
    # ==========================
    elif args.type == "detailed":
        detailed_produced = False
        
        # CHECK 1: YEARLY (Priority 1) - On Jan 1-12 based on sign index
        if today.month == 1 and today.day == sign_idx:
            try:
                print(f"\n🎆 HAPPY NEW YEAR! It is Jan {today.day}! Generating YEARLY Horoscope for {target_sign}...")
                yearly_script = agents['astrologer'].generate_yearly_forecast(target_sign, year_str)
                yearly_header = f"Yearly Horoscope: {year_str}"
                
                suffix = f"Yearly_{year_str}"
                produce_video_from_script(
                    agents, target_sign, suffix, yearly_script, year_str,
                    period_type="Yearly", header_text=yearly_header
                )
                

                
                if args.upload:
                    sign_clean = target_sign.split()[0]
                    path = f"outputs/{sign_clean}_{suffix}.mp4"
                    process_immediate_upload(agents, path, yearly_script, target_sign, year_str, "Yearly")

                detailed_produced = True
                
            except Exception as e:
                print(f"❌ Yearly Video Failed: {e}")

        # CHECK 2: MONTHLY (Priority 2, only if not Yearly)
        if not detailed_produced and today.day == sign_idx: 
            try:
                print(f"\n📅 It is Day {today.day}! Generating MONTHLY Horoscope for {target_sign}...")
                monthly_script = agents['astrologer'].generate_monthly_forecast(target_sign, month_year)
                monthly_header = f"Monthly Horoscope: {month_year}"
                
                suffix = f"Monthly_{today.strftime('%B_%Y')}"
                produce_video_from_script(
                    agents, target_sign, suffix, monthly_script, month_year,
                    period_type="Monthly", header_text=monthly_header
                )
                

                
                if args.upload:
                    sign_clean = target_sign.split()[0]
                    path = f"outputs/{sign_clean}_{suffix}.mp4"
                    process_immediate_upload(agents, path, monthly_script, target_sign, month_year, "Monthly")

                detailed_produced = True
                
            except Exception as e:
                print(f"❌ Monthly Video Failed: {e}")

        # CHECK 3: DAILY INSIGHT (Priority 3, Fallback)
        if not detailed_produced:
            try:
                print(f"\n✨ Generating DAILY COSMIC INSIGHT (Evening Special)...")
                insight_script = agents['astrologer'].generate_daily_insight_script(target_sign, date_str)
                insight_header = f"Cosmic Insight: {date_str}"
                
                suffix = f"Insight_{today.strftime('%Y%m%d')}"
                produce_video_from_script(
                    agents, target_sign, suffix, insight_script, date_str,
                    period_type="Daily_Insight", header_text=insight_header
                )
                

                
                if args.upload:
                    sign_clean = target_sign.split()[0]
                    path = f"outputs/{sign_clean}_{suffix}.mp4"
                    process_immediate_upload(agents, path, insight_script, target_sign, date_str, "Daily_Insight")

                
            except Exception as e:
                print(f"❌ Insight Video Failed: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

    # Removed old bulk upload loop


if __name__ == "__main__":
    main()
