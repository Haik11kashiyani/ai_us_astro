import os
import json
import asyncio
import edge_tts
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NarratorAgent:
    """
    The Narrator Agent uses Edge-TTS (Neural) to generate human-like English voiceovers.
    Optimized for American English with natural, engaging delivery.
    """
    
    def __init__(self):
        # Neural Voices for English:
        # en-US-JennyNeural (Female, warm, professional)
        # en-US-AriaNeural (Female, engaging)
        # en-US-GuyNeural (Male, authoritative)
        # en-US-ChristopherNeural (Male, smooth, documentary style)
        self.voice = "en-US-ChristopherNeural"  # Supports emotional styles
        self.rate = "+0%"
        self.pitch = "+0Hz" # Natural deep voice

    async def generate_audio(self, text: str, output_path: str):
        """
        Generates MP3 audio and saves word-level subtitles to a JSON file.
        Uses SSML for emotional expression if tags are present.
        """
        if not text: return False
        
        # 1. Parse Emotion Tags (Simple Block-Level)
        # Mapping: (Tag) -> SSML Style
        style_map = {
            "(Happy)": "cheerful",
            "(Excited)": "excited",
            "(Serious)": "serious",  # Guy doesn't support serious explicitly, mapping to default or similar
            "(Caution)": "whispering", # Dramatic effect
            "(Warm)": "hopeful"
        }
        
        active_style = None
        clean_text = text.strip()
        
        for tag, style in style_map.items():
            if tag in clean_text:
                active_style = style
                clean_text = clean_text.replace(tag, "").strip() # Remove tag
                break
        
        # Remove any other potential bracketed text (backups)
        import re
        clean_text = re.sub(r'\s*\(.*?\)\s*', ' ', clean_text, flags=re.IGNORECASE).strip()
        
        logging.info(f"🎙️ Narrator: Speaking ({active_style or 'Default'}) {len(clean_text)} chars...")
        subtitle_path = output_path.replace(".mp3", ".json")
        
        # 2. Construct SSML if style is active
        # GuyNeural supports: angry, cheerful, excited, hopeful, sad, shouting, terrified, unfriendly, whispering
        # For "Serious", we might use default or just slightly slower rate? Let's use clean text if no mapping.
        
        final_text = clean_text
        if active_style:
             # Construct valid SSML
             final_text = f"""
                <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
                    <voice name="{self.voice}">
                        <mstts:express-as style="{active_style}">
                            <prosody rate="{self.rate}" pitch="{self.pitch}">
                                {clean_text}
                            </prosody>
                        </mstts:express-as>
                    </voice>
                </speak>
             """
        
        # Retry logic for EdgeTTS
        for attempt in range(3):
            try:
                # If SSML is used, we must strictly *not* pass voice/rate/pitch to Communicate as args, 
                # or ensure Communicate handles SSML detection. EdgeTTS detects <speak> automatically.
                # However, if we pass SSML, we shouldn't pass rate/pitch args again if they are inside SSML.
                
                if active_style:
                     communicate = edge_tts.Communicate(final_text, self.voice) # Params inside SSML
                else:
                     communicate = edge_tts.Communicate(final_text, self.voice, rate=self.rate, pitch=self.pitch)
                
                subtitles = []
                
                with open(output_path, "wb") as file:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            file.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                             # Adjust offsets if needed? Usually fine.
                            subtitles.append({
                                "text": chunk["text"],
                                "start": chunk["offset"] / 10000000, 
                                "duration": chunk["duration"] / 10000000
                            })
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                    if subtitles:
                        with open(subtitle_path, "w", encoding="utf-8") as f:
                            json.dump(subtitles, f, ensure_ascii=False, indent=2)
                    logging.info(f"   ✅ EdgeTTS Audio saved: {output_path}")
                    return True

                
            except Exception as e:
                logging.warning(f"⚠️ EdgeTTS Attempt {attempt+1} Failed: {e}")
                await asyncio.sleep(2)

        logging.warning("⚠️ All EdgeTTS attempts failed. Switching to Fallback (gTTS)...")
        if os.path.exists(output_path): os.remove(output_path)
            
        return self._fallback_gtts(clean_text, output_path, subtitle_path)

    def _fallback_gtts(self, text: str, output_path: str, subtitle_path: str) -> bool:
        """Fallback using Google Text-to-Speech (gTTS) with pseudo-subtitles."""
        try:
            from gtts import gTTS
            from mutagen.mp3 import MP3
            
            # Use English language
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_path)
            
            if os.path.exists(output_path):
                # Generate Pseudo-Subtitles for highlighting
                try:
                    audio = MP3(output_path)
                    duration = audio.info.length
                    words = text.split()
                    word_duration = duration / max(len(words), 1)
                    
                    subtitles = []
                    current_time = 0.0
                    for word in words:
                        subtitles.append({
                            "text": word,
                            "start": current_time,
                            "duration": word_duration
                        })
                        current_time += word_duration
                        
                    with open(subtitle_path, "w", encoding="utf-8") as f:
                        json.dump(subtitles, f, ensure_ascii=False, indent=2)
                        
                except Exception as e:
                    logging.warning(f"⚠️ Could not generate pseudo-subtitles: {e}")

                logging.info(f"   ✅ gTTS Fallback Audio saved: {output_path}")
                return True
            return False
        except Exception as e:
            logging.error(f"❌ gTTS Fallback Failed: {e}")
            return False

    def speak(self, text: str, output_path: str):
        """Synchronous wrapper for async speak."""
        asyncio.run(self.generate_audio(text, output_path))
