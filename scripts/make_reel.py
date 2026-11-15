"""Build one 1080x1920 Hindi product reel: voice, synced captions, b-roll.

Usage: python scripts/make_reel.py [--day N]   (N is 0-based; default = today)
Writes out/reel.mp4 and out/meta.json.
"""
import argparse, asyncio, datetime, json, os, random, subprocess, sys, time
from pathlib import Path

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
FONT = str(ROOT / "assets/fonts/NotoSansDevanagari-Bold.ttf")
W, H, FPS = 1080, 1920, 30
GAP = 0.18  # silence between spoken lines
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def run(cmd):
    print("  ffmpeg/ffprobe:", Path(str(cmd[-1])).name, flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(map(str, cmd))[:300]}\n{r.stderr[-1500:]}")
    return r.stdout


def today_index(cfg):
    start = datetime.date.fromisoformat(cfg["start_date"])
    return (datetime.datetime.now(IST).date() - start).days


def pick(day, products):
    n = len(products)
    cycle, pos = divmod(day, n)
    order = list(range(n))
    random.Random(1000 + cycle).shuffle(order)
    return products[order[pos]], cycle % 3


def script_lines(p, template):
    """Return list of (spoken text, style). First line is the hook."""
    name, b, cta_no = p["name"], p["b"], f"फाइंड नंबर {p['id']}"
    if template == 0:
        return [(p["problem"], "hook"),
                (f"इसका आसान हल है, {name}।", "name"),
                (b[0] + "।", "body"), (b[1] + "।", "body"), (b[2] + "।", "body"),
                (f"लिंक बायो में है, {cta_no}।", "cta")]
    if template == 1:
        return [(f"{name} लेने की तीन वजहें।", "hook"),
                (f"पहली, {b[0]}।", "body"), (f"दूसरी, {b[1]}।", "body"),
                (f"तीसरी, {b[2]}।", "body"),
                ("काम की लगी तो सेव कर लो।", "body"),
                (f"लिंक बायो में है, {cta_no}।", "cta")]
    return [("काश ये चीज़ मुझे पहले मिल जाती।", "hook"),
            (f"ये है {name}।", "name"),
            (p["problem"], "body"),
            (b[0] + "।", "body"), (b[1] + "।", "body"),
            ("जिसे इसकी ज़रूरत है, उसे भेज दो।", "body"),
            (f"लिंक बायो में है, {cta_no}।", "cta")]


async def tts(text, path, cfg):
    for attempt in range(4):
        print("  voice:", path.name, "try", attempt + 1, flush=True)
        try:
            await edge_tts.Communicate(text, cfg["voice"], rate=cfg["voice_rate"]).save(str(path))
            if path.stat().st_size > 1000:
                return
        except Exception as e:  # network hiccups are common, retry
            print("tts retry:", e)
        time.sleep(3 * (attempt + 1))
    sys.exit("TTS failed after retries")


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(path)]).strip())


def build_voice(lines, cfg):
    """Synthesize each line; return (voice wav path, [(start, end)] per line)."""
    wavs, spans, t = [], [], 0.25
    for i, (text, _) in enumerate(lines):
        mp3, wav = OUT / f"l{i}.mp3", OUT / f"l{i}.wav"
        asyncio.run(tts(text, mp3, cfg))
        run(["ffmpeg", "-y", "-i", str(mp3), "-af",
             "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
             "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
             "-ar", "44100", "-ac", "1", str(wav)])
        d = duration(wav)
        spans.append((t, t + d))
        t += d + GAP
        wavs.append(wav)
    total = t + 0.6
    inputs, parts = [], []
    for i, w in enumerate(wavs):
        inputs += ["-i", str(w)]
        parts.append(f"[{i}]adelay={int(spans[i][0]*1000)}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(wavs)))
    fc = ";".join(parts) + f";{mix}amix=inputs={len(wavs)}:normalize=0,apad,atrim=0:{total:.3f}[v]"
    voice = OUT / "voice.wav"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", str(voice)])
    return voice, spans, total


def chunks(text, span, size=3):
    """Split a line into caption chunks of ~size words, timed by length."""
    groups = []
    for phrase in [x for x in text.split(",") if x.strip()]:  # break at commas first
        words = phrase.split()
        part = [" ".join(words[i:i + size]) for i in range(0, len(words), size)]
        if len(part) > 1 and len(part[-1].split()) == 1:  # no orphan word
            tail = part.pop()
            part[-1] += " " + tail
        groups += part
    total = sum(len(g) for g in groups)
    out, t = [], span[0]
    for g in groups:
        d = (span[1] - span[0]) * len(g) / total
        out.append((g.rstrip("।,"), t, t + d))
        t += d
    return out


def font(size):
    return ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)


def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def caption_png(text, style, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = {"hook": 108, "name": 104, "cta": 100}.get(style, 92)
    fill = {"hook": (255, 222, 60), "name": (120, 255, 170), "cta": (255, 222, 60)}.get(style, (255, 255, 255))
    f = font(size)
    lines = wrap(d, text, f, 900)
    lh = int(size * 1.45)
    y = 980 - lh * len(lines) // 2
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y), ln, font=f, fill=fill, stroke_width=10, stroke_fill=(0, 0, 0))
        y += lh
    img.save(path)


def base_png(p, cfg, path):
    """Always-on layer: dark tint, page name, find-number badge, footer."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 105))
    d = ImageDraw.Draw(img)
    f1, f2, f3 = font(46), font(64), font(44)
    t = cfg["page_name"]
    d.text(((W - d.textlength(t, font=f1)) / 2, 270), t, font=f1, fill=(255, 255, 255, 230),
           stroke_width=4, stroke_fill=(0, 0, 0))
    badge = f"फाइंड #{p['id']}"
    bw = d.textlength(badge, font=f2) + 80
    d.rounded_rectangle(((W - bw) / 2, 350, (W + bw) / 2, 460), 55, fill=(255, 222, 60, 255))
    d.text(((W - bw) / 2 + 40, 358), badge, font=f2, fill=(20, 20, 20))
    foot = f"लिंक बायो में  -  फाइंड #{p['id']}"
    d.text(((W - d.textlength(foot, font=f3)) / 2, 1420), foot, font=f3, fill=(255, 255, 255, 235),
           stroke_width=4, stroke_fill=(0, 0, 0))
    img.save(path)


def background(p, total, rng):
    """Pexels portrait b-roll if a key is set, otherwise an animated gradient."""
    bg = OUT / "bg.mp4"
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    clips = []
    if key:
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                             params={"query": p["broll"], "orientation": "portrait", "per_page": 12},
                             headers={"Authorization": key}, timeout=30)
            r.raise_for_status()
            vids = [v for v in r.json().get("videos", []) if v.get("duration", 0) >= 5]
            rng.shuffle(vids)
            for v in vids[:4]:
                files = [f for f in v["video_files"] if f.get("height") and f["height"] >= 1280
                         and f.get("file_type") == "video/mp4"]
                if not files:
                    continue
                f = min(files, key=lambda x: x["height"])
                dest = OUT / f"clip{len(clips)}.mp4"
                with requests.get(f["link"], stream=True, timeout=120) as dl:
                    dl.raise_for_status()
                    with open(dest, "wb") as fh:
                        for blk in dl.iter_content(1 << 16):
                            fh.write(blk)
                clips.append((dest, v["duration"]))
        except Exception as e:
            print("Pexels unavailable, using gradient:", e)
            clips = []
    if clips:
        seg = total / len(clips) + 0.05
        inputs, parts = [], []
        for i, (c, dur) in enumerate(clips):
            inputs += ["-stream_loop", "-1", "-t", f"{seg:.3f}", "-i", str(c)]
            parts.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                         f"crop={W}:{H},fps={FPS},setsar=1,format=yuv420p[c{i}]")
        cat = "".join(f"[c{i}]" for i in range(len(clips)))
        fc = ";".join(parts) + f";{cat}concat=n={len(clips)}:v=1:a=0[v]"
        run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-t", f"{total:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an", str(bg)])
    else:
        palettes = [("0x1f4037", "0x99f2c8"), ("0x232526", "0x414345"), ("0x42275a", "0x734b6d"),
                    ("0x0f2027", "0x2c5364"), ("0x8e2de2", "0x4a00e0"), ("0xb24592", "0xf15f79")]
        c0, c1 = rng.choice(palettes)
        run(["ffmpeg", "-y", "-f", "lavfi", "-i",
             f"gradients=s={W}x{H}:r={FPS}:c0={c0}:c1={c1}:x0=0:y0=0:x1={W}:y1={H}:speed=0.02:d={total:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(bg)])
    return bg, bool(clips)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int)
    a = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text())
    products = json.loads((ROOT / "products.json").read_text())
    day = a.day if a.day is not None else today_index(cfg)
    if day < 0 or day >= cfg["total_days"]:
        print(f"day {day} is outside the {cfg['total_days']}-day run, nothing to post")
        Path(os.environ.get("GITHUB_OUTPUT", os.devnull)).open("a").write("skip=yes\n")
        return
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()
    p, template = pick(day, products)
    lines = script_lines(p, template)
    rng = random.Random(day)

    voice, spans, total = build_voice(lines, cfg)
    bg, broll = background(p, total, rng)

    base = OUT / "base.png"
    base_png(p, cfg, base)
    overlays = []
    for (text, style), span in zip(lines, spans):
        for ctext, s, e in chunks(text, span):
            png = OUT / f"cap{len(overlays)}.png"
            caption_png(ctext, style, png)
            overlays.append((png, s, e))

    inputs = ["-i", str(bg), "-i", str(voice), "-i", str(base)]
    for png, _, _ in overlays:
        inputs += ["-i", str(png)]
    fc, last = ["[0:v][2:v]overlay[b0]"], "b0"
    for i, (_, s, e) in enumerate(overlays):
        fc.append(f"[{last}][{i+3}:v]overlay=x=0:y='if(lt(t-{s:.3f},0.12),(1-(t-{s:.3f})/0.12)*45,0)':enable='between(t,{s:.3f},{e:.3f})'[b{i+1}]")
        last = f"b{i+1}"
    reel = OUT / "reel.mp4"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "1:a", "-af", "loudnorm=I=-14:TP=-1:LRA=11",
         "-t", f"{total:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "21",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
         "-movflags", "+faststart", str(reel)])

    site = cfg.get("site_url") or "link in bio"
    caption = (f"{p['problem']}\n\n{p['name']} — FIND #{p['id']}\n"
               f"लिंक बायो में है 👆 ({site})\n\n"
               f"सेव कर लो, बाद में काम आएगा।\n\n"
               f"#ad Affiliate link: खरीदने पर हमें छोटा कमीशन मिलता है, आपको कोई एक्स्ट्रा खर्च नहीं।\n\n"
               f"{cfg['hashtags']}")
    meta = {"day": day, "product_id": p["id"], "name": p["name"], "template": template,
            "seconds": round(total, 1), "broll": broll, "caption": caption,
            "title": f"{p['name']} | FIND #{p['id']}"}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    for tmp in OUT.glob("*"):
        if tmp.name not in ("reel.mp4", "meta.json"):
            tmp.unlink()
    print(json.dumps({k: meta[k] for k in ("day", "product_id", "name", "template", "seconds", "broll")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
