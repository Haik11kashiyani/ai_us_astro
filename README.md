# AI Video Studio: Stellar Horoscopes

An autonomous, production-grade video studio for **Western Astrology** YouTube Shorts.

## Features

- 🌟 **Authentic Western Astrology** - Based on planetary transits, aspects, and sun sign analysis
- 🎬 **AI-Powered Content** - Uses advanced LLMs for genuine horoscope predictions
- 🎙️ **Natural English Voice** - Neural TTS for professional narration
- 📹 **Premium Video Production** - Animated backgrounds with karaoke-style text
- 📤 **Automated YouTube Upload** - Scheduled publishing with viral-optimized metadata

## The Team (AI Agents)

- **Astrologer Agent**: Writes authentic Western Astrology scripts using OpenRouter/Gemini LLMs
- **Director Agent**: Analyzes content mood and creates cinematic direction
- **Narrator Agent**: Speaks in natural American English using Neural TTS
- **Editor Agent**: Renders premium animated videos with zodiac-themed visuals

## Zodiac Signs

Aries ♈ | Taurus ♉ | Gemini ♊ | Cancer ♋ | Leo ♌ | Virgo ♍ | Libra ♎ | Scorpio ♏ | Sagittarius ♐ | Capricorn ♑ | Aquarius ♒ | Pisces ♓

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Environment Variables

Create a `.env` file with:

```
OPENROUTER_API_KEY=sk-or-your-key
GOOGLE_AI_API_KEY=your-google-ai-key

# YouTube API (for uploads)
YOUTUBE_CLIENT_ID=your-client-id
YOUTUBE_CLIENT_SECRET=your-client-secret
YOUTUBE_REFRESH_TOKEN=your-refresh-token
```

### 3. Add Zodiac Images

Place 12 zodiac sign images in `assets/12_photos/`:

- `aries.png`
- `taurus.png`
- `gemini.png`
- `cancer.png`
- `leo.png`
- `virgo.png`
- `libra.png`
- `scorpio.png`
- `sagittarius.png`
- `capricorn.png`
- `aquarius.png`
- `pisces.png`

## Usage

### Generate a Daily Horoscope Video

```bash
python main.py --sign "Aries" --type shorts
```

### Generate and Upload to YouTube

```bash
python main.py --sign "Leo" --type shorts --upload
```

### Generate Detailed Content (Monthly/Yearly)

```bash
python main.py --sign "Scorpio" --type detailed
```

## GitHub Actions

This repo is configured to run daily on the cloud.
Check `.github/workflows/` for automation schedules.

## Output

Videos are saved to the `outputs/` folder:

- `Aries_Daily_20260126.mp4`
- `Leo_Monthly_January_2026.mp4`
- etc.

## License

This work is licensed under a Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License.
