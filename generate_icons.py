"""Generates simple, on-brand PWA icons (regular + maskable) without external assets.
Run once: python3 generate_icons.py
"""
from PIL import Image, ImageDraw

PURPLE = (91, 33, 182)       # #5B21B6
PURPLE_DARK = (59, 15, 115)  # #3B0F73
WHITE = (255, 255, 255)

OUT_DIR = "app/static/icons"


def draw_mark(draw, cx, cy, size, color):
    """Draws a simplified printer / press icon: a stack + registration crosshair."""
    s = size
    # Printer body (rounded rect)
    body_w, body_h = s * 0.62, s * 0.34
    draw.rounded_rectangle(
        [cx - body_w / 2, cy - body_h / 2, cx + body_w / 2, cy + body_h / 2],
        radius=s * 0.06, fill=color
    )
    # Paper slot (lighter cut-out)
    slot_w, slot_h = s * 0.34, s * 0.16
    draw.rectangle(
        [cx - slot_w / 2, cy - body_h / 2 - slot_h * 0.4, cx + slot_w / 2, cy - body_h / 2 + slot_h * 0.3],
        fill=WHITE
    )
    # Output tray
    tray_w = s * 0.5
    draw.rectangle(
        [cx - tray_w / 2, cy + body_h / 2 - s * 0.02, cx + tray_w / 2, cy + body_h / 2 + s * 0.14],
        fill=WHITE
    )
    # Registration crosshair (signature motif), offset top-right
    rx, ry, rlen = cx + s * 0.34, cy - s * 0.32, s * 0.16
    lw = max(2, int(s * 0.016))
    draw.line([(rx - rlen / 2, ry), (rx + rlen / 2, ry)], fill=WHITE, width=lw)
    draw.line([(rx, ry - rlen / 2), (rx, ry + rlen / 2)], fill=WHITE, width=lw)
    draw.ellipse([rx - rlen / 3, ry - rlen / 3, rx + rlen / 3, ry + rlen / 3], outline=WHITE, width=lw)


def make_icon(size, filename, maskable=False):
    img = Image.new("RGB", (size, size), PURPLE)
    draw = ImageDraw.Draw(img)

    # Subtle gradient-esque corner shading using an overlay ellipse
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.ellipse([-size * 0.3, -size * 0.3, size * 0.9, size * 0.9], fill=(255, 255, 255, 25))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))

    # For maskable icons, keep the mark within the safe zone (center 80%)
    mark_size = size * (0.5 if maskable else 0.58)
    draw = ImageDraw.Draw(img)
    draw_mark(draw, size / 2, size / 2, mark_size, WHITE)

    img.save(f"{OUT_DIR}/{filename}")
    print(f"wrote {OUT_DIR}/{filename}")


if __name__ == "__main__":
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    make_icon(192, "icon-192.png")
    make_icon(512, "icon-512.png")
    make_icon(512, "icon-maskable-512.png", maskable=True)
    make_icon(180, "apple-touch-icon.png")
