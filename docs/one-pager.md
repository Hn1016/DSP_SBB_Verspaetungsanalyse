# One-Pager: Wo entstehen und wo verschwinden Verspätungen im Schweizer Bahnnetz?

Stand: 2026-10-17, Schritt 2 und «Fertig» nachgeführt am 2026-10-29, Prüfungen an die Richtlinien v3 angeglichen am
2026-11-01, Regeln für die Rangliste festgelegt am 2026-11-10 (Issue #32). Quellen: Aufgabenstellung (`docs/requirements.md`) und die Entscheidungen im Projektlog (`docs/log.md`).
Was dort nicht entschieden ist, steht hier als **offen**.

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

**Regeln für die Rangliste (entschieden vom Team, Log 2026-11-10, Issue #32):**

- **Richtung:** getrennt; A→B und B→A sind verschiedene Abschnitte (Log «Richtung»).
- **Positiver Zuwachs:** Pro Abschnitt zählt das Mittel der Streckenverspätung nach Referenzwert je Soll-Fahrzeit
  (Issue #23). Ist das Mittel positiv, trägt der Abschnitt Mittel × Fahrten bei; das Total ist die Summe über alle
  Abschnitte mit positivem Mittel (Log «Positiver Zuwachs»).
- **Hauptkennzahl:** absolut, Minuten Zuwachs im ganzen Zeitraum (Mittel × Fahrten). Pro Fahrt und pro
  Streckenkilometer als Begleitspalten; der Vergleich mit der Baseline «sortiert nach Zugzahl» prüft, ob die
  Rangliste nur Volumen und Länge abbildet (Log «Hauptkennzahl»).
- **Systematisch:** mindestens 100 gemessene Fahrten und 30 Betriebstage mit Messung im Zeitraum, mindestens 20
  Betriebstage pro Zeitfenster (beibehalten, Log 2026-11-12, Befund #39; ob 20 Betriebstage genügen, offen, Issue
  #38). Das 95-%-Konfidenzintervall des Mittels wird über die Tagesmittel je Betriebstag gerechnet, nicht über
  Fahrten. Verstärker, wenn es ganz über 0 liegt und das Mittel mindestens 0.25 min beträgt; Absorber, wenn es ganz
  unter 0 liegt und das Mittel höchstens −0.25 min beträgt; sonst neutral (Log «Systematisch»).
- **Zeitfenster** nach Soll-Abfahrt an A (beibehalten, Log 2026-11-12, Befund #39): Tageszeit Morgenspitze 6–9 Uhr,
  Tag 9–16, Abendspitze 16–19, Abend/Nacht 19–6; Wochentag Montag–Freitag und Samstag/Sonntag; Jahreszeit
  meteorologisch (Dez–Feb, Mär–Mai, Jun–Aug, Sep–Nov); Fahrplan 2025 (bis 13.12.2025) und 2026 (Log «Zeitfenster»).
- **Stabil**, wenn die Spearman-Rangkorrelation zwischen den beiden Fahrplänen mindestens 0.7 beträgt und mindestens
  7 der Top 10 in beiden vorkommen; über 20 Paare zufälliger 4-Wochen-Fenster ist der Median der Korrelation
  mindestens 0.7. Die Erwartung kommt ins Paket Stabilitätsprüfung (Log «Stabilität»).

Offen:
- Der Referenzwert je Soll-Haltezeit für die Haltverspätung (A8).
- Bezugsgrösse für den Anteil der Top 10 am positiven Zuwachs: roh oder relativ zum Klassenmittel der Soll-Fahrzeit.
  Mit Referenzwert ist die Summe über alle Fahrten null, und etwa die Hälfte der Abschnitte hat per Konstruktion
  einen positiven Zuwachs (Log 2026-11-10, Befund #23: roh 28.8 %, mit Referenzwert 21.8 %). Entscheid im Paket
  Kennzahlen.

## Wie (How)

**Quellen:**

- SBB IstDaten v2 von opentransportdata.swiss, Monatsarchive (Log 2026-10-05), verfügbar ab 13.7.2025. Der
  Zeitraum (siehe Eingrenzung) enthält den Fahrplanwechsel vom 14.12.2025.
- Haltestellenliste (Service Points) mit Koordinaten, Schnappschuss mit Abrufdatum (Log 2026-10-05).
- Von data.sbb.ch: Züge pro Streckenabschnitt (Auslastungsmass), Linie (Betriebspunkte), Kilometrierungspunkte.
  Noch nicht geladen.

**Eingrenzung (entschieden, Log 2026-10-05 und 2026-10-06):** nur `PRODUKT_ID = 'Zug'`; nur Halte in der Schweiz
(BPUIC 85…); nur `REAL` gilt als gemessen; Ausfälle bleiben in den Daten und werden ausgewiesen.

**Eingrenzung (entschieden vom Team, Log 2026-11-10, Issue #32):**

- **Raum:** Kanton Zürich, beide Halte eines Abschnitts im Kanton. LEB, MBC und ZB fahren nicht im Kanton Zürich;
  ein Ausschluss ist nicht nötig (Log «Raum»).
- **Zeitraum:** 1.8.2025 bis 31.7.2026, zwölf volle Monate ohne fehlende Tage, mit dem Fahrplanwechsel vom
  14.12.2025 (Log «Zeitraum»). `period.py` setzt diesen Zeitraum seit Issue #33 (vorher 13.7.2025 bis 30.6.2026,
  Log 2026-11-08, Issue #30).
- **Durchfahrten** zählen als Punkt: Eine Durchfahrt kann Halt A oder B eines Abschnitts sein (Log 2026-11-08,
  Issue #24). Als Halt werden sie nicht ausgewertet.
- **Schwelle 80 % `REAL`:** bleibt als Vergleich der Rangliste mit und ohne Abschnitte unter 80 % (Log «Schwelle
  80 % `REAL`»).

**Schritte:**

1. Monatsarchive laden und je Betriebstag als Parquet speichern (bestehend: `download`, `load`).
2. Abschnitte bilden: Halte einer Fahrt nach `ZEILE` ordnen, nur zwischen zwei nicht ausgefallenen Halten mit
   `REAL`; doppelte Zeilen, rückwärts laufende Soll-Zeiten und Werte über ±12 Stunden verwerfen (Regeln zentral in
   `quality.delays()`, Log 2026-10-28). Der Anteil `REAL` wird je Abschnitt und Halt als Spalte geführt. Halte ohne
   `REAL`-Zeit fallen nicht still weg, sondern werden im Bericht als Abdeckungslücke genannt; die Rangliste wird mit
   und ohne Abschnitte unter 80 % `REAL` verglichen (Log 2026-10-25).
3. Strecken- und Haltverspätung je Fahrt berechnen.
4. Je Abschnitt bzw. Halt und Zeitfenster aggregieren.
5. Je Abschnitt eine einfache Regression des Zuwachses auf die eingehende Verspätung: Die Steigung zeigt, ob ein
   Abschnitt einen konstanten Betrag addiert oder proportional verstärkt.
6. Normieren pro Fahrt und pro Streckenkilometer, mit der Zugzahl pro Abschnitt vergleichen.
7. Prüfungen nach Abschnitt 3 der Richtlinien, dann Karte und Bericht.

Offen:
- Wie Halte (BPUIC) auf die Streckenabschnitte und Kilometrierung von data.sbb.ch abgebildet werden (A6).

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
- Jede zentrale Zahl im Bericht hat eine Prüfung hinter sich: die eine aus Baseline, Permutation, Placebo,
  Rechenprobe oder Stabilität, deren Scheitern den Satz ändern würde, mit der Erwartung vor dem Lauf (Richtlinien v3,
  Abschnitt 3).
- Die interaktive Karte zeigt Verstärker und Absorber.
- Der Bericht nennt zu jedem Top-10-Eintrag, welche Art Massnahme infrage kommt, und offen auch widerlegte
  Hypothesen.
- Nach `git clone` ergeben `uv sync` und die Befehle im README dieselben Ergebnisse aus denselben Rohdaten.
- Jeder Abschnitt und Halt bekommt einen Wert oder einen genannten Grund, warum er nicht bewertet wird («nie
  gemessen», «zu wenige Fahrten»); nichts fällt still weg (Log 2026-11-10, Issue #32, «Wert oder Grund»).
