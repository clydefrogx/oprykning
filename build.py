"""Builds the cross-pool dashboard for Herre Senior 4 7:7 Efterår.

Run:      python build.py
Output:   site/index.html  (open it in a browser)
Needs:    pip install requests beautifulsoup4
"""
import datetime
import html
import pathlib
import re
import shutil
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Pool pages P1..P8 have consecutive numbers 496331..496338
POOLS = {f"P{i}": f"https://www.dbu.dk/resultater/pulje/{496330 + i}/" for i in range(1, 9)}
PROMOTE = 12  # the 12 best eligible teams move up
MY_TEAM = "Union 9"  # marked with a dot in the tables
SITE_URL = "https://clydefrogx.github.io/oprykning/"  # share previews need the full address
ASSETS = pathlib.Path("assets")  # icons, share image and manifest, copied into site/
TITLE = "Hvem rykker op? - Herre Senior 4 7:7"
DESC = f"Stillingen lige nu i Herre Senior 4 7:7 Efterår. Hvis sæsonen sluttede i dag, ville disse {PROMOTE} hold rykke op. Opdateres hver dag kl. 03:00."


# One slow or failing answer from dbu.dk should not cost us the whole nightly update:
# try again up to 4 times, waiting longer each time (also for dropped connections)
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "dbu-dashboard (student project)"
_retry = HTTPAdapter(max_retries=Retry(total=4, backoff_factor=3, status_forcelist=(429, 500, 502, 503, 504)))
SESSION.mount("https://", _retry)
SESSION.mount("http://", _retry)


def read_pool(url):
    """Read one pool page and return a list of teams (one dict per team)."""
    r = SESSION.get(url, timeout=30)
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


def today_dk():
    """Today's date in Denmark as dd-mm-yyyy (UTC date if the time zone data is missing, e.g. on Windows)."""
    try:
        now = datetime.datetime.now(ZoneInfo("Europe/Copenhagen"))
    except ZoneInfoNotFoundError:
        now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%d-%m-%Y")


def num(x, sign=False):
    """Format a number the Danish way (decimal comma)."""
    return (f"{x:+.2f}" if sign else f"{x:.2f}").replace(".", ",")


CSS = """
:root{color-scheme:dark;--bg:#060b11;--panel:#0d1925;--panel2:#112133;--line:#172636;--bd:#1f3042;--fg:#f4f7fa;--mute:#adb9c5;--bup:#2563d6;--bupd:#1d4ea8;--ring:#6b7886;--blue:#7aa5ff;--gold:#ffc83d}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(70rem 26rem at 50% -8rem,rgba(37,99,214,.3),transparent 70%) no-repeat,var(--bg);color:var(--fg);font:16px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.in{max-width:46rem;margin:0 auto;padding:0 .75rem 3rem}
.hero{padding:1.75rem .25rem 0}
.hero+h2{margin-top:.69rem}
.kick{display:inline-block;margin:0 0 .8rem;padding:.3rem .75rem;border-radius:2rem;background:rgba(122,165,255,.12);border:1px solid rgba(122,165,255,.3);font-size:.8rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--blue)}
h1{font-size:2.5rem;line-height:1.05;font-weight:800;letter-spacing:-.02em;margin:0}
.sub{margin:.75rem 0 0;color:var(--mute);font-size:1.05rem;max-width:44ch}
.sub+.sub{margin-top:.8rem}
h2{display:flex;align-items:center;gap:.6rem;margin:1.75rem .25rem .2rem;font-size:1.2rem;font-weight:800}
h2 span{padding:.15rem .65rem;border-radius:2rem;background:var(--bupd);font-size:.78rem;font-weight:700;letter-spacing:.04em}
.note{margin:.2rem .25rem .8rem;font-size:.92rem;color:var(--mute);max-width:56ch}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:1rem;overflow:hidden;box-shadow:0 .5rem 1.5rem rgba(0,0,0,.35)}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-variant-numeric:tabular-nums}
.c-rk{width:3.2rem}.c-n{width:2.8rem}.c-s{width:.65rem}
th{background:var(--panel2);color:var(--mute);font-size:.8rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;text-align:center;padding:.7rem 0;border-bottom:1px solid var(--bd)}
td{text-align:center;vertical-align:middle;padding:.75rem 0;font-size:.875rem;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
th:first-child,td.rk{text-align:left;padding-left:calc(.8rem + .22rem)}  /* .22rem = the blue bar */
.tm{text-align:left;padding-left:.25rem}
.tm b{display:block;font-size:.875rem;font-weight:650;line-height:1.3}
.tm small{display:block;font-size:.8rem;color:var(--mute)}
.dot{display:inline-block;width:.6rem;height:.6rem;margin-left:.45rem;border-radius:50%;background:var(--gold);box-shadow:0 0 0 .18rem rgba(255,200,61,.25)}
.bd{display:inline-block;min-width:1.9rem;padding:.15rem .3rem;border-radius:.6rem;background:var(--bd);font-weight:700;font-size:.95rem;line-height:1.2;text-align:center}
.b-up,.up .bd{background:var(--bup)}
.b-out,.out .bd{background:transparent;color:var(--mute);box-shadow:inset 0 0 0 1.5px var(--ring)}
.up{background:linear-gradient(90deg,rgba(37,99,214,.16),transparent 70%)}
.up td.rk{box-shadow:inset .22rem 0 0 var(--bup)}
.out .tm b{color:var(--mute)}
.legend{margin-top:2rem;padding:1rem 1.1rem;background:var(--panel);border:1px solid var(--bd);border-radius:1rem;font-size:.92rem;color:var(--mute)}
.legend p{margin:.45rem 0}
.legend b{color:var(--fg)}
.legend .dot{margin:0 .6rem 0 .1rem}
.sw{display:inline-block;width:.9rem;height:.9rem;margin-right:.5rem;border-radius:.3rem;vertical-align:-.1rem}
.src{margin:.3rem .25rem 0;font-size:.85rem;color:var(--mute)}
.legend+.src{margin-top:1rem}
@media(max-width:26rem){.in{padding-left:.5rem;padding-right:.5rem}}
@media(min-width:40rem){.in{padding:0 1rem 4rem}h1{font-size:3rem}.c-rk{width:4rem}.c-n{width:4.2rem}.c-s{width:.8rem}}
"""

def group(teams):
    """One standings card: a header row and one row per team."""
    head = ('<tr><th>#</th><th class="tm">Hold</th><th title="Kampe">K</th>'
            '<th title="Point">P</th>'
            '<th title="Pointgennemsnit: point pr. kamp">P/K</th>'
            '<th title="Målgennemsnit: målforskel pr. registreret kamp">MF/K</th><th></th></tr>')
    rows = []
    for t in teams:
        cls = "up" if t["promotes"] else ("out" if not t["eligible"] else "")
        dot = '<span class="dot" title="Dit hold"></span>' if t["team"] == MY_TEAM else ""
        ep = t["elig_place"]
        if not t["eligible"]:
            sub = f'{t["pool"]}, nr. {t["place"]}, udeblivelse'
        elif ep != t["place"]:
            sub = f'{t["pool"]}, nr. {t["place"]} (nr. {ep})'
        else:
            sub = f'{t["pool"]}, nr. {t["place"]}'
        rows.append(  # one row per team, everything centred vertically
            f'<tr class="{cls}"><td class="rk"><span class="bd">{t["rank"]}</span></td>'
            f'<td class="tm"><b>{html.escape(t["team"])}{dot}</b><small>{sub}</small></td>'
            f'<td>{t["played"]}</td><td>{t["points"]}</td>'
            f'<td>{num(t["ppm"])}</td><td>{num(t["gdpm"], sign=True)}</td><td></td></tr>'
        )
    cols = '<col class="c-rk"><col>' + '<col class="c-n">' * 2 + '<col class="c-n">' * 2 + '<col class="c-s">'
    return f'<div class="card"><table><colgroup>{cols}</colgroup>{head}{"".join(rows)}</table></div>'


def render(teams):
    """Return the finished HTML page as text."""
    winners = [t for t in teams if t["elig_place"] == 1]
    seconds = [t for t in teams if t["elig_place"] != 1 and t["rank"] <= PROMOTE]  # the best 2nds, who move up
    rest = [t for t in teams if t["elig_place"] != 1 and t["rank"] > PROMOTE]  # everyone below the line, no-shows last
    slots = PROMOTE - len(winners)  # places left for the 2nds
    sections = [
        ("Puljevindere", f"{len(winners)} pladser", "Nr. 1 i hver pulje rykker op.", winners),
        ("De bedste 2'ere", f"{slots} pladser", f"De {slots} bedste 2'ere rykker op.", seconds),
        ("Resten", f"{len(rest)} hold", "Disse hold rykker ikke op. Hold med udeblivelse står nederst.", rest),
    ]
    body = "".join(f'<h2>{h}<span>{b}</span></h2><p class="note">{n}</p>{group(ts)}' for h, b, n, ts in sections if ts)
    return f"""<!doctype html>
<html lang="da"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#060b11">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="manifest" href="manifest.webmanifest">
<meta property="og:type" content="website"><meta property="og:locale" content="da_DK">
<meta property="og:title" content="{TITLE}"><meta property="og:description" content="{DESC}">
<meta property="og:url" content="{SITE_URL}"><meta property="og:image" content="{SITE_URL}og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}</style></head><body><div class="in">
<div class="hero"><p class="kick">Herre Senior 4 7:7 Efterår</p><h1>Hvem rykker op?</h1>
<p class="sub">Stillingen lige nu. Hvis sæsonen sluttede i dag, ville disse {PROMOTE} hold rykke op.</p>
<p class="sub">Opdateres hver dag kl. 03:00</p></div>
{body}
<div class="legend">
<p><b>K</b> kampe</p>
<p><b>P</b> point</p>
<p><b>P/K</b> pointgennemsnit (point pr. kamp)</p>
<p><b>MF/K</b> målgennemsnit (målforskel pr. registreret kamp)</p>
<p><span class="sw b-up"></span>Rykker op</p>
<p><span class="sw b-out"></span>Kan ikke rykke op (udeblivelse)</p>
<p><b>(nr. x)</b> placering når hold med udeblivelse ikke tælles med</p>
<p><span class="dot"></span>{html.escape(MY_TEAM)} er dit hold</p>
<p>Næste hold i puljen rykker en plads op, når et hold er udeblevet.</p>
</div>
<p class="src">Kilde: dbu.dk.</p>
<p class="src">Opdateret {today_dk()}</p>
</div></body></html>"""


def main():
    pools = {}
    for name, url in POOLS.items():
        pools[name] = read_pool(url)
        time.sleep(2)  # be gentle with DBU's server
    out = pathlib.Path("site")
    out.mkdir(exist_ok=True)
    shutil.copytree(ASSETS, out, dirs_exist_ok=True)  # icons, share image, manifest
    teams = rank_all(pools)
    (out / "index.html").write_text(render(teams), encoding="utf-8")
    print("Wrote site/index.html with", sum(len(v) for v in pools.values()), "teams")


if __name__ == "__main__":
    main()
