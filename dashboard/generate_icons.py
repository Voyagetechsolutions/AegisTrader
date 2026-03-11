#!/usr/bin/env python3
"""
Generate PWA icons for Aegis Trader
Requires: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size):
    """Create a single icon of the specified size."""
    # Create image with gradient background
    img = Image.new('RGB', (size, size), color='#00d4aa')
    draw = ImageDraw.Draw(img)
    
    # Create gradient effect (simple approximation)
    for y in range(size):
        # Interpolate between #00d4aa and #0099cc
        ratio = y / size
        r = int(0 * (1 - ratio) + 0 * ratio)
        g = int(212 * (1 - ratio) + 153 * ratio)
        b = int(170 * (1 - ratio) + 204 * ratio)
        color = (r, g, b)
        draw.line([(0, y), (size, y)], fill=color)
    
    # Add lightning bolt emoji (simplified as text)
    try:
        # Try to use a system font
        font_size = int(size * 0.6)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Draw lightning bolt symbol
    text = "⚡"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text((x, y), text, fill='white', font=font)
    
    return img

def generate_all_icons():
    """Generate all required PWA icons."""
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Create icons directory if it doesn't exist
    os.makedirs('icons', exist_ok=True)
    
    for size in sizes:
        print(f"Generating {size}x{size} icon...")
        icon = create_icon(size)
        icon.save(f'icons/icon-{size}x{size}.png', 'PNG')
    
    print("All icons generated successfully!")
    print("Icons saved in the 'icons' directory")

if __name__ == "__main__":
    generate_all_icons()