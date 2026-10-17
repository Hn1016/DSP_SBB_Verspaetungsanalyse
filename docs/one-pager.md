# One-Pager: Wo entstehen und wo verschwinden Verspätungen im Schweizer Bahnnetz?

Stand: 2026-10-17. Quellen: Aufgabenstellung (`docs/requirements.md`) und die Entscheidungen im Projektlog
(`docs/log.md`). Was dort nicht entschieden ist, steht hier als **offen**.

## Warum (Why)

**Die Frage, wie sie ankam:** «Welche Abschnitte und Halte vergrössern Verspätungen systematisch (Verstärker),
welche bauen sie ab (Absorber), und wie stabil ist dieses Muster über Wochentage, Tageszeiten, Jahreszeiten und
über den Fahrplanwechsel hinweg?»

**Wer das Ergebnis liest:** Fahrplanung, Betriebssteuerung und Infrastrukturplanung eines Bahnbetreibers,
exemplarisch SBB Personenverkehr. Gegenmassnahmen sind lokal und teuer; sie müssen dort ansetzen, wo Verspätung
entsteht. Die Leser sind keine Data Scientists.

Offen:
- Welche der drei Stakeholdergruppen die Hauptleserin ist und was sie mit der Rangliste entscheidet.

## Was (What)

**Was die Leser bekommen:**

- Eine Rangliste der zehn Abschnitte und der zehn Halte, an denen eine Massnahme den grössten Netzeffekt hätte,
  mit einer Einschätzung, welche Art Massnahme dort infrage kommt.
- Eine interaktive Netzkarte mit Verstärker- und Absorber-Abschnitten.
- Einen kurzen Bericht, der auch sagt, wie belastbar die Rangliste ist und wo ihre Grenzen liegen.

**Einheit des Ergebnisses:** eine Zeile pro Abschnitt und Zeitfenster und eine Zeile pro Halt und Zeitfenster,
getrennt ausgewertet.

- Abschnitt: zwei aufeinanderfolgende Halte derselben Fahrt; Streckenverspätung = Ankunftsverspätung an B minus
  Abfahrtsverspätung an A.
- Halt: Haltverspätung = Abfahrts- minus Ankunftsverspätung am selben Halt, bezogen auf einen Referenzwert je
  Soll-Haltezeit (Log 2026-10-06: die rohe Haltverspätung misst bei 73 % der Halte die Fahrplanrundung).

**Kennzahlen (aus der Aufgabenstellung):** Anteil des positiven Verspätungszuwachses, den die Top-10 erklären,
absolut, pro Fahrt und pro Streckenkilometer; Stabilität der Rangliste über zufällig gezogene Zeitfenster und
zwischen den beiden Fahrplänen (Rangkorrelation).

Offen (vor der ersten Rangliste festzulegen, in einem eigenen Pull Request ohne Code):
- Gilt ein Abschnitt je Richtung (A→B und B→A getrennt) oder richtungsunabhängig?
- Was «systematisch» heisst: Mindestzahl gemessener Fahrten je Abschnitt und Zeitfenster und die Schwelle, ab der
  ein Abschnitt Verstärker oder Absorber ist.
- Wie der positive Verspätungszuwachs gerechnet wird (pro Fahrt nur positive Werte oder positive Mittelwerte je
  Abschnitt) und welche der drei Normierungen die Rangliste für den Bericht bestimmt.
- Die Zeitfenster: Einteilung der Tageszeiten, Wochentage und Jahreszeiten.
- Ab welcher Rangkorrelation die Rangliste als stabil gilt, und Grösse und Anzahl der zufälligen Zeitfenster.
- Der Referenzwert je Soll-Haltezeit für die Haltverspätung.

## Wie (How)

**Quellen:**

- SBB IstDaten v2 von opentransportdata.swiss, Monatsarchive (Log 2026-10-05), verfügbar ab 2025-07. Der Zeitraum
  ab 2025-07 enthält den Fahrplanwechsel im Dezember 2025.
- Haltestellenliste (Service Points) mit Koordinaten, Schnappschuss mit Abrufdatum (Log 2026-10-05).
- Von data.sbb.ch: Züge pro Streckenabschnitt (Auslastungsmass), Linie (Betriebspunkte), Kilometrierungspunkte.
  Noch nicht geladen.

**Eingrenzung (entschieden, Log 2026-10-05 und 2026-10-06):** nur `PRODUKT_ID = 'Zug'`; nur Halte in der Schweiz
(BPUIC 85…); nur `REAL` gilt als gemessen; Ausfälle bleiben in den Daten und werden ausgewiesen.

**Schritte:**

1. Monatsarchive laden und je Betriebstag als Parquet speichern (bestehend: `download`, `load`).
2. Abschnitte bilden: Halte einer Fahrt nach `ZEILE` ordnen, nur zwischen zwei nicht ausgefallenen Halten mit
   `REAL`; doppelte Zeilen, rückwärts laufende Soll-Zeiten und Werte über ±12 Stunden verwerfen.
3. Strecken- und Haltverspätung je Fahrt berechnen.
4. Je Abschnitt bzw. Halt und Zeitfenster aggregieren.
5. Je Abschnitt eine einfache Regression des Zuwachses auf die eingehende Verspätung: Die Steigung zeigt, ob ein
   Abschnitt einen konstanten Betrag addiert oder proportional verstärkt.
6. Normieren pro Fahrt und pro Streckenkilometer, mit der Zugzahl pro Abschnitt vergleichen.
7. Prüfungen nach Abschnitt 6 der Richtlinien, dann Karte und Bericht.

Offen:
- Der Raum: ganzes Netz oder eine Region; ob Betreiber mit tiefer `REAL`-Abdeckung (LEB, MBC, ZB) ausgeschlossen
  oder separat ausgewiesen werden.
- Der genaue Analysezeitraum (zwölf Monate oder alles ab 2025-07).
- Wie Halte (BPUIC) auf die Streckenabschnitte und Kilometrierung von data.sbb.ch abgebildet werden.
- Durchfahrten: vorerst wie Halte ohne Fahrgastwechsel behandelt, nicht als Halt ausgewertet (Annahme,
  Log 2026-10-06).

## Nicht-Ziele (Non-goals)

- Kein Prognosemodell.
- Keine Ursachenanalyse. Betriebliche Ursachen (Rollmaterial, Personal, Anschlussregeln) sind nicht in den Daten.
- Keine Halte im Ausland: nur 10.7 % `REAL` und keine Koordinaten (Log 2026-10-06).
- `PROGNOSE` und `GESCHAETZT` werden nicht als gemessene Zeiten gezählt.
- Keine Betriebspunkte der Infrastruktur: Die Daten enthalten nur Halte, ein Abschnitt reicht von Halt zu Halt.

## Fertig (Done)

- Die Rangliste der zehn wichtigsten Abschnitte und Halte existiert, mit den Kennzahlen absolut, pro Fahrt und
  pro Streckenkilometer.
- Ihre Stabilität ist gemessen: über zufällige Zeitfenster und zwischen den beiden Fahrplänen.
- Jede zentrale Zahl im Bericht ist durch mindestens eine Prüfung abgesichert (Baseline, Permutation, Placebo,
  Rechenprobe oder Stabilität).
- Die interaktive Karte zeigt Verstärker und Absorber.
- Der Bericht nennt zu jedem Top-10-Eintrag, welche Art Massnahme infrage kommt, und offen auch widerlegte
  Hypothesen.
- Nach `git clone` ergeben `uv sync` und die Befehle im README dieselben Ergebnisse aus denselben Rohdaten.

Offen:
- Ob jeder Abschnitt und Halt entweder einen Wert oder einen genannten Grund bekommt, warum er nicht bewertet wird
  (z. B. zu wenige gemessene Fahrten), statt still zu entfallen.
