#!/usr/bin/env python3
"""Show how the keyword tagger treats real headlines: what it keeps, what it drops, and with which tags.

    python scripts/eval_tags.py            # the current inbox plus a fresh fetch from every source
    python scripts/eval_tags.py --offline  # the current inbox only

Use it before and after editing SUBJECTS or MACHINES in update_feed.py. Read the KEEP and drop lists and judge
them by hand; the tags are hints for learners, so a wrong tag is worse than no tag.
"""
import json, sys, importlib.util
from pathlib import Path

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("update_feed", here / "update_feed.py")
uf = importlib.util.module_from_spec(spec); spec.loader.exec_module(uf)

items = {i["title"]: i for i in json.loads(uf.FEED.read_text(encoding="utf-8")).get("inbox", [])}
if "--offline" not in sys.argv:
    for s in uf.SOURCES:
        try:
            for i in uf.items(s["name"], uf.fetch(s["url"])): items.setdefault(i["title"], i)
        except Exception as e:
            print(f"{s['name']}: fetch failed ({e})", file=sys.stderr)

kept = 0
for title in items:
    t = uf.tags(title)
    keep = bool(t["subjects"] or t["machines"]); kept += keep
    print(("KEEP " if keep else "drop ") + ", ".join(t["subjects"] + t["machines"]).ljust(30) + title[:90])
print(f"\n{kept} of {len(items)} kept")
