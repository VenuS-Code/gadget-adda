"""Generate docs/index.html (the link-in-bio page) from products.json + config.json."""
import html, json
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config.json").read_text())
products = json.loads((ROOT / "products.json").read_text())
tag = cfg.get("amazon_tag", "").strip()

cards = []
for p in products:
    url = f"https://www.amazon.in/s?k={quote_plus(p['q'])}" + (f"&tag={quote_plus(tag)}" if tag else "")
    cards.append(
        f'<a class="card" href="{html.escape(url)}" target="_blank" rel="sponsored noopener" '
        f'data-k="{p["id"]} {html.escape(p["name"])} {html.escape(p["q"])}">'
        f'<span class="num">#{p["id"]}</span><span class="txt"><b>{html.escape(p["name"])}</b>'
        f'<small>{html.escape(p["b"][0])}</small></span><span class="go">Amazon पर देखें</span></a>')

page = f"""<!doctype html>
<html lang="hi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(cfg['page_name'])} | रील में दिखी हर चीज़ का लिंक</title>
<meta name="description" content="रील में दिखे टेक गैजेट्स के लिंक, फाइंड नंबर से ढूँढें।">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{{--bg:#fbf7ef;--ink:#1c1a17;--mut:#6b655c;--card:#fff;--line:#e7dfd0;--acc:#ffde3c;--cta:#1f6f4a}}
@media(prefers-color-scheme:dark){{:root{{--bg:#15130f;--ink:#f4efe4;--mut:#a79f92;--card:#211e19;--line:#35302a;--cta:#5fd39a}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:'Noto Sans Devanagari',system-ui,sans-serif;line-height:1.5}}
main{{max-width:560px;margin:0 auto;padding:28px 16px 60px}}
h1{{font-size:30px;font-weight:800;margin:0 0 4px}}p.sub{{margin:0 0 18px;color:var(--mut)}}
input{{width:100%;padding:14px 16px;font:inherit;font-size:17px;border:2px solid var(--ink);border-radius:14px;background:var(--card);color:var(--ink);position:sticky;top:10px;z-index:2}}
.list{{display:grid;gap:10px;margin-top:16px}}
.card{{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;align-items:center;padding:14px;background:var(--card);border:1px solid var(--line);border-radius:16px;text-decoration:none;color:inherit}}
.card:active{{transform:scale(.99)}}
.num{{grid-row:span 2;background:var(--acc);color:#1c1a17;font-weight:800;font-size:18px;min-width:58px;text-align:center;padding:10px 6px;border-radius:12px}}
.txt b{{display:block;font-size:17px}}.txt small{{color:var(--mut);font-size:14px}}
.go{{grid-column:2;color:var(--cta);font-weight:600;font-size:14px}}
.none{{display:none;color:var(--mut);padding:20px 0;text-align:center}}
footer{{margin-top:34px;font-size:13px;color:var(--mut)}}
</style></head><body><main>
<h1>{html.escape(cfg['page_name'])}</h1>
<p class="sub">रील में जो नंबर दिखा था, वही यहाँ लिखें।</p>
<input id="q" type="search" inputmode="search" placeholder="फाइंड नंबर या नाम लिखें, जैसे 12" aria-label="फाइंड नंबर या नाम">
<div class="list" id="list">{''.join(cards)}</div>
<p class="none" id="none">इस नाम से कुछ नहीं मिला।</p>
<footer>As an Amazon Associate I earn from qualifying purchases. इन लिंक से खरीदने पर हमें छोटा कमीशन मिलता है, आपके लिए दाम वही रहता है। दाम और उपलब्धता Amazon पर देखें।</footer>
</main><script>
const q=document.getElementById('q'),cards=[...document.querySelectorAll('.card')],none=document.getElementById('none');
q.addEventListener('input',()=>{{const v=q.value.trim().toLowerCase().replace('#','');let n=0;
cards.forEach(c=>{{const k=c.dataset.k.toLowerCase();const hit=!v||(/^\\d+$/.test(v)?k.split(' ')[0]===v:k.includes(v));c.style.display=hit?'':'none';if(hit)n++}});
none.style.display=n?'none':'block'}});
</script></body></html>"""
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs/index.html").write_text(page)
print(f"site built: {len(products)} products, affiliate tag {'set' if tag else 'NOT set'}")
