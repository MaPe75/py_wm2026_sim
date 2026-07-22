# WM-2026-Tippspiel-Optimierer — Methodik & Quellen (Stand: Gruppenphase)

Ein vollständiger Überblick über das Modell hinter den Tipps: die Formeln,
wie das Modell aus echten Ergebnissen dazulernt, wie Wettquoten einfließen,
woher die Daten stammen — und wie gut es bisher abgeschnitten hat.

---

## 1. Grundidee

Das Modell ist ein **Poisson-Tormodell** im Stil von Maher (1982). Jede
Mannschaft hat eine Stärkezahl (Rating). Aus der Rating-Differenz zweier
Teams werden die erwarteten Tore beider Seiten abgeleitet; die tatsächliche
Toranzahl ist poissonverteilt. Daraus ergibt sich für jedes Spiel die
komplette Wahrscheinlichkeitsmatrix aller Ergebnisse (0:0, 1:0, 2:1, …) und
daraus der **punktoptimale Tipp** für die jeweilige Tippspielregel.

Kernbotschaft: Der wahrscheinlichste Spielausgang und der punktoptimale Tipp
sind **nicht dasselbe**. Welcher Tipp die meisten erwarteten Punkte bringt,
hängt von der Punkteregel ab (Tendenz / Tordifferenz / exaktes Ergebnis).

Das Modell besteht aus fünf Schichten, die nacheinander angewendet werden:

1. Basis-Rating (Teamstärke vor dem Turnier)
2. Form-Korrektur aus den Testspielen
3. Markt-Anker aus den Titelquoten
4. xG-Update aus den echten Turnierergebnissen (nach jedem Spieltag)
5. 1X2-Matchquoten je Spiel (überschreiben das Rating, wo vorhanden)

---

## 2. Die Formeln

### 2.1 Erwartete Tore aus der Rating-Differenz

Gastgeber (Mexiko, USA, Kanada) erhalten vorab +4 auf ihr Rating.

```
diff   = (R_Team − R_Gegner) / 100
λ_Team = 1,35 · 10^(0,9 · diff)          (begrenzt auf [0,18 ; 4,2])
```

λ ist die erwartete Toranzahl: Basiswert 1,35 bei gleich starken Teams, der
Exponent 0,9 steuert, wie stark ein Rating-Vorsprung in Tore umschlägt.

### 2.2 Ergebnis-Wahrscheinlichkeit (Poisson)

```
P(k Tore | λ) = (λ^k · e^(−λ)) / k!
P(Ergebnis h:a) = P(h | λ_A) · P(a | λ_B)
```

### 2.3 Punktoptimaler Tipp (Erwartungswert-Maximierung)

```
E[Punkte | Tipp] = Σ_{h,a}  P(h:a) · Punkte(Tipp, h:a)
Tipp* = argmax_Tipp  E[Punkte | Tipp]
```

Verwendete Punkteregel (neutraler Platz):
Sieg 2 / 3 / 4 (Tendenz / Tordifferenz / exakt), Unentschieden 2 / – / 4.

### 2.4 xG-Update nach jedem Spieltag

Nach gespielten Partien lernt das Modell dazu — ein Elo-artiges Update auf
Torbasis. Entscheidend: Lernsignal ist nicht der reine Endstand, sondern
eine Mischung aus tatsächlicher Tordifferenz und **Expected-Goals(xG)-
Differenz**. xG misst die Chancenqualität und sagt künftige Leistung besser
voraus als das oft zufällige Resultat.

```
perf      = 0,35 · (Tore_A − Tore_B)  +  0,65 · (xG_A − xG_B)
            (ohne xG: perf = Tore_A − Tore_B)
erwartet  = λ_A − λ_B            (aus den Ratings VOR dem Spiel)
surprise  = perf − erwartet
Δ         = begrenze( 0,8 · surprise , auf ±2,5 )
R_A ← R_A + Δ ;  R_B ← R_B − Δ   (Nullsumme; starke Dämpfung)
```

Praxisbeispiel: Kanada spielte trotz drückender Überlegenheit nur 1:1
(xG ~2,4 : 0,7). Auf reiner Tordifferenz wäre Kanada abgewertet worden; mit
xG stieg das Rating leicht — und zwei Spiele später bestätigte ein 6:0 die
Qualität. Genau dafür ist die xG-Schicht da.

### 2.5 Markt-Anker aus Titelquoten

Buchmacher-Titelquoten bündeln die Markterwartung. Sie werden entovigoriert
(Buchmachermarge herausgerechnet) und leicht in die Top-Team-Ratings
gemischt:

```
p_i      = (1 / Quote_i) / Σ_j (1 / Quote_j)
R_Markt  = lineare Abbildung von logit(p_i) auf die Rating-Skala [80 … 96]
R_neu    = 0,75 · R_alt  +  0,25 · R_Markt          (Blend 25 %)
```

Nur 25 % Gewicht, weil Titelquoten auch Turnierbaum/Gruppenschwere
enthalten und damit kein reines Stärkemaß sind.

### 2.6 1X2-Matchquoten je Spiel (neueste Erweiterung)

Für einzelne Spiele lassen sich die echten Sieg/Remis/Niederlage-Quoten
hinterlegen. Daraus werden die λ-Werte **direkt** kalibriert — wo eine
Matchquote vorliegt, ersetzt sie das ratingbasierte λ.

```
1. Quoten -> implizite W'keiten, devigt:
     p_H, p_X, p_A  =  (1/Q_H, 1/Q_X, 1/Q_A) / Σ
2. Numerische Suche nach (λ_Heim, λ_Gast), deren Poisson-Modell
   genau diese 1X2-W'keiten reproduziert (Grid-Suche).
3. λ_final = 0,85 · λ_Quote + 0,15 · λ_Rating         (Blend 85 %)
```

Hintergrund: Beim Spiel Schweiz–Kanada sah das ratingbasierte Modell Kanada
nach dem 6:0 gegen Katar minimal vorne (der Sieg war nicht gegnergewichtet).
Die Buchmacher hatten die Schweiz klar als Favorit. Mit der
Matchquoten-Kalibrierung kippt λ von 1,32 : 1,38 (Rating) auf 1,05 : 0,85
(Quote) — der Tipp wechselt korrekt auf die Schweiz. Besonders wertvoll in
der K.-o.-Runde, wo jedes einzelne Spiel zählt.

### 2.7 K.-o.-Modus

Im K. o. wird das Ergebnis nach Verlängerung/Elfmeter gewertet — kein Remis
möglich. Die Remis-Wahrscheinlichkeit nach 90 Minuten wird auf die beiden
Sieg-Ausgänge umverteilt:

```
q_A = begrenze( 0,5 + (R_A − R_B)/300 , auf [0,25 ; 0,75] )
P(h:h)  →  P(h+1 : h) · q_A   +   P(h : h+1) · (1 − q_A)
```

Remis-Tipps werden aus der Optimierung ausgeschlossen.

### 2.8 Margin-Analyse (Tippstrategie)

Zusatzauswertung je Spiel: Wahrscheinlichkeit für 2+ Tore Unterschied plus
Vergleich der Erwartungswerte von 1:0 / 2:0 / 2:1. Ergebnis über alle
Spiele: In der Gruppenphase ist der knappe Favoritensieg (1:0) fast immer
optimal, weil er das dichte 1-Tor-Band abdeckt; ein 2:1 ist nahezu
gleichwertig (~0,01 Erwartungspunkte Abstand) und damit eine spektakulärere
Alternative ohne nennenswerten Nachteil.

---

## 3. Bisherige Trefferleistung (Backtest, 1.+2. Spieltag)

Über die 44 ausgewerteten Gruppenspiele hätte das Modell **72 Punkte**
erzielt, Schnitt **1,64 pro Spiel**.

| | 1. Spieltag | 2. Spieltag |
|---|---|---|
| Schnitt/Spiel | 1,46 | 1,85 |
| Treffer (Tendenz oder besser) | 14/24 | 15/20 |

Der 2. Spieltag war deutlich besser — Beleg dafür, dass das xG-Update und
die Quoten die Ratings sinnvoll schärfen. Schwachpunkt am 1. Spieltag waren
die zahnlosen Favoriten-Remis (Spanien 0:0, Belgien 1:1, Kanada 1:1 …),
genau die Spiele, die die xG-Schicht danach entschärft hat.

---

## 4. Methodische Quellen

- **Maher, M. J. (1982):** *Modelling association football scores.*
  Statistica Neerlandica, 36, S. 109–118.
  → Das verwendete unabhängige Poisson-Modell.

- **Dixon, M. & Coles, S. (1997):** *Modelling association football scores
  and inefficiencies in the football betting market.* Applied Statistics
  (JRSS Series C), 46(2), S. 265–280.
  → Bekannte Verfeinerung (Korrelationsparameter ρ für niedrige Ergebnisse,
  Zeitgewichtung). **Nicht implementiert** — wäre der nächste Ausbauschritt
  und würde knappe Remis (0:0, 1:1) etwas höher bewerten.

- **Elo-Rating-System** (Arpad Elo) bzw. die Fußball-Adaption *World
  Football Elo Ratings*: konzeptionelle Grundlage des Rating-Updates (2.4).

- **Expected Goals (xG):** Chancenbewertungsmaß (Opta, StatsBomb);
  Grundlage des xG-gewichteten Updates.

- **Devigging / implizite Wahrscheinlichkeiten aus Quoten:** Standard der
  Wettmarkt-Analyse (Herausrechnen der Buchmachermarge); Grundlage von
  2.5 und 2.6.

---

## 5. Datenquellen

- **Spielplan & Ergebnisse:** FIFA.com, UEFA.com, sportschau.de,
  fussballdaten.de, flashscore.de, kicker.de, sportsillustrated.de
- **FIFA-Weltrangliste:** Orientierung für die Basis-Ratings
- **Titel- und Matchquoten:** öffentliche Quotenvergleiche
- **xG-Werte:** wo gesetzt, Schätzungen aus dem Spielverlauf; durch echte
  Messwerte (fbref, Sofascore, Opta) ersetzbar

---

## 6. Bewusste Einschränkungen

- **Keine Dixon-Coles-Korrektur** — niedrige Ergebnisse leicht unterschätzt.
- **Unabhängige Tore** — reale schwache Korrelation wird ignoriert.
- **Siege nicht gegnergewichtet** — ein 6:0 gegen einen Schwachen wird im
  Rating-Update überbewertet (Grund, warum 2.6 für Einzelspiele wichtig ist).
- **Keine Spielermotivation** — z. B. Messis Jagd auf den Goldenen Schuh
  (Team drückt auch bei Führung weiter) steckt in keinem Team-Rating; dafür
  gibt es einen separaten Torschützen-Tracker.
- **Konservative Kalibrierung** (λ-Basis 1,35) — Kantersiege werden eher
  unterschätzt.
- **Ratings teils handgesetzt**, mit Markt-Anker korrigiert.

---

*Modelltyp: unabhängiges Poisson-Tormodell (Maher 1982) mit Elo-artigem
xG-Update, Titelquoten-Anker und 1X2-Matchquoten-Kalibrierung.
Implementiert in Python; Tipps werden auf die jeweilige Punkteregel
optimiert.*
