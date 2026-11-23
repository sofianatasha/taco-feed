"""Print what is in data/posts.json, safe for any characters in names and text.

Usage:
  python build/peek.py                 summary + the 60 newest posts
  python build/peek.py --n 120         more rows
  python build/peek.py --kind li       only one source (x, li, blog)
  python build/peek.py --untagged      only posts with no theme
  python build/peek.py --theme local   only posts with that theme

The scheduled task uses this instead of ad hoc python -c one-liners. A one-liner that prints
a name with a special character crashes on the Windows console, and the retry with an
environment-variable prefix waits for an approval that never comes.
"""
import argparse, collections, json, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=60)
ap.add_argument("--kind", choices=["x", "li", "blog"])
ap.add_argument("--theme")
ap.add_argument("--untagged", action="store_true")
a = ap.parse_args()

posts = json.load(open(os.path.join(ROOT, "data", "posts.json"), encoding="utf-8"))
themes = json.load(open(os.path.join(ROOT, "data", "themes.json"), encoding="utf-8"))

newest = {}
for p in posts:
    if p["ts"] > newest.get(p["kind"], ""):
        newest[p["kind"]] = p["ts"]
print(len(posts), "posts |", dict(collections.Counter(p["kind"] for p in posts)))
print("newest per source:", newest)
tc = collections.Counter(t for p in posts for t in p.get("themes") or [])
print("themes:", ", ".join(f"{t['id']}={tc.get(t['id'], 0)}{' (archived)' if t.get('archived') else ''}" for t in themes))
print("untagged:", sum(1 for p in posts if not p.get("themes")))
print()

rows = sorted(posts, key=lambda p: p["ts"], reverse=True)
if a.kind:
    rows = [p for p in rows if p["kind"] == a.kind]
if a.theme:
    rows = [p for p in rows if a.theme in (p.get("themes") or [])]
if a.untagged:
    rows = [p for p in rows if not p.get("themes")]
for p in rows[: a.n]:
    print(p["ts"][:16], p["kind"], p["col"], (p.get("name") or "")[:24], "|", p["url"][:100], "|", ",".join(p.get("themes") or []), "|", (p.get("sum") or "")[:110])
