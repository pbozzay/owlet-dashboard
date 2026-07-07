from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[1] / "app" / "static"


def rounded_gradient(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    assert px is not None
    for y in range(size):
        for x in range(size):
            t = (x * 0.35 + y * 0.65) / size
            if t < 0.42:
                k = t / 0.42
                c0 = (29, 78, 216)
                c1 = (18, 32, 51)
            else:
                k = (t - 0.42) / 0.58
                c0 = (18, 32, 51)
                c1 = (15, 23, 42)
            px[x, y] = tuple(int(c0[i] * (1 - k) + c1[i] * k) for i in range(3)) + (255,)

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gpx = glow.load()
    assert gpx is not None
    cx, cy = int(size * 0.32), int(size * 0.23)
    max_r = size * 0.58
    for y in range(size):
        for x in range(size):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            a = max(0, 1 - d / max_r) ** 1.8
            gpx[x, y] = (96, 165, 250, int(115 * a))
    img = Image.alpha_composite(img, glow)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.21875), fill=255)
    img.putalpha(mask)
    return img


def scale_points(points: list[tuple[float, float]], s: int) -> list[tuple[int, int]]:
    return [(round(x * s / 512), round(y * s / 512)) for x, y in points]


def draw_icon(size: int) -> Image.Image:
    s = size
    img = rounded_gradient(s)
    d = ImageDraw.Draw(img)
    def box(x0, y0, x1, y1):
        return tuple(round(v * s / 512) for v in (x0, y0, x1, y1))
    def w(v):
        return max(1, round(v * s / 512))

    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    owl = scale_points([
        (120, 170), (128, 108), (174, 73), (220, 92), (238, 101), (249, 118), (256, 135),
        (263, 118), (274, 101), (292, 92), (338, 73), (384, 108), (392, 170), (400, 234),
        (350, 280), (300, 258), (277, 248), (264, 229), (256, 208), (248, 229), (235, 248),
        (212, 258), (162, 280), (112, 234),
    ], s)
    sd.polygon([(x, y + w(15)) for x, y in owl], fill=(2, 6, 23, 85))
    shadow = shadow.filter(ImageFilter.GaussianBlur(w(14)))
    img = Image.alpha_composite(img, shadow)
    d = ImageDraw.Draw(img)
    d.polygon(owl, fill=(248, 250, 252, 245))

    d.ellipse(box(159, 126, 255, 222), fill=(219, 234, 254, 255))
    d.ellipse(box(257, 126, 353, 222), fill=(219, 234, 254, 255))
    d.ellipse(box(185, 152, 229, 196), fill=(18, 32, 51, 255))
    d.ellipse(box(283, 152, 327, 196), fill=(18, 32, 51, 255))
    d.ellipse(box(209, 157, 223, 171), fill=(147, 197, 253, 255))
    d.ellipse(box(307, 157, 321, 171), fill=(147, 197, 253, 255))
    d.line(scale_points([(244, 212), (256, 232), (268, 212)], s), fill=(249, 115, 22, 255), width=w(16), joint="curve")

    pulse = scale_points([(106, 328), (174, 328), (194, 286), (229, 382), (263, 246), (297, 328), (406, 328)], s)
    d.line(pulse, fill=(56, 189, 248, 255), width=w(24), joint="curve")
    # Highlight line for tiny-size legibility.
    d.line(pulse, fill=(186, 230, 253, 120), width=max(1, w(8)), joint="curve")

    sock = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sock)
    sd.rounded_rectangle(box(195, 327, 279, 458), radius=w(27), fill=(248, 250, 252, 245))
    sd.rounded_rectangle(box(252, 356, 394, 458), radius=w(52), fill=(248, 250, 252, 245))
    sd.rounded_rectangle(box(216, 346, 258, 437), radius=w(12), fill=(219, 234, 254, 255))
    sd.rounded_rectangle(box(258, 376, 373, 437), radius=w(32), fill=(219, 234, 254, 255))
    sd.pieslice(box(322, 376, 373, 437), start=-90, end=90, fill=(37, 99, 235, 220))
    img = Image.alpha_composite(img, sock)

    d = ImageDraw.Draw(img)
    d.arc(box(92, 38, 420, 154), start=196, end=344, fill=(147, 197, 253, 120), width=w(14))
    return img


for size in (32, 180, 192, 512):
    icon = draw_icon(1024).resize((size, size), Image.Resampling.LANCZOS)
    icon.save(OUT / f"icon-{size}.png")

ico_sizes = [(16, 16), (32, 32), (48, 48)]
ico = draw_icon(256)
ico.save(OUT / "favicon.ico", sizes=ico_sizes)
print("wrote", ", ".join(p.name for p in [OUT / 'favicon.ico', *(OUT / f'icon-{s}.png' for s in (32, 180, 192, 512))]))
