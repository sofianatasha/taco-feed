"""Build index.html from data/*.json. Run from anywhere: python build/build.py"""
import json, os, sys
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR = timezone(timedelta(hours=-3))
KEEP_DAYS = 10

cols = json.load(open(os.path.join(ROOT, "data", "columns.json"), encoding="utf-8"))
themes = json.load(open(os.path.join(ROOT, "data", "themes.json"), encoding="utf-8"))
posts = json.load(open(os.path.join(ROOT, "data", "posts.json"), encoding="utf-8"))

now = datetime.now(AR)
cut = (now - timedelta(days=KEEP_DAYS)).isoformat()
posts = [p for p in posts if p["ts"] >= cut]
posts.sort(key=lambda p: p["ts"], reverse=True)
for p in posts:
    t = datetime.fromisoformat(p["ts"]).astimezone(AR)
    p["day"] = t.strftime("%a %b %d").replace(" 0", " ")
    p["time"] = t.strftime("%I:%M %p").lstrip("0")
theme_ids = {t["id"] for t in themes}
for p in posts:
    p["themes"] = [t for t in p.get("themes", []) if t in theme_ids]
for t in themes:
    t["n"] = sum(1 for p in posts if t["id"] in p["themes"])
themes = [t for t in themes if t["n"] > 0]

tpl = open(os.path.join(ROOT, "build", "template.html"), encoding="utf-8").read()
data = "const COLS=" + json.dumps(cols, ensure_ascii=False) + ";\nconst THEMES=" + json.dumps(themes, ensure_ascii=False) + ";\nconst P=" + json.dumps(posts, ensure_ascii=False) + ";"
out = tpl.replace("/*DATA*/", data).replace("{{REFRESH}}", now.strftime("%b %d, %I:%M %p").replace(" 0", " ") + " ART")
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print(f"index.html: {len(posts)} posts, {len(themes)} themes, {len(out)//1024} KB")
