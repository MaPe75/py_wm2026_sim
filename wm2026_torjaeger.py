#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WM 2026 – TORSCHUETZENKOENIG-TRACKER  (Goldener Schuh)
======================================================

Eigenstaendige Erweiterung. Beantwortet eine andere Frage als das
Match-Modell: Welcher SPIELER schiesst am Ende die meisten Tore?

Warum getrennt? Das Match-Modell kennt nur Teamstaerken. Der
Torschuetzenkoenig haengt an drei Dingen, die das Team-Rating NICHT
abbildet:
  1. wie viele Tore das Team noch erwartet (Restprogramm),
  2. welcher ANTEIL davon auf den einen Spieler entfaellt (Fokus),
  3. der persoenliche "Push" (Messi will den Rekord/Goldenen Schuh und
     drueckt auch beim 2:0 weiter -> realer Effekt, den Statistik bestaetigt).

Prognose je Spieler:
    erwartete_Resttore = Rest_Teamtore * Tor_Anteil * Push_Faktor
    Saison_Prognose     = bisherige_Tore + erwartete_Resttore

Tiebreak laut Tippspiel/FIFA: bei Gleichstand zaehlen Assists, dann
weniger Spielzeit -> hier vereinfacht ueber den TIEBREAK-Wert abbildbar.
"""

from collections import defaultdict

# ===========================================================================
# Aktueller Stand (nach 2 Spieltagen, Quelle: oeffentliche Torschuetzenlisten)
# Spieler: (Team, bisherige_Tore, Push-Faktor, Tor-Anteil am Team,
#           erwartete_restliche_Teamspiele)
#   Push  : 1.00 neutral; >1 = persoenlicher Tordrang (Rekordjagd etc.)
#   Anteil: grober Schaetzwert, welcher Teil der Teamtore ueber ihn laeuft
# ===========================================================================
SPIELER = {
    # Name:            (Team,           Tore, Push, Anteil, Restspiele)
    "Messi":           ("Argentinien",   5,   1.25, 0.45,   1),   # Rekordjagd, letzte WM
    "Mbappe":          ("Frankreich",    4,   1.15, 0.50,   1),
    "Haaland":         ("Norwegen",      4,   1.15, 0.55,   1),
    "Undav":           ("Deutschland",   3,   1.05, 0.30,   1),
    "J. David":        ("Kanada",        3,   1.05, 0.40,   1),
    "Kane":            ("England",       2,   1.10, 0.45,   2),   # erst 1 Spiel
    "Havertz":         ("Deutschland",   2,   1.00, 0.25,   1),
    "Vinicius":        ("Brasilien",     2,   1.00, 0.30,   1),
    "Gakpo":           ("Niederlande",   2,   1.00, 0.30,   1),
    "Oyarzabal":       ("Spanien",       2,   1.00, 0.25,   1),
}

# Erwartete Tore pro verbleibendem Spiel je Team (grob; kann aus dem
# Match-Modell uebernommen werden: Summe der lambda ueber die Restspiele).
TEAM_TORE_PRO_SPIEL = {
    "Argentinien": 2.0, "Frankreich": 2.3, "Norwegen": 2.0, "Deutschland": 2.4,
    "Kanada": 1.9, "England": 2.2, "Brasilien": 2.2, "Niederlande": 2.3,
    "Spanien": 2.5,
}


def prognose():
    rows = []
    for name, (team, tore, push, anteil, restspiele) in SPIELER.items():
        rest_teamtore = TEAM_TORE_PRO_SPIEL.get(team, 1.8) * restspiele
        erwartet_rest = rest_teamtore * anteil * push
        saison = tore + erwartet_rest
        rows.append((name, team, tore, erwartet_rest, saison))
    rows.sort(key=lambda r: r[4], reverse=True)
    return rows


def print_tracker():
    print("=" * 74)
    print("  TORSCHUETZENKOENIG-PROGNOSE WM 2026  (Goldener Schuh)")
    print("=" * 74)
    print(f"{'Spieler':<12}{'Team':<14}{'jetzt':>6}{'erw.Rest':>10}{'Prognose':>10}")
    print("-" * 74)
    for name, team, tore, rest, saison in prognose():
        print(f"{name:<12}{team:<14}{tore:>6}{rest:>10.2f}{saison:>10.2f}")
    best = prognose()[0]
    print("-" * 74)
    print(f"  TIPP Torschuetzenkoenig : {best[0]} ({best[1]})")
    print(f"  TIPP 'Team des Toptorjaegers' : {best[1]}")
    print("\n  Hinweis: Push-Faktor und Tor-Anteil sind Experteneinschaetzungen,")
    print("  keine Messwerte. Messi hat als Rekordhalter den hoechsten Push (1.25);")
    print("  bei Gleichstand entscheiden laut Regel Assists, dann weniger Spielzeit.")


# ===========================================================================
# OPTIONAL: Team-Offensiv-Bias fuers Match-Modell
# ===========================================================================
# In wm2026_md3.py kann man λ eines "Tordrang"-Teams anheben, um das
# Weiterspielen-trotz-Fuehrung abzubilden. Beispiel zum Einbauen in
# expected_goals()/lambdas():
#
#   OFFENSIV_BIAS = {"Argentinien": 1.15, "Frankreich": 1.10, "Norwegen": 1.10}
#   lam_team *= OFFENSIV_BIAS.get(team, 1.0)
#
# Effekt: Tipps fuer diese Teams verschieben sich von 2:0 Richtung 3:0/3:1.
OFFENSIV_BIAS = {
    "Argentinien": 1.15,   # Messi-Krone -> Team drueckt auch bei Fuehrung
    "Frankreich": 1.10,
    "Norwegen": 1.10,
    "England": 1.05,
}


if __name__ == "__main__":
    print_tracker()
    print("\n  (OFFENSIV_BIAS fuer das Match-Modell unten im Code definiert.)")
