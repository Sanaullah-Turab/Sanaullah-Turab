import json, os, sys, urllib.request
from datetime import date, datetime, timedelta

token = os.environ["GH_TOKEN"]
user = os.environ.get("GH_USER") or os.environ["GITHUB_REPOSITORY_OWNER"]
out = sys.argv[1] if len(sys.argv) > 1 else "dist/streak.svg"
mock = os.environ.get("MOCK_DAYS")


def gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)["data"]["user"]


def load_days():
    if mock:
        return json.load(open(mock))
    created = gql(f'{{user(login:"{user}"){{createdAt}}}}')["createdAt"]
    start = datetime.fromisoformat(created.replace("Z", "+00:00")).year
    days = {}
    for y in range(start, date.today().year + 1):
        q = f'''{{user(login:"{user}"){{contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{y}-12-31T23:59:59Z"){{contributionCalendar{{weeks{{contributionDays{{date contributionCount}}}}}}}}}}}}'''
        weeks = gql(q)["contributionsCollection"]["contributionCalendar"]["weeks"]
        for w in weeks:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    return days


days = load_days()
today = date.today()
dates = sorted(d for d in days if date.fromisoformat(d) <= today)
total = sum(days[d] for d in dates)
first = date.fromisoformat(next(d for d in dates if days[d] > 0))

longest = cur = 0
best_start = run_start = None
prev = None
for d in dates:
    dd = date.fromisoformat(d)
    if days[d] > 0:
        if prev is not None and (dd - prev).days == 1 and cur > 0:
            cur += 1
        else:
            cur = 1
            run_start = dd
        if cur > longest:
            longest, best_start = cur, run_start
        prev = dd
    else:
        cur = 0
        prev = None

streak = 0
d = today
if days.get(d.isoformat(), 0) == 0:
    d -= timedelta(days=1)
s_end = d
while days.get(d.isoformat(), 0) > 0:
    streak += 1
    d -= timedelta(days=1)
s_start = d + timedelta(days=1)


def fmt(a, b):
    return f"{a.strftime('%b %d').replace(' 0', ' ')} - {b.strftime('%b %d').replace(' 0', ' ')}"


cols = [
    (f"{total:,}", "Total contributions", f"{first.strftime('%b %Y')} - Present"),
    (str(streak), "Current streak", fmt(s_start, s_end) if streak else "Start one today"),
    (str(longest), "Longest streak", fmt(best_start, best_start + timedelta(days=longest - 1)) if longest else ""),
]

W, H = 760, 190
cw = W / 3
import math
R = 42
circ = 2 * math.pi * R
frac = min(1.0, streak / longest) if longest else 0
last = [days.get((today - timedelta(days=29 - i)).isoformat(), 0) for i in range(30)]
peak = max(max(last), 1)
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contribution streak">',
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2A1B11"/><stop offset="1" stop-color="#5A3518"/></linearGradient></defs>',
    '<style>.n{font:700 38px "Segoe UI",Ubuntu,sans-serif;fill:#F28C28}.l{font:600 15px "Segoe UI",Ubuntu,sans-serif;fill:#FFF1E3}.s{font:400 13px "Segoe UI",Ubuntu,sans-serif;fill:#D9B596}'
    '@keyframes up{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}.c{animation:up .7s ease both}'
    f'@keyframes ring{{from{{stroke-dashoffset:{circ:.2f}}}to{{stroke-dashoffset:{circ*(1-frac):.2f}}}}}.r{{stroke-dasharray:{circ:.2f};animation:ring 1.6s ease-out both}}'
    '@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}.b{transform-box:fill-box;transform-origin:bottom;animation:grow .8s ease-out both}</style>',
    f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="url(#g)" stroke="#C66E26" stroke-opacity=".55"/>',
]
bw = (W - 56) / 30
for i, v in enumerate(last):
    h = 3 + 11 * v / peak
    parts.append(f'<rect class="b" style="animation-delay:{i*0.02:.2f}s" x="{28+i*bw+2:.1f}" y="{H-12-h:.1f}" width="{bw-4:.1f}" height="{h:.1f}" rx="2" fill="#F28C28" fill-opacity="{0.25 if v==0 else 0.55}"/>')
for i, (n, label, sub) in enumerate(cols):
    cx = cw * i + cw / 2
    if i == 1:
        parts.append(f'<circle cx="{cx}" cy="64" r="{R}" fill="none" stroke="#4A2D17" stroke-width="4"/><circle class="r" cx="{cx}" cy="64" r="{R}" fill="none" stroke="#F28C28" stroke-width="4" stroke-linecap="round" transform="rotate(-90 {cx} {64})"/>')
    parts.append(f'<g class="c" style="animation-delay:{i*0.15}s" text-anchor="middle"><text class="n" x="{cx}" y="77">{n}</text><text class="l" x="{cx}" y="128">{label}</text><text class="s" x="{cx}" y="148">{sub}</text></g>')
    if i:
        parts.append(f'<line x1="{cw*i}" y1="28" x2="{cw*i}" y2="150" stroke="#C66E26" stroke-opacity=".4"/>')
parts.append("</svg>")
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
open(out, "w").write("".join(parts))