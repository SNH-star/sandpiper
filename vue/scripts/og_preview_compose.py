#!/usr/bin/env python3
"""Draws the link-preview image (1200 x 630) from the home page's own photo and text, with no browser.

    python scripts/og_preview_compose.py --html path/to/saved-home-page.html

The headline, figures and version are read from a "Save page as" copy of the home page (so they are the live
numbers); or give them with --runs --tbp --projects --version. It lays the photo, glow and text out the way
src/views/Home.vue styles them, and overwrites public/og-preview.png. It is an approximation drawn with DejaVu Serif,
not a screenshot: for the exact look, screenshot the page and use `npm run og-preview -- screenshot.png`.
"""
import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PHOTO = ROOT / 'src/assets/sandpiper.jpg'
OUT = ROOT / 'public/og-preview.png'
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
W, H = 1200, 630
CREAM = (250, 249, 246)
INK = (54, 54, 54)
INK_STRONG = (46, 46, 46)
INK_MUTED = (82, 82, 82)
ACCENT = (27, 116, 104)
ACCENT_DEEP = (21, 92, 83)
LEFT = 68          # .home-hero-inner: 3% margin plus 2rem padding
TOP = 48           # 3rem padding
TEXT_WIDTH = 880


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def read_page(html: str) -> dict:
    """The figures the home page shows, from a saved copy of it."""
    def text(cls):
        match = re.search(rf'class="{cls}"[^>]*>([^<]*)<', html)
        return match.group(1).strip() if match else None
    headline = re.match(r'([\d,]+)', text('home-headline') or '')
    sub = re.match(r'([\d,]+) Tbp across ([\d,]+) projects', text('home-subheadline') or '')
    version = re.search(r'Sandpiper ([\d.]+) is a resource', html)
    if not (headline and sub and version):
        raise SystemExit('Could not find the headline, figures and version in that page.')
    return {'runs': headline.group(1), 'tbp': sub.group(1), 'projects': sub.group(2), 'version': version.group(1)}


def background() -> Image.Image:
    """The hero photo, covering the frame, with the page's contrast and saturation boost."""
    photo = Image.open(PHOTO).convert('RGB')
    scale = max(W / photo.width, H / photo.height)
    photo = photo.resize((round(photo.width * scale), round(photo.height * scale)), Image.LANCZOS)
    left, top = (photo.width - W) // 2, (photo.height - H) // 2
    photo = photo.crop((left, top, left + W, top + H))
    photo = ImageEnhance.Contrast(photo).enhance(1.3)
    photo = ImageEnhance.Color(photo).enhance(1.4)
    return ImageEnhance.Brightness(photo).enhance(0.96)


def glow(image: Image.Image) -> Image.Image:
    """The soft cream radial glow behind the text (.home-hero-inner::before)."""
    mask = Image.new('L', (W, H), 0)
    cx, cy, rx, ry = 0.32 * 1000 + 40, 0.45 * 560 + 20, 700, 330
    pixels = mask.load()
    for y in range(H):
        for x in range(W):
            d = (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) ** 0.5
            alpha = 0.55 - 0.27 * (d / 0.55) if d < 0.55 else 0.28 * (1 - (d - 0.55) / 0.25) if d < 0.80 else 0
            pixels[x, y] = int(255 * max(alpha, 0))
    return Image.composite(Image.new('RGB', (W, H), CREAM), image, mask)


def draw_text(image: Image.Image, xy, text, fnt, fill, glow_strength=0.9) -> int:
    """Text with a cream halo (the page's text-shadow); returns its height."""
    halo = Image.new('L', (W, H), 0)
    ImageDraw.Draw(halo).text(xy, text, font=fnt, fill=255)
    halo = halo.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * glow_strength))
    image.paste(Image.new('RGB', (W, H), CREAM), (0, 0), halo)
    ImageDraw.Draw(image).text(xy, text, font=fnt, fill=fill)
    box = ImageDraw.Draw(image).textbbox(xy, text, font=fnt)
    return box[3] - box[1]


def fit(text: str, name: str, size: int, limit: int) -> ImageFont.FreeTypeFont:
    while size > 20 and ImageDraw.Draw(Image.new('L', (1, 1))).textlength(text, font=font(name, size)) > limit:
        size -= 1
    return font(name, size)


def wrap(text: str, fnt, limit: int) -> list[str]:
    measure = ImageDraw.Draw(Image.new('L', (1, 1)))
    lines, line = [], ''
    for word in text.split():
        trial = f'{line} {word}'.strip()
        if measure.textlength(trial, font=fnt) > limit and line:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def compose(figures: dict) -> Image.Image:
    image = glow(background())
    y = TOP
    head = f"{figures['runs']} metagenomes screened."
    head_font = fit(head, 'DejaVuSerif-Bold.ttf', 56, TEXT_WIDTH)
    draw_text(image, (LEFT, y), head, head_font, INK)
    y += int(head_font.size * 1.25) + 8
    sub = f"{figures['tbp']} Tbp across {figures['projects']} projects"
    draw_text(image, (LEFT, y), sub, font('DejaVuSans-Bold.ttf', 19), INK_STRONG)
    y += 56
    body = font('DejaVuSans.ttf', 16)
    lede = f"Sandpiper {figures['version']} is a resource for interrogating public shotgun metagenome datasets, presenting the results generated by SingleM."
    for line in wrap(lede, body, 400):
        draw_text(image, (LEFT, y), line, body, INK)
        y += 27
    y += 12
    thanks = 'We gratefully acknowledge the large collective effort expended in administering, gathering, sequencing and uploading these datasets into the public domain.'
    for line in wrap(thanks, body, 400):
        draw_text(image, (LEFT, y), line, body, INK_MUTED)
        y += 27
    y += 14
    label = font('DejaVuSans.ttf', 16)
    width = int(ImageDraw.Draw(image).textlength('Start exploring', font=label)) + 56
    pill = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(pill)
    pdraw.rounded_rectangle((LEFT, y, LEFT + width, y + 38), radius=19, fill=CREAM + (153,), outline=ACCENT_DEEP + (255,), width=1)
    image = Image.alpha_composite(image.convert('RGBA'), pill).convert('RGB')
    draw = ImageDraw.Draw(image)
    draw.text((LEFT + 16, y + 9), 'Start exploring', font=label, fill=ACCENT_DEEP)
    ax = LEFT + width - 24
    draw.line((ax, y + 19, ax + 12, y + 19), fill=ACCENT_DEEP, width=2)
    draw.line((ax + 7, y + 14, ax + 12, y + 19, ax + 7, y + 24), fill=ACCENT_DEEP, width=2)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--html', type=Path, help='a saved copy of the home page')
    parser.add_argument('--runs'); parser.add_argument('--tbp'); parser.add_argument('--projects'); parser.add_argument('--version')
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    figures = read_page(args.html.read_text(encoding='utf-8')) if args.html else {}
    figures.update({k: v for k, v in vars(args).items() if k in ('runs', 'tbp', 'projects', 'version') and v})
    missing = [k for k in ('runs', 'tbp', 'projects', 'version') if k not in figures]
    if missing:
        raise SystemExit(f'Give --html, or --{" --".join(missing)}')
    compose(figures).save(args.out)
    print(f'Wrote {args.out}: {figures["runs"]} runs, {figures["tbp"]} Tbp, {figures["projects"]} projects, Sandpiper {figures["version"]}')


if __name__ == '__main__':
    main()
