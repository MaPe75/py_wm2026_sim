#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WM 2026 – BACKTEST der Tipp-Empfehlungen (MD1 + MD2, 44 Spiele)
================================================================
Bewertet die jeweils NEUEREN (spieltagspezifischen) Tipps gegen die
echten Ergebnisse nach der Punkteregel: Sieg 2/3/4, Remis 2/-/4.
"""

PTS_WIN_TEND, PTS_WIN_DIFF, PTS_WIN_EXACT = 2, 3, 4
PTS_DRAW_TEND, PTS_DRAW_EXACT = 2, 4


def points(tip, res):
    th, ta = tip; h, a = res
    if (th, ta) == (h, a):
        return PTS_DRAW_EXACT if h == a else PTS_WIN_EXACT
    if th == ta and h == a:
        return PTS_DRAW_TEND
    if (th > ta and h > a) or (th < ta and h < a):
        return PTS_WIN_DIFF if th - ta == h - a else PTS_WIN_TEND
    return 0


def kat(tip, res):
    p = points(tip, res)
    return {4: "EXAKT", 3: "Tordiff", 2: "Tendenz", 0: "daneben"}[p]


# (Heim, Gast, tipH, tipG, ergH, ergG)  -- Tipp wie vom Skript ausgegeben
MD1 = [
    ("Mexiko", "Suedafrika", 1, 0, 2, 0),
    ("Suedkorea", "Tschechien", 1, 0, 2, 1),
    ("Kanada", "Bosnien", 1, 0, 1, 1),
    ("Katar", "Schweiz", 0, 1, 1, 1),
    ("Brasilien", "Marokko", 1, 0, 1, 1),
    ("Haiti", "Schottland", 0, 1, 0, 1),
    ("USA", "Paraguay", 1, 0, 4, 1),
    ("Australien", "Tuerkei", 0, 1, 2, 0),
    ("Deutschland", "Curacao", 1, 0, 7, 1),
    ("Elfenbeinkueste", "Ecuador", 1, 0, 1, 0),
    ("Niederlande", "Japan", 1, 0, 2, 2),
    ("Schweden", "Tunesien", 1, 0, 5, 1),
    ("Belgien", "Aegypten", 1, 0, 1, 1),
    ("Iran", "Neuseeland", 1, 0, 2, 2),
    ("Spanien", "Kap Verde", 1, 0, 0, 0),
    ("Saudi-Arabien", "Uruguay", 0, 1, 1, 1),
    ("Frankreich", "Senegal", 1, 0, 3, 1),
    ("Irak", "Norwegen", 0, 1, 1, 4),
    ("Argentinien", "Algerien", 1, 0, 3, 0),
    ("Oesterreich", "Jordanien", 1, 0, 3, 1),
    ("Portugal", "DR Kongo", 1, 0, 1, 1),
    ("Usbekistan", "Kolumbien", 0, 1, 1, 3),
    ("England", "Kroatien", 1, 0, 4, 2),
    ("Ghana", "Panama", 1, 0, 1, 0),
]

MD2 = [
    ("Tschechien", "Suedafrika", 1, 0, 1, 1),
    ("Mexiko", "Suedkorea", 1, 0, 1, 0),
    ("Schweiz", "Bosnien", 1, 0, 4, 1),
    ("Kanada", "Katar", 1, 0, 6, 0),
    ("Schottland", "Marokko", 0, 1, 0, 1),
    ("Brasilien", "Haiti", 1, 0, 3, 0),
    ("USA", "Australien", 1, 0, 2, 0),
    ("Tuerkei", "Paraguay", 1, 0, 0, 1),
    ("Deutschland", "Elfenbeinkueste", 1, 0, 2, 1),
    ("Curacao", "Ecuador", 0, 1, 0, 0),
    ("Niederlande", "Schweden", 1, 0, 5, 1),
    ("Japan", "Tunesien", 1, 0, 4, 0),      # real: Tunesien 0:4 Japan
    ("Belgien", "Iran", 1, 0, 0, 0),
    ("Neuseeland", "Aegypten", 0, 1, 1, 3),
    ("Spanien", "Saudi-Arabien", 1, 0, 4, 0),
    ("Kap Verde", "Uruguay", 0, 1, 2, 2),   # real: Uruguay 2:2 Kap Verde
    ("Frankreich", "Irak", 1, 0, 3, 0),
    ("Senegal", "Norwegen", 0, 1, 2, 3),    # real: Norwegen 3:2 Senegal
    ("Argentinien", "Oesterreich", 1, 0, 2, 0),
    ("Algerien", "Jordanien", 1, 0, 2, 1),  # real: Jordanien 1:2 Algerien
]


def auswerten(spiele, titel):
    total = 0
    zb = {"EXAKT": 0, "Tordiff": 0, "Tendenz": 0, "daneben": 0}
    print(f"\n{'='*70}\n  {titel}\n{'='*70}")
    print(f"{'Spiel':<34}{'Tipp':>6}{'Erg':>6}{'Pkt':>5}  Kategorie")
    print("-" * 70)
    for h, g, th, ta, eh, ea in spiele:
        p = points((th, ta), (eh, ea))
        k = kat((th, ta), (eh, ea))
        total += p
        zb[k] += 1
        print(f"{h+' - '+g:<34}{f'{th}:{ta}':>6}{f'{eh}:{ea}':>6}{p:>5}  {k}")
    n = len(spiele)
    print("-" * 70)
    print(f"  Summe: {total} Pkt aus {n} Spielen  (Schnitt {total/n:.2f}/Spiel)")
    print(f"  Treffer: {zb['EXAKT']}x EXAKT(4) · {zb['Tordiff']}x Tordiff(3) · "
          f"{zb['Tendenz']}x Tendenz(2) · {zb['daneben']}x daneben(0)")
    return total, n, zb


if __name__ == "__main__":
    t1, n1, z1 = auswerten(MD1, "1. SPIELTAG")
    t2, n2, z2 = auswerten(MD2, "2. SPIELTAG (ohne K/L, noch nicht gespielt)")
    tot, n = t1 + t2, n1 + n2
    z = {k: z1[k] + z2[k] for k in z1}
    print(f"\n{'='*70}\n  GESAMT\n{'='*70}")
    print(f"  {tot} Punkte aus {n} Spielen  (Schnitt {tot/n:.2f}/Spiel)")
    print(f"  Trefferquote (Tendenz oder besser): "
          f"{100*(n - z['daneben'])/n:.0f} %")
    print(f"  davon exakt richtig: {z['EXAKT']}/{n} = {100*z['EXAKT']/n:.0f} %")
    # theoretische Vergleichswerte
    print(f"\n  Einordnung:")
    print(f"   max. moeglich (alles exakt): {4*n} Pkt")
    print(f"   reine Tendenz-Quote: {z['EXAKT']}+{z['Tordiff']}+{z['Tendenz']} = "
          f"{z['EXAKT']+z['Tordiff']+z['Tendenz']} von {n} Spielen getroffen")
