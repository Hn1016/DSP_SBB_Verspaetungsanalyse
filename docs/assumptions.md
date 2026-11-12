# Annahmen

Was wahr sein muss, damit die Schritte in «Wie» (`docs/one-pager.md`) die Tabelle in «Was» ergeben. Abgeleitet aus
dem One-Pager, ohne die Daten zu öffnen. Die Wichtigkeit ist die Einschätzung des Teams (2026-10-17). Status und
Evidenz sind nach den Einträgen in `docs/log.md` nachgeführt (2026-11-08); wo kein Eintrag etwas belegt, gilt «offen»
bzw. «tief».

- **Status:** was die Prüfungen im Log zur Annahme ergeben haben, mit Verweis auf den Eintrag. «offen» = nicht geprüft
  oder nur ein Hinweis; «gestützt» = geprüft und gehalten; «teilweise» = ein Teil gehalten, ein Teil nicht;
  «widerlegt» = geprüft und nicht gehalten.
- **Evidenz:** wie stark das Log dafür spricht, dass die Annahme gilt. «tief» = nicht geprüft, nur ein Hinweis oder
  widerlegt; «mittel» = nur indirekt oder nur zum Teil geprüft; «hoch» = direkt geprüft und gehalten.

Sortiert nach Wichtigkeit (hoch zuerst), dann Evidenz (tief zuerst), dann Status («offen» zuerst), dann Nummer:
Wichtiges mit wenig Evidenz steht oben. Ausnahme: A10, A9 und A5 stehen in der Reihenfolge, in der sie geprüft werden
(Log 2026-11-08, «Reihenfolge der nächsten Prüfungen»).

| # | Annahme | Wichtigkeit | Evidenz | Status |
|---|---|---|---|---|
| 10 | **Genug Fahrten:** Pro Abschnitt bzw. Halt und Zeitfenster gibt es genug gemessene Fahrten, um ein systematisches Muster von Zufall zu unterscheiden, auch für Abschnitte über den Fahrplanwechsel hinweg. | hoch | mittel | teilweise (Log 2026-11-12, Befund #39: für Abschnitte gestützt, Mindestzahlen bestätigt; offen für Halte und ob 20 Betriebstage statistisch genügen) |
| 9 | **Ausfälle verzerren nicht:** Abschnitte mit Ausfällen wegzulassen verschiebt die Rangliste nicht wesentlich, obwohl Ausfälle sich an Störungstagen mit hohen Verspätungen häufen. | hoch | tief | offen (Log 2026-10-29, «Evidenz von A9 und A10 ohne Grundlage») |
| 5 | **Gleicher Weg:** Ein Haltepaar A→B bezeichnet im ganzen Zeitraum denselben physischen Weg; Umleitungen und geänderte Laufwege unter derselben Haltefolge sind selten. | hoch | tief | offen (Log 2026-10-06, H2: nur Hinweis auf Umleitungen) |
| 1 | **Echte Messung:** Zeiten mit Status `REAL` sind an allen Schweizer Halten tatsächlich gemessen, mit vergleichbarer Genauigkeit, und nicht nachträglich ergänzt oder interpoliert. | hoch | mittel | offen (Log 2026-10-06, H5: nur Plausibilität) |
| 2 | **Kein systematisches Fehlen:** Ob eine Zeit `REAL` ist, hängt nicht von der Verspätung oder vom Abschnitt ab, sodass das Weglassen von Nicht-`REAL`-Zeilen die Werte eines Abschnitts nicht verschiebt. | hoch | mittel | teilweise (Log 2026-10-25, H6; 2026-10-28, Korrektur H6b) |
| 4 | **Reihenfolge stabil:** Die Zeilenreihenfolge (`ZEILE`) ist in allen Monaten die Fahrreihenfolge einer Fahrt, nicht nur im geprüften September 2026. | hoch | mittel | teilweise (Log 2026-11-08, Befund #30: in 10 von 12 Monaten unter 0.1 %; Log 2026-11-10: meist Umleitungen, die `sections` nicht betreffen; Befund #33: Juli 2026 0.91 von 10'000) |
| 6 | **Zuordnung zu data.sbb.ch:** Abschnitte von Halt zu Halt lassen sich den Streckenabschnitten, Kilometrierungspunkten und Zugzahlen von data.sbb.ch eindeutig zuordnen. | mittel | tief | offen (kein Log-Eintrag) |
| 8 | **Referenzwert genügt:** Nach Abzug eines Referenzwerts je Soll-Haltezeit misst die Haltverspätung den Betrieb und nicht mehr die Fahrplanrundung. | mittel | tief | offen (Log 2026-10-06, Nebenbefund: nur die Verzerrung) |
| 7 | **Rundung neutral für Abschnitte:** Die Minutenauflösung der Soll-Zeiten verzerrt die Streckenverspätung nicht systematisch je Abschnitt (wie sie es bei der Haltverspätung tut). | mittel | tief | widerlegt (Log 2026-11-05, Befund A7, #18; Ursache offen; Log 2026-11-10, Befund #23: Klassenmittel über zwölf Monate gleich, Referenzwert je Soll-Fahrzeit gilt) |
| 3 | **Abdeckung über den ganzen Zeitraum:** Die `REAL`-Abdeckung im Zeitraum (ab 2025-08) ist in beiden Fahrplänen ähnlich wie im geprüften September 2026. | mittel | hoch | gestützt (Log 2026-11-08, Befund #30: Kanton Zürich, jeder Monat über 99 %; Log 2026-11-10, Befund #33: Juli 2026 99.37 %) |
