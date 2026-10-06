"""Builds the cross-pool dashboard for Herre Senior 4 7:7 Efterår.

Run:      python build.py
Output:   site/index.html  (open it in a browser)
Needs:    pip install requests beautifulsoup4
"""
import datetime
import html
import json
import pathlib
import re
import time

import requests
from bs4 import BeautifulSoup

# Pool pages P1..P8 have consecutive numbers 496331..496338
POOLS = {f"P{i}": f"https://www.dbu.dk/resultater/pulje/{496330 + i}/" for i in range(1, 9)}
PROMOTE = 12  # the 12 best eligible teams move up


def read_pool(url):
    """Read one pool page and return a list of teams (one dict per team)."""
    r = requests.get(url, timeout=30, headers={"User-Agent": "dbu-dashboard (student project)"})
    r.raise_for_status()
    teams = []
    for tr in BeautifulSoup(r.text, "html.parser").find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        if len(cells) < 8 or not cells[0].isdigit():
            continue  # header rows and other tables
        gf, ga = (int(n) for n in re.findall(r"\d+", cells[6])[:2])  # "26 - 15"
        teams.append({
            "place": int(cells[0]), "team": cells[1], "played": int(cells[2]),
            "gf": gf, "ga": ga, "points": int(cells[7]),
            # DBU marks teams with a no-show with "!" (title text: "udeblevet")
            "noshow": "!" in tr.get_text() or "udeblevet" in str(tr).lower(),
        })
    if len(teams) < 2:
        raise ValueError(f"No standings table found at {url}")  # stop: keep the old page
    return teams


def rank_all(pools):
    """Apply the cross-pool rules and return all teams in final order."""
    for name, teams in pools.items():
        n = 0
        for t in sorted(teams, key=lambda t: t["place"]):
            t["pool"] = name
            t["eligible"] = not t["noshow"]
            n += t["eligible"]
            t["elig_place"] = n if t["eligible"] else None  # place among eligible teams
            k = t["played"] or 1  # avoid dividing by zero
            t["ppm"] = t["points"] / k
            t["gdpm"] = (t["gf"] - t["ga"]) / k
            t["gfpm"] = t["gf"] / k
    flat = [t for teams in pools.values() for t in teams]
    # rules in order: eligible, place in pool, points/match, goal diff/match, goals/match
    flat.sort(key=lambda t: (not t["eligible"], t["elig_place"] or 99, -t["ppm"], -t["gdpm"], -t["gfpm"]))
    for i, t in enumerate(flat, 1):
        t["rank"] = i
        t["promotes"] = t["eligible"] and i <= PROMOTE
    return flat


def num(x, sign=False):
    """Format a number the Danish way (decimal comma)."""
    return (f"{x:+.2f}" if sign else f"{x:.2f}").replace(".", ",")


COLS = [("K", "Kampe"), ("P", "Point"), ("P/K", "Point pr. kamp"), ("MF/K", "Målforskel pr. kamp"), ("M/K", "Mål pr. kamp")]


HIST = pathlib.Path("history.json")  # remembers the last two rankings, so arrows can be shown


def apply_history(teams):
    """Set t["move"]: places gained (+) or lost (-) since the standings last changed."""
    now = {f'{t["pool"]}|{t["team"]}': t["rank"] for t in teams}
    fingerprint = repr(sorted((t["pool"], t["team"], t["place"], t["played"], t["points"], t["gf"], t["ga"], t["noshow"])
                              for t in teams))
    try:
        h = json.loads(HIST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        h = {}
    if h.get("fp") != fingerprint:  # new results: the old ranking becomes the one we compare with
        h = {"fp": fingerprint, "previous": h.get("current", {}), "current": now}
        HIST.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")
    for t in teams:
        old = h.get("previous", {}).get(f'{t["pool"]}|{t["team"]}')
        t["move"] = None if old is None else old - t["rank"]  # positive = moved up


CSS = """
:root{color-scheme:dark;--bg:#070d13;--panel:#0c1a26;--line:#14222e;--hd:#0e1a24;--fg:#fff;--mute:#8b99a6;--up:#3ddc84;--down:#ff5a65;--bd:#1c2a37;--bup:#1d4ea8;--bout:#a3281f;--blue:#6b9bff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.in{max-width:44rem;margin:0 auto;padding-bottom:3rem}
.hero{background:var(--panel);padding:1.25rem 1rem 1.1rem}
.kick{margin:0 0 .35rem;font-size:.75rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}
h1{font-size:2rem;line-height:1.1;font-weight:800;margin:0}
.sub{margin:.5rem 0 0;color:var(--mute);font-size:.9rem;max-width:52ch}
h2{margin:1.5rem 1rem .15rem;font-size:.8rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}
.note{margin:.15rem 1rem .6rem;font-size:.8rem;color:var(--mute);max-width:56ch}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-variant-numeric:tabular-nums}
.c-rk{width:3.4rem}.c-n{width:3.4rem}
th{background:var(--hd);color:var(--mute);font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;text-align:center;padding:.65rem 0}
th.tm{text-align:left;padding-left:.25rem}
td{text-align:center;padding:.7rem 0;font-size:1rem;border-bottom:1px solid var(--line)}
.key{font-weight:800}
.bd{display:inline-block;min-width:2rem;padding:.2rem .35rem;border-radius:.5rem;background:var(--bd);font-weight:700;font-size:.95rem;line-height:1.2}
.up .bd{background:var(--bup)} .out .bd{background:var(--bout)}
.mv{display:block;margin-top:.15rem;font-size:.65rem;font-style:normal;font-weight:700;color:var(--mute)}
.mv.u{color:var(--up)} .mv.d{color:var(--down)}
.tm{text-align:left;padding-left:.25rem}
.tm b{display:block;font-weight:600;overflow-wrap:anywhere}
.tm small{display:block;font-size:.72rem;color:var(--mute)}
.out .tm b{color:var(--mute)}
.line td{text-align:left;padding:.35rem 1rem;background:var(--hd);color:var(--blue);font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;border-bottom:0}
.foot{margin:1.5rem 1rem 0}
"""

def arrow(m):
    """Small arrow under the rank number: up, down or unchanged."""
    if m is None:
        return ""  # no earlier ranking to compare with
    if m == 0:
        return '<i class="mv" title="Uændret">–</i>'
    word = "plads" if abs(m) == 1 else "pladser"
    if m > 0:
        return f'<i class="mv u" title="Op {m} {word}">▲{m}</i>'
    return f'<i class="mv d" title="Ned {-m} {word}">▼{-m}</i>'


def group(teams):
    """One standings table. Classes p and g switch between the points and the goals columns."""
    head = ('<tr><th>#</th><th class="tm">Hold</th><th title="Kampe">K</th>'
            '<th title="Point">P</th><th class="key" title="Point pr. kamp">P/K</th></tr>')
    rows = []
    for t in teams:
        cls = "up" if t["promotes"] else ("out" if not t["eligible"] else "")
        ep = t["elig_place"]
        if not t["eligible"]:
            sub = f'{t["pool"]}, nr. {t["place"]}, udeblivelse'
        elif ep != t["place"]:
            sub = f'{t["pool"]}, nr. {t["place"]} (regnes som nr. {ep})'
        else:
            sub = f'{t["pool"]}, nr. {t["place"]}'
        rows.append(
            f'<tr class="{cls}"><td><span class="bd">{t["rank"]}</span>{arrow(t.get("move"))}</td>'
            f'<td class="tm"><b>{html.escape(t["team"])}</b><small>{sub}</small></td>'
            f'<td>{t["played"]}</td><td>{t["points"]}</td><td class="key">{num(t["ppm"])}</td></tr>'
        )
        if t["rank"] == PROMOTE:  # the promotion line
            rows.append('<tr class="line"><td colspan="5">Grænse for oprykning</td></tr>')
    cols = '<col class="c-rk"><col>' + '<col class="c-n">' * 3
    return f'<table><colgroup>{cols}</colgroup>{head}{"".join(rows)}</table>'


def render(teams):
    """Return the finished HTML page as text."""
    winners = [t for t in teams if t["elig_place"] == 1]
    rest = [t for t in teams if t["elig_place"] != 1]  # the 2nds first, then everyone else
    slots = PROMOTE - len(winners)  # places left for the 2nds
    sections = [
        ("Puljevindere", "Nr. 1 i hver pulje rykker op.", winners),
        ("De bedste 2'ere", f"De {slots} bedste 2'ere rykker op. Under linjen står de øvrige hold, og hold med udeblivelse står nederst.", rest),
    ]
    body = "".join(f'<h2>{h}</h2><p class="note">{n}</p>{group(ts)}' for h, n, ts in sections if ts)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%d-%m-%Y kl. %H:%M UTC")
    return f"""<!doctype html>
<html lang="da"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0c1a26">
<title>Hvem rykker op? - Herre Senior 4 7:7</title>
<style>{CSS}</style></head><body><div class="in">
<div class="hero"><p class="kick">Herre Senior 4 7:7 Efterår</p><h1>Hvem rykker op?</h1>
<p class="sub">De {PROMOTE} bedste oprykningsberettigede hold på tværs af {len(POOLS)} puljer rykker op. Opdateret {now}.</p></div>
{body}
<p class="note foot"><b>K</b> kampe, <b>P</b> point, <b>P/K</b> point pr. kamp. Blåt rangnummer: rykker op. Rødt: kan ikke rykke op på grund af udeblivelse. ▲▼ viser flytning i placering siden stillingen sidst ændrede sig.</p>
<p class="note">Kilde: dbu.dk. Næste hold i puljen rykker en plads op, når et hold har udeblivelse.</p>
</div></body></html>"""


def main():
    pools = {}
    for name, url in POOLS.items():
        pools[name] = read_pool(url)
        time.sleep(2)  # be gentle with DBU's server
    out = pathlib.Path("site")
    out.mkdir(exist_ok=True)
    teams = rank_all(pools)
    apply_history(teams)
    (out / "index.html").write_text(render(teams), encoding="utf-8")
    print("Wrote site/index.html with", sum(len(v) for v in pools.values()), "teams")


if __name__ == "__main__":
    main()
