# SBB Verspätungsanalyse — Projektanforderungen

> Konsolidiert aus der Aufgabenstellung (Projekt 24) und den Arbeitsrichtlinien DS-Projekt HS 2026.
> Diese Datei gehört ins Repository (z. B. `docs/requirements.md`) und kann in `CLAUDE.md` referenziert werden.

---

## Aufgabenstellung — Projekt 24

**Titel:** Wo entstehen und wo verschwinden Verspätungen im Schweizer Bahnnetz? Ausbreitungskarte aus den SBB IstDaten

**Betreuung:** Dr. Václav Pechtor, ZHAW IWI, Fachstelle Data Science, pect@zhaw.ch
**Team:** 2 Studierende

### 1. Impact (Der geschäftliche Wert)

Verspätungsminuten kosten Bahnbetreiber Geld (Anschlussbrüche, Personaleinsatz, Pönalen) und Fahrgäste Zeit. Gegenmassnahmen wirken lokal und sind teuer, sie müssen dort ansetzen, wo Verspätung entsteht. Messbar: Anteil des Verspätungszuwachses in den zehn wichtigsten Abschnitten oder Halten.

### 2. Context (Der geschäftliche Rahmen)

Fahrplanung und Betriebssteuerung eines Bahnbetreibers, exemplarisch SBB Personenverkehr. Stakeholder: Fahrplaner, Betriebssteuerung, Infrastrukturplanung. Kein Firmenpartner, alle Daten öffentlich. Betriebliche Ursachen (Rollmaterial, Personal, Anschlussregeln) sind nicht in den Daten.

### 3. Question (Die datengetriebene Entscheidungsfrage)

Welche Abschnitte und Halte vergrössern Verspätungen systematisch (Verstärker), welche bauen sie ab (Absorber), und wie stabil ist dieses Muster über Wochentage, Tageszeiten, Jahreszeiten und über den Fahrplanwechsel hinweg? Ergebnis ist eine Rangliste der Abschnitte und Halte, an denen eine Massnahme den grössten Netzeffekt hätte.

### 4. Data (Die Basis für die Lösung)

- **Quelle:** SBB IstDaten (Soll- und Ist-Zeiten jeder Zugfahrt an jedem Halt, opentransportdata.swiss, Archiv ab ca. 2018) und Haltestellenkoordinaten. Von data.sbb.ch: Züge pro Streckenabschnitt (jährlich, Personen- und Güterverkehr getrennt) als Auslastungsmass, Linie (Betriebspunkte), Kilometrierungspunkte.
- **Umfang:** 1 bis 2 Millionen Halte pro Tag über alle Betreiber (CSV). Ein Jahr für eine Region liegt im einstelligen GB-Bereich (DuckDB, Laptop). Die Eingrenzung des Raums ist eine erste Entscheidung des Teams.
- **Qualität:** Nur Zeilen mit Status REAL (AN_/AB_PROGNOSE_STATUS) sind gemessene Zeiten, PROGNOSE und GESCHAETZT werden getrennt behandelt, die Abdeckung unterscheidet sich je Betreiber. Die Daten enthalten Halte, keine Betriebspunkte der Infrastruktur, ein Abschnitt ist der Weg zwischen zwei aufeinanderfolgenden Halten derselben Fahrt. Ausfälle (FAELLT_AUS) häufen sich an Störungstagen und bleiben in den Daten. Durchfahrten haben keine Ist-Zeit. Fahrplanwechsel im Dezember: Ein Jahr umfasst zwei Fahrpläne.

### 5. Signal (Das zu erkennende Muster)

Zwei Differenzen pro Fahrt, getrennt ausgewertet:

- **Streckenverspätung:** Ankunftsverspätung am Halt B minus Abfahrtsverspätung am Halt A.
- **Haltverspätung:** Abfahrts- minus Ankunftsverspätung am selben Halt.

Aggregiert pro Abschnitt bzw. Halt und Zeitfenster: systematisch positiv heisst Verstärker, systematisch negativ Absorber.

### 6. Modelling & Evaluation (Die Lösung und Messung)

- **Methode:** Rekonstruktion der Abschnitte, deskriptive Aggregation pro Abschnitt und Zeitfenster, Darstellung auf der Netzgeometrie. Pro Abschnitt eine einfache Regression des Zuwachses auf die eingehende Verspätung: Die Steigung zeigt, ob ein Abschnitt einen konstanten Betrag addiert oder proportional verstärkt. Vergleich mit der Zugzahl pro Abschnitt. Kein Prognosemodell, keine Ursachenanalyse.
- **KPIs:** Anteil des positiven Verspätungszuwachses, den die Top-10-Abschnitte erklären, absolut, pro Fahrt und pro Streckenkilometer (sonst bildet die Rangliste nur Volumen und Länge ab). Stabilität der Rangliste über zufällig gezogene Zeitfenster und zwischen den beiden Fahrplänen des Jahres (Rangkorrelation).
- **Output:** Interaktive Netzkarte mit Verstärker- und Absorber-Abschnitten, reproduzierbares Repository, kurzer Bericht mit den zehn wichtigsten Abschnitten und einer Einschätzung, welche Art Massnahme dort infrage kommt.
- **Profil:** Python und Coding-Agenten (z. B. Claude Code) hilfreich. Entscheidend ist kritisches Prüfen der Ergebnisse.

---

## Arbeitsrichtlinien DS-Projekt HS 2026

**Betreuung:** Dr. Václav Pechtor, ZHAW IWI, Fachstelle Data Science, pect@zhaw.ch

### 1. Umgebung und Reproduzierbarkeit

- Python-Umgebung mit uv: `pyproject.toml` und `uv.lock` im Repository, Python-Version fixiert.
- Nach `git clone` genügen `uv sync` und die im README dokumentierten Befehle, um von den Rohdaten zu den Ergebnissen zu gelangen. Keine manuellen Zwischenschritte.
- README: Setup, Datenbeschaffung und die Befehle je Ergebnis (z. B. Daten laden, Pipeline ausführen, Karte oder App starten).
- Läuft auf dem Rechner jedes Teammitglieds oder vollständig in einer dokumentierten Cloud-Umgebung.
- Empfohlen: VS Code mit integriertem Terminal. Unter Windows Bash als Terminal-Profil (WSL oder Git Bash, in Git for Windows enthalten), da Shell-Skripte und Agenten-Werkzeuge Bash voraussetzen.

### 2. Notebooks, Code und Coding-Agenten

- Notebooks als reine Textdateien, diffbar in Git (z. B. marimo).
- Kein Google Colab: Umgebung nicht fixierbar (kein Lockfile), Notebooks im Pull Request nicht sinnvoll prüfbar, flüchtige Laufzeit (Daten und Pakete gehen verloren).
- Einsatz von Coding-Agenten wird erwartet (z. B. Claude Code, im Notebook mit marimo pair).
- Wiederverwendbare Logik als Funktionen in `src/`, Notebooks für Exploration und Ergebnisdarstellung.
- Agenten-Konfiguration (`AGENTS.md`, `CLAUDE.md`) im Repository.

### 3. Versionierung (Git und GitHub)

- Ein Repository pro Team. Bitte Betreuer von Beginn an einladen (GitHub: `vp-82`).
- `main` ist geschützt und jederzeit lauffähig, Arbeit in Feature-Branches.
- Merge nur per Pull Request, Review durch ein Teammitglied, das den Code nicht geschrieben hat.
- Commits klein und thematisch abgegrenzt, mit aussagekräftiger Commit-Message.
- Zugangsdaten und Rohdaten per `.gitignore` ausgeschlossen (z. B. `.env`, `data/raw/`).

### 4. Daten

- Rohdaten bleiben unverändert.
- Download-Skript mit Quelle, Abrufdatum und Prüfsumme.
- Abgeleitete Daten (z. B. bereinigte Tabellen, Aggregate, zugeschnittene Raster) als Parquet oder DuckDB, Raster als GeoTIFF.
- Ein gemeinsamer Ablageort pro Team für grosse oder zugeschnittene Extrakte (z. B. Cloud-Bucket, optional mit DVC versioniert, siehe Abschnitt 5).
- Selbst gesammelte, nicht erneut abrufbare Daten: ab dem ersten Tag versioniert und gesichert.
- Quellen- und Lizenzangaben der Datenanbieter im README.

### 5. Optionale Werkzeuge

*(nicht abschliessend — Einsatz im Projektlog begründen)*

| Werkzeug | Sinnvoll, wenn |
|---|---|
| DVC (Data Version Control) | Daten nicht erneut abrufbar sind oder grosse Extrakte im Team geteilt werden. Versioniert Daten neben dem Code, Remote z. B. GCS-Bucket. |
| dbt (dbt-duckdb) | die Pipeline überwiegend aus SQL mit mehreren Stufen besteht und Tests sowie Lineage gewünscht sind. |
| Google Cloud Platform | Rechenleistung oder gemeinsamer Speicher nötig ist. USD 50 Guthaben pro Person. Budget-Alarm einrichten, Setup dokumentieren. |

### 6. Qualitätssicherung

Jede zentrale Zahl im Bericht ist durch mindestens eine der folgenden Prüfungen abgesichert:

| Prüfung | Frage | Beispiel |
|---|---|---|
| Einfache Baseline | Ist das Ergebnis besser als die einfachste denkbare Lösung? | Modell gegen «Vorhersage = Mittelwert», Rangliste gegen «Sortierung nach Volumen». |
| Zufallsvergleich (Permutation) | Käme dasselbe Ergebnis auch durch Zufall zustande? | Labels zufällig neu verteilen, Kennzahl 1000-mal neu berechnen, echtes Ergebnis mit dieser Verteilung vergleichen. |
| Placebo | Findet die Methode einen Effekt, wo keiner sein kann? | Dieselbe Auswertung auf Tagen oder Gruppen ohne erwarteten Effekt. Ein «Effekt» dort deutet auf einen Methodenfehler. |
| Rechenprobe | Gelten Zusammenhänge, die exakt gelten müssen? | Teilsummen ergeben das Total, Anteile ergeben 100 %, keine negativen Fahrzeiten. |
| Stabilität | Bleibt das Ergebnis bei leicht anderen Bedingungen? | Top 10 aus zwei Zeiträumen, mit anderer Stichprobe oder anderer Annahme vergleichen. |

- Automatisierte Datentests (pytest oder dbt tests): Zeilenzahlen, eindeutige Schlüssel, Wertebereiche.
- Instabiles Ergebnis: ändert sich deutlich bei leicht anderer Annahme, anderem Zeitraum oder anderer Stichprobe.
- Null-Ergebnis: kein Zusammenhang oder kein Unterschied gefunden. Beides ist ein gültiges Resultat, wenn es belegt und offen berichtet wird.
- Jedes Teammitglied versteht den eigenen Teil im Detail und hat ein solides Verständnis der übrigen Teile.

### 7. Projektlog

- Eine Markdown-Datei im Repository (`docs/log.md`), Änderung im selben Pull Request wie der zugehörige Code.
- Einträge mit Datum, keine Prompt-Transkripte.

| Eintragstyp | Inhalt |
|---|---|
| Entscheidung | Entscheidung (inkl. Werkzeugwahl): Alternativen, Begründung, Beleg. |
| Annahme | Was angenommen wird, wie und wann es geprüft wird. |
| Hypothese | Vor der Analyse notiert, mit Erwartung. Danach Befund und Entscheidung (siehe Abschnitt 8). |
| KI-Einsatz | Aufgabe, Reflektion über die Delegation, Art der Prüfung, was übernommen oder verworfen wurde und warum. |

### 8. Vorgehen: iterativ und hypothesengetrieben (Vorschlag)

- Planung, Meilensteine und Arbeitsteilung legt das Team selbst fest (Teil der Bewertung).
- Fragestellung, Eingrenzung und Methode müssen nicht zu Beginn zu 100 % feststehen und werden über die Iterationen geschärft.
- Start: Repository und Umgebung aufsetzen, Daten an einer kleinen Stichprobe sichten, Durchstich (einfachste End-to-End-Pipeline bis zu einem ersten Ergebnis).
- Danach kurze Iterationen (1 bis 2 Wochen) nach folgendem Zyklus:

| Schritt | Inhalt |
|---|---|
| 1. Hypothese | Prüfbare Aussage mit Erwartung, vor der Analyse im Projektlog notiert. Betrifft Daten, Methode oder fachlichen Zusammenhang. Beispiele: «Die Daten decken den gewählten Raum vollständig ab», «Die Rangliste bleibt zwischen zwei Zeiträumen stabil». |
| 2. Kleinster Test | Einfachste Analyse, die die Hypothese stützen oder widerlegen kann, zuerst auf kleinem Datenausschnitt. |
| 3. Befund | Ergebnis mit der Erwartung vergleichen, Prüfungen aus Abschnitt 6 anwenden. |
| 4. Entscheidung | Weiterverfolgen, anpassen oder verwerfen. Begründung im Projektlog, nächste Hypothese ableiten. |

- Reihenfolge: zuerst die Hypothese, deren Scheitern das Projekt am stärksten verändern würde.
- Umfang wächst schrittweise: erst kleiner Ausschnitt, dann voller Raum und Zeitraum.
- Widerlegte Hypothesen sind ein Ergebnis und gehören in den Bericht (und allenfalls in die Präsentation).

### 9. Präsentation

- Zielpublikum: Stakeholder aus dem Abschnitt Context der Ausschreibung, keine Data Scientists.
- Das Publikum kennt danach die Antwort auf die Entscheidungsfrage, die Empfehlung, die Belastbarkeit des Ergebnisses und seine Grenzen.
- Schwerpunkt auf Ergebnis und Begründung, Technik nur so weit nötig.
- Zahlen und Karten sind selbsterklärend (Bezugsgrösse, Legende).
- Widerlegte Hypothesen und Kurswechsel aus dem Projektlog werden offen gezeigt.
- Aufbau, Form und Demo sind dem Team überlassen.
- Jedes Teammitglied beantwortet Fragen zum eigenen Teil im Detail und hat ein solides Verständnis des Ganzen.
