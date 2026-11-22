# Prompt für die Claude-Desktop-App (Code-Tab, Ordner `/Users/timkiebler/Hackathon/START`)

Alles ab der Linie unten in eine neue Session kopieren.

---

Du arbeitest im Repo `/Users/timkiebler/Hackathon/START`. Wir testen Preisquellen aus dem Netz gegen die versteckten fairen Werte `t` alter Fälle einer Versicherungs-Challenge. Die Pipeline steht schon in `research/prices/`:
- `normalize.py` führt `norm/*.csv` und `raw/baupreislexikon/manual.csv` zu `prices.csv` zusammen
- `match.py` ordnet jeder Testzeile pro Quelle einen Preis zu
- `compare.py` schreibt die Rangliste nach `report.md`

Es fehlen noch zwei Quellen, die sich nur im Browser abrufen lassen. Nimm dafür den eingebauten Browser der App, nicht curl. Arbeite nur an diesen zwei Aufgaben.

## Regeln

- **Login:** baupreislexikon.de braucht einen Login. Bitte den Nutzer, sich im Browser selbst anzumelden, und tippe nie ein Passwort ein.
- **Nur lesen:** Lies nur Seiten, die ein normaler Nutzer sieht. Kein Auslesen von APIs oder Tokens, kein Massenabruf, nichts kaufen, keine Formulare absenden außer Suchfeldern.
- **Keine Werte erfinden:** Fehlt ein Preis oder ist er hinter einer Bezahlschranke (z. B. „PLUS“-Lizenz), lass die Zelle leer und schreib den Grund in die Antwort.
- **Rohdateien:** Sie gehören nach `research/prices/raw/<quelle>/`, das ist gitignored. Python, das sie liest, läuft mit `python3 -I`.
- **Kein Commit.** Am Ende zeigst du nur das Ergebnis.
- **Nicht anfassen:** Lass `match.py`, `compare.py`, `testset.json` und `past-cases/` unverändert. Zahlen dürfen nicht an die Grenzen angepasst werden.

## Aufgabe 1: baupreislexikon.de, 7 Positionen

Lies `research/prices/raw/baupreislexikon/manual.csv`. Spalten:
`fall,zeile,suchbegriff,position_bpl,einheit,menge,preis_min,preis_mittel,preis_max,netto_brutto,plz`

Für jede der 7 Zeilen:

1. **Suchen:** Gib den `suchbegriff` (gekürzt auf die Kernbegriffe) in baupreislexikon ein, Region bzw. PLZ **80331**. Nimm die passendste Position. Gibt es keine Komplettposition, nimm die Hauptposition. Beispiele: bei 7/1 „Leckortung“ plus „Fitting erneuern“ als zwei Positionen, bei 8/x die Entsorgung bzw. Deponiegebühr.
2. **Eintragen:**
   - `position_bpl`: Titel der Position, bei mehreren Positionen mit „ + “ verbunden
   - `einheit`: z. B. Stk, m³, t, h, psch
   - `menge`: die Menge, auf die sich die Rechnungszeile bezieht. Wo nichts klar ist, 1. Für 8/3 (Grünschnitt eines großen Baums) 4 m³ bzw. 0,8 t, für 8/4 (Wurzelstock unter 1 m³) 1 m³ bzw. 0,8 t, für 8/2 (eine Schuppen-Glasscheibe) 1 Stk.
   - `preis_min`, `preis_mittel`, `preis_max` pro Einheit. Bei mehreren Positionen die Summe der Einzelpreise × ihrer Menge, dann `menge` = 1.
   - `netto_brutto`: netto oder brutto, wie angezeigt
3. **Belegen:** Speichere pro Position einen Screenshot oder ein PDF der Preisseite als `raw/baupreislexikon/c<fall>_l<zeile>.png` bzw. `.pdf`.

Zahlen mit Punkt als Dezimaltrenner, keine Tausenderpunkte. Kommas in Texten sind erlaubt, weil die Felder in Anführungszeichen stehen.

## Aufgabe 2: Apple-Reparaturpreise für MacBooks

**a) Self Service Repair Store**, https://selfservicerepair.eu/de-de (Land Deutschland), Modelle:
- MacBook Pro 14" (alle Generationen, die angeboten werden: M1 Pro/Max, M2, M3, M4 …)
- MacBook Air 13" und 15"

Je Modell gesucht:
- **Display** (komplette Display-Einheit)
- **Gehäuse:** Top Case mit Akku/Tastatur und Bottom Case

Notiere je Teil:
- Preis in EUR, wie angezeigt
- die Rückgabegutschrift für das Altteil, falls angezeigt
- Name und Generation des Modells

Speichere jede Teileseite als HTML (Webseite komplett) oder PDF nach `research/prices/raw/apple/`.

**b) Apple-Reparaturkosten**, https://support.apple.com/de-de/mac-laptops/repair?services=service (Kostenschätzung außerhalb der Garantie, ohne AppleCare). Erfasse für dieselben Modelle den Preis für „Display beschädigt“ und „sonstiger Schaden“ (Gehäuse bzw. Unfallschaden), falls angezeigt. Seite als PDF oder Screenshot nach `raw/apple/`.

**c) CSV schreiben:** `research/prices/norm/apple_manual.csv`, nicht `apple.csv`, denn die wird von `fetch_norm.py` überschrieben. Header exakt so:

```
source,item,unit,price_gross_eur,region,date,url,note,tag
```

Pro Teil bzw. Preis eine Zeile:
- `source`:
  - `apple_ssr` für die Teilepreise aus a)
  - `apple_repair` für Apples Reparaturpreis aus b)
- `item`: beginnt mit dem Modellnamen in der Form `MacBook Pro 14" M3 Display` bzw. `MacBook Air 13" M2 Top Case`. Der Text „MacBook Pro 14“ muss so drinstehen, `match.py` filtert darauf.
- `unit`: `pcs`
- `price_gross_eur`: Bruttopreis vor Abzug der Gutschrift, Punkt als Dezimaltrenner
- `region`: `DE`
- `date`: `2026-11`
- `url`: die Seite
- `note`: z. B. `Rückgabegutschrift 123.45` oder `Kostenschätzung ohne AppleCare`
- `tag`:
  - `laptop_display` für das Display bzw. „Display beschädigt“
  - `laptop_housing` für Top Case, Bottom Case bzw. sonstigen Schaden

## Abschluss

1. Im Ordner `research/prices` ausführen:
   `python3 -I normalize.py && python3 -I match.py && python3 -I compare.py`
2. Antworte kurz mit:
   - der neuen Rangliste aus der Konsolenausgabe
   - den Zeilen zu `baupreislexikon`, `apple_ssr` und `apple_repair` aus `report.md` (Abschnitt „Match details“)
   - welchen Positionen oder Preisen du nicht finden konntest und warum
