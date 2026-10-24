# Design: Fahrer-App – Wiegescheine per KI auslesen und Mengen auswerten

Datum: 2026-10-24
Repo: maxim7578/Maximilian
Status: ENTWURF (Entscheidungen des Gründers stehen fest, an echten Scheinen noch nicht getestet)

## Ziel

Der Fahrer fotografiert den Wiegeschein. Die App erkennt Sorte und Netto-Gewicht, ordnet den Schein dem Fahrer und seinem Fahrzeug zu und speichert ihn. Der Admin sieht, wie viel jeder Fahrer entsorgt hat: heute, pro Monat, pro Jahr und über mehrere Jahre.

## Entscheidungen

| Thema | Entscheidung |
|---|---|
| Auslesen | KI-Bilderkennung (Claude mit Bildverständnis), keine einfache Texterkennung |
| Was die KI liest | Pro Zeile Sorte, Netto und Einheit. Dazu das gedruckte Gesamt-Netto als Kontrollwert (falls vorhanden) und das Kennzeichen, nur für den Abgleich. Sonst nichts: kein Brutto, keine Tara, kein Datum, keine Scheinnummer. |
| Zuordnung zum Fahrer | Über den Login. Jeder Fahrer hat sein Fahrzeug im System. |
| Kennzeichen-Abgleich | Ja: Das gelesene Kennzeichen muss zum Fahrzeug des eingeloggten Fahrers passen. |
| Sorten | PPK (1.04 und B19 zusammen), AZV, Folie 98/2, Holz, Sperrmüll, Mischschrott |
| Mehrere Sorten pro Schein | Ja, nicht jeder Schein hat nur eine Sorte |
| Einheit | kg oder Tonnen, wechselt je Schein. Die KI erkennt sie, intern wird alles in kg gespeichert. |
| Datum | Zeitpunkt des Hochladens. Der Admin kann es ändern. |
| Auswertung | Nur für den Admin: pro Fahrer, Sorte, Tag, Monat und Jahr, jahrelang |

## Ablauf für den Fahrer

1. Foto vom Schein aufnehmen.
2. Die App schickt das Foto an eine Funktion im Hintergrund, die die KI aufruft.
3. Die App zeigt die erkannten Zeilen, zum Beispiel „PPK – 12,48 t = 12.480 kg“, und das erkannte Kennzeichen.
4. Der Fahrer bestätigt oder korrigiert eine Zeile, löscht sie oder fügt eine fehlende hinzu.
5. Ist alles in Ordnung, wird der Schein gespeichert. Bei einer Auffälligkeit (siehe Prüfregeln) bekommt er den Status „Zu prüfen“.

## Was die KI zurückgibt

Die Ausgabe wird fest vorgegeben (strukturiert), nie als freier Text:

```json
{
  "kennzeichen": "XX-AB 123",
  "gesamt_netto": { "wert": 15.2, "einheit": "t" },
  "positionen": [
    { "sorte": "PPK", "netto": { "wert": 12.48, "einheit": "t" } },
    { "sorte": "Folie 98/2", "netto": { "wert": 2720, "einheit": "kg" } }
  ]
}
```

- Ist ein Wert nicht lesbar, steht dort `null`. Die KI darf nie raten.
- Die App rechnet jede Position in kg um und speichert Wert und Einheit zusätzlich so, wie sie auf dem Schein stehen.

## Sortenzuordnung

| Sorte in der App | Erkennt die KI auch als |
|---|---|
| PPK | „1.04 Kartonagen (B19)“, „1.04.00 Verpackungen aus Papier und Karton (B19)“, „Kaufhausaltpapier 1.04“ (AVV 150101, alle zählen als PPK) |
| AZV | „Abfall zur Verwertung“, „Gemischte Abfälle (zur Verwertung)“ (AVV 200301) – **zu bestätigen** |
| Folie 98/2 | „PE-Folien, 98/2“ (AVV 150102) |
| Holz | Holz |
| Sperrmüll | Sperrmüll |
| Mischschrott | Mischschrott, Mischrott |

Steht etwas anderes auf dem Schein, ist die Sorte „unbekannt“ und der Schein kommt zu „Zu prüfen“. Die Bezeichnungen oben stammen aus den fünf Testscheinen. Für Holz und Mischschrott gibt es noch keinen Beispielschein. „Gemischte Verpackungen“ (AVV 150106, Testschein 2) passt zu keiner der sechs Sorten und ist offen.

## Datenmodell (neu)

In der App gibt es heute keine Tabelle für Wiegescheine. Gesehen habe ich Fahrer, Fahrzeugübergabe und Fahrzeugbestand.

**Wiegeschein**
- Fahrer und Fahrzeug (aus dem Login)
- Foto
- Zeitpunkt (Hochladen, vom Admin änderbar)
- Status: bestätigt oder zu prüfen, dazu der Prüfgrund
- gelesenes Kennzeichen
- Gesamt-Netto als Kontrollwert (kg)

**Position** (mehrere pro Schein)
- Sorte
- Netto in kg
- gelesener Wert und gelesene Einheit
- „vom Fahrer geändert“ (ja oder nein)

Monats- und Jahressummen werden **nie gespeichert**, sondern immer aus den Positionen berechnet. So bleiben die Auswertungen jahrelang richtig, auch wenn der Admin später etwas korrigiert.

## Prüfregeln („Zu prüfen“)

Ein Schein bekommt den Status „Zu prüfen“, wenn eines davon zutrifft:

- Das Kennzeichen passt nicht zum Fahrzeug des Fahrers, oder es ist nicht lesbar. Verglichen wird ohne Leerzeichen und Bindestriche und ohne Unterschied zwischen Groß- und Kleinschreibung.
- Eine Sorte ist unbekannt.
- Ein Netto fehlt, ist nicht lesbar oder null, oder die Einheit ist unklar.
- Die Summe der Positionen weicht um mehr als **2 kg** vom gedruckten Gesamt-Netto ab (Vorschlag). Eine kleine Toleranz ist nötig: Auf Testschein 3 ergeben die Zeilen 651 kg, gedruckt sind 650 kg.
- Die Summe aller Positionen eines Scheins liegt über **30.000 kg** (Vorschlag, bitte bestätigen).
- Mögliches Duplikat: gleicher Fahrer, gleiche Positionen, innerhalb von **10 Minuten** (Vorschlag, bitte bestätigen), oder dasselbe Foto zweimal.

**Vorschlag:** Scheine mit „Zu prüfen“ zählen erst in die Summen, wenn der Admin sie freigibt oder korrigiert. Sie stehen in einer eigenen Liste mit ihrer Menge, damit nichts unbemerkt fehlt.

## Ansicht für den Admin

- Kopfzahlen: Netto-Summe für **Heute**, **Dieser Monat**, **Dieses Jahr** und einen frei wählbaren Zeitraum (in kg und in Tonnen).
- Tabelle pro Fahrer und Sorte für den gewählten Zeitraum.
- Monatsübersicht über mehrere Jahre mit Vergleich zum Vorjahr.
- Liste aller Scheine mit Foto, Positionen und Status.
- Prüfliste mit allen Scheinen auf „Zu prüfen“.
- Korrekturen durch den Admin werden protokolliert: wer, wann, alter und neuer Wert.
- Vorschlag: Fahrer sehen nur ihre eigenen Scheine.

## KI-Anbindung

- Die Funktion läuft im Hintergrund der App. Der API-Schlüssel liegt dort als geheimer Wert und nie in der App auf dem Handy.
- Modell: Start mit `claude-haiku-5-5` und `claude-sonnet-5-5` im Vergleich auf den Testfotos. Genommen wird das günstigere Modell, das die Kriterien unten erreicht.
- Die Sortenliste steht fest im Auftrag an die KI, die Ausgabe ist strukturiert vorgegeben.
- Das Foto wird vor dem Versand verkleinert.
- Das Foto geht zur Erkennung an die Claude-Schnittstelle. Wiegescheine enthalten Geschäftsdaten. Ob dafür ein Vertrag zur Auftragsverarbeitung nötig ist, muss vor dem Einsatz geklärt werden.

## Test vor dem Einbau

Mit den Fotos echter Scheine, darunter mindestens je einer mit Tonnen, mit kg, mit mehreren Sorten und ein schlechter (schief, Schatten, verblasst).

Kriterium: Bei den Testfotos wird **kein falscher Wert still übernommen**. Jede Sorte und jedes Netto ist entweder richtig oder als „Zu prüfen“ markiert. Zusätzlich wird gezählt, wie oft Sorte und Netto exakt stimmen.

## Testfälle aus fünf echten Scheinen

Die fünf Scheine (CamScanner-PDFs vom 20. bis 23.10.2026) sind der Prüfstand für die Erkennung. Erwartet wird:

| Nr. | Aussteller | Kennzeichen | Positionen (Sorte → Netto) | Besonderheit |
|---|---|---|---|---|
| 1 | REMONDIS Saar Entsorgung | NF-RR 4500 | PPK → 320 kg | Beschriftung „NETTO(kg)“ |
| 2 | Mandausch Containerdienst | PI RR 4960 | gemischte Verpackungen → 480 kg (0,480 t), Sorte offen | Einheit t. Die Zeile „Betriebsstätten-/Brandschutzpauschale, 1,000 Stk“ ist keine Menge und wird ignoriert. |
| 3 | Degenkolbe Recycling | PI RR 4840 | PPK → 415 kg, AZV → 118 kg, Sperrmüll → 118 kg | Drei Sorten. Die Zeilen ergeben 651 kg, gedruckt sind 650 kg. Drei Wägungen, darunter „Tara/Brutto“. Das Netto steht als „Netto²“. |
| 4 | Knettenbrech + Gurdulic | PI RR 4910 | PPK → 560 kg (0,560 t) | Einheit t. Das Netto hat **keine Beschriftung**, es ist die dritte Zahl in der Zeile nach den beiden Wägungen. Das Kennzeichen steht vor „Eingang“. |
| 5 | REMONDIS Südwest (Dillingen) | NF-RR 4500 | Folie 98/2 → 410 kg | Beschriftung „NETTO(kg)“ |

Erkenntnisse daraus:

- **Jeder Aussteller hat ein anderes Layout.** Die Erkennung darf sich nicht auf feste Positionen oder die Beschriftung „Netto“ verlassen, deshalb kommt die KI-Bilderkennung zum Einsatz.
- **Einheit und Schreibweise wechseln.** Es gibt „3.330“ in der Spalte „Gewicht in kg“ (also 3330 kg) und „3,440 t“ (3,44 Tonnen). Die KI muss die Einheit aus der Spalte oder Zeile lesen, nicht aus dem Zahlenbild raten. Im Zweifel „Zu prüfen“.
- **Kennzeichen** stehen als „NF-RR 4500“ (mit Bindestrich) und „PI RR 4960“ (nur Leerzeichen). Der Abgleich muss beides gleich behandeln.
- **Nicht jede Zeile ist eine Menge.** Pauschalen in „Stk“ gehören nicht in die Summen.
- **Handschrift am Rand** (Filialnamen, Orte) wird nicht gelesen und ignoriert.
- **Hochladedatum und Scheindatum können auseinanderliegen.** Schein 2 trägt das Datum 20.10., wurde aber am 22.10. gescannt. Ohne gelesenes Datum zählt so ein Schein zum Tag des Hochladens. Am Monatsende kann das die Monatssumme verschieben.

## Offene Punkte

- Weitere Testscheine mit **Holz**, **Mischschrott** und möglichst einem schlechten Foto (schief, Schatten, verblasst). Die fünf vorhandenen sind saubere Scans.
- Welche Sorte ist **„gemischte Verpackungen“ (AVV 150106)**: AZV, Mischschrott oder eine siebte Sorte?
- Ist **„Gemischte Abfälle (zur Verwertung)“** wirklich AZV?
- Soll die KI zusätzlich das **Datum des Scheins** lesen? Das wäre ein weiteres Feld und würde die Monatssummen genauer machen (siehe Schein 2).
- Grenzwerte bestätigen: 30.000 kg pro Schein, 10 Minuten für Duplikate.
- Einverstanden damit, dass Scheine mit „Zu prüfen“ erst nach Freigabe in die Summen zählen?
- Wer ist Admin (Rollen)? Dürfen Fahrer einen gespeicherten Schein nachträglich ändern?
- Wo steht das Kennzeichen im System, am Fahrer oder am Fahrzeug? Die Verbindung zur Fahrer-App war beim Schreiben ausgefallen, ungeprüft.
- Datenschutz: Vertrag zur Auftragsverarbeitung für die Foto-Übertragung.
