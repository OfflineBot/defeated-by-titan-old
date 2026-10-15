# Defeated by Titan — was das Spiel ist

Updated: 2026-10-15

Die Gameplay-Beschreibung. Kein Code, keine Dateien, keine Technik — nur das Spiel, so wie
es sich anfühlen soll und so, wie es durch Monate von Playtests festgelegt wurde. Jede
Regel hier hat sich im Spielen bewiesen oder wurde vom Spieler ausdrücklich so bestimmt.

---

## 1 · In drei Sätzen

Ein 3D-Low-Poly-Actionspiel über den Kampf gegen Titanen, im Geist von Attack on Titan.
Du bist ein Mensch mit dem **Vector Gear** — zwei Seilhaken, zwei Gastanks, zwei Klingen —
in einer Stadt, die der Menschheit nicht mehr gehört. Ein Titan stirbt **nur** durch einen
schnellen Schnitt in den **Cortex** im Nacken; alles andere macht ihn höchstens wütend.

## 2 · Die Welt und ihre Stimmung

Die Menschheit lebt in **drei konzentrischen Bastionsringen**: **Ashgate** außen,
**Ironrose** in der Mitte, **Highspire** innen. Der entscheidende Unterschied zur Vorlage:
**Der Krieg ist bereits verloren.** Ashgate ist vor langer Zeit gefallen. Die Vorhut
fliegt **Bergungsmissionen in die eigenen Ruinen** — keine Rückeroberungsfeldzüge.

Die Stimmung ist **elegisch, nicht Horror**: eine strukturell noch stehende, aber
verlassene Stadt unter einem Asche-Himmel. Gedämpfte, entsättigte Farben; Wärme bedeutet
immer etwas — Licht, Leben oder einen Titan. Drei Signalfarben sind heilig und kommen
nirgendwo sonst vor: **Cyan** (ankerbar / Seil), **Bernstein** (Cortex / Ziel),
**Karmin** (Gefahr).

Die Spielstadt Ashgate konkret: Fachwerkviertel mit Gassen und Dachlandschaft, eine
**monumentale Bastionsmauer** mit Toren (echte AoT-Mauer, zwei Tore: ein hartes, ein
weicheres), ein Fluss/Kanal mit Brücken und Ufertürmen, Ruinenfelder und Trümmer in den
offenen Flächen, eine Garnison als begehbares Gebäude. **Das Gelände muss dramatisch
sein** — Hügel, Terrassen, echtes Relief; „flach" ist ein abgelehnter Zustand. Höhe ist
nicht Dekoration, sondern Treibstoff: Jede Mauerkante, jeder Turm, jeder First ist eine
Sprosse für das Seil.

Wasser: Man schwimmt darin und wird langsam (Gas kostet dort mehr); **Wasser hält keinen
Haken**.

Der Spielbereich hat keine sichtbare Kante: eine unsichtbare Grenze hält den Spieler, und
wer durch einen Fehler hinausfällt, wird zurückteleportiert — niemals Tod durch den Rand.

## 3 · Die Säulen und das Tor

1. **Bewegung zuerst.** Das Spiel steht und fällt mit dem Schwingen. Kein Meta-System
   (Skilltree, Economy, Lineages, Raids, Kosmetik), bevor die Bewegung überzeugt.
2. **Das Tor:** Ein Blindtest gegen *Attack on Titan Revolution* mit zehn Testern — unsere
   Bewegung muss mindestens gleichziehen. Vorher wird nichts anderes ausgebaut.
3. **Lesbarkeit bei 60 m/s.** Jede visuelle Entscheidung wird daran gemessen, ob sie beim
   schnellen Schwingen noch funktioniert: Titan-Silhouetten, der Bernstein-Punkt, die
   Struktur der Stadt.

## 4 · Das Vector Gear — die Bewegung (das Herz des Spiels)

### Die Haken (Q = links, E = rechts)

- **Alles ist hakbar.** Jede Oberfläche, ohne Hardcoded-Punkte. Später ganz vereinzelt
  bewusste Ausnahmen („sehr wenig!") — die Regel bleibt: Was du siehst, hältst du.
- **Toggle, nicht Halten** (umstellbar in den Einstellungen): Ein Tipp setzt den Haken und
  er BLEIBT. Ein zweiter Tipp auf einen verankerten Arm = Seil weg, sofort neu raus auf
  den aktuellen Blickpunkt (Re-Fire in einem Zug). Langes Drücken = reines Lösen.
  Ein Fehlschuss löst die Rastung von selbst.
- **Der Marker lügt nie:** Wo die Markierung sitzt, landet das Seil — exakt, auch in
  voller Bewegung. Das war die wichtigste Einzelforderung des Spielers („das ist wichtig.
  und dann muss das seil auch dahin!!").
- Der Haken fliegt **sehr schnell und weit** (Richtung 500 m Reichweite), aber sichtbar —
  „nicht frame-perfekt, aber man soll sehen, wie es aufspannt".
- **Zwei Seile spreizen** links/rechts (die Arme zielen in Hemisphären); das Mausrad
  stellt ein, wie weit sie auseinander dürfen. Der Fächer ist dynamisch: eng beim
  schnellen Schwingen, offen beim Suchen.
- **Ziel-Assist einstellbar 0–100 %** plus drei Modi: FREI (reiner Strahl), ASSISTIERT
  (Snap nur im Fangwinkel — Standard), SNAP. Der Snap sucht **nur seitlich** („dann ist
  es auch besser einzuschätzen") — niemals rauf/runter relativ zum Fadenkreuz.

### Das Seil — die Regeln, die sich das Spiel erarbeitet hat

Diese Sätze sind Gesetz; jeder stammt aus einem Playtest:

1. **Das Seil ist eine Ratsche mit hartem Maximum.** Einmal eingezogen, wird es nie von
   selbst länger. Es hält als echte physische Grenze — am Limit wirst du auf die Kugel
   um den Anker gezwungen und schwingst.
2. **Verbunden heißt gezogen — immer, standardmäßig, auch vom Boden aus.** Haken rein,
   und es zieht dich sofort ran, ohne dass du hinsehen oder eine Taste drücken musst.
3. **W** = zusätzlicher Schub **in Blickrichtung** (obendrauf auf den Zug — vom Stand weg
   muss W den freien Zug deutlich schlagen, „dass man dort richtig hingezogen wird").
4. **A/D** = seitlich, **relativ zum Anker** („DAS IST WICHTIG") — tangential auf der
   Kugel. Der Grundzug bleibt dabei an, nur schwächer: je stärker seitlich, desto weniger
   Zug. A/D dürfen das Seil **niemals** verlängern.
5. **S** löst den Zug („S spannt nur, bewegt nicht"): Der Ranzieh-Anteil stoppt, nur die
   Seitwärtsbewegung bleibt; die Distanz darf dabei nicht wachsen. S zieht dich NIEMALS
   zum Seil hin.
6. **Ctrl** = aktives Einziehen (Reel) — deutlich stärker als der Grundzug.
7. **Zwei Seile gleichzeitig sind ein Zustand, kein Fehler:** Beide bleiben, du hängst
   gespannt dazwischen (sein Wort: „du hängst fest") — daraus baut man Stand-offs und
   präzise Positionen vor dem Nacken.
8. **Blickwinkel beim Hängen ist begrenzt** (~±80° seitlich), damit die Kamera nie hinter
   den eigenen Anker dreht.

### Gefühl und Energie

- **Die Welt ist schwer.** Hohe Gravitation (nach mehreren „zu leicht"-Verdikten immer
  weiter erhöht), kräftiger Sprung, Laufen 6 m/s — der Kontrast macht das Schwingen groß.
- **Schwung erhält Energie.** Ein guter Bogen trägt dich mit 30–60+ m/s; Herumschwingen
  um einen Anker ist richtig und gewollt, kein Overshoot-Fehler.
- **Gas ist die Ressource der Bewegung:** Boost (Space, stark), Seitensteuerung unter
  Seil, aktives Einziehen — alles kostet Gas. Leerer Tank = halbe Steuerkraft und kein
  Boost. Nachfüllen an Versorgungsstationen. Kosten spürbar, aber nicht knausrig
  („zum testen [viel]. später etwas runter. aber nicht soo viel").
- **Das FOV atmet mit der Geschwindigkeit** — in jede Richtung, weich öffnend, langsamer
  zurück („ein kleiner übergang"), nie ein Sprung.
- **Sprint-Stopp läuft aus statt zu rutschen** — gerutscht wird nur oberhalb einer
  Mindestgeschwindigkeit.

## 5 · Der Kampf

### Die Klingen

- Zwei Klingen (Maustasten links/rechts), als Paar geführt.
- **Der Schnitt ist ein sichtbarer Bogen nach vorn** — der Stahl kreuzt das Blickfeld auf
  genau den Ticks, die treffen können. (Die alte Version schnitt unsichtbar 90° seitlich —
  abgeschafft.)
- Klingen verschleißen mit Treffern (Schärfe sinkt), Ersatz gehört zum Gear.
- **Hitstop** beim Treffer: ein kurzer Einfrier-Moment verkauft den Impact.
- Treffer-Feedback auf dem Schirm (Treffermarke), Schadenszahlen als Ausbaustufe.

### Der Cortex — die einzige Art zu töten

- Im **Nacken**, nur **von hinten** erreichbar. **Nicht direkt sichtbar — „man muss es
  wissen"**: kein aufgemalter Schwachpunkt-Kreis; die Nackenpartie ist als dunkleres Band
  mit dezentem Bernsteinkern gestaltet, der Rest ist Spielerwissen.
- Der Schnitt zählt nur **schnell**: unterhalb einer Mindest-Durchfluggeschwindigkeit
  (Größenordnung 20 m/s) kratzt er nur. Der Durchflug am Nacken ist ein kurzes Fenster —
  Timing ist der Skill.
- Körpertreffer töten nie, haben aber Funktion: Sie staffeln (Stagger), verschleißen die
  Klinge und — beim Warden — öffnen die Deckung.

### Sekundäre Trefferzonen

Arme und Beine registrieren eigene Treffer. Die wichtigste Regel: **Der Warden deckt
seinen Nacken mit der Hand und öffnet nur, wenn man seine Arme frontal attackiert** —
erst der Arm-Treffer, dann der Nackenlauf. Zwei-Phasen-Kill als Design.

## 6 · Die Titanen — acht Arten, acht Verhalten

Größenklassen: klein ~8 m · mittel ~20 m · groß ~28 m · riesig ~42 m. Jede Art ist auf
einen Blick erkennbar (Statur, Haltung, Farbton) und verhält sich anders:

| Art | Klasse | Verhalten im Kampf |
|---|---|---|
| **Husk** | mittel | Der Standard: langsam, frontal, gnadenlos simpel — das Lernziel. |
| **Errant** | mittel | Schnell und schief: lehnt, schlängelt, bricht Angriffswinkel. |
| **Scuttler** | klein | Flink, springt mit kurzem Lunge-Sprint — schwer zu verfolgen, schnell tot. |
| **Weaver** | klein | Ausweichend; attackiert nur, was er **sieht** — von tot hinten kriegt man ihn nicht zum Öffnen, man muss die Flanke spielen. |
| **Warden** | groß | Die Deckung: Hand über dem Nacken, öffnet nur auf frontale Arm-Treffer. |
| **Lurker** | groß | Der Lauerer: steht, wartet, explodiert auf kurze Distanz — chast nicht. |
| **Chorus** | mittel | Der Rudel-Typ: symmetrisch, ruhig, in Paaren/Gruppen — teilt sich auf und flankiert. |
| **Bellower** | riesig | Der Rufer: hört **Gasgeräusch** und brüllt — zieht andere Titanen heran. Selten, ein Ereignis, kein Standardgegner. |

Titanen nehmen die Welt wahr (Sicht, beim Bellower Gehör) — Schleichen über Dächer ohne
Gasstöße ist eine echte Option. Ein toter Titan gibt jedes Seil frei, das an ihm hing.
Titanen sind selbst hakbar — an einem laufenden Titanen zu hängen ist legitimes Werkzeug.

## 7 · Der Loop

1. **Hub** (sichere Garnison): Hier steht man nach jedem Einsatz. Vom Hub aus startet
   alles — Türen/Pads zu den Missionen, **F am Brett öffnet die Missionsübersicht**,
   F blättert durch, Halten startet.
2. **Sortie**: Missionstypen — Tutorial, Skirmish (in Stufen Recruit/Veteran/Elite),
   Parcours (reine Bewegung auf Zeit), Breach, Eskorte, Rettung/Halten als
   Objective-Varianten. Ziele und Kill-Zähler sichtbar im HUD.
3. **Debrief**: Was der Einsatz brachte — XP, Verdienst, Statistik.
4. **Progression** („ganz ausbauen"): Verdienste fließen in Gear-Ausbau — Klingen-Stufen,
   Gastank-Größe, Haken-Parameter. Punkte sind sichtbar und ausgebbar; der Fortschritt
   wird gespeichert.
5. **Tod/Scheitern**: Zurück in den Hub, Fortschritt der Mission verloren, Gear bleibt.

Multiplayer ist von Anfang an **mitgedacht** („richtig bauen"): alles spieler-zählbar,
nichts Single-Player-verdrahtet — auch wenn der Netzcode später kommt. Sound liefert der
Spieler selbst zu („Ich liefere die Sounds").

## 8 · HUD und Lesbarkeit

- **Das Fadenkreuz ist ein X**: vier Striche, 45° rotiert, **Mitte komplett leer** —
  Größe und Farbe einstellbar. Jeder Strich trägt einen dünnen Kontrastrand, damit es
  auf jedem Untergrund liest. Keine Kreise, keine Ringe, keine Buchstaben in der Mitte —
  alles, was dort je stand, ist ersatzlos gestrichen („die kreise können ganz weg!").
- **Farbsemantik des Fadenkreuzes/Markers**: Cyan = hier hält ein Seil (auch auf einem
  Titanenkörper — der hält ein Seil). Bernstein = Cortex im Visier. Weiß = frei/nichts.
- Gasanzeige, Klingenzustand (Pips), Lebensanzeige, Missionsziel oben — alles am Rand,
  **die Bildmitte gehört dem Spiel**.
- **Einstellungen im Spiel** (Escape → Menü): Empfindlichkeit, FOV, Assist-Stärke und
  -Modus, Haken Toggle/Hold, Fadenkreuz-Größe/-Farbe, **alle Keybinds frei belegbar**
  (Konfliktauflösung durch Tausch). Änderungen wirken sofort, ohne Neustart, und werden
  gespeichert.

## 9 · Steuerung (Standardbelegung)

| Eingabe | Wirkung |
|---|---|
| WASD | Laufen · unter Seil: W Schub in Blickrichtung, A/D tangential um den Anker, S löst den Zug |
| Maus | Blick/Ziel; beim Hängen seitlich auf ~±80° begrenzt |
| Q / E | Haken links / rechts — Tipp setzt (Toggle), Tipp auf verankert = neu werfen, lang = lösen |
| Mausrad | Seil-Spreizung (wie weit die zwei Anker auseinander dürfen) |
| Maus L / R | Klinge links / rechts (Schwung mit sichtbarem Bogen) |
| Space | Gas-Boost |
| Ctrl | Seil aktiv einziehen |
| Shift | (Sprint — Feinabstimmung offen, Spieler-Erinnerung beim Playtest) |
| F | Interagieren / Missionsbrett |
| Escape | Menü/Einstellungen |

## 10 · Was dieses Spiel NICHT ist

- Kein Shooter, kein Soulslike, kein Builder. **Die Bewegung ist das Spiel**; der Kampf
  ist die Prüfung, wie gut du dich bewegst.
- Kein Meta-Fortschritt vor dem Bewegungs-Tor: Trait-Tree, Wirtschaft, Lineages, Raids,
  Kosmetik sind bewusst NACH dem Gate.
- Keine Horror-Inszenierung: Die Titanen sind unheimlich durch Größe, Stille und die
  verlorene Stadt — nicht durch Gore oder Jumpscares.
- Keine UI-Bevormundung: kein aufgemalter Schwachpunkt, kein Zielpfad, keine Minimap-
  Krücken. Das Spiel belohnt Wissen und Blick.

## 11 · Offene Geschmacksfragen (bewusst beim Spieler)

- **Wie dramatisch das Terrain genau wird** (Terrassen-Stadt, Schlucht, beides) — Richtung
  entschieden: „richtiges Terrain", deutlich mehr Relief; die Ausprägung urteilt sein Auge.
- Die genauen Gas-Kosten und die Gravitation als Feingefühl (immer am Playtest geeicht).
- Wie laut der Cortex-Bernstein leuchten darf, ohne Regel 10 zu brechen.
- Ob die Wach-Türme der Stadt als verkleidete Hebewerke bleiben oder durch Glockentürme/
  Speicher ersetzt werden — die Stadt braucht IRGENDETWAS Hohes, sonst stirbt die
  Seil-Lane (gemessen, nicht Geschmack).
