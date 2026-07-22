#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WM 2026 – OPTIMIERER 3. SPIELTAG  (mit Tabellenstand, xG-Dominanz & Quoten)
===========================================================================

Stand: nach dem 2. Spieltag (Gruppen K und L spielen MD2 erst am 23./24.06.,
diese vier Spiele sind unten als offen markiert).

Pipeline (wie gehabt):
  1. Markt-Anker aus Titelquoten leicht einmischen (Blend 25 %).
  2. xG-basiertes Rating-Update aus ALLEN gespielten Ergebnissen
     (perf = 0,35*Tordiff + 0,65*xG-Diff; sonst reine Tordiff; gedaempft).
  3. Aktuellen Tabellenstand je Gruppe ausgeben.
  4. Punktoptimale Tipps fuer den 3. Spieltag + Margin-Analyse.

Punkteregel: Sieg 2/3/4, Unentschieden 2/-/4 (neutraler Platz).
"""

import math
from collections import defaultdict

# ===========================================================================
# Parameter
# ===========================================================================
ETA, CAP = 0.8, 2.5
W_GOALS, W_XG = 0.35, 0.65
BLEND_ODDS = 0.25
PTS_WIN_TENDENCY, PTS_WIN_GOALDIFF, PTS_WIN_EXACT = 2, 3, 4
PTS_DRAW_TEND, PTS_DRAW_EXACT = 2, 4
MAX_GOALS = 8

# ===========================================================================
# Stammdaten
# ===========================================================================
GROUPS = {
    "A": ["Mexiko", "Suedafrika", "Suedkorea", "Tschechien"],
    "B": ["Kanada", "Bosnien-H.", "Katar", "Schweiz"],
    "C": ["Brasilien", "Marokko", "Haiti", "Schottland"],
    "D": ["USA", "Paraguay", "Australien", "Tuerkei"],
    "E": ["Deutschland", "Curacao", "Elfenbeinkueste", "Ecuador"],
    "F": ["Niederlande", "Japan", "Schweden", "Tunesien"],
    "G": ["Belgien", "Aegypten", "Iran", "Neuseeland"],
    "H": ["Spanien", "Kap Verde", "Saudi-Arabien", "Uruguay"],
    "I": ["Frankreich", "Senegal", "Irak", "Norwegen"],
    "J": ["Argentinien", "Algerien", "Oesterreich", "Jordanien"],
    "K": ["Portugal", "DR Kongo", "Usbekistan", "Kolumbien"],
    "L": ["England", "Kroatien", "Ghana", "Panama"],
}

BASE = {
    "Spanien": 95, "Frankreich": 94, "Argentinien": 93, "England": 92,
    "Brasilien": 91, "Portugal": 91, "Niederlande": 88, "Deutschland": 87,
    "Belgien": 86, "Kroatien": 85, "Marokko": 85, "Kolumbien": 84,
    "Uruguay": 84, "Senegal": 83, "Norwegen": 83, "Schweiz": 82,
    "Japan": 81, "USA": 81, "Mexiko": 81, "Schweden": 80, "Ecuador": 79,
    "Oesterreich": 79, "Tuerkei": 79, "Aegypten": 77, "Suedkorea": 77,
    "Elfenbeinkueste": 78, "Iran": 76, "Algerien": 76, "Australien": 76,
    "Kanada": 77, "Bosnien-H.": 75, "Schottland": 75, "Tschechien": 76,
    "Paraguay": 74, "Tunesien": 74, "Ghana": 74, "DR Kongo": 73,
    "Saudi-Arabien": 72, "Usbekistan": 72, "Suedafrika": 72, "Katar": 71,
    "Panama": 72, "Kap Verde": 70, "Irak": 70, "Jordanien": 69,
    "Neuseeland": 68, "Haiti": 66, "Curacao": 64,
}
FORM = {
    "Elfenbeinkueste": +3.0, "Frankreich": -1.5, "Spanien": -1.0,
    "Irak": +2.0, "Norwegen": +1.5, "Schweden": -1.0, "Iran": +1.0,
    "Panama": +1.0, "Mexiko": +1.5, "USA": +1.0, "Kanada": +1.0,
}
RATING = {t: BASE[t] + FORM.get(t, 0.0) for g in GROUPS.values() for t in g}
HOME_BONUS = {"Mexiko": 4, "USA": 4, "Kanada": 4}

MARKET_ODDS = {
    "Frankreich": 5.6, "Spanien": 7.0, "England": 9.5, "Argentinien": 11.0,
    "Brasilien": 12.0, "Portugal": 13.0, "Deutschland": 13.0,
    "Niederlande": 21.0, "Belgien": 26.0, "Kroatien": 34.0, "Uruguay": 34.0,
    "Kolumbien": 41.0, "Marokko": 41.0, "Norwegen": 51.0,
}

# ===========================================================================
# ERGEBNISSE  (1. + 2. Spieltag).  Optional xG: (a,b,xg_a,xg_b).
# ===========================================================================
ERGEBNISSE = {
    # ---------- 1. Spieltag ----------
    ("Mexiko", "Suedafrika"): (2, 0),
    ("Suedkorea", "Tschechien"): (2, 1),
    ("Kanada", "Bosnien-H."): (1, 1, 2.4, 0.7),
    ("Katar", "Schweiz"): (1, 1, 0.8, 1.9),
    ("Schottland", "Haiti"): (1, 0),
    ("Brasilien", "Marokko"): (1, 1, 1.9, 1.2),
    ("USA", "Paraguay"): (4, 1),
    ("Australien", "Tuerkei"): (2, 0),
    ("Elfenbeinkueste", "Ecuador"): (1, 0),
    ("Deutschland", "Curacao"): (7, 1, 4.4, 0.9),
    ("Niederlande", "Japan"): (2, 2, 1.9, 1.5),
    ("Schweden", "Tunesien"): (5, 1),
    ("Belgien", "Aegypten"): (1, 1, 1.9, 1.0),
    ("Iran", "Neuseeland"): (2, 2),
    ("Spanien", "Kap Verde"): (0, 0, 2.6, 0.3),
    ("Saudi-Arabien", "Uruguay"): (1, 1),
    ("Frankreich", "Senegal"): (3, 1),
    ("Irak", "Norwegen"): (1, 4),
    ("Argentinien", "Algerien"): (3, 0),
    ("Oesterreich", "Jordanien"): (3, 1),
    ("Portugal", "DR Kongo"): (1, 1, 2.2, 0.8),
    ("Usbekistan", "Kolumbien"): (1, 3),
    ("England", "Kroatien"): (4, 2),
    ("Ghana", "Panama"): (1, 0),
    # ---------- 2. Spieltag ----------
    ("Tschechien", "Suedafrika"): (1, 1),
    ("Mexiko", "Suedkorea"): (1, 0),
    ("Schweiz", "Bosnien-H."): (4, 1),
    ("Kanada", "Katar"): (6, 0),                 # Dominanz bestaetigt
    ("Schottland", "Marokko"): (0, 1),
    ("Brasilien", "Haiti"): (3, 0),
    ("USA", "Australien"): (2, 0),
    ("Tuerkei", "Paraguay"): (0, 1),
    ("Deutschland", "Elfenbeinkueste"): (2, 1),  # spaeter Undav-Treffer
    ("Ecuador", "Curacao"): (0, 0),
    ("Niederlande", "Schweden"): (5, 1),
    ("Tunesien", "Japan"): (0, 4),
    ("Belgien", "Iran"): (0, 0, 1.8, 0.5),       # Belgien dominant, Iran mauert
    ("Neuseeland", "Aegypten"): (1, 3),
    ("Spanien", "Saudi-Arabien"): (4, 0),
    ("Uruguay", "Kap Verde"): (2, 2),            # Uruguay laesst erneut Federn
    ("Frankreich", "Irak"): (3, 0),
    ("Norwegen", "Senegal"): (3, 2),
    ("Argentinien", "Oesterreich"): (2, 0),
    ("Jordanien", "Algerien"): (1, 2),
    # ---------- 2. Spieltag Gruppen K & L: noch offen (23./24.06.) ----------
    # ("Portugal", "Usbekistan"): (?, ?),
    # ("Kolumbien", "DR Kongo"): (?, ?),
    # ("England", "Ghana"): (?, ?),
    # ("Panama", "Kroatien"): (?, ?),
}

# ===========================================================================
# >>> 3. SPIELTAG – die dritten Spiele jeder Mannschaft <<<
# ===========================================================================
MD3_FIXTURES = [
    ("A", "Tschechien", "Mexiko"),
    ("A", "Suedafrika", "Suedkorea"),
    ("B", "Schweiz", "Kanada"),
    ("B", "Bosnien-H.", "Katar"),
    ("C", "Schottland", "Brasilien"),
    ("C", "Marokko", "Haiti"),
    ("D", "Tuerkei", "USA"),
    ("D", "Paraguay", "Australien"),
    ("E", "Ecuador", "Deutschland"),
    ("E", "Curacao", "Elfenbeinkueste"),
    ("F", "Tunesien", "Niederlande"),
    ("F", "Japan", "Schweden"),
    ("G", "Neuseeland", "Belgien"),
    ("G", "Aegypten", "Iran"),
    ("H", "Kap Verde", "Saudi-Arabien"),
    ("H", "Uruguay", "Spanien"),
    ("I", "Norwegen", "Frankreich"),
    ("I", "Senegal", "Irak"),
    ("J", "Algerien", "Oesterreich"),
    ("J", "Jordanien", "Argentinien"),
    ("K", "Kolumbien", "Portugal"),
    ("K", "DR Kongo", "Usbekistan"),
    ("L", "Panama", "England"),
    ("L", "Kroatien", "Ghana"),
]


def expected_goals(r_team, r_opp):
    diff = (r_team - r_opp) / 100.0
    return max(0.18, min(1.35 * (10 ** (diff * 0.9)), 4.2))


# ===========================================================================
# Markt-Anker
# ===========================================================================
def apply_market_anchor(blend=BLEND_ODDS, verbose=True):
    if blend <= 0 or not MARKET_ODDS:
        return
    raw = {t: 1.0 / o for t, o in MARKET_ODDS.items()}
    s = sum(raw.values())
    impl = {t: raw[t] / s for t in raw}
    lo = math.log(min(impl.values()) / (1 - min(impl.values())))
    hi = math.log(max(impl.values()) / (1 - max(impl.values())))
    rlo, rhi = 80.0, 96.0
    for t, p in impl.items():
        lod = math.log(p / (1 - p))
        r_market = rlo + (lod - lo) / (hi - lo) * (rhi - rlo)
        RATING[t] = (1 - blend) * RATING[t] + blend * r_market
    if verbose:
        print("Markt-Anker (Titelquoten, Blend 25 %) angewendet.\n")


# ===========================================================================
# xG-basiertes Rating-Update
# ===========================================================================
def update_ratings(results, verbose=True):
    snapshot = dict(RATING)
    deltas = defaultdict(float)

    def exp_diff(a, b):
        ra = snapshot[a] + HOME_BONUS.get(a, 0)
        rb = snapshot[b] + HOME_BONUS.get(b, 0)
        return expected_goals(ra, rb) - expected_goals(rb, ra)

    for (a, b), val in results.items():
        if len(val) == 4:
            ga, gb, xa, xb = val
            perf = W_GOALS * (ga - gb) + W_XG * (xa - xb)
        else:
            ga, gb = val
            perf = ga - gb
        d = max(-CAP, min(CAP, ETA * (perf - exp_diff(a, b))))
        deltas[a] += d
        deltas[b] -= d
    for t, d in deltas.items():
        RATING[t] += d

    if verbose:
        print("=" * 74)
        print("  RATING nach 2 Spieltagen (Top/Flop-Veraenderungen ggü. Start)")
        print("=" * 74)
        start = {t: BASE[t] + FORM.get(t, 0.0) for t in RATING}
        ch = sorted(RATING, key=lambda t: RATING[t] - start[t], reverse=True)
        for t in ch[:6] + ["..."] + ch[-6:]:
            if t == "...":
                print("   ...")
                continue
            print(f"   {t:<16} {start[t]:6.1f} -> {RATING[t]:6.1f}  ({RATING[t]-start[t]:+.1f})")
        print()


# ===========================================================================
# Tabellenstand
# ===========================================================================
def standings():
    tbl = {t: dict(sp=0, s=0, u=0, n=0, gf=0, ga=0, pkt=0)
           for g in GROUPS.values() for t in g}
    for (a, b), val in ERGEBNISSE.items():
        ga, gb = val[0], val[1]
        for t, f, ag in ((a, ga, gb), (b, gb, ga)):
            tbl[t]["sp"] += 1; tbl[t]["gf"] += f; tbl[t]["ga"] += ag
        if ga > gb:
            tbl[a]["s"] += 1; tbl[a]["pkt"] += 3; tbl[b]["n"] += 1
        elif gb > ga:
            tbl[b]["s"] += 1; tbl[b]["pkt"] += 3; tbl[a]["n"] += 1
        else:
            tbl[a]["u"] += 1; tbl[b]["u"] += 1; tbl[a]["pkt"] += 1; tbl[b]["pkt"] += 1
    return tbl


def print_standings():
    tbl = standings()
    print("=" * 74)
    print("  TABELLENSTAND (nach 2 Spieltagen; K & L erst 1 Spiel)")
    print("=" * 74)
    for g, teams in GROUPS.items():
        ranked = sorted(teams, key=lambda t: (tbl[t]["pkt"],
                        tbl[t]["gf"] - tbl[t]["ga"], tbl[t]["gf"]), reverse=True)
        print(f"\nGruppe {g}   {'Sp':>3}{'S':>3}{'U':>3}{'N':>3}{'Tore':>8}{'Pkt':>5}")
        for pos, t in enumerate(ranked, 1):
            s = tbl[t]
            print(f"  {pos}. {t:<15}{s['sp']:>3}{s['s']:>3}{s['u']:>3}{s['n']:>3}"
                  f"{f'{s['gf']}:{s['ga']}':>8}{s['pkt']:>5}")
    print()


# ===========================================================================
# Tipp-Optimierer + Margin-Analyse
# ===========================================================================
def poisson_pmf(lam):
    p = [math.exp(-lam)]
    for k in range(1, MAX_GOALS + 1):
        p.append(p[-1] * lam / k)
    return p


def points(tip, res):
    th, ta = tip; h, a = res
    if (th, ta) == (h, a):
        return PTS_DRAW_EXACT if h == a else PTS_WIN_EXACT
    if th == ta and h == a:
        return PTS_DRAW_TEND
    if (th > ta and h > a) or (th < ta and h < a):
        return PTS_WIN_GOALDIFF if th - ta == h - a else PTS_WIN_TENDENCY
    return 0


def _matrix(a, b):
    ra = RATING[a] + HOME_BONUS.get(a, 0)
    rb = RATING[b] + HOME_BONUS.get(b, 0)
    pa, pb = poisson_pmf(expected_goals(ra, rb)), poisson_pmf(expected_goals(rb, ra))
    return [[pa[h] * pb[x] for x in range(MAX_GOALS + 1)] for h in range(MAX_GOALS + 1)]


def _ep(tip, P):
    return sum(P[h][x] * points(tip, (h, x))
               for h in range(MAX_GOALS + 1) for x in range(MAX_GOALS + 1))


def optimal_tip(a, b):
    P = _matrix(a, b)
    best, best_ep = None, -1
    for th in range(6):
        for ta in range(6):
            ep = _ep((th, ta), P)
            if ep > best_ep:
                best, best_ep = (th, ta), ep
    pw = sum(P[h][x] for h in range(MAX_GOALS + 1) for x in range(MAX_GOALS + 1) if h > x)
    pd = sum(P[h][h] for h in range(MAX_GOALS + 1))
    return best, best_ep, pw, pd, 1 - pw - pd


def md2_complete(g):
    """True, wenn fuer beide Teams jeder Gruppe schon 2 Spiele vorliegen."""
    tbl = standings()
    return all(tbl[t]["sp"] >= 2 for t in GROUPS[g])


def print_md3_tips():
    print("=" * 74)
    print("  TIPPS 3. SPIELTAG  (Regel Sieg 2/3/4, Remis 2/-/4)")
    print("=" * 74)
    print(f"{'Gr':<3}{'Spiel':<34}{'TIPP':>6}{'E[Pkt]':>8}{'P(1/X/2) %':>14}")
    print("-" * 74)
    for g, a, b in MD3_FIXTURES:
        tip, ep, pw, pd, pl = optimal_tip(a, b)
        flag = "" if md2_complete(g) else "  * (MD2 offen)"
        print(f"{g:<3}{a+' - '+b:<34}{tip[0]}:{tip[1]:<3}{ep:>7.2f}"
              f"{100*pw:>6.0f}/{100*pd:>2.0f}/{100*pl:>2.0f}{flag}")
    print()


def print_margin_analysis():
    rows = []
    for g, a, b in MD3_FIXTURES:
        P = _matrix(a, b)
        pA = sum(P[h][x] for h in range(MAX_GOALS+1) for x in range(MAX_GOALS+1) if h > x)
        pB = sum(P[h][x] for h in range(MAX_GOALS+1) for x in range(MAX_GOALS+1) if x > h)
        fav = a if pA >= pB else b

        def margin(d):
            return sum(P[h][x] for h in range(MAX_GOALS+1) for x in range(MAX_GOALS+1)
                       if (h - x == d if fav == a else x - h == d))

        p1 = margin(1)
        p2p = sum(margin(d) for d in range(2, MAX_GOALS + 1))
        e10 = _ep((1, 0) if fav == a else (0, 1), P)
        e20 = _ep((2, 0) if fav == a else (0, 2), P)
        e21 = _ep((2, 1) if fav == a else (1, 2), P)
        rows.append((g, fav, a if fav == b else b, p1 + p2p, p1, p2p, e10, e20, e21))
    rows.sort(key=lambda r: r[5], reverse=True)
    print("=" * 86)
    print("  MARGIN-ANALYSE  (sortiert nach Wahrscheinlichkeit fuer 2+ Tore)")
    print("=" * 86)
    print(f"{'Gr':<3}{'Favorit -> Underdog':<30}{'P(Sieg)':>8}{'P(+1)':>7}{'P(>=2)':>8}"
          f"   {'E[1:0]':>7}{'E[2:0]':>7}{'E[2:1]':>7}")
    print("-" * 86)
    for g, fav, dog, pwin, p1, p2p, e10, e20, e21 in rows:
        up = " <= 2:0 fast gratis" if (e10 - e20) < 0.03 and p2p > 0.35 else ""
        print(f"{g:<3}{fav+' -> '+dog:<30}{100*pwin:>7.0f}%{100*p1:>6.0f}%{100*p2p:>7.0f}%"
              f"   {e10:>7.2f}{e20:>7.2f}{e21:>7.2f}{up}")
    print()


if __name__ == "__main__":
    apply_market_anchor()
    update_ratings(ERGEBNISSE)
    print_standings()
    print_md3_tips()
    print_margin_analysis()
