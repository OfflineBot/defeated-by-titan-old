# 05 · Spielablauf, HUD, Steuerung

## Der Loop

1. **Hub** (sichere Garnison): Start- und Rückkehrort. **F am Missionsbrett** öffnet die
   Übersicht, F blättert, Halten startet den Einsatz.
2. **Sortie**: Missionstypen — Tutorial · Skirmish (Recruit/Veteran/Elite) · Parcours
   (reine Bewegung auf Zeit) · Breach · Eskorte · Rettung/Halten. Ziele und Kill-Zähler
   im HUD.
3. **Debrief**: XP, Verdienst, Statistik.
4. **Progression** („ganz ausbauen"): Verdienst fließt in Gear — Klingen-Stufen,
   Tankgröße, Haken-Parameter. Punkte sichtbar und ausgebbar; alles wird gespeichert.
5. **Tod/Scheitern**: zurück in den Hub; Missionsfortschritt weg, Gear bleibt.

Multiplayer ist von Anfang an **mitgedacht** („richtig bauen") — nichts wird
Single-Player-verdrahtet, auch wenn der Netzcode später kommt. Sound liefert der
Spieler selbst zu.

## HUD und Lesbarkeit

- **Fadenkreuz = X**: vier Striche, 45° rotiert, **Mitte komplett leer**; Größe und
  Farbe einstellbar; dünner Kontrastrand, damit es überall liest. Keine Kreise, keine
  Ringe, keine Buchstaben in der Mitte — ersatzlos gestrichen.
- **Farbsemantik:** Cyan = hier hält ein Seil (auch auf Titanenkörpern) · Bernstein =
  Cortex im Visier · Weiß = frei/nichts.
- Gasanzeige, Klingen-Pips, Leben, Missionsziel — alles am Rand. **Die Bildmitte
  gehört dem Spiel.**
- **Einstellungen im Spiel** (Escape): Empfindlichkeit, FOV, Assist-Stärke/-Modus,
  Haken Toggle/Hold, Fadenkreuz-Größe/-Farbe, **alle Keybinds frei** (Konflikt = Tausch).
  Änderungen wirken sofort und werden gespeichert.

## Steuerung (Standard)

| Eingabe | Wirkung |
|---|---|
| WASD | Laufen · unter Seil: W Schub in Blickrichtung, A/D tangential um den Anker, S löst den Zug |
| Maus | Blick/Ziel; hängend seitlich ~±80° begrenzt |
| Q / E | Haken links/rechts — Tipp setzt (Toggle), Tipp auf verankert = neu werfen, lang = lösen |
| Mausrad | Seil-Spreizung |
| Maus L / R | Klinge links/rechts (sichtbarer Bogen) |
| Space | Gas-Boost |
| Ctrl | Seil aktiv einziehen |
| Shift | Sprint (Feinabstimmung offen) |
| F | Interagieren / Missionsbrett |
| Escape | Menü/Einstellungen |
