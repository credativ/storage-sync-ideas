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

## Fehlerverhalten

### Unvollständige Synchronisation

Nach einem oder auch während eines Synchronisationslaufs werden Statuszeilen
folgender Form geloggt:

[//]: # (@pandoc@\small@)
> ```
> Synchronization complete at HH:MM:SS  (X items transferred, Y skipped, 0 failed)
> ```
[//]: # (@pandoc@\normalsize@)

oder

[//]: # (@pandoc@\small@)
> ```
> Synchronization incomplete at HH:MM:SS  (X items transferred, Y skipped, Z failed)
> failed: example.txt
> failed: example.log
> ```
[//]: # (@pandoc@\normalsize@)

Unaufgelöste Konfliktfälle werden als `skipped` gezählt, während
Übertragungsfehler oder während der Übertragung veränderte Dateien als `failed`
markiert werden. Letztere werden beim nächsten Synchronisationslauf
abgearbeitet, und stellen damit nicht zwangsläufig ein schwerwiegendes Problem
dar.  Es ist dennoch ratsam, das Unison-Log auf Fehlermeldungen (`Error`,
`Failed`) hin zu überwachen, da manche Synchronisierungfehler beispielsweise
aufgrund fehlender Berechtigungen für einzelne Dateien (z.B.
`immutable`-Attribut) ein Dauerzustand sein könnten.

[//]: # (@pandoc@\small@)
> ```
> Failed [file.txt]: Error in deleting:
> Operation not permitted [unlink(/path/to/file.txt)]
> ```
[//]: # (@pandoc@\normalsize@)

### Neustartverhalten

Der `repeat`-Modus der 2.53.3 Version ist im Gegensatz zur 2.52 Version in dem
Sinne fehlertoleranter, dass Unison im `repeat`-Modus bei gewissen Fehlern
nicht mehr terminiert, sondern die ausstehende Aktion nach einer Pause
wiederholt probiert. Das ist insbesondere für den Watch-basierten
`repeat`-Modus bei einem Verbindungsfehler zum Unison-Partner vorteilhaft, da
`unison-fsmonitor`-Events zwischengespeichert und nach Verbindungswiederaufbau
abgearbeitet werden können. Als zweites konkretes Beispiel erwähnt der
[Commit](https://github.com/bcpierce00/unison/pull/830/commits/f53ad280350d6cdcb2f3f80898e5c5d8b7f2c556)
einen Abbruch des `unison-fsmonitor`.

### Terminierende Fehler

In die Kategorie terminierender Fehler fallen fatale Fehler, bei denen Unison
auch im `repeat`-Modus terminiert. Dazu gehören beispielsweise

* ein unerwartet leeres Synchronisationsverzeichnis (`root`) beim Unison-Start, oder
* Konfigurationsfehler.

Ein unerwartet leeres Synchronisationsverzeichnis tritt typischerweise auf,
wenn es sich dabei um einen Mountpoint handelt, der nicht beziehungsweise zu
spät eingebunden wurde. Im Allgemeinen ist von temporären Mounts unterhalb der
Synchronisationsverzeichnisse abzuraten, wenn Unison im Watch-basierten
`repeat`-Modus betrieben werden soll, da etablierte `inotify`-Watches nicht in
den Mountpoint übernommen werden.

### Archivdateifehler

Fehler aufgrund eines unerwarteten Zustands der Archivdateien sind fatal, aber
nicht terminierend. Im Allgemeinen wird sich ein solcher Fehlerzustand jedoch
nicht von alleine lösen.

Beispiel 1:

[//]: # (@pandoc@\small@)
> ```
> Fatal error: Internal error: On-disk archives are not identical.
>
> This can happen when both machines have the same hostname.
> It can also happen when one copy of Unison has been compiled with
> OCaml version 3 and one with OCaml version 4.
>
> If this is not the case and you get this message repeatedly, please:
>   a) Send a bug report to unison-users@seas.upenn.edu (you may need
>      to join the group before you will be allowed to post).
>      For information, see https://github.com/bcpierce00/unison/wiki
>   b) Move the archive files on each machine to some other directory
>      (in case they may be useful for debugging).
>      The archive files on this machine are in the directory
>        /var/lib/unison
>      and have names of the form
>        arXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
>      where the X's are hexadecimal numbers.
>   c) Run unison again to synchronize from scratch.
> ```
[//]: # (@pandoc@\normalsize@)

Beispiel 2:

[//]: # (@pandoc@\small@)
> ```
> Fatal error: Server: End_of_file exception raised in loading archive (this indicates a bug!)
> ```
[//]: # (@pandoc@\normalsize@)

Beispiel 3:

[//]: # (@pandoc@\small@)
> ```
> Fatal error: Warning: inconsistent state.
> The archive file is missing on some hosts.
> For safety, the remaining copies should be deleted.
>   Archive ar9e9edd866457bb789787bf4bb290cfba on host one.example should be DELETED
>   Archive ar9ae33d4fd332f66439606677bd2a804b on host two.example is MISSING
> Please delete archive files as appropriate and try again
> or invoke Unison with -ignorearchives flag.
> ```
[//]: # (@pandoc@\normalsize@)
