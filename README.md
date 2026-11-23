# Taco Feed

Static AI + SEO news deck, live at https://sofianatasha.github.io/taco-feed/ (noindex).

- `data/posts.json` holds every post. `data/themes.json` holds the topic chips and their 3-line briefs (`"archived": true` hides a chip but keeps its tags on older cards). `data/takeaways.json` holds the Key takeaways (max 6, each linked to a topic).
- `build/enrich.py` adds posts with real photos and text. `build/peek.py` lists what the feed holds. `build/build.py` writes `index.html` with the last 28 days, grouped by week.
- Two scheduled tasks keep it fresh: a refresh at noon and 8 PM ART, and a Tuesday rewrite of the topics and takeaways.
