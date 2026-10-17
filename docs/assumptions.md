# Annahmen

Was wahr sein muss, damit die Schritte in «Wie» (`docs/one-pager.md`) die Tabelle in «Was» ergeben. Abgeleitet aus
dem One-Pager, ohne die Daten zu öffnen. Wichtigkeit und Evidenz sind die Einschätzungen des Teams (2026-10-17).

Sortiert nach Wichtigkeit (hoch zuerst), dann nach Evidenz (tief zuerst): Wichtiges mit wenig Evidenz steht oben.
# ist die ursprüngliche Nummer.

| # | Annahme | Wichtigkeit | Evidenz | Status |
|---|---|---|---|---|
| 2 | **Kein systematisches Fehlen:** Ob eine Zeit `REAL` ist, hängt nicht von der Verspätung oder vom Abschnitt ab, sodass das Weglassen von Nicht-`REAL`-Zeilen die Werte eines Abschnitts nicht verschiebt. | hoch | tief | ungeprüft |
| 5 | **Gleicher Weg:** Ein Haltepaar A→B bezeichnet im ganzen Zeitraum denselben physischen Weg; Umleitungen und geänderte Laufwege unter derselben Haltefolge sind selten. | hoch | mittel | ungeprüft; im September 2026 laufen 145 Abschnitte in der Soll-Zeit rückwärts, vermutlich Umleitungen (Log 2026-10-06) |
| 1 | **Echte Messung:** Zeiten mit Status `REAL` sind an allen Schweizer Halten tatsächlich gemessen, mit vergleichbarer Genauigkeit, und nicht nachträglich ergänzt oder interpoliert. | hoch | hoch | ungeprüft |
| 4 | **Reihenfolge stabil:** Die Zeilenreihenfolge (`ZEILE`) ist in allen Monaten die Fahrreihenfolge einer Fahrt, nicht nur im geprüften September 2026. | hoch | hoch | gilt für September 2026 (Log 2026-10-06); andere Monate ungeprüft |
| 9 | **Ausfälle verzerren nicht:** Abschnitte mit Ausfällen wegzulassen verschiebt die Rangliste nicht wesentlich, obwohl Ausfälle sich an Störungstagen mit hohen Verspätungen häufen. | hoch | hoch | ungeprüft |
| 10 | **Genug Fahrten:** Pro Abschnitt bzw. Halt und Zeitfenster gibt es genug gemessene Fahrten, um ein systematisches Muster von Zufall zu unterscheiden, auch für Abschnitte über den Fahrplanwechsel hinweg. | hoch | hoch | ungeprüft |
| 3 | **Abdeckung über den ganzen Zeitraum:** Die `REAL`-Abdeckung ab 2025-07 ist in beiden Fahrplänen ähnlich wie im geprüften September 2026. | mittel | tief | September 2026: 96.2 % an Schweizer Halten (Log 2026-10-06); andere Monate ungeprüft |
| 8 | **Referenzwert genügt:** Nach Abzug eines Referenzwerts je Soll-Haltezeit misst die Haltverspätung den Betrieb und nicht mehr die Fahrplanrundung. | mittel | mittel | ungeprüft |
| 6 | **Zuordnung zu data.sbb.ch:** Abschnitte von Halt zu Halt lassen sich den Streckenabschnitten, Kilometrierungspunkten und Zugzahlen von data.sbb.ch eindeutig zuordnen. | mittel | hoch | ungeprüft; Daten von data.sbb.ch noch nicht geladen |
| 7 | **Rundung neutral für Abschnitte:** Die Minutenauflösung der Soll-Zeiten verzerrt die Streckenverspätung nicht systematisch je Abschnitt (wie sie es bei der Haltverspätung tut). | mittel | hoch | ungeprüft |
