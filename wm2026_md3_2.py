#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WM 2026 – OPTIMIERER 3. SPIELTAG  v2  (mit 1X2-Matchquoten)
===========================================================

NEU gegenueber v1:
  * Komplette MD1+MD2-Ergebnisse (alle 48 Spiele) sind eingetragen.
  * 1X2-MATCHQUOTEN: Fuer einzelne Spiele koennen die echten
    Sieg/Remis/Niederlage-Quoten hinterlegt werden. Daraus werden die
    erwarteten Tore (lambda) DIREKT kalibriert, statt sie aus dem
    Rating-Modell abzuleiten. Wo keine Matchquote vorliegt, faellt das
    Modell automatisch auf das ratingbasierte lambda zurueck.

Hintergrund (Schweiz-Kanada): Das ratingbasierte Modell sah Kanada nach
dem 6:0 gegen Katar minimal vorne (Katar-Sieg nicht gegnergewichtet). Die
Buchmacher hatten die Schweiz klar als Favorit (~2,40 ggü. 3,20). Mit der
Matchquoten-Kalibrierung uebernimmt das Modell die Marktmeinung.

Kalibrierung:
  1. Quoten -> implizite W'keiten, Buchmachermarge herausgerechnet (devig).
  2. Numerische Suche nach (lambda_Heim, lambda_Gast), deren Poisson-Modell
     diese 1X2-W'keiten reproduziert.
  3. Diese lambda werden im Tipp-Optimierer verwendet (Blend BLEND_MATCH).
"""

import math
from collections import defaultdict

ETA, CAP = 0.8, 2.5
W_GOALS, W_XG = 0.35, 0.65
BLEND_ODDS = 0.25
BLEND_MATCH = 0.85
PTS_WIN_TENDENCY, PTS_WIN_GOALDIFF, PTS_WIN_EXACT = 2, 3, 4
PTS_DRAW_TEND, PTS_DRAW_EXACT = 2, 4
MAX_GOALS = 8

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

# 1X2-Matchquoten je Spiel: (Heim, Gast): (Q_Heim, Q_X, Q_Gast)
MATCH_ODDS = {
    ("Schweiz", "Kanada"): (2.40, 3.00, 3.20),
    # weitere MD3-Spiele aus der App nachtragen:
    # ("Tschechien", "Mexiko"): (oh, od, oa),
}

ERGEBNISSE = {
    # 1. Spieltag
    ("Mexiko", "Suedafrika"): (2, 0), ("Suedkorea", "Tschechien"): (2, 1),
    ("Kanada", "Bosnien-H."): (1, 1, 2.4, 0.7), ("Katar", "Schweiz"): (1, 1, 0.8, 1.9),
    ("Schottland", "Haiti"): (1, 0), ("Brasilien", "Marokko"): (1, 1, 1.9, 1.2),
    ("USA", "Paraguay"): (4, 1), ("Australien", "Tuerkei"): (2, 0),
    ("Elfenbeinkueste", "Ecuador"): (1, 0), ("Deutschland", "Curacao"): (7, 1, 4.4, 0.9),
    ("Niederlande", "Japan"): (2, 2, 1.9, 1.5), ("Schweden", "Tunesien"): (5, 1),
    ("Belgien", "Aegypten"): (1, 1, 1.9, 1.0), ("Iran", "Neuseeland"): (2, 2),
    ("Spanien", "Kap Verde"): (0, 0, 2.6, 0.3), ("Saudi-Arabien", "Uruguay"): (1, 1),
    ("Frankreich", "Senegal"): (3, 1), ("Irak", "Norwegen"): (1, 4),
    ("Argentinien", "Algerien"): (3, 0), ("Oesterreich", "Jordanien"): (3, 1),
    ("Portugal", "DR Kongo"): (1, 1, 2.2, 0.8), ("Usbekistan", "Kolumbien"): (1, 3),
    ("England", "Kroatien"): (4, 2), ("Ghana", "Panama"): (1, 0),
    # 2. Spieltag
    ("Tschechien", "Suedafrika"): (1, 1), ("Mexiko", "Suedkorea"): (1, 0),
    ("Schweiz", "Bosnien-H."): (4, 1), ("Kanada", "Katar"): (6, 0),
    ("Schottland", "Marokko"): (0, 1), ("Brasilien", "Haiti"): (3, 0),
    ("USA", "Australien"): (2, 0), ("Tuerkei", "Paraguay"): (0, 1),
    ("Deutschland", "Elfenbeinkueste"): (2, 1), ("Ecuador", "Curacao"): (0, 0),
    ("Niederlande", "Schweden"): (5, 1), ("Tunesien", "Japan"): (0, 4),
    ("Belgien", "Iran"): (0, 0, 1.8, 0.5), ("Neuseeland", "Aegypten"): (1, 3),
    ("Spanien", "Saudi-Arabien"): (4, 0), ("Uruguay", "Kap Verde"): (2, 2),
    ("Frankreich", "Irak"): (3, 0), ("Norwegen", "Senegal"): (3, 2),
    ("Argentinien", "Oesterreich"): (2, 0), ("Jordanien", "Algerien"): (1, 2),
    ("Portugal", "Usbekistan"): (5, 0), ("England", "Ghana"): (0, 0),
    ("Panama", "Kroatien"): (0, 1), ("Kolumbien", "DR Kongo"): (1, 0),
}

MD3_FIXTURES = [
    ("A", "Tschechien", "Mexiko"), ("A", "Suedafrika", "Suedkorea"),
    ("B", "Schweiz", "Kanada"), ("B", "Bosnien-H.", "Katar"),
    ("C", "Schottland", "Brasilien"), ("C", "Marokko", "Haiti"),
    ("D", "Tuerkei", "USA"), ("D", "Paraguay", "Australien"),
    ("E", "Ecuador", "Deutschland"), ("E", "Curacao", "Elfenbeinkueste"),
    ("F", "Tunesien", "Niederlande"), ("F", "Japan", "Schweden"),
    ("G", "Neuseeland", "Belgien"), ("G", "Aegypten", "Iran"),
    ("H", "Kap Verde", "Saudi-Arabien"), ("H", "Uruguay", "Spanien"),
    ("I", "Norwegen", "Frankreich"), ("I", "Senegal", "Irak"),
    ("J", "Algerien", "Oesterreich"), ("J", "Jordanien", "Argentinien"),
    ("K", "Kolumbien", "Portugal"), ("K", "DR Kongo", "Usbekistan"),
    ("L", "Panama", "England"), ("L", "Kroatien", "Ghana"),
]


def expected_goals(r_team, r_opp):
    diff = (r_team - r_opp) / 100.0
    return max(0.18, min(1.35 * (10 ** (diff * 0.9)), 4.2))


def poisson_pmf(lam):
    p = [math.exp(-lam)]
    for k in range(1, MAX_GOALS + 1):
        p.append(p[-1] * lam / k)
    return p


def apply_market_anchor(blend=BLEND_ODDS):
    if blend <= 0 or not MARKET_ODDS:
        return
    raw = {t: 1.0 / o for t, o in MARKET_ODDS.items()}
    s = sum(raw.values())
    impl = {t: raw[t] / s for t in raw}
    lo = math.log(min(impl.values()) / (1 - min(impl.values())))
    hi = math.log(max(impl.values()) / (1 - max(impl.values())))
    for t, p in impl.items():
        lod = math.log(p / (1 - p))
        r_market = 80.0 + (lod - lo) / (hi - lo) * 16.0
        RATING[t] = (1 - blend) * RATING[t] + blend * r_market


def update_ratings(results):
    snap = dict(RATING)
    d = defaultdict(float)

    def exp_diff(a, b):
        ra, rb = snap[a] + HOME_BONUS.get(a, 0), snap[b] + HOME_BONUS.get(b, 0)
        return expected_goals(ra, rb) - expected_goals(rb, ra)

    for (a, b), val in results.items():
        if len(val) == 4:
            ga, gb, xa, xb = val
            perf = W_GOALS * (ga - gb) + W_XG * (xa - xb)
        else:
            ga, gb = val
            perf = ga - gb
        delta = max(-CAP, min(CAP, ETA * (perf - exp_diff(a, b))))
        d[a] += delta
        d[b] -= delta
    for t in d:
        RATING[t] += d[t]


def _poisson_1x2(la, lb):
    pa, pb = poisson_pmf(la), poisson_pmf(lb)
    ph = pd = pw = 0.0
    for h in range(MAX_GOALS + 1):
        for x in range(MAX_GOALS + 1):
            p = pa[h] * pb[x]
            if h > x:
                ph += p
            elif h == x:
                pd += p
            else:
                pw += p
    return ph, pd, pw


_ODDS_CACHE = {}


def lambdas_from_odds(oh, od, oa):
    key = (oh, od, oa)
    if key in _ODDS_CACHE:
        return _ODDS_CACHE[key]
    inv = [1 / oh, 1 / od, 1 / oa]
    s = sum(inv)
    th, td, ta = inv[0] / s, inv[1] / s, inv[2] / s
    best = None
    rng = [x / 20 for x in range(4, 71)]
    for la in rng:
        for lb in rng:
            ph, pd, pw = _poisson_1x2(la, lb)
            err = (ph - th) ** 2 + (pd - td) ** 2 + (pw - ta) ** 2
            if best is None or err < best[0]:
                best = (err, la, lb)
    _ODDS_CACHE[key] = (best[1], best[2])
    return best[1], best[2]


def match_lambdas(a, b):
    ra, rb = RATING[a] + HOME_BONUS.get(a, 0), RATING[b] + HOME_BONUS.get(b, 0)
    la_r, lb_r = expected_goals(ra, rb), expected_goals(rb, ra)
    if (a, b) in MATCH_ODDS:
        la_o, lb_o = lambdas_from_odds(*MATCH_ODDS[(a, b)])
        return (BLEND_MATCH * la_o + (1 - BLEND_MATCH) * la_r,
                BLEND_MATCH * lb_o + (1 - BLEND_MATCH) * lb_r, True)
    return la_r, lb_r, False


def standings():
    tbl = {t: dict(sp=0, pkt=0, gf=0, ga=0) for g in GROUPS.values() for t in g}
    for (a, b), val in ERGEBNISSE.items():
        ga, gb = val[0], val[1]
        for t, f, ag in ((a, ga, gb), (b, gb, ga)):
            tbl[t]["sp"] += 1; tbl[t]["gf"] += f; tbl[t]["ga"] += ag
        if ga > gb:
            tbl[a]["pkt"] += 3
        elif gb > ga:
            tbl[b]["pkt"] += 3
        else:
            tbl[a]["pkt"] += 1; tbl[b]["pkt"] += 1
    return tbl


def print_standings():
    tbl = standings()
    print("=" * 70)
    print("  TABELLENSTAND nach 2 Spieltagen (komplett)")
    print("=" * 70)
    for g, teams in GROUPS.items():
        ranked = sorted(teams, key=lambda t: (tbl[t]["pkt"],
                        tbl[t]["gf"] - tbl[t]["ga"], tbl[t]["gf"]), reverse=True)
        line = "  ".join(f"{i+1}.{t}({tbl[t]['pkt']})" for i, t in enumerate(ranked))
        print(f"  {g}: {line}")
    print()


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
    la, lb, _ = match_lambdas(a, b)
    pa, pb = poisson_pmf(la), poisson_pmf(lb)
    return [[pa[h] * pb[x] for x in range(MAX_GOALS + 1)] for h in range(MAX_GOALS + 1)]


def _ep(tip, P):
    return sum(P[h][x] * points(tip, (h, x))
               for h in range(MAX_GOALS + 1) for x in range(MAX_GOALS + 1))


def optimal_tip(a, b):
    P = _matrix(a, b)
    best, bep = None, -1
    for th in range(6):
        for ta in range(6):
            ep = _ep((th, ta), P)
            if ep > bep:
                best, bep = (th, ta), ep
    pw = sum(P[h][x] for h in range(MAX_GOALS+1) for x in range(MAX_GOALS+1) if h > x)
    pd = sum(P[h][h] for h in range(MAX_GOALS + 1))
    return best, bep, pw, pd, 1 - pw - pd


def print_md3_tips():
    print("=" * 76)
    print("  TIPPS 3. SPIELTAG")
    print("=" * 76)
    print(f"{'Gr':<3}{'Spiel':<34}{'TIPP':>6}{'E[Pkt]':>8}{'P(1/X/2) %':>14}  Quelle")
    print("-" * 76)
    for g, a, b in MD3_FIXTURES:
        tip, ep, pw, pd, pl = optimal_tip(a, b)
        src = "QUOTE" if (a, b) in MATCH_ODDS else "Rating"
        print(f"{g:<3}{a+' - '+b:<34}{tip[0]}:{tip[1]:<3}{ep:>7.2f}"
              f"{100*pw:>6.0f}/{100*pd:>2.0f}/{100*pl:>2.0f}   {src}")
    print()


if __name__ == "__main__":
    apply_market_anchor()
    update_ratings(ERGEBNISSE)
    print_standings()
    la_r, lb_r, _ = match_lambdas("Schweiz", "Kanada")  # vor Quoten-Blend zeigen
    ra = RATING["Schweiz"]; rb = RATING["Kanada"] + HOME_BONUS["Kanada"]
    pure_r = (expected_goals(ra, rb), expected_goals(rb, ra))
    lo, loo = lambdas_from_odds(2.40, 3.00, 3.20)
    print(f"  Schweiz-Kanada:  lambda(nur Rating)={pure_r[0]:.2f}:{pure_r[1]:.2f}  ->  "
          f"lambda(aus Quote)={lo:.2f}:{loo:.2f}\n")
    print_md3_tips()
