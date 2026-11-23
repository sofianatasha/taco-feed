"""Build index.html from data/*.json. Run from anywhere: python build/build.py

Reads the data files and writes index.html only. It never writes posts.json.
The page shows the last KEEP_DAYS days, grouped by calendar week (Monday to Sunday, ART).
"""
import json, os, sys
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR = timezone(timedelta(hours=-3))
KEEP_DAYS = 28
MAX_TAKE = 6


def load(name, default):
    path = os.path.join(ROOT, "data", name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_ts(s):
    t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=AR)
    return t.astimezone(AR)


def week_label(i):
    return "This week" if i <= 0 else "Last week" if i == 1 else f"{i} weeks ago"


def week_range(start):
    end = start + timedelta(days=6)
    if start.month == end.month:
        return f"{start:%b} {start.day} to {end.day}"
    return f"{start:%b} {start.day} to {end:%b} {end.day}"


cols = load("columns.json", [])
themes = load("themes.json", [])
posts = load("posts.json", [])
take = load("takeaways.json", {"items": []})

now = datetime.now(AR)
cut = now - timedelta(days=KEEP_DAYS)
this_monday = now.date() - timedelta(days=now.weekday())

kept = []
for p in posts:
    try:
        t = parse_ts(p["ts"])
    except (KeyError, ValueError):
        continue
    if t < cut:
        continue
    p["_t"] = t
    kept.append(p)
posts = sorted(kept, key=lambda p: p["_t"], reverse=True)

weeks = {}
for p in posts:
    t = p.pop("_t")
    p["day"] = t.strftime("%a %b %d").replace(" 0", " ")
    p["time"] = t.strftime("%I:%M %p").lstrip("0")
    monday = t.date() - timedelta(days=t.weekday())
    wk = max(0, (this_monday - monday).days // 7)
    p["wk"] = wk
    weeks.setdefault(wk, {"i": wk, "label": week_label(wk), "range": week_range(monday)})

theme_ids = {t["id"] for t in themes}
for p in posts:
    p["themes"] = [t for t in (p.get("themes") or []) if t in theme_ids]
for t in themes:
    t["n"] = sum(1 for p in posts if t["id"] in p["themes"])
    t["archived"] = bool(t.get("archived"))
themes = [t for t in themes if t["n"] > 0]
live = {t["id"] for t in themes}

items = take.get("items", []) if isinstance(take, dict) else (take or [])
takeaways = []
for it in items:
    text = (it.get("text") or "").strip()
    th = it.get("theme")
    if not text or (th and th not in live):
        continue
    takeaways.append({"theme": th or None, "text": text})
takeaways = takeaways[:MAX_TAKE]

dump = lambda o: json.dumps(o, ensure_ascii=False)
data = (f"const COLS={dump(cols)};\nconst THEMES={dump(themes)};\nconst TAKE={dump(takeaways)};\n"
        f"const WEEKS={dump([weeks[k] for k in sorted(weeks)])};\nconst P={dump(posts)};")
tpl = open(os.path.join(ROOT, "build", "template.html"), encoding="utf-8").read()
out = tpl.replace("/*DATA*/", data).replace("{{REFRESH}}", now.strftime("%b %d, %I:%M %p").replace(" 0", " ") + " ART")
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(out)
active = sum(1 for t in themes if not t["archived"])
print(f"index.html: {len(posts)} posts in {len(weeks)} weeks, {active} topics ({len(themes) - active} archived), "
      f"{len(takeaways)} takeaways, {len(out) // 1024} KB")
