#!/usr/bin/env python3
"""Refresh the "inbox" of zola-feed.json from public RSS feeds. as_of_date: 2026-10-03

Run by the GitHub Action every six hours. Only the inbox is automatic; exams, watch,
events, notices and edition are edited by hand. If every source fails, the file is left
untouched. The output is validated before it is written, so the app never receives a
malformed feed.
"""
import json, re, sys, hashlib, datetime as dt, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED = Path(__file__).resolve().parent.parent / "zola-feed.json"
# Add or replace sources here. Each must be an RSS or Atom URL that opens in a browser.
SOURCES = [
    {"name": "PIB", "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Reg=3&Lang=1"},  # English, all ministries
]
KEEP_DAYS, KEEP_MAX = 45, 150

# Keyword -> machine. A match is a hint for the learner, never a verified link.
MACHINES = [
    ("M01", r"\bbill\b.*\b(passed|introduced|lok sabha|rajya sabha)|money bill|joint sitting"),
    ("M02", r"\bgovernor\b.*\b(assent|bill)|article 200|article 201"),
    ("M03", r"\bordinance\b|article 123"),
    ("M04", r"article 213"),
    ("M05", r"constitution\s*\(.*amendment\)|constitutional amendment|article 368|ratification"),
    ("M06", r"national emergency|article 352"),
    ("M07", r"president'?s rule|article 356"),
    ("M08", r"financial emergency|article 360"),
    ("M09", r"anti-defection|tenth schedule|disqualification petition"),
    ("M10", r"concurrent list|union list|state list|article 254|repugnan"),
    ("M11", r"\bhung\b|floor test|government formation"),
    ("M12", r"\bgovernor\b.*\b(invite|chief minister|floor test)"),
    ("M13", r"\bgst council\b|\bgst\b"),
    ("M14", r"\brepo rate\b|monetary policy committee|\bmpc\b|\bcrr\b|money supply"),
    ("M15", r"inflation target|\bcpi\b|consumer price index"),
    ("M16", r"\bmsp\b|minimum support price|procurement|public distribution|food corporation|buffer stock"),
    ("M17", r"finance commission|devolution|divisible pool"),
    ("M18", r"environment(al)? clearance|\beia\b|environment impact assessment|public hearing"),
    ("M19", r"\brti\b|right to information|information commission"),
    ("M20", r"representation of the people|election commission|disqualif"),
    ("M21", r"article 311|disciplinary|civil servant.*(dismiss|removal)"),
    ("M22", r"\bcag\b|comptroller and auditor general|public accounts committee"),
    ("M23", r"co-?operative"),
]
SUBJECTS = [
    # Indian polity and governance. A bare "President" is not enough (it matched foreign presidents).
    ("Polity", r"constitution|parliament|lok sabha|rajya sabha|\bgovernor|president of india|president droupadi|rashtrapati|vice[- ]president|"
               r"supreme court|high court|election|\bbill\b|\bact\b|amendment|ordinance|panchayat|federal|union cabinet|cabinet approves|"
               r"lokpal|\bcag\b|tribunal|right to information|governance|gram sabha"),
    ("Economy", r"\brbi\b|reserve bank|inflation|\bgdp\b|fiscal|\btax|\bgst\b|\bbank|export|import|\bmsp\b|\btrade|\bports?\b|shipping|maritime|"
                r"shipbuilding|investment|\bfdi\b|\bmsme|startup|budget|disinvestment|\bpli\b|infrastructure|railway|highway|logistics|"
                r"\boil\b|petroleum|\bcoal\b|insurance|\bsebi\b|rupee|employment|labour|manufactur|industr|farmer|\bkisan|agricultur|co-?operative|gold"),
    ("Environment", r"climate|forest|wildlife|biodiversity|pollution|environment|\btiger|elephant|wetland|plastic|emission|renewable|\bsolar|"
                    r"wind energy|green hydrogen|ivory|leopard|pangolin|species|ozone|\bcop ?\d|unfccc|mangrove|coral|\briver|ganga|"
                    r"\bwaste|carbon|net[- ]zero|monsoon|cyclone|flood|drought|earthquake|disaster|air quality|\bcaqm\b|\baqi\b|swachh"),
    ("S&T", r"\bisro\b|satellite|\bspace\b|vaccine|quantum|semiconductor|\bai\b|artificial intelligence|\bdrdo\b|missile|nuclear|"
            r"research|technolog|digital|cyber|telecom|bhashini|\b[56]g\b|biotech|genom|science|innovation|patent|supercomput|drone|gaganyaan|chandrayaan"),
    ("IR", r"bilateral|summit|\bmou\b|foreign|united nations|\bg20\b|brics|\bquad\b|\bsco\b|asean|foreign delegation|ambassador|treaty|joint statement|"
           r"external affairs|russia|china|united states|\busa\b|japan|france|\buk\b|britain|bangladesh|nepal|sri lanka|bhutan|maldives|"
           r"myanmar|afghanistan|india[- ][a-z]+ (?:ties|relations|partnership)"),
    ("History", r"heritage|cultur|museum|archaeolog|monument|unesco|mahatma gandhi|gandhi smriti|freedom fighter|tribal|festival|handicraft|textile|"
                r"jayanti|ancient|temple|literature|classical language"),
]

def tags(title):
    """Keyword hints for a headline. Hints, not verified links; the app labels them that way."""
    low = title.lower()
    return {"machines": [m for m, rx in MACHINES if re.search(rx, low)][:5],
            "subjects": [s for s, rx in SUBJECTS if re.search(rx, low)][:3]}

def relevant(item):
    return bool(item["machines"] or item["subjects"])

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "zola-feed/1 (+study tool)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()

def when(text):
    if not text: return ""
    try: d = parsedate_to_datetime(text)
    except Exception:
        try: d = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception: return ""
    if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def items(name, raw):
    root = ET.fromstring(raw)
    out = []
    for it in root.iter():
        tag = it.tag.split('}')[-1]
        if tag not in ("item", "entry"): continue
        g = lambda k: next((c for c in it if c.tag.split('}')[-1] == k), None)
        t, l = g("title"), g("link")
        p = next((x for x in (g("pubDate"), g("published"), g("updated")) if x is not None), None)  # empty Elements are falsy
        title = re.sub(r"\s+", " ", (t.text or "") if t is not None else "").strip()
        link = ((l.text or l.get("href") or "") if l is not None else "").strip()
        if not title or not link.startswith("https://"):
            if link.startswith("http://"): link = "https://" + link[7:]
            else: continue
        out.append({
            "id": hashlib.sha1(link.encode()).hexdigest()[:16],
            "title": title[:300], "url": link[:600], "published": when(p.text if p is not None else ""),
            "source": name,
            **tags(title),
        })
    return out

def validate(f):
    assert f.get("schema") == "zola-feed/1", "schema"
    dt.datetime.fromisoformat(f["updated"].replace("Z", "+00:00"))
    for k in ("exams", "watch", "events", "inbox", "notices"): assert isinstance(f.get(k), list), k
    assert sum(1 for e in f["exams"] if e.get("primary")) <= 1, "more than one primary exam"
    ids = [e.get("id") for e in f["exams"]]
    assert len(ids) == len(set(ids)), "two exams share an id"
    for e in f["exams"]: dt.date.fromisoformat(e["date"])
    for w in f["watch"]: dt.date.fromisoformat(w["date"]); assert w.get("title"), "watch item without a title"
    for ev in f["events"]:
        assert ev.get("id") and ev.get("title"), "event without an id or title"
        assert ev.get("status", "UNVERIFIED") in ("UNVERIFIED", "VERIFIED"), f"event {ev['id']}: status must be UNVERIFIED or VERIFIED"
    for n in f["notices"]:
        assert n.get("level", "info") in ("info", "correction", "warning"), "notice level must be info, correction or warning"
    links = [x.get("source", {}).get("url", "") for x in f["exams"] + f["events"]] + [f.get("edition", {}).get("url", "")]
    for u in links: assert not u or u.startswith("https://"), f"link is not https: {u}"
    for i in f["inbox"]: assert i["url"].startswith("https://") and i["title"], "inbox item"
    assert len(json.dumps(f)) < 1_400_000, "feed too large"

def main():
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    fresh, ok = [], 0
    for s in SOURCES:
        try:
            fresh += items(s["name"], fetch(s["url"])); ok += 1
            print(f"{s['name']}: ok")
        except Exception as e:
            print(f"{s['name']}: failed ({e})", file=sys.stderr)
    if not ok:
        print("No source answered; leaving the feed unchanged."); return 0
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    merged = {i["id"]: i for i in feed.get("inbox", [])}
    for i in fresh:
        # PIB's feed carries no dates: keep the time this bot first saw the release (within six hours).
        if not i["published"]: i["published"] = merged.get(i["id"], {}).get("published") or now
        merged[i["id"]] = i
    for i in merged.values(): i.update(tags(i["title"]))          # better keyword lists apply to old items too
    inbox = sorted((i for i in merged.values() if relevant(i) and (not i["published"] or i["published"] >= cutoff)),
                   key=lambda i: i["published"], reverse=True)[:KEEP_MAX]
    if inbox == feed.get("inbox", []):
        print("Inbox unchanged."); return 0
    feed["inbox"] = inbox
    feed["updated"] = now
    validate(feed)
    FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {len(inbox)} inbox items.")
    return 0

if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        try: validate(json.loads(FEED.read_text(encoding="utf-8")))
        except (AssertionError, KeyError, ValueError, TypeError, AttributeError) as e:
            print(f"zola-feed.json is NOT valid: {type(e).__name__}: {e}", file=sys.stderr); sys.exit(1)
        print("zola-feed.json is valid."); sys.exit(0)
    sys.exit(main())
