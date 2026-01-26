from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

os.makedirs("assets/zodiac_icons", exist_ok=True)
img = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
# Draw a golden circle
draw.ellipse([10, 10, 190, 190], outline="gold", width=5)
# Draw text "♈"
try:
    font = ImageFont.truetype("arial", 100)
except:
    font = ImageFont.load_default()
    
# Draw 'A' as fallback symbol
draw.text((70, 40), "A", fill="gold", font=font)

img.save("assets/zodiac_icons/Mesh (Aries).png")
print("Placeholder icon created.")
