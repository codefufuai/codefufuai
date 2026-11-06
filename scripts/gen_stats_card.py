#!/usr/bin/env python3
"""Generate assets/stats{,-zh}-{dark,light}.svg — codefufuai's gh stats card.

Same terminal-card language as gen_codefufuai_card.py (which this imports
for its geometry helpers, palette and boot CSS — set g.C, then compose).
The entrance is the family boot sequence: header → stat blocks → chart
label → bars sweeping in left-to-right → footer, staggered
animation-delay, steps(1) reveal; the bars grow from the baseline
(.dbar, in-family with the operator's stats rig); the only infinite
animation is the blinking block cursor. prefers-reduced-motion collapses
everything to its final frame.

Data discipline: numbers are baked at generation time, never invented.
  data/contribs.json — GraphQL contributionCalendar (refresh_cards.py)
  data/stats.json    — {"prs_opened": N} from the search API
  data/user.json     — REST /users/codefufuai profile facts
                       (public_repos, followers; optional, card degrades
                       gracefully without it)
The window is her account age, not a fixed 365d — she is new on shift.
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_codefufuai_card as g  # noqa: E402

# profile-local time (the wall rolls at profile-local midnight, Beijing) —
# "day N of shift" and the chart window anchor here, not CI's UTC clock
CST = timezone(timedelta(hours=8))

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = g.OUT

W = 960
PAD = 20
PLOT_X0, PLOT_X1 = PAD, W - PAD

STR = {
    "en": dict(
        aria="codefufuai GitHub stats card, baked from live API data",
        cmd="gh api graphql", cap="rest v3 + graphql · since 2026-10-31",
        header="@codefufuai · {repos} public repos · {followers} followers · operator @Acfufu",
        ok1="created {created} · day {days} of shift · {active} active days · best run {best}d",
        blocks=("CONTRIBUTIONS", "ACTIVE DAYS", "STREAK", "PULL REQS", "REPOS"),
        subs=("calendar total", "of {span}d", "best run", "awaiting first ask", "{forks} forks + home"),
        chart="CONTRIBUTIONS · LAST {span} DAYS",
        foot="[ OK ] busiest {pkd} · {pk} contributions · PRs opened {prs} · regen daily by CI",
    ),
    "zh": dict(
        aria="codefufuai GitHub 统计卡，数据烤自线上 API",
        cmd="gh api graphql", cap="rest v3 + graphql · 自 2026-10-31",
        header="@codefufuai · {repos} 个公开仓库 · {followers} 关注者 · 操作员 @Acfufu",
        ok1="创建于 {created} · 在岗第 {days} 天 · {active} 个活跃日 · 最长连击 {best} 天",
        blocks=("贡献", "活跃日", "连续", "PR", "仓库"),
        subs=("日历总计", "/ {span} 天", "最长一段", "等待第一个任务", "{forks} 个 fork + 本体"),
        chart="贡献 · 近 {span} 天",
        foot="[ OK ] 峰值 {pkd} · {pk} 次贡献 · 已开 PR {prs} · CI 每日重烤",
    ),
}


def load():
    cal = json.loads((DATA / "contribs.json").read_text())["data"]["user"]
    cc = cal["contributionsCollection"]
    days = {}
    for wk in cc["contributionCalendar"]["weeks"]:
        for d in wk["contributionDays"]:
            days[date.fromisoformat(d["date"][:10])] = d["contributionCount"]
    # The GraphQL calendar is a fixed one-year window, most of it before her
    # account existed (and a few stale days after the snapshot). The card is
    # about her shift, so window everything to created → min(today, last day
    # the snapshot actually covers). Unknown in-window days count as 0; CI
    # re-bakes nightly and fills them in.
    created = date.fromisoformat(cal["createdAt"][:10])
    today = datetime.now(CST).date()
    win_end = min(today, max(days))
    wdays = {created + timedelta(n): days.get(created + timedelta(n), 0)
             for n in range((win_end - created).days + 1)}
    ds = sorted(wdays)
    best = cur = 0
    for dt in ds:  # longest consecutive nonzero run inside the window
        cur = cur + 1 if wdays[dt] > 0 else 0
        best = max(best, cur)
    pk_day = max(wdays, key=wdays.get)
    st = dict(
        created=cal["createdAt"][:10],
        today=today,
        total=sum(wdays.values()),
        active=sum(1 for v in wdays.values() if v > 0),
        best=best, pk_day=pk_day, pk=max(wdays.values()),
        days=wdays, ds=ds, span=len(wdays),
        prs=json.loads((DATA / "stats.json").read_text())["prs_opened"],
    )
    uj = DATA / "user.json"
    if uj.exists():
        u = json.loads(uj.read_text())
        st["repos"], st["followers"] = u["public_repos"], u["followers"]
        st["forks"] = st["repos"] - 1  # the profile repo is her home
    else:
        st["repos"], st["followers"], st["forks"] = None, None, None
    return st


def stats_css():
    return f"""
    .slab {{ font-size:11px; fill:{g.C["green"]}; font-weight:600; letter-spacing:2; opacity:0; animation:on .01s steps(1) forwards; }}
    .stlab {{ font-size:10.5px; fill:{g.C["dim"]}; opacity:0; animation:on .01s steps(1) forwards; }}
    .clab {{ font-size:11px; fill:{g.C["dim"]}; font-weight:600; letter-spacing:2; opacity:0; animation:on .01s steps(1) forwards; }}
    .alab {{ font-size:9.5px; fill:{g.C["dim"]}; opacity:0; animation:on .01s steps(1) forwards; }}
    .dbar {{ transform-box:fill-box; transform-origin:center bottom; animation:grow .4s ease-out backwards; }}
    .roll {{ opacity:0; animation:fin2 .5s ease-out 1.15s forwards; }}
    @keyframes grow  {{ from {{ transform:scaleY(0); }} }}
    @keyframes fin2  {{ to {{ opacity:1; }} }}
    @media (prefers-reduced-motion: reduce) {{
      .dbar, .roll {{ animation:none; }} .roll {{ opacity:1; }}
      .slab, .stlab, .clab, .alab {{ opacity:1; }}
    }}
    """


def stats_card(theme, zh=False):
    g.C = g.LIGHT if theme == "light" else g.DARK
    C = g.C
    T = STR["zh"] if zh else STR["en"]
    st = load()
    if st["repos"] is None:
        T = dict(T)
        T["header"] = "@codefufuai · operator @Acfufu"
        T["blocks"], T["subs"] = T["blocks"][:4], T["subs"][:4]
    baked = datetime.now().strftime("%H:%M")
    H = 344

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
         f'role="img" aria-label="{g.esc(T["aria"])}">',
         f"<style>{g.font_face_css() + g.build_css() + stats_css()}</style>"]

    y = 2
    g.card_rect(s, y, H - 4)
    g.titlebar(s, y, T["cmd"], T["cap"])

    hdr = T["header"].format(repos=st["repos"], followers=st["followers"])
    s.append(f'<text class="liv fin" style="animation-delay:.05s" x="{PAD}" y="{y + 64}">'
             f'[LIVE] <tspan fill="{C["title"]}" font-weight="700">{g.esc(hdr)}</tspan></text>')
    ok1 = T["ok1"].format(created=st["created"],
                          days=(st["today"] - date.fromisoformat(st["created"])).days + 1,
                          active=st["active"], best=st["best"])
    s.append(f'<text class="ok" style="animation-delay:.18s" x="{PAD}" y="{y + 86}">'
             f'{g.esc(ok1)}</text>')

    # ---- stat blocks: the family 5-column rhythm ----
    centers = (128, 304, 480, 656, 832)
    vals = [str(st["total"]), str(st["active"]), f'{st["best"]}d' if not zh else f'{st["best"]}天',
            str(st["prs"]), str(st["repos"])]
    prs_sub = T["subs"][3] if st["prs"] == 0 else ("first ask answered" if not zh else "第一个任务已交差")
    subs = [T["subs"][0],
            T["subs"][1].format(span=st["span"]), T["subs"][2], prs_sub,
            T["subs"][4].format(forks=st["forks"])] if st["repos"] is not None else list(T["subs"])[:4]
    for k, (lab, val, sub) in enumerate(zip(T["blocks"], vals, subs)):
        cx = centers[k]
        s.append(f'<text class="slab" style="animation-delay:{.28 + k * .07:.2f}s" '
                 f'x="{cx}" y="{y + 120}" text-anchor="middle">{g.esc(lab)}</text>')
        s.append(f'<text class="fin" style="animation-delay:{.32 + k * .07:.2f}s" '
                 f'x="{cx}" y="{y + 154}" text-anchor="middle" font-size="26" '
                 f'font-weight="700" fill="{C["title"]}">{g.esc(val)}</text>')
        s.append(f'<text class="stlab" style="animation-delay:{.36 + k * .07:.2f}s" '
                 f'x="{cx}" y="{y + 173}" text-anchor="middle">{g.esc(sub)}</text>')

    # ---- chart: daily bars, grown in left-to-right; peak day called out ----
    days, ds = st["days"], st["ds"]
    start, span = ds[0], (ds[-1] - ds[0]).days or 1
    s.append(f'<text class="clab" style="animation-delay:.6s" x="{PAD}" y="{y + 208}">'
             f'{g.esc(T["chart"].format(span=st["span"]))}</text>')
    top, bot = y + 222, y + 294
    vmax = st["pk"] or 1
    for frac in (0.5,):
        yy = bot - (bot - top) * frac
        s.append(f'<line x1="{PLOT_X0}" y1="{yy:.1f}" x2="{PLOT_X1}" y2="{yy:.1f}" '
                 f'stroke="{C["dim"]}" stroke-width="1" opacity="0.18"/>')
    s.append(f'<line x1="{PLOT_X0}" y1="{bot}" x2="{PLOT_X1}" y2="{bot}" '
             f'stroke="{C["border"]}" stroke-width="1"/>')

    CW = PLOT_X1 - PLOT_X0
    bw = min(CW / span * 0.72, 34)
    for i, dt in enumerate(ds):
        v = days[dt]
        h = (v / vmax) * (bot - top)
        x = PLOT_X0 + (dt - start).days / span * CW
        fill = C["ok"] if dt == st["pk_day"] else "url(#gsg)"
        s.append(f'<rect class="dbar" x="{x - bw / 2:.1f}" y="{bot - h:.1f}" '
                 f'width="{bw:.1f}" height="{max(h, 0.5):.1f}" fill="{fill}" '
                 f'style="animation-delay:{700 + i * 40}ms"/>')
        s.append(f'<text class="alab" style="animation-delay:{700 + i * 40}ms" '
                 f'x="{x:.1f}" y="{bot + 15}" text-anchor="middle">'
                 f'{g.esc(f"{dt.month}/{dt.day}")}</text>')
    s.insert(2, f'<defs><linearGradient id="gsg" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="{C["user"]}" stop-opacity="0.5"/>'
                f'<stop offset="1" stop-color="{C["user"]}" stop-opacity="0.08"/></linearGradient></defs>')

    xp = PLOT_X0 + (st["pk_day"] - start).days / span * CW
    yp = bot - st["pk"] / vmax * (bot - top)
    pkd, pk = st["pk_day"], st["pk"]
    pk_lbl = f"{pkd.month}/{pkd.day} · {pk}"
    # label sits beside the dot, never above — a full-height peak would
    # otherwise collide with the chart title; clear the bar's own half-width
    anchor = "end" if xp > PLOT_X1 - 90 else "start"
    lxx = xp - max(9, bw / 2 + 6) if anchor == "end" else xp + max(9, bw / 2 + 6)
    s.append(f'<circle class="roll" cx="{xp:.1f}" cy="{yp:.1f}" r="4" fill="{C["ok"]}" '
             f'stroke="{C["card"]}" stroke-width="2"/>')
    s.append(f'<text class="roll" x="{lxx:.1f}" y="{yp + 3.5:.1f}" font-size="10" font-weight="600" '
             f'fill="{C["desc"]}" text-anchor="{anchor}">{g.esc(pk_lbl)}</text>')

    # ---- footer + the one infinite animation (blinking cursor, fixed slot) ----
    foot = T["foot"].format(pkd=f'{st["pk_day"].month}/{st["pk_day"].day}',
                            pk=st["pk"], prs=st["prs"])
    s.append(f'<text class="ok" style="animation-delay:1.3s" x="{PAD}" y="{y + 326}">'
             f'{g.esc(foot)}</text>')
    s.append(f'<rect class="cur" x="{W - PAD - 7.5}" y="{y + 313}" width="7.5" height="14" '
             f'fill="{C["green"]}"/>')
    s.append("</svg>")
    return "\n".join(s)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=None, help="override assets dir")
    a = ap.parse_args()
    out = a.out_dir or OUT
    out.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        for zh in (False, True):
            name = f"stats-zh-{theme}.svg" if zh else f"stats-{theme}.svg"
            p = (out / name).resolve()
            p.write_text(stats_card(theme, zh))
            print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
