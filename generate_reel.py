#!/usr/bin/env python3
"""
Letter to the Universe — daily Reel generator
------------------------------------------------
Renders a vertical (1080x1920) video showing:
  - today's quote/prompt
  - the running "letters released" counter
  - a call to action

Usage:
    python3 generate_reel.py --count 1284 --quote-index auto --output reel.mp4

The counter number is passed in (fetched from your counter API beforehand —
see fetch_count.py). This script does no networking itself, so it can run
anywhere: your laptop, a GitHub Actions runner, etc.
"""

import argparse
import datetime
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
HERE = Path(__file__).parent
FONT_DIR = HERE / "fonts"
OUT_DIR = HERE / "_render"

# ---------- palette (matches the web page) ----------
BG_DEEP = (10, 14, 31)
INK = (241, 233, 220)
GOLD = (227, 184, 114)
VIOLET = (154, 159, 209)
GREY = (123, 128, 152)
FLAME = (241, 101, 46)

# ---------- fonts ----------
def load_font(path, size, variation=None):
    f = ImageFont.truetype(str(path), size)
    if variation:
        try:
            f.set_variation_by_name(variation)
        except Exception:
            pass
    return f

def fraunces(size, variation="Light Italic"):
    return load_font(FONT_DIR / "Fraunces-Italic.ttf", size, variation)

def inter(size, variation="Regular"):
    return load_font(FONT_DIR / "Inter-Regular.ttf", size, variation)


# ---------- starfield (deterministic per render so it doesn't jitter frame to frame) ----------
def make_starfield(seed=7, count=220):
    rnd = random.Random(seed)
    stars = []
    for _ in range(count):
        stars.append({
            "x": rnd.uniform(0, W),
            "y": rnd.uniform(0, H),
            "r": rnd.uniform(0.8, 2.6),
            "phase": rnd.uniform(0, math.tau),
            "speed": rnd.uniform(0.6, 1.6),
        })
    return stars

def draw_background(t, stars):
    img = Image.new("RGB", (W, H), BG_DEEP)
    draw = ImageDraw.Draw(img, "RGBA")

    # soft nebula glows (static, matches the CSS radial-gradients on the site)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([-200, -300, 700, 500], fill=(122, 110, 180, 26))
    gdraw.ellipse([500, 1300, 1400, 2100], fill=(227, 184, 114, 16))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"), (0, 0))

    draw = ImageDraw.Draw(img, "RGBA")
    for s in stars:
        tw = (math.sin(t * s["speed"] + s["phase"]) + 1) / 2  # 0..1 twinkle
        alpha = int(60 + tw * 195)
        r = s["r"]
        draw.ellipse([s["x"] - r, s["y"] - r, s["x"] + r, s["y"] + r], fill=(255, 255, 255, alpha))
    return img


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def tracked_text_width(draw, text, font, tracking):
    w = 0
    for ch in text:
        w += draw.textlength(ch, font=font) + tracking
    return w - tracking if text else 0


def draw_tracked_text(draw, cx, y, text, font, fill, tracking=6):
    total_w = tracked_text_width(draw, text, font, tracking)
    x = cx - total_w / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def draw_embers(draw, t, seed=3, count=26):
    rnd = random.Random(seed)
    for i in range(count):
        life = ((t * 0.18) + rnd.random()) % 1.0
        x = rnd.uniform(W * 0.15, W * 0.85)
        y = H * (1.05 - life * 1.15)
        alpha = int(255 * math.sin(life * math.pi))
        if alpha <= 0:
            continue
        r = 2 + 2 * (1 - life)
        color = tuple(int(FLAME[j] + (GOLD[j] - FLAME[j]) * life) for j in range(3))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color + (alpha,))


def render_frame(t, stars, quote, count_value, count_label, show_counter, show_cta, opacity_overrides=None):
    img = draw_background(t, stars).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    ov = opacity_overrides or {}

    # eyebrow
    eyebrow_font = inter(30, "SemiBold")
    eb = "A PLACE THAT FORGETS"
    a = int(255 * ov.get("eyebrow", 1))
    if a > 0:
        draw_tracked_text(draw, W / 2, 300, eb, eyebrow_font, VIOLET + (a,), tracking=7)

    # quote
    q_font = fraunces(72, "Light Italic")
    a = int(255 * ov.get("quote", 1))
    if a > 0:
        lines = wrap_text(draw, quote, q_font, W * 0.78)
        total_h = len(lines) * 92
        y = 480 - total_h / 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=q_font)
            lw = bbox[2] - bbox[0]
            draw.text(((W - lw) / 2, y), line, font=q_font, fill=INK + (a,))
            y += 92

    # counter
    a = int(255 * ov.get("counter", 1))
    if show_counter and a > 0:
        num_font = fraunces(150, "SemiBold Italic")
        num_txt = f"{count_value:,}"
        bbox = draw.textbbox((0, 0), num_txt, font=num_font)
        nw = bbox[2] - bbox[0]
        ny = 980
        # soft gold glow behind the number
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow_layer)
        gdraw.text(((W - nw) / 2, ny), num_txt, font=num_font, fill=GOLD + (min(a, 140),))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(18))
        img = Image.alpha_composite(img, glow_layer)
        draw = ImageDraw.Draw(img, "RGBA")
        draw.text(((W - nw) / 2, ny), num_txt, font=num_font, fill=GOLD + (a,))

        label_font = inter(34, "Medium")
        lbl = count_label
        bbox = draw.textbbox((0, 0), lbl, font=label_font)
        lw = bbox[2] - bbox[0]
        draw.text(((W - lw) / 2, ny + 190), lbl, font=label_font, fill=GREY + (a,))

    # embers (always present, subtle)
    draw_embers(draw, t)

    # CTA
    a = int(255 * ov.get("cta", 1))
    if show_cta and a > 0:
        cta_font = inter(38, "SemiBold")
        cta = "Write yours — link in bio"
        bbox = draw.textbbox((0, 0), cta, font=cta_font)
        cw = bbox[2] - bbox[0]
        # pill background
        pad_x, pad_y = 34, 20
        x0 = (W - cw) / 2 - pad_x
        y0 = 1660
        x1 = (W + cw) / 2 + pad_x
        y1 = y0 + 34 + pad_y * 2 - 14
        pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(pill)
        pdraw.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 2,
                                 fill=(227, 184, 114, min(a, 255)))
        img = Image.alpha_composite(img, pill)
        draw = ImageDraw.Draw(img, "RGBA")
        draw.text(((W - cw) / 2, y0 + pad_y - 6), cta, font=cta_font, fill=(33, 20, 5, a))

    return img.convert("RGB")


def ease(x):
    return x * x * (3 - 2 * x)  # smoothstep


def build_video(quote, count_value, count_label, out_path, fps=30, seed=7):
    OUT_DIR.mkdir(exist_ok=True)
    for f in OUT_DIR.glob("*.png"):
        f.unlink()

    stars = make_starfield(seed=seed)

    # timeline (seconds)
    T_EYEBROW_IN   = (0.10, 0.55)
    T_QUOTE_IN     = (0.35, 1.10)
    T_COUNTER_IN   = (2.60, 3.35)
    T_CTA_IN       = (5.20, 5.80)
    T_END          = 8.00

    n_frames = int(T_END * fps)
    for i in range(n_frames):
        t = i / fps
        ov = {
            "eyebrow": ease(min(1, max(0, (t - T_EYEBROW_IN[0]) / (T_EYEBROW_IN[1] - T_EYEBROW_IN[0])))),
            "quote":   ease(min(1, max(0, (t - T_QUOTE_IN[0]) / (T_QUOTE_IN[1] - T_QUOTE_IN[0])))),
            "counter": ease(min(1, max(0, (t - T_COUNTER_IN[0]) / (T_COUNTER_IN[1] - T_COUNTER_IN[0])))),
            "cta":     ease(min(1, max(0, (t - T_CTA_IN[0]) / (T_CTA_IN[1] - T_CTA_IN[0])))),
        }
        frame = render_frame(
            t=t, stars=stars, quote=quote,
            count_value=count_value, count_label=count_label,
            show_counter=True, show_cta=True, opacity_overrides=ov,
        )
        frame.save(OUT_DIR / f"f_{i:04d}.png")

    # assemble with ffmpeg (silent, vertical, Instagram-ready h264/mp4)
    cmd = [
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", str(OUT_DIR / "f_%04d.png"),
        "-vf", "format=yuv420p",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def pick_quote(quotes, mode="auto", index=None):
    if index is not None:
        return quotes[int(index) % len(quotes)]
    if mode == "auto":
        day_num = datetime.date.today().timetuple().tm_yday
        return quotes[day_num % len(quotes)]
    return random.choice(quotes)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, required=True, help="current total letters released")
    p.add_argument("--count-label", default="letters released to the universe")
    p.add_argument("--quotes-file", default=str(HERE / "quotes.json"))
    p.add_argument("--quote-index", default="auto", help="'auto' cycles by day-of-year, 'random', or an integer")
    p.add_argument("--output", default=str(HERE / "reel.mp4"))
    args = p.parse_args()

    quotes = json.loads(Path(args.quotes_file).read_text())
    idx = None
    mode = args.quote_index
    if mode not in ("auto", "random"):
        idx = int(mode)
        mode = "index"
    quote = pick_quote(quotes, mode=mode, index=idx)

    build_video(quote, args.count, args.count_label, args.output)

    meta_path = Path(args.output).with_suffix(".json")
    meta_path.write_text(json.dumps({
        "date": datetime.date.today().isoformat(),
        "count": args.count,
        "quote": quote,
        "suggested_caption": f"{quote}\n\n{args.count:,} {args.count_label} so far.\n\nWrite yours — link in bio.",
    }, indent=2))

    print(f"Wrote {args.output}  |  quote: \"{quote}\"  |  count: {args.count}")


if __name__ == "__main__":
    main()
