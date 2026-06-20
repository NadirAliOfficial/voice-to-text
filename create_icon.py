"""Generate icon.png for Voice Typer."""
import math
from PIL import Image, ImageDraw

SIZE = 512

def make_icon():
    img  = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── background circle ──
    pad = 8
    draw.ellipse([pad, pad, SIZE - pad, SIZE - pad], fill="#161616")

    # ── outer glow rings ──
    for i, (r_frac, alpha) in enumerate([(0.48, 40), (0.44, 60), (0.40, 30)]):
        r = int(SIZE * r_frac)
        cx = cy = SIZE // 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=(231, 76, 60, alpha), width=3)

    # ── red accent ring ──
    r = int(SIZE * 0.46)
    cx = cy = SIZE // 2
    draw.arc([cx - r, cy - r, cx + r, cy + r],
             start=-30, end=210, fill="#e74c3c", width=6)

    # ── microphone body ──
    mw, mh = 90, 140
    cx, cy = SIZE // 2, SIZE // 2 - 20
    # capsule
    draw.rounded_rectangle(
        [cx - mw // 2, cy - mh // 2, cx + mw // 2, cy + mh // 2],
        radius=mw // 2, fill="#e74c3c",
    )
    # inner highlight
    draw.rounded_rectangle(
        [cx - mw // 2 + 10, cy - mh // 2 + 14,
         cx - mw // 2 + 22, cy - mh // 2 + 55],
        radius=6, fill=(255, 255, 255, 60),
    )

    # ── mic stand arc ──
    aw = 120
    ay_top = cy + mh // 2 - 20
    draw.arc([cx - aw // 2, ay_top, cx + aw // 2, ay_top + aw],
             start=0, end=180, fill="white", width=10)

    # ── stand post ──
    post_top = ay_top + aw // 2
    post_bot = post_top + 50
    draw.line([cx, post_top, cx, post_bot], fill="white", width=10)
    draw.line([cx - 36, post_bot, cx + 36, post_bot], fill="white", width=10)
    draw.ellipse([cx - 5, post_top - 5, cx + 5, post_top + 5], fill="white")

    # ── save ──
    img.save("icon.png")
    print("icon.png saved.")

if __name__ == "__main__":
    make_icon()
