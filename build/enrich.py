"""Add or update posts in data/posts.json with real author photos, text and images.

Usage (one post per call, or a JSON list file):
  python build/enrich.py --kind x    --url https://x.com/user/status/ID --col g --sum "Why it matters." --themes hydrogen,core
  python build/enrich.py --kind li   --url https://www.linkedin.com/posts/slug-share-ID-xxxx/ --col s --sum "..." --name "Full Name" --sub "Role or company"
  python build/enrich.py --kind blog --url https://site.com/article --col b --sum "..." --title "Article title" --name "Site name" --ts 2026-11-18T12:00:00-03:00
  python build/enrich.py --file new_posts.json      (a list of the same fields)

Posts are keyed by url. Running again on the same url updates the summary, column and themes.
No login is needed: X data comes from the public syndication endpoint and LinkedIn data from the public embed page.
"""
import argparse, json, os, re, sys, html, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "data", "posts.json")
AR = timezone(timedelta(hours=-3))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def load():
    if os.path.exists(POSTS):
        return json.load(open(POSTS, encoding="utf-8"))
    return []


def save(posts):
    posts.sort(key=lambda p: p["ts"], reverse=True)
    json.dump(posts, open(POSTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def fav(domain):
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"


def x_post(url):
    m = re.search(r"/status/(\d+)", url)
    if not m:
        raise ValueError("no status id in " + url)
    sid = m.group(1)
    j = json.loads(get(f"https://cdn.syndication.twimg.com/tweet-result?id={sid}&token=a&lang=en"))
    if j.get("__typename") == "TweetTombstone":
        raise ValueError("tweet unavailable: " + url)
    u = j["user"]
    text = j.get("text", "")
    nt = (j.get("note_tweet") or {}).get("note_tweet_results", {}).get("result", {}).get("text")
    if nt:
        text = nt
    for e in j.get("entities", {}).get("urls", []):
        text = text.replace(e["url"], e.get("display_url", e.get("expanded_url", "")))
    for e in j.get("entities", {}).get("media", []):
        text = text.replace(e["url"], "")
    md = j.get("mediaDetails") or []
    ts = datetime.strptime(j["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    return {
        "kind": "x", "url": f"https://x.com/{u['screen_name']}/status/{sid}",
        "name": u["name"], "sub": u["screen_name"],
        "avatar": u["profile_image_url_https"].replace("_normal", "_bigger"),
        "text": text.strip(), "img": md[0]["media_url_https"] if md else None,
        "likes": j.get("favorite_count", 0), "replies": j.get("conversation_count", 0),
        "ts": ts.isoformat(),
    }


def li_post(url, name=None, sub=None):
    m = re.search(r"(share|ugcPost|activity)-(\d{15,})", url) or re.search(r"urn:li:(share|ugcPost|activity):(\d{15,})", url)
    if not m:
        raise ValueError("no LinkedIn id in " + url)
    kind, pid = m.group(1), m.group(2)
    s = get(f"https://www.linkedin.com/embed/feed/update/urn:li:{kind}:{pid}")
    d = re.search(r'<meta property="og:description" content="([^"]*)"', s)
    av = re.search(r'(https://media\.licdn\.com/dms/image/[^"&\s]*profile-displayphoto[^"\s]*?e=2147483647[^"\s]*)', s)
    im = re.search(r'(https://media\.licdn\.com/dms/image/[^"&\s]*feedshare[^"\s]*?e=2147483647[^"\s]*)', s)
    t = re.search(r'<meta property="og:title" content="([^"]*)"', s)
    title = html.unescape(t.group(1)) if t else ""
    if not name:
        name = title.split(" on LinkedIn")[0].strip() if " on LinkedIn" in title else name
    ts = datetime.fromtimestamp((int(pid) >> 22) / 1000, timezone.utc)
    clean = re.sub(r"[?#].*$", "", url)
    return {
        "kind": "li", "url": clean, "name": name or "LinkedIn", "sub": sub or "",
        "avatar": html.unescape(av.group(1)) if av else None,
        "text": html.unescape(d.group(1)) if d else "",
        "img": html.unescape(im.group(1)) if im else None,
        "ts": ts.isoformat(),
    }


def blog_post(url, title, name, ts, logo=None):
    dom = urllib.parse.urlparse(url).netloc.replace("www.", "")
    return {"kind": "blog", "url": url, "name": name or dom, "sub": dom, "title": title,
            "logo": logo or fav(dom), "ts": ts}


def add(spec, posts):
    kind = spec["kind"]
    if kind == "x":
        p = x_post(spec["url"])
    elif kind == "li":
        p = li_post(spec["url"], spec.get("name"), spec.get("sub"))
    else:
        p = blog_post(spec["url"], spec.get("title", ""), spec.get("name"), spec["ts"], spec.get("logo"))
    p["col"] = spec["col"]
    p["sum"] = spec.get("sum", "")
    p["themes"] = [t for t in (spec.get("themes") or []) if t]
    for i, old in enumerate(posts):
        if old["url"] == p["url"]:
            posts[i] = p
            return "updated"
    posts.append(p)
    return "added"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--kind", choices=["x", "li", "blog"])
    ap.add_argument("--url"); ap.add_argument("--col"); ap.add_argument("--sum", default="")
    ap.add_argument("--themes", default=""); ap.add_argument("--title"); ap.add_argument("--name")
    ap.add_argument("--sub"); ap.add_argument("--ts"); ap.add_argument("--logo")
    a = ap.parse_args()
    specs = json.load(open(a.file, encoding="utf-8")) if a.file else [{
        "kind": a.kind, "url": a.url, "col": a.col, "sum": a.sum, "title": a.title, "name": a.name,
        "sub": a.sub, "ts": a.ts, "logo": a.logo, "themes": [t.strip() for t in a.themes.split(",")]}]
    posts = load()
    for s in specs:
        try:
            print(add(s, posts), s["url"])
        except Exception as e:
            print("FAILED", s.get("url"), e)
    save(posts)
    print(len(posts), "posts in data/posts.json")


if __name__ == "__main__":
    main()
