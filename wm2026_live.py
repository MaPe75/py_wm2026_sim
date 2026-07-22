#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WM 2026 – LIVE-UPDATE
=====================

Workflow nach jedem Spieltag:
  1. Echte Ergebnisse unten in ERGEBNISSE eintragen.
  2. Skript ausfuehren.

Das Skript macht dann zwei Dinge:

  A) RATING-UPDATE ("Form lernen")
     Fuer jedes gespielte Spiel wird die Ueberraschung gemessen:
         surprise = (tatsaechliche Tordifferenz) - (erwartete Tordifferenz)
     und das Rating gedaempft angepasst (Elo-Prinzip auf Torbasis):
         delta = clip(ETA * surprise, +/- CAP)
         RATING[A] += delta ; RATING[B] -= delta
     ETA klein halten! Ein Spiel ist Stichprobe n=1. Default: ETA=0.8,
     CAP=2.5 -> selbst ein 0:5-Debakel verschiebt maximal 2.5 Punkte.

  B) ERGEBNIS-FIXIERUNG ("Tabelle einfrieren")
     Die Monte-Carlo-Simulation verwendet fuer bereits gespielte Spiele
     das ECHTE Ergebnis und wuerfelt nur die offenen Spiele. Damit sind
     alle Bonus-Wahrscheinlichkeiten (Gruppensieger, Halbfinale, Titel)
     BEDINGTE Wahrscheinlichkeiten: P(... | bisherige Ergebnisse).

Ausgabe:
  - Rating-Veraenderungen (wer hat ueber-/unterperformt)
  - punktoptimale Tipps fuer alle NOCH OFFENEN Gruppenspiele
  - aktualisierte Bonus-Wahrscheinlichkeiten
"""

import math
import random
from collections import defaultdict

# ===========================================================================
# >>> HIER ECHTE ERGEBNISSE EINTRAGEN <<<
# Schluessel exakt wie in GROUPS geschrieben, Reihenfolge wie im Spielplan.
# Beispiel nach Spieltag 1:
#   ERGEBNISSE = {
#       ("Mexiko", "Suedafrika"): (2, 1),
#       ("Suedkorea", "Tschechien"): (0, 0),
#       ("Deutschland", "Curacao"): (3, 0),
#       ...
#   }
# ===========================================================================
ERGEBNISSE = {
    # ("Mexiko", "Suedafrika"): (2, 1),
}

# ===========================================================================
# >>> K.-o.-SPIELE HIER EINTRAGEN, sobald die Paarungen feststehen <<<
# (Sechzehntelfinale ab 28.06.). Tippregel im K.o.: Ergebnis NACH
# Elfmeterschiessen -> ein Unentschieden ist als Tipp nicht moeglich.
# Beispiel:
#   KO_SPIELE = [("Deutschland", "Norwegen"), ("Frankreich", "Tuerkei")]
# ===========================================================================
KO_SPIELE = []

# Lernparameter fuer das Rating-Update
ETA = 0.8    # Rating-Punkte pro Tor Ueberraschung (klein = traege/robust)
CAP = 2.5    # maximale Verschiebung pro Spiel

# ---------------------------------------------------------------------------
# Punkteregel Tippspiel
# ---------------------------------------------------------------------------
PTS_WIN_TENDENCY, PTS_WIN_GOALDIFF, PTS_WIN_EXACT = 2, 3, 4
PTS_DRAW_TEND, PTS_DRAW_EXACT = 2, 4
MAX_GOALS = 8

# ---------------------------------------------------------------------------
# Modell-Stammdaten
# ---------------------------------------------------------------------------
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
    "Brasilien": 91, "Portugal": 91,
    "Niederlande": 88, "Deutschland": 87, "Belgien": 86, "Kroatien": 85,
    "Marokko": 85,
    "Kolumbien": 84, "Uruguay": 84, "Senegal": 83, "Norwegen": 83,
    "Schweiz": 82, "Japan": 81, "USA": 81, "Mexiko": 81,
    "Ecuador": 79, "Oesterreich": 79, "Australien": 76, "Schweden": 80,
    "Aegypten": 77, "Iran": 76, "Suedkorea": 77, "Elfenbeinkueste": 78,
    "Panama": 72, "Paraguay": 74, "Algerien": 76, "Tuerkei": 79,
    "Tunesien": 74, "Katar": 71, "Saudi-Arabien": 72, "Usbekistan": 72,
    "Kap Verde": 70, "Schottland": 75, "Kanada": 77, "Bosnien-H.": 75,
    "Ghana": 74, "DR Kongo": 73, "Tschechien": 76, "Suedafrika": 72,
    "Irak": 70, "Neuseeland": 68, "Jordanien": 69, "Haiti": 66, "Curacao": 64,
}
FORM = {
    "Elfenbeinkueste": +3.0, "Frankreich": -1.5, "Spanien": -1.0,
    "Irak": +2.0, "Norwegen": +1.5, "Schweden": -1.0, "Iran": +1.0,
    "Panama": +1.0, "Mexiko": +1.5, "USA": +1.0, "Kanada": +1.0,
}
RATING = {t: BASE[t] + FORM.get(t, 0.0) for g in GROUPS.values() for t in g}
HOME_BONUS = {"Mexiko": 4, "USA": 4, "Kanada": 4}
FIXTURE_PATTERN = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]


def expected_goals(r_team, r_opp):
    diff = (r_team - r_opp) / 100.0
    return max(0.18, min(1.35 * (10 ** (diff * 0.9)), 4.2))


def lambdas(a, b):
    ra = RATING[a] + HOME_BONUS.get(a, 0)
    rb = RATING[b] + HOME_BONUS.get(b, 0)
    return expected_goals(ra, rb), expected_goals(rb, ra)


# ===========================================================================
# A) RATING-UPDATE aus echten Ergebnissen
# ===========================================================================
def update_ratings(results, eta=ETA, cap=CAP, verbose=True):
    """Elo-artiges Update auf Torbasis. Nullsumme, gedaempft, gedeckelt."""
    if not results:
        if verbose:
            print(">> Keine Ergebnisse eingetragen - Ratings unveraendert.\n")
        return
    deltas = defaultdict(float)
    rows = []
    # WICHTIG: Erwartung mit den URSPRUENGLICHEN Ratings berechnen,
    # damit die Reihenfolge der Spiele keine Rolle spielt.
    snapshot = dict(RATING)

    def exp_goals_snap(a, b):
        ra = snapshot[a] + HOME_BONUS.get(a, 0)
        rb = snapshot[b] + HOME_BONUS.get(b, 0)
        return expected_goals(ra, rb), expected_goals(rb, ra)

    for (a, b), (ga, gb) in results.items():
        la, lb = exp_goals_snap(a, b)
        surprise = (ga - gb) - (la - lb)
        d = max(-cap, min(cap, eta * surprise))
        deltas[a] += d
        deltas[b] -= d
        rows.append((a, b, ga, gb, la - lb, surprise, d))

    for t, d in deltas.items():
        RATING[t] += d

    if verbose:
        print("=" * 78)
        print("  RATING-UPDATE aus echten Ergebnissen")
        print("=" * 78)
        print(f"{'Spiel':<34}{'Erg.':>6}{'erw.Diff':>9}{'Surpr.':>8}{'Delta':>7}")
        for a, b, ga, gb, ed, s, d in rows:
            print(f"{a+' - '+b:<34}{ga}:{gb:<4}{ed:>+8.2f}{s:>+8.2f}{d:>+7.2f}")
        print("\nNeue Ratings (nur veraenderte Teams):")
        for t in sorted(deltas, key=lambda t: deltas[t], reverse=True):
            print(f"   {t:<18} {snapshot[t]:6.1f} -> {RATING[t]:6.1f}  ({deltas[t]:+.2f})")
        print()


# ===========================================================================
# Tipp-Optimierer (analytisch, nur offene Spiele)
# ===========================================================================
def poisson_pmf(lam):
    p = [math.exp(-lam)]
    for k in range(1, MAX_GOALS + 1):
        p.append(p[-1] * lam / k)
    return p


def points(tip, result):
    th, ta = tip
    h, a = result
    if (th, ta) == (h, a):
        return PTS_DRAW_EXACT if h == a else PTS_WIN_EXACT
    if th == ta and h == a:
        return PTS_DRAW_TEND
    if (th > ta and h > a) or (th < ta and h < a):
        return PTS_WIN_GOALDIFF if th - ta == h - a else PTS_WIN_TENDENCY
    return 0


def optimal_tip(a, b):
    la, lb = lambdas(a, b)
    pa, pb = poisson_pmf(la), poisson_pmf(lb)
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


def optimal_tip_ko(a, b):
    """K.-o.-Modus: gewertet wird das Ergebnis NACH Elfmeterschiessen.

    Ein Remis ist weder als Endstand noch als Tipp moeglich. Modell:
    Remis-Wahrscheinlichkeit nach 90 Min wird auf die beiden
    Sieg-Ausgaenge umverteilt; der Sieger geht typischerweise mit
    einem Tor Vorsprung vom Platz (h:h -> h+1:h bzw. h:h+1).
    """
    la, lb = lambdas(a, b)
    ra = RATING[a] + HOME_BONUS.get(a, 0)
    rb = RATING[b] + HOME_BONUS.get(b, 0)
    q_a = min(0.75, max(0.25, 0.5 + (ra - rb) / 300.0))  # Sieg-W'keit in VL/Elfm.
    pa, pb = poisson_pmf(la), poisson_pmf(lb)
    P = [[pa[h] * pb[x] for x in range(MAX_GOALS + 1)] for h in range(MAX_GOALS + 1)]
    # Remis-Diagonale aufloesen: h:h -> (h+1):h mit q_a, h:(h+1) mit 1-q_a
    for h in range(MAX_GOALS):
        m = P[h][h]
        P[h][h] = 0.0
        P[h + 1][h] += m * q_a
        P[h][h + 1] += m * (1 - q_a)
    best, best_ep = None, -1
    for th in range(6):
        for ta in range(6):
            if th == ta:
                continue   # Remis-Tipp im K.o. nicht erlaubt
            ep = sum(P[h][x] * points((th, ta), (h, x))
                     for h in range(MAX_GOALS + 1) for x in range(MAX_GOALS + 1))
            if ep > best_ep:
                best, best_ep = (th, ta), ep
    pw = sum(P[h][x] for h in range(MAX_GOALS + 1) for x in range(MAX_GOALS + 1) if h > x)
    return best, best_ep, pw, 1 - pw


def print_ko_tips():
    if not KO_SPIELE:
        return
    print("=" * 78)
    print("  TIPPS K.-O.-RUNDE  (Ergebnis nach Elfm., kein Remis moeglich)")
    print("=" * 78)
    print(f"{'Spiel':<40}{'TIPP':>6}{'E[Pkt]':>8}{'P(Sieg A/B) %':>16}")
    print("-" * 78)
    for a, b in KO_SPIELE:
        tip, ep, pw, pl = optimal_tip_ko(a, b)
        print(f"{a+' - '+b:<40}{tip[0]}:{tip[1]:<4}{ep:>7.2f}"
              f"{100*pw:>8.0f}/{100*pl:>3.0f}")
    print()


def print_open_tips():
    open_games = []
    for g, teams in GROUPS.items():
        for md_i, (i, j) in enumerate(FIXTURE_PATTERN):
            a, b = teams[i], teams[j]
            if (a, b) not in ERGEBNISSE and (b, a) not in ERGEBNISSE:
                open_games.append((g, 1 if md_i < 2 else 2 if md_i < 4 else 3, a, b))
    if not open_games:
        print(">> Alle Gruppenspiele gespielt.")
        return
    print("=" * 78)
    print("  TIPPS FUER DIE OFFENEN GRUPPENSPIELE (mit aktualisierten Ratings)")
    print("=" * 78)
    print(f"{'Gr':<3}{'ST':<3}{'Spiel':<36}{'TIPP':>6}{'E[Pkt]':>8}{'P(1/X/2) %':>15}")
    print("-" * 78)
    for g, md, a, b in sorted(open_games, key=lambda x: (x[1], x[0])):
        tip, ep, pw, pd, pl = optimal_tip(a, b)
        print(f"{g:<3}{md:<3}{a+' - '+b:<36}{tip[0]}:{tip[1]:<4}{ep:>7.2f}"
              f"{100*pw:>6.0f}/{100*pd:>2.0f}/{100*pl:>2.0f}")
    print()


# ===========================================================================
# B) MONTE CARLO mit fixierten Ergebnissen (bedingte Wahrscheinlichkeiten)
# ===========================================================================
def poisson_rng(lam, rng):
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def sim_match(a, b, rng, knockout=False, host=None):
    """Gespieltes Spiel -> echtes Ergebnis; offenes Spiel -> Simulation."""
    if not knockout:
        if (a, b) in ERGEBNISSE:
            ga, gb = ERGEBNISSE[(a, b)]
            return ga, gb
        if (b, a) in ERGEBNISSE:
            gb, ga = ERGEBNISSE[(b, a)]
            return ga, gb
    ra = RATING[a] + (HOME_BONUS.get(a, 0) if host else 0)
    rb = RATING[b] + (HOME_BONUS.get(b, 0) if host else 0)
    ga = poisson_rng(expected_goals(ra, rb), rng)
    gb = poisson_rng(expected_goals(rb, ra), rng)
    if knockout and ga == gb:
        ea = poisson_rng(expected_goals(ra + 1, rb) * 0.33, rng)
        eb = poisson_rng(expected_goals(rb + 1, ra) * 0.33, rng)
        ga, gb = ga + ea, gb + eb
        if ga == gb:
            if rng.random() < 0.5 + (ra - rb) / 400.0:
                ga += 1
            else:
                gb += 1
    return ga, gb


def run_tournament(rng):
    standings, tables = {}, {}
    for g, teams in GROUPS.items():
        tbl = {t: [0, 0, 0] for t in teams}
        host_group = any(t in HOME_BONUS for t in teams)
        for i, j in FIXTURE_PATTERN:
            a, b = teams[i], teams[j]
            ga, gb = sim_match(a, b, rng, host=host_group)
            tbl[a][1] += ga; tbl[a][2] += gb
            tbl[b][1] += gb; tbl[b][2] += ga
            if ga > gb:
                tbl[a][0] += 3
            elif gb > ga:
                tbl[b][0] += 3
            else:
                tbl[a][0] += 1; tbl[b][0] += 1
        standings[g] = sorted(teams, key=lambda t: (tbl[t][0], tbl[t][1] - tbl[t][2],
                                                    tbl[t][1], RATING[t]), reverse=True)
        tables[g] = tbl
    thirds = sorted([(g, standings[g][2]) for g in GROUPS],
                    key=lambda x: (tables[x[0]][x[1]][0],
                                   tables[x[0]][x[1]][1] - tables[x[0]][x[1]][2],
                                   tables[x[0]][x[1]][1], RATING[x[1]]),
                    reverse=True)[:8]
    W = {g: standings[g][0] for g in GROUPS}
    R = {g: standings[g][1] for g in GROUPS}
    T = [t[1] for t in thirds]
    s16 = [(W["A"], T[0]), (W["B"], T[1]), (W["D"], T[2]), (W["E"], T[3]),
           (W["G"], T[4]), (W["I"], T[5]), (W["K"], T[6]), (W["L"], T[7]),
           (W["C"], R["F"]), (W["F"], R["C"]), (W["H"], R["J"]), (W["J"], R["H"]),
           (R["A"], R["B"]), (R["E"], R["I"]), (R["D"], R["G"]), (R["K"], R["L"])]

    def rnd(pairs):
        out = []
        for a, b in pairs:
            ga, gb = sim_match(a, b, rng, knockout=True)
            out.append(a if ga > gb else b)
        return out

    w32 = rnd(s16)
    af = rnd([(w32[i], w32[j]) for i, j in
              [(3, 5), (2, 4), (0, 7), (1, 6), (8, 11), (9, 10), (12, 15), (13, 14)]])
    vf = rnd([(af[i], af[j]) for i, j in [(0, 4), (1, 5), (2, 6), (3, 7)]])
    hf = rnd([(vf[0], vf[2]), (vf[1], vf[3])])
    champ = rnd([(hf[0], hf[1])])[0]
    return standings, vf, champ


def bonus_update(n=20000, seed=7):
    rng = random.Random(seed)
    grp_win = {g: defaultdict(int) for g in GROUPS}
    semi, champs = defaultdict(int), defaultdict(int)
    for _ in range(n):
        standings, semifinalists, champ = run_tournament(rng)
        for g in GROUPS:
            grp_win[g][standings[g][0]] += 1
        for t in semifinalists:
            semi[t] += 1
        champs[champ] += 1
    cond = " | bisherige Ergebnisse" if ERGEBNISSE else ""
    print("=" * 78)
    print(f"  BONUS-WAHRSCHEINLICHKEITEN  ({n:,} Turniere{cond})")
    print("=" * 78)
    print("\nGruppensieger:")
    for g in GROUPS:
        top = sorted(grp_win[g].items(), key=lambda x: x[1], reverse=True)[:3]
        line = "  |  ".join(f"{t} {100*c/n:.0f}%" for t, c in top)
        print(f"   {g}:  {line}")
    print("\nHalbfinale (Top 8):")
    for t, c in sorted(semi.items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"   {t:<18} {100*c/n:5.1f}%")
    print("\nWeltmeister (Top 6):")
    for t, c in sorted(champs.items(), key=lambda x: x[1], reverse=True)[:6]:
        print(f"   {t:<18} {100*c/n:5.1f}%")


if __name__ == "__main__":
    update_ratings(ERGEBNISSE)
    print_open_tips()
    print_ko_tips()
    # Bonus-Wahrscheinlichkeiten sind nach Turnierstart nur noch zur Info
    # (Tipps sind fixiert). Bei Bedarf einkommentieren:
    # bonus_update(n=20000, seed=7)
