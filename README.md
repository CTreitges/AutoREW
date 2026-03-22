# AutoREW - PA-Einmessungstool mit REW API

AutoREW ist ein Python-basiertes Automatisierungstool für die professionelle Einmessung von PA-Systemen. Es nutzt die API von [Room EQ Wizard (REW)](https://www.roomeqwizard.com/), um komplexe Mess- und Optimierungsprozesse in einem geführten Workflow zu automatisieren.

Das Tool eignet sich ideal für Veranstaltungstechniker und System-Engineers, die Konsistenz und Effizienz bei der Einmessung von Lautsprechersystemen (Main L/R, Subs, Delays, Fills, Monitore) anstreben.

## Hauptfunktionen

*   **Vollautomatisierte REW-Steuerung:** Fernsteuerung von Sweeps, Generator-Signalen und SPL-Metern über die REW API.
*   **Workflow-Presets:** Vordefinierte Setups für verschiedene Szenarien (Konferenz, Musik-Stereo, Multi-Zone PA, Monitor-Wedges).
*   **Zonen-Management:** Einfache Verwaltung von verschiedenen Beschallungszonen mit individuellen Kanälen und Messpositionen.
*   **Automatisches Alignment:** Unterstützung bei SPL-Alignment (Pegelanpassung) und Time-Alignment (Verzögerungszeit-Berechnung).
*   **EQ-Optimierung:** Automatische Generierung von Filter-Settings basierend auf Zielkurven direkt in REW.
*   **Berichtserstellung:** Export von Messergebnissen und System-Reports (PDF).
*   **Moderne GUI:** Benutzerfreundliche Oberfläche basierend auf PyQt6.

## Voraussetzungen

*   **Python 3.10+**
*   **Room EQ Wizard (REW)** (Version mit aktivierter API, i.d.R. ab V5.20+)
*   **Netzwerkzugriff:** AutoREW muss die REW API über TCP/IP erreichen können (standardmäßig localhost:4735).

## Installation

1.  Repository klonen:
    ```bash
    git clone https://github.com/DeinBenutzername/AutoREW.git
    cd AutoREW
    ```

2.  Virtuelle Umgebung erstellen und aktivieren:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # Linux/macOS:
    source .venv/bin/activate
    ```

3.  Abhängigkeiten installieren:
    ```bash
    pip install -r requirements.txt
    ```

## Nutzung

1.  **REW starten:** Öffnen Sie Room EQ Wizard und stellen Sie sicher, dass die API unter `Preferences -> API` aktiviert ist.
2.  **AutoREW starten:**
    *   Über die Batch-Datei (Windows): Doppelklick auf `start.bat`
    *   Über die Konsole: `python main.py`
3.  **Verbindung herstellen:** In der GUI die Host-Adresse und den Port von REW eingeben und auf "Verbinden" klicken.
4.  **Preset wählen:** Wählen Sie ein passendes Preset (z.B. "Musik (Stereo + Sub)") aus.
5.  **Workflow durchlaufen:** Folgen Sie den Anweisungen in den Tabs:
    *   **Zonen-Setup:** Konfiguration der Ausgänge und Zonen.
    *   **Messung:** Durchführung der automatisierten Sweeps für jede Zone und Position.
    *   **Analyse:** SPL- und Time-Alignment durchführen.
    *   **Export:** Zusammenfassung der Filter-Settings und Generierung des Reports.

## Projektstruktur

*   `autorew/`: Das Hauptpaket
    *   `analysis/`: Logik für Alignment, EQ-Generierung und Reports.
    *   `ui/`: GUI-Definitionen und Widgets.
    *   `workflow/`: Engine für den automatisierten Messablauf und Presets.
    *   `rew_client.py`: Client für die Kommunikation mit der REW API.
*   `main.py`: Einstiegspunkt der Anwendung.
*   `requirements.txt`: Python-Abhängigkeiten.
*   `start.bat`: Schnelles Startskript für Windows-Systeme.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe die [LICENSE](LICENSE) Datei für Details (falls vorhanden).
