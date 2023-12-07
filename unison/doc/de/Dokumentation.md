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

## Betriebsmodi

* `unison` kann einmalig aufgerufen werden, so dass es nach einer einzelnen
  Synchronisierung terminiert. Bei einem interaktiven Aufruf (ohne `-batch`)
  wird der Benutzer unter Anderem für jede Veränderung, auch ohne Konflikte, vor
  die Wahl gestellt, in welche Richtung synchronisiert werden soll. Im
  Batch-Modus werden keine Rückfragen gestellt, und Konfliktfälle übersprungen,
  falls keine Präferenz definiert ist. Der Batch-Modus ist damit für Cron-Aufrufe
  geeignet.

* Der Betrieb im `repeat` Modus sorgt für eine langlebige Synchronisierung sich
  verändernder Daten und kann damit als Systemdienst aufgesetzt werden.  Der
  intervallbasierte `repeat`-Modus erzeugt zeitgesteuerte Synchronisationen der
  gesamten Synchronisationsverzeichnisse und ist damit gründlich aber bei vielen
  Daten auch potenziell langsam.
  Der watchbasierte `repeat`-Modus nutzt das Hilfsprogramm `unison-fsmonitor`
  um die Synchronisationsverzeichnisse auf Veränderungen zu überwachen und nur
  diese punktuell zu synchronisieren. Dies verspricht eine schnellere Reaktions-
  und Synchronisationszeit. Der `unison-fsmonitor` nutzt die `inotify`-API des
  Kernels.

## Übertragungsmethoden

In der Standardkonfiguration synchronisiert Dateien mittels eines internen
Übertragungsalgorithmus.

Darüber hinaus ist es möglich mit den Optionen `copyprog`, `copyprogrest`,
`copyquoterm`, `copythreshold` und `copymax` eine externe Übertragung mittels
`rsync` zu aktivieren und zu konfigurieren.
[Es ist möglich, dass die externe Übertragungsmöglichkeit in zukünftigen
Versionen wegfallen wird](https://github.com/bcpierce00/unison/issues/871).

## Änderungserkennung

Unison hat einen langsamen und einen schnelleren Änderungserkennungsmodus, der
jeweils mit der `fastcheck`-Option einstellbar ist. Der langsame Modus bezieht
unter die Inhalte von Dateien für eine Synchronisationsentscheidung des Inhalts
ein, während sich der schnelle Modus auf die `mtime` und Dateigröße verlässt.
Da die Modifikationszeit einer Datei beliebig rückdatierbar ist, kann der
schnelle Modus Inhaltsänderungen übersehen.

## Konfigurationsprofile

Unison arbeitet mit Kommandozeilenoptionen oder mit Konfigurationsprofilen, so
dass ein Aufruf von `unison <profilname>` bereits eine gewünschte
Synchronisation anstoßen kann. Zusätzliche Kommandozeilenoptionen können die
Konfiguration ergänzen, so dass der Service-Manager beispielsweise ein Profil
im `repeat`-Modus betreibt, während ein Benutzer den einmaligen manuellen Modus
nutzt. Das Ablageverzeichnis für Profildateien kann mit der `UNISON`
Umgebungsvariable beeinflusst werden.
