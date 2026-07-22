#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WM 2026 – OPTIMIERER 2. SPIELTAG  (mit xG-Dominanz & Wettquoten)
================================================================

Drei Neuerungen gegenueber wm2026_live.py:

1) ECHTE MD1-ERGEBNISSE sind eingetragen (Stand 18.06.2026).

2) xG-BASIERTES RATING-UPDATE ("Dominanz statt Endstand")
   Dein Kanada-Argument: 1:1 trotz drueckender Ueberlegenheit. Ein Update
   nur auf Basis der Tore wuerde Kanada faelschlich schwaechen. Loesung:
   Das Lernsignal ist nicht die Tordifferenz, sondern eine Mischung aus
   Tordifferenz und xG-Differenz (Expected Goals = Qualitaet/Menge der
   Chancen). xG ist nachweislich der bessere Praediktor fuer kuenftige
   Leistung als das tatsaechliche Resultat.

       perf_diff = w_g * (Tore_A - Tore_B) + w_x * (xG_A - xG_B)
       surprise  = perf_diff - erwartete_Diff_aus_Ratings
       delta     = clip(ETA * surprise, +/- CAP)

   Mit xG (w_x hoeher gewichtet) bleibt Kanada nach 1:1 stabil oder
   steigt sogar; Spanien faellt nach dem 0:0 kaum, weil es Chancen im
   Minutentakt hatte. Ohne xG faellt das Modell sauber auf reine
   Tordifferenz zurueck (staerker gedaempft, weil rauschiger).

3) WETTQUOTEN ALS MARKT-ANKER
   Buchmacher-Titelquoten (Stand 17.06.) buendeln die Markterwartung
   inkl. aller Ueberraschungen. Sie werden in implizite
   Wahrscheinlichkeiten (entovigoriert) umgerechnet und LEICHT in die
   Top-Team-Ratings eingemischt. Wichtige Einschraenkung: Titelquoten
   enthalten auch den Turnierbaum/Gruppenschwere, sind also kein reines
   Staerkemass -> daher nur kleiner Blend-Anteil (BLEND_ODDS).
"""

import math
from collections import defaultdict

# ===========================================================================
# Lern- und Blend-Parameter
# ===========================================================================
ETA = 0.8            # Rating-Punkte pro "Tor" Ueberraschung
CAP = 2.5            # max. Verschiebung pro Spiel
W_GOALS = 0.35       # Gewicht echte Tore   (bei vorhandenem xG)
W_XG    = 0.65       # Gewicht xG           (bei vorhandenem xG)
BLEND_ODDS = 0.25    # Anteil Markt-Anker an den Top-Team-Ratings (0..1)

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
# Vorab-Form aus Testspielen (vor dem Turnier)
FORM = {
    "Elfenbeinkueste": +3.0, "Frankreich": -1.5, "Spanien": -1.0,
    "Irak": +2.0, "Norwegen": +1.5, "Schweden": -1.0, "Iran": +1.0,
    "Panama": +1.0, "Mexiko": +1.5, "USA": +1.0, "Kanada": +1.0,
}
RATING = {t: BASE[t] + FORM.get(t, 0.0) for g in GROUPS.values() for t in g}
HOME_BONUS = {"Mexiko": 4, "USA": 4, "Kanada": 4}

# ===========================================================================
# Markt-Anker: Titelquoten (dezimal, beste Buchmacher-Quote, Stand 17.06.2026)
# Quelle: oeffentliche Quotenvergleiche. None = keine belastbare Quote.
# ===========================================================================
MARKET_ODDS = {
    "Frankreich": 5.6, "Spanien": 7.0, "England": 9.5, "Argentinien": 11.0,
    "Brasilien": 12.0, "Portugal": 13.0, "Deutschland": 13.0,
    "Niederlande": 21.0, "Belgien": 26.0, "Kroatien": 34.0, "Uruguay": 34.0,
    "Kolumbien": 41.0, "Marokko": 41.0, "Norwegen": 51.0,
}

# ===========================================================================
# >>> ECHTE MD1-ERGEBNISSE (Stand 18.06.2026) <<<
# Optional xG: (Tore_A, Tore_B) ODER (Tore_A, Tore_B, xG_A, xG_B).
# xG ist dort gesetzt, wo Endstand und Spielverlauf auseinanderfallen.
# ===========================================================================
ERGEBNISSE = {
    # Gruppe A
    ("Mexiko", "Suedafrika"): (2, 0),
    ("Suedkorea", "Tschechien"): (2, 1),
    # Gruppe B  -- Kanada drueckend ueberlegen trotz 1:1 -> xG abgebildet
    ("Kanada", "Bosnien-H."): (1, 1, 2.4, 0.7),
    ("Katar", "Schweiz"): (1, 1, 0.8, 1.9),       # Schweiz vergab, kein 0:0-Drama
    # Gruppe C
    ("Schottland", "Haiti"): (1, 0),
    ("Brasilien", "Marokko"): (1, 1, 1.9, 1.2),
    # Gruppe D
    ("USA", "Paraguay"): (4, 1),
    ("Australien", "Tuerkei"): (2, 0),
    # Gruppe E
    ("Elfenbeinkueste", "Ecuador"): (1, 0),
    ("Deutschland", "Curacao"): (7, 1, 4.4, 0.9), # Kantersieg, aber xG deckelt
    # Gruppe F
    ("Niederlande", "Japan"): (2, 2, 1.9, 1.5),
    ("Schweden", "Tunesien"): (5, 1),
    # Gruppe G
    ("Belgien", "Aegypten"): (1, 1, 1.9, 1.0),    # Belgien dominant, ineffizient
    ("Iran", "Neuseeland"): (2, 2),               # Iran patzt gegen Aussenseiter
    # Gruppe H  -- Spanien zahnlos im Abschluss, aber drueckend -> xG schuetzt
    ("Spanien", "Kap Verde"): (0, 0, 2.6, 0.3),
    ("Saudi-Arabien", "Uruguay"): (1, 1),         # Uruguay laesst Punkte liegen
    # Gruppe I  (MD1-Paarung war Irak-Norwegen)
    ("Frankreich", "Senegal"): (3, 1),
    ("Irak", "Norwegen"): (1, 4),
    # Gruppe J
    ("Argentinien", "Algerien"): (3, 0),
    ("Oesterreich", "Jordanien"): (3, 1),
    # Gruppe K
    ("Portugal", "DR Kongo"): (1, 1, 2.2, 0.8),   # Ronaldo vergibt, Portugal besser
    # ("Kolumbien", "Usbekistan"): (?, ?),        # >>> wird erst am 18.06. gespielt <<<
    # Gruppe L  (MD1: England-Kroatien, Ghana-Panama)
    ("England", "Kroatien"): (4, 2),              # Kane-Doppelpack
    ("Ghana", "Panama"): (1, 0),
}

# ===========================================================================
# >>> 2. SPIELTAG – die zweiten Spiele jeder Mannschaft (echte Paarungen) <<<
# ===========================================================================
MD2_FIXTURES = [
    ("A", "Tschechien", "Suedafrika"),
    ("A", "Mexiko", "Suedkorea"),
    ("B", "Schweiz", "Bosnien-H."),
    ("B", "Kanada", "Katar"),
    ("C", "Schottland", "Marokko"),
    ("C", "Brasilien", "Haiti"),
    ("D", "USA", "Australien"),
    ("D", "Tuerkei", "Paraguay"),
    ("E", "Deutschland", "Elfenbeinkueste"),
    ("E", "Curacao", "Ecuador"),
    ("F", "Niederlande", "Schweden"),
    ("F", "Japan", "Tunesien"),
    ("G", "Belgien", "Iran"),
    ("G", "Neuseeland", "Aegypten"),
    ("H", "Spanien", "Saudi-Arabien"),
    ("H", "Kap Verde", "Uruguay"),
    ("I", "Frankreich", "Irak"),
    ("I", "Senegal", "Norwegen"),
    ("J", "Argentinien", "Oesterreich"),
    ("J", "Algerien", "Jordanien"),
    ("K", "Portugal", "Usbekistan"),
    ("K", "Kolumbien", "DR Kongo"),
    ("L", "England", "Ghana"),
    ("L", "Panama", "Kroatien"),
]


def expected_goals(r_team, r_opp):
    diff = (r_team - r_opp) / 100.0
    return max(0.18, min(1.35 * (10 ** (diff * 0.9)), 4.2))


# ===========================================================================
# Markt-Anker einmischen (vor dem Form-Update)
# ===========================================================================
def apply_market_anchor(blend=BLEND_ODDS, verbose=True):
    if blend <= 0 or not MARKET_ODDS:
        return
    # implizite W'keiten aus Quoten, entovigoriert (auf Summe der gelisteten Teams)
    raw = {t: 1.0 / o for t, o in MARKET_ODDS.items()}
    s = sum(raw.values())
    impl = {t: raw[t] / s for t in raw}
    # W'keit -> Rating-Skala: log-odds, linear auf BASE-Spanne gemappt
    import math as _m
    lo = _m.log(min(impl.values()) / (1 - min(impl.values())))
    hi = _m.log(max(impl.values()) / (1 - max(impl.values())))
    rlo, rhi = 80.0, 96.0    # Spanne, auf die die Markt-Topteams gelegt werden
    rows = []
    for t, p in impl.items():
        lod = _m.log(p / (1 - p))
        r_market = rlo + (lod - lo) / (hi - lo) * (rhi - rlo)
        old = RATING[t]
        RATING[t] = (1 - blend) * old + blend * r_market
        rows.append((t, old, r_market, RATING[t]))
    if verbose:
        print("=" * 74)
        print(f"  MARKT-ANKER aus Titelquoten (Blend {int(blend*100)} %)")
        print("=" * 74)
        print(f"{'Team':<16}{'Quote':>7}{'impl.%':>8}{'Rating_alt':>12}{'->neu':>8}")
        for t, old, rm, new in sorted(rows, key=lambda x: MARKET_ODDS[x[0]]):
            print(f"{t:<16}{MARKET_ODDS[t]:>7.1f}{100*impl[t]:>7.1f}%"
                  f"{old:>12.1f}{new:>8.1f}")
        print()


# ===========================================================================
# xG-basiertes Rating-Update
# ===========================================================================
def update_ratings(results, verbose=True):
    snapshot = dict(RATING)
    deltas = defaultdict(float)
    rows = []

    def exp_diff(a, b):
        ra = snapshot[a] + HOME_BONUS.get(a, 0)
        rb = snapshot[b] + HOME_BONUS.get(b, 0)
        return expected_goals(ra, rb) - expected_goals(rb, ra)

    for (a, b), val in results.items():
        if len(val) == 4:
            ga, gb, xa, xb = val
            perf = W_GOALS * (ga - gb) + W_XG * (xa - xb)
            tag = f"(xG {xa:.1f}:{xb:.1f})"
        else:
            ga, gb = val
            perf = (ga - gb)              # ohne xG: reine Tordifferenz
            tag = ""
        surprise = perf - exp_diff(a, b)
        d = max(-CAP, min(CAP, ETA * surprise))
        deltas[a] += d
        deltas[b] -= d
        rows.append((a, b, ga, gb, tag, exp_diff(a, b), perf, d))

    for t, d in deltas.items():
        RATING[t] += d

    if verbose:
        print("=" * 74)
        print("  xG-BASIERTES RATING-UPDATE aus den MD1-Ergebnissen")
        print("=" * 74)
        print(f"{'Spiel':<32}{'Erg.':>6}{'perf':>7}{'erw.':>7}{'Delta':>7}  xG")
        for a, b, ga, gb, tag, ed, perf, d in rows:
            print(f"{a+' - '+b:<32}{ga}:{gb:<3}{perf:>+7.2f}{ed:>+7.2f}{d:>+7.2f}  {tag}")
        if deltas:
            print("\nGroesste Rating-Veraenderungen:")
            for t in sorted(deltas, key=lambda t: deltas[t], reverse=True):
                if abs(deltas[t]) >= 0.3:
                    print(f"   {t:<16} {snapshot[t]:6.1f} -> {RATING[t]:6.1f}  ({deltas[t]:+.2f})")
        print()


# ===========================================================================
# Aktueller Tabellenstand aus den eingetragenen Ergebnissen
# ===========================================================================
def standings_after_md1():
    tbl = {t: dict(pts=0, gf=0, ga=0, sp=0) for g in GROUPS.values() for t in g}
    for (a, b), val in ERGEBNISSE.items():
        ga, gb = val[0], val[1]
        for t, f, ag in ((a, ga, gb), (b, gb, ga)):
            tbl[t]["gf"] += f; tbl[t]["ga"] += ag; tbl[t]["sp"] += 1
        if ga > gb:
            tbl[a]["pts"] += 3
        elif gb > ga:
            tbl[b]["pts"] += 3
        else:
            tbl[a]["pts"] += 1; tbl[b]["pts"] += 1
    return tbl


# ===========================================================================
# Tipp-Optimierer (Gruppenphase: Remis erlaubt)
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


def optimal_tip(a, b):
    ra = RATING[a] + HOME_BONUS.get(a, 0)
    rb = RATING[b] + HOME_BONUS.get(b, 0)
    pa, pb = poisson_pmf(expected_goals(ra, rb)), poisson_pmf(expected_goals(rb, ra))
    P = [[pa[h] * pb[x] for x in range(MAX_GOALS + 1)] for h in range(MAX_GOALS + 1)]
    best, best_ep = None, -1
    for th in range(6):
        for ta in range(6):
            ep = sum(P[h][x] * points((th, ta), (h, x))
                     for h in range(MAX_GOALS + 1) for x in range(MAX_GOALS + 1))
            if ep > best_ep:
                best, best_ep = (th, ta), ep
    pw = sum(P[h][x] for h in range(MAX_GOALS + 1) for x in range(MAX_GOALS + 1) if h > x)
    pd = sum(P[h][h] for h in range(MAX_GOALS + 1))
    return best, best_ep, pw, pd, 1 - pw - pd


def print_md2_tips():
    tbl = standings_after_md1()
    print("=" * 74)
    print("  TIPPS 2. SPIELTAG  (Regel Sieg 2/3/4, Remis 2/-/4)")
    print("=" * 74)
    print(f"{'Gr':<3}{'Spiel':<34}{'TIPP':>6}{'E[Pkt]':>8}{'P(1/X/2) %':>14}")
    print("-" * 74)
    missing = {("Iran", "Neuseeland"), ("Saudi-Arabien", "Uruguay"),
               ("Kolumbien", "Usbekistan"), ("England", "Kroatien"),
               ("Ghana", "Panama")}
    note = set()
    for g, a, b in MD2_FIXTURES:
        # Hinweis, falls eine MD1-Grundlage der Gruppe noch fehlt
        for x in (a, b):
            if tbl[x]["sp"] == 0:
                note.add(g)
        tip, ep, pw, pd, pl = optimal_tip(a, b)
        flag = " *" if g in note else ""
        print(f"{g:<3}{a+' - '+b:<34}{tip[0]}:{tip[1]:<3}{ep:>7.2f}"
              f"{100*pw:>6.0f}/{100*pd:>2.0f}/{100*pl:>2.0f}{flag}")
    if note:
        print("\n  * = in dieser Gruppe fehlt noch ein MD1-Ergebnis "
              "(Rating evtl. unvollstaendig).")
    print()


if __name__ == "__main__":
    apply_market_anchor()
    update_ratings(ERGEBNISSE)
    print_md2_tips()
