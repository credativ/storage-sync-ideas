[//]: # (@pandoc@\newpage@)
Dieses Dokument beschreibt die Vorgehensweise, um ein synchronisationsfähiges
Unison-Paar auf Rocky Linux 8 Basis zu erhalten.

# Betriebsvoraussetzungen

Der im Rahmen dieser Dokumentation relevante Unison-Betriebsmodus ist eine
Synchronisation über SSH. Vom Betrieb im Socket-Modus rät die
Upstream-Dokumentation ab. Ein mindestens einseitiger SSH-Zugriff ist daher
zwingend erforderlich.

Die SSH-Verbindung muss ausreichend performant sein, um mit der Änderungsrate
der zu synchronisierenden Nutzdaten mithalten zu können.

# Grenzen

Unison synchronisiert Verzeichnisse mit dortigen Unterverzeichnissen und
Dateien, bei Bedarf inklusive ihrer Berechtigungen, des Besitzers und Gruppe.
Dies geschieht nicht durch das Replizieren von Systemaufrufen, sondern durch
"Lesen-Vergleichen-Schreiben", so dass eine Dateiumbenennung effektiv als
Synchronisation zweier Dateien ausgeführt wird.

Konsistenz wird "irgendwann" erreicht, d.h. es gibt im Normalfall (ohne
`atomic`) keine Garantien oder Aussagen zu dateiübergreifenden Eigenschaften.
Synthetisches Beispiel:

* Zwei Dateien mit unterschiedlichem Inhalt in einem Verzeichnis `V` werden
  lokal mittels `renameat2(..., RENAME_EXCHANGE)` vertauscht. Die Invariante,
  dass sich die Inhalte unterscheiden, bleibt dabei erhalten.
* Unison bemerkt Inhaltsänderungen in beiden Dateien und stößt die
  Synchronisation an. Auf der anderen Seite wird die obige Invariante nicht
  eingehalten.

Falls der Verzeichnispfad `V` stattdessen als `atomic` (siehe `man`page)
deklariert wurde, gilt:

* Für einen kurzen Zeitraum existiert `V` nicht.
* Vor der Synchronisation geöffnete Dateideskriptoren aus `V` betreffen
  mittlerweile gelöschte Dateien.

Generell gibt es keine Garantien zu langlebigen Dateideskriptoren von zu
synchronisierenden Daten.

Systemübergreifendes File-Locking wird nicht unterstützt.

# Funktionsdesign

Analog zu `rsync` über SSH muss `unison` im SSH-Modus auf beiden Seiten eines
Synchronisationspaares installiert sein. Die Seite, auf dem `unison` primär
gestartet wird, sei es manuell über ein Terminal oder vom Service Manager,
verbindet per SSH auf die andere Seite des Paares und führt dort eine sekundäre
`unison`-Instanz aus.

Es werden prinzipiell Änderungen beider Seiten berücksichtigt, die
Synchronisation ist damit bidirektional. Über ein internes Archiv, das den
Zustand des lokalen Synchronisationsverzeichnisses ("`root`") dokumentiert,
kann Unison ermitteln, welche lokalen Änderungen seit der letzten
Synchronisation stattgefunden haben.

Wenn Unison feststellt, dass eine Datei seit dem letzten Synchronisationslauf
nur auf einer Seite verändert worden ist, kann es diese konfliktfrei, ohne
Nutzerinteraktion auf die andere Seite übertragen.

## Konfliktresolution

Konflikte entstehen, wenn zwischen zwei Synchronisationsläufen ungleichartige
Änderungen auf beiden Seiten stattgefunden haben. Je nach Situation werden
Konflikte unterschiedlich behandelt oder ignoriert:

* Bei manuellem Aufruf des interaktiven Modus über ein Terminal kann der
  Benutzer für jeden Konfliktfall einzeln entscheiden, welche Seite gewinnen
  soll.
* Im Batch-Modus werden Konflikte übersprungen, falls keine Präferenz
  (`prefer`) definiert ist.
* Konflikte werden automatisch aufgelöst (`prefer`).
