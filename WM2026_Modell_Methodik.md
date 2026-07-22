# WM-2026-Tippspiel-Optimierer — Methodik & Quellen

Ein kurzer, vollständiger Überblick über das Modell hinter den Tipps:
welche Formeln verwendet werden, worauf sie beruhen und woher die Daten
stammen.

---

## 1. Grundidee

Das Modell ist ein **Poisson-Tormodell** im Stil von Maher (1982). Jede
Mannschaft hat eine Stärkezahl (Rating). Aus der Rating-Differenz zweier
Teams werden die erwarteten Tore beider Seiten abgeleitet; die tatsächliche
Toranzahl ist dann poissonverteilt. Daraus lässt sich für jedes Spiel die
komplette Wahrscheinlichkeitsmatrix aller Ergebnisse (0:0, 1:0, 2:1, …)
berechnen — und daraus wiederum der **punktoptimale Tipp** für die jeweilige
Tippspielregel.

Wichtig: Der wahrscheinlichste Spielausgang und der punktoptimale Tipp sind
**nicht dasselbe**. Welcher Tipp die meisten erwarteten Punkte bringt, hängt
von der Punkteregel ab (Tendenz / Tordifferenz / exaktes Ergebnis).

---

## 2. Die Formeln

### 2.1 Erwartete Tore aus der Rating-Differenz

Für Heim-/Gastgeber-Teams (Mexiko, USA, Kanada) wird vor der Rechnung ein
Bonus von +4 auf das Rating addiert.

```
diff   = (R_Team − R_Gegner) / 100
λ_Team = 1,35 · 10^(0,9 · diff)          (begrenzt auf [0,18 ; 4,2])
```

`λ` (Lambda) ist die erwartete Toranzahl. Basiswert 1,35 Tore bei gleich
starken Teams; der Exponent 0,9 steuert, wie stark sich ein Rating-Vorsprung
in Tore übersetzt.

### 2.2 Ergebnis-Wahrscheinlichkeit (Poisson)

Die Tore beider Teams werden als unabhängige Poisson-Variablen modelliert:

```
P(k Tore | λ) = (λ^k · e^(−λ)) / k!

P(Ergebnis h:a) = P(h | λ_A) · P(a | λ_B)
```

Über alle h, a entsteht eine vollständige Ergebnismatrix.

### 2.3 Punktoptimaler Tipp (Erwartungswert-Maximierung)

Für jeden möglichen Tipp wird der Punkte-Erwartungswert gebildet und das
Maximum gewählt:

```
E[Punkte | Tipp] = Σ_{h,a}  P(h:a) · Punkte(Tipp, h:a)

Tipp* = argmax_Tipp  E[Punkte | Tipp]
```

`Punkte(...)` ist die konkrete Tippspielregel
(z. B. Sieg 2 / 3 / 4, Unentschieden 2 / – / 4).

### 2.4 Rating-Update nach jedem Spieltag (xG-basiert)

Nach gespielten Partien lernt das Modell dazu — ein Elo-artiges Update auf
Torbasis. Entscheidend: Das Lernsignal ist nicht der reine Endstand, sondern
eine Mischung aus tatsächlicher Tordifferenz und **Expected-Goals(xG)-
Differenz**. xG misst die Qualität der Torchancen und ist der bessere
Prädiktor für künftige Leistung als das oft zufällige Resultat (z. B. ein
dominantes Team, das nur 1:1 spielt, wird nicht bestraft).

```
perf      = 0,35 · (Tore_A − Tore_B)  +  0,65 · (xG_A − xG_B)
            (ohne xG: perf = Tore_A − Tore_B)

erwartet  = λ_A − λ_B            (aus den Ratings VOR dem Spiel)
surprise  = perf − erwartet
Δ         = begrenze( 0,8 · surprise , auf ±2,5 )

R_A ← R_A + Δ
R_B ← R_B − Δ                    (Nullsumme: Summe der Ratings bleibt gleich)
```

Die starke Dämpfung (Faktor 0,8, Deckel ±2,5) verhindert, dass ein einzelnes
Spiel das Rating überreißt — ein Spiel ist nur eine Stichprobe der Größe 1.

### 2.5 Markt-Anker aus Wettquoten

Buchmacher-Titelquoten bündeln die Markterwartung. Sie werden in implizite
Wahrscheinlichkeiten umgerechnet (die Buchmachermarge / „Vig" wird
herausgerechnet) und leicht in die Top-Team-Ratings eingemischt:

```
p_i      = (1 / Quote_i) / Σ_j (1 / Quote_j)      (entovigoriert)
R_Markt  = lineare Abbildung von logit(p_i) auf die Rating-Skala [80 … 96]
R_neu    = 0,75 · R_alt  +  0,25 · R_Markt          (Blend 25 %)
```

Nur 25 % Gewicht, weil Titelquoten auch die Turnierbaum- und Gruppenschwere
enthalten und damit kein reines Stärkemaß sind.

### 2.6 K.-o.-Modus

Im K. o. wird das Ergebnis nach Verlängerung/Elfmeter gewertet — ein Remis
ist ausgeschlossen. Die Unentschieden-Wahrscheinlichkeit nach 90 Minuten wird
auf die beiden Sieg-Ausgänge umverteilt:

```
q_A = begrenze( 0,5 + (R_A − R_B)/300 , auf [0,25 ; 0,75] )

P(h:h)  →  P(h+1 : h)  · q_A   +   P(h : h+1) · (1 − q_A)
```

Remis-Tipps werden aus der Optimierung ausgeschlossen.

---

## 3. Methodische Quellen

Das Modell beruht auf etablierten Verfahren der Sportstatistik:

- **Maher, M. J. (1982):** *Modelling association football scores.*
  Statistica Neerlandica, 36, S. 109–118.
  → Das ursprüngliche unabhängige Poisson-Modell für Fußballtore.
  Dieses Modell wird hier verwendet.

- **Dixon, M. & Coles, S. (1997):** *Modelling association football scores
  and inefficiencies in the football betting market.* Applied Statistics
  (Journal of the Royal Statistical Society, Series C), 46(2), S. 265–280.
  → Bekannte Verfeinerung mit Korrelationsparameter ρ (korrigiert niedrige
  Ergebnisse 0:0/1:1) und Zeitgewichtung. **Hinweis:** Diese Korrektur ist
  hier *nicht* implementiert — das Modell nutzt die einfachere
  Maher-Variante. Die DC-Korrektur wäre der nächste Ausbauschritt.

- **Elo-Rating-System** (Arpad Elo, 1978) bzw. die Fußball-Adaption
  *World Football Elo Ratings* (eloratings.net): konzeptionelle Grundlage
  des Rating-Updates in 2.4.

- **Expected Goals (xG):** modernes Chancen-Bewertungsmaß, popularisiert von
  Anbietern wie Opta und StatsBomb; Grundlage des xG-gewichteten Updates.

- **Devigging / implizite Wahrscheinlichkeiten aus Quoten:** Standardpraxis
  in der Wettmarkt-Analyse (Herausrechnen der Buchmachermarge).

---

## 4. Datenquellen (Stand der Implementierung)

Die konkreten Zahlen (Gruppen, Ergebnisse, Quoten, Ranglisten) wurden aus
öffentlich zugänglichen Quellen zusammengetragen:

- **Spielplan & Ergebnisse:** FIFA.com, UEFA.com, sportschau.de, web.de,
  fussballdaten.de, flashscore.de, blick.ch
- **FIFA-Weltrangliste:** als Orientierung für die Basis-Ratings
- **Wettquoten (Titel):** öffentliche Quotenvergleiche (Stand 17.06.2026)
- **xG-Werte:** wo gesetzt, plausible Schätzungen aus dem Spielverlauf —
  für maximale Präzision durch echte Messwerte (fbref, Sofascore, Opta)
  ersetzbar.

---

## 5. Bewusste Einschränkungen

- **Keine Dixon-Coles-Korrektur:** niedrige Ergebnisse (0:0, 1:1) werden vom
  reinen Poisson-Modell leicht unterschätzt.
- **Unabhängige Tore:** in Wirklichkeit korrelieren Heim- und Auswärtstore
  schwach (Spielstand beeinflusst die Spielweise).
- **Konservative Kalibrierung:** der Basiswert 1,35 / Exponent 0,9 erzeugt
  eher torarme Prognosen; sehr klare Favoritensiege (5:0, 7:1) werden
  tendenziell unterschätzt.
- **Ratings sind teils handgesetzt** (mit Markt-Anker korrigiert), keine aus
  einer langen Spielhistorie geschätzten Maximum-Likelihood-Parameter.
- **xG-Schätzungen** ersetzen keine offiziellen Messwerte.

---

*Modelltyp: unabhängiges Poisson-Tormodell (Maher 1982) mit Elo-artigem
xG-Update und Quoten-Anker. Implementiert in Python.*
