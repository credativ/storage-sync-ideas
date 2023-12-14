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

# Beziehen der Software

Da Rocky Linux Unison in keinem seiner Repositorys anbietet, muss die Software
aus den [Upstream-Sourcen](https://github.com/bcpierce00/unison) gebaut werden.
Dabei werden zwei Binaries `unison` und `unison-fsmonitor`, eine
englischsprachige `man`page und eine englischsprachige Dokumentation im
PDF-Format erzeugt.

Die Bauabhängigkeiten für Version 2.52 sind mit Hilfe der unter Rocky Linux 8
angebotenen Repositorys erfüllbar. Ältere Versionen sind aus
Interoperabilitätsgründen zu meiden.

Diese Dokumentation empfiehlt die Nutzung von mindestens Version 2.53.1 (Stand
Dezember 2023: 2.53.3) aufgrund der verbesserten Fehlertoleranz im
`repeat`-Modus.  Für deren Bau wird eine höhere Ocaml-Version vorausgesetzt,
die erst in den Repositorys von Rocky Linux 9 zur Verfügung steht. Für Rocky
Linux 8 gilt daher folgendes Vorgehen:

* Beziehen der Ocaml Source-RPM aus dem Rocky Linux 9 CRB-Repository
  (Stand Dezember 2023: Ocaml 4.11.x)
* Bau der bezogenen Ocaml Source-RPM unter Rocky Linux 8
* Installation von Ocaml 4.11.x unter Rocky Linux 8
* Bau von Unison 2.53.3

Es bietet sich an, die gebauten Binaries, die `man`page und die Dokumentation
zu paketieren. Im Anhang findet sich eine [Bauanleitung als
`Dockerfile`](#bauanleitung).

# Beispiele

Die folgenden Beispiele nutzen `passwd` und `sshpass` nur für das Demo-Setup.

[//]: # (yum install passwd sshpass ncurses procps)

## Demo-Setup und erster Lauf

System `secondary` betreibt den SSH-Dienst.

[//]: # (@pandoc@\small@)
> ```
> sh-4.4# podman run --name secondary -h secondary --rm \
>     --volume "$(realpath packaging)":/packaging \
>     --network=bridge:ip=10.88.1.2 --add-host primary:10.88.1.1 \
>     --tty --interactive rockylinux:8
> [root@secondary /]# yum install -y /packaging/rpms/unison-2.53.3-1.el8.x86_64.rpm
> [root@secondary /]# yum install -y passwd
> [root@secondary /]# echo -n somepassword | passwd --stdin root
> [root@secondary /]# yum -y install openssh-server
> [root@secondary /]# ssh-keygen -A
> [root@secondary /]# /usr/sbin/sshd
> ```
[//]: # (@pandoc@\normalsize@)

System `primary` betreibt Unison.

[//]: # (@pandoc@\small@)
> ```
> sh-4.4# podman run --name primary -h primary --rm \
>     --volume "$(realpath packaging)":/packaging \
>     --network=bridge:ip=10.88.1.1 --add-host secondary:10.88.1.2 \
>     --tty --interactive rockylinux:8
> [root@primary /]# yum install -y /packaging/rpms/unison-2.53.3-1.el8.x86_64.rpm
> [root@primary /]# yum install -y sshpass openssh-clients
> [root@primary /]# ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ''
> [root@primary /]# echo -n somepassword | sshpass ssh-copy-id \
>                -i /root/.ssh/id_ed25519.pub -o StrictHostKeyChecking=no secondary
> [root@primary /]# ssh secondary passwd -l root
>
> [root@primary /]# ssh secondary unison -version
> unison version 2.53.3 (ocaml 4.11.1)
>
> [root@primary /]# mkdir /srv/sync && ssh secondary mkdir /srv/sync
> [root@primary /]# unison /srv/sync/ ssh://secondary//srv/sync/ -batch -auto
> Unison 2.53.3 (ocaml 4.11.1): Contacting server...
> Connected [//primary//srv/sync -> //secondary//srv/sync]
>
> Looking for changes
> Warning: No archive files were found for these roots, whose canonical names are:
>     /srv/sync
>     //secondary//srv/sync
> This can happen either
> because this is the first time you have synchronized these roots,
> or because you have upgraded Unison to a new version with a different
> archive format.
>
> Update detection may take a while on this run if the replicas are
> large.
>
> Unison will assume that the 'last synchronized state' of both replicas
> was completely empty.  This means that any files that are different
> will be reported as conflicts, and any files that exist only on one
> replica will be judged as new and propagated to the other replica.
> If the two replicas are identical, then no changes will be reported.
>
> If you see this message repeatedly, it may be because one of your machines
> is getting its address from DHCP, which is causing its host name to change
> between synchronizations.  See the documentation for the UNISONLOCALHOSTNAME
> environment variable for advice on how to correct this.
>
>
>   Waiting for changes from server
> Reconciling changes
> Nothing to do: replicas have been changed only in identical ways since last sync.
>
> [root@primary /]# hostname | tee /srv/sync/primary
> [root@primary /]# ssh secondary 'hostname | tee /srv/sync/secondary'
>
> [root@primary /]# unison /srv/sync/ ssh://secondary//srv/sync/ \
>     -batch -auto -logfile /unison.log
> Unison 2.53.3 (ocaml 4.11.1): Contacting server...
> Connected [//primary//srv/sync -> //secondary//srv/sync]
>
> Looking for changes
>   Waiting for changes from server
> Reconciling changes
> new file ---->            primary
>          <---- new file   secondary
>
> 2 items will be synced, 0 skipped
> 8 B to be synced from local to secondary
> 10 B to be synced from secondary to local
> Propagating updates
> Unison 2.53.3 (ocaml 4.11.1) started propagating changes at 12:01:22.57 on 13 Dec 2023
> [BGN] Copying primary from /srv/sync to //secondary//srv/sync
> [BGN] Copying secondary from //secondary//srv/sync to /srv/sync
> [END] Copying primary
> [END] Copying secondary
> Unison 2.53.3 (ocaml 4.11.1) finished propagating changes at 12:01:22.58 on 13 Dec 2023, 0.002 s
> Saving synchronizer state
> Synchronization complete at 12:01:22  (2 items transferred, 0 skipped, 0 failed)
>
> [root@primary /]# md5sum /srv/sync/*
> 4272f9624c9902f8adddce9abb7b2fec  /srv/sync/primary
> e1f5e71ebca45019df6134e857efc85a  /srv/sync/secondary
>
> [root@primary /]# ssh secondary 'md5sum /srv/sync/*'
> 4272f9624c9902f8adddce9abb7b2fec  /srv/sync/primary
> e1f5e71ebca45019df6134e857efc85a  /srv/sync/secondary
> ```
[//]: # (@pandoc@\normalsize@)

## Repeat-Modus

[//]: # (@pandoc@\small@)
> ```
> [root@primary /]# unison /srv/sync/ ssh://secondary//srv/sync/ -batch -auto \
>     -logfile /unison.log -repeat watch > /dev/null 2>&1 &
>
> [root@primary /]# for I in {1..3}
> > do date >> /srv/sync/primary
> > ssh secondary 'date >> /srv/sync/secondary'
> > sleep 3
> > done
>
> [root@primary /]# grep Synchronization /unison.log
> Synchronization complete at 12:01:22  (2 items transferred, 0 skipped, 0 failed)
> Synchronization complete at 12:04:24  (1 item transferred, 0 skipped, 0 failed)
> Synchronization complete at 12:04:25  (1 item transferred, 0 skipped, 0 failed)
> Synchronization complete at 12:04:27  (2 items transferred, 0 skipped, 0 failed)
> Synchronization complete at 12:04:30  (1 item transferred, 0 skipped, 0 failed)
> Synchronization complete at 12:04:31  (1 item transferred, 0 skipped, 0 failed)
>
> [root@primary /]# kill %+
> ```
[//]: # (@pandoc@\normalsize@)

# Erweitertes Setup

Dieser Abschnitt beschreibt eine Möglichkeit zur Definition von
Systemd-Service-Instanzen auf Basis von Unison-Profilen. Damit kann ein großer
Datenpool in mehrere Untereinheiten aufgeteilt werden, deren Unison-Profile
gegebenenfalls mit individuellen Einstellungen versehen werden.
Das Setup sieht hier eine Nutzung als `root` vor.

## Relevante Komponenten

Primäres System:

  - `/etc/unison/id_ed25519`
  - [`/etc/systemd/system/unison@.service`](#systemd-service-unit)
  - [`/usr/local/sbin/unison-testserver`](#servertest-skript) (optional)

Sekundäres System:

  - [`/root/.ssh/authorized_keys`](#ssh-authorized-key)

Beide Systeme:

  - [Installiertes `unison`](#bauanleitung)
  - [`/usr/local/sbin/unison`](#unison-wrapper-skript)
  - [`/usr/local/sbin/unison-rsync`](#rsync-wrapper-skript)
  - [`/var/lib/unison/<profilname>.prf`](#demo-profil)

## Komponentenbeschreibung

### Privater SSH-Schlüssel

Selbst wenn bereits ein privater Schlüssel für Systemdienste eingerichtet sein
sollte, wird ein separater Schlüssel benötigt, da dessen
Authorized-Keys-Eintrag mit einem `command`-Override versehen werden muss.

### Service Unit

Die im Anhang dargestellte [Service-Unit](#systemd-service-unit) startet einen
[Unison-Wrapper](#unison-wrapper-skript) unter Angabe eines Profilnamens sowie den
notwendigen Kommandozeilenoptionen für einen nicht-interaktiven
Watch-Modus-Betrieb. Es wird angenommen, dass diese Optionen nicht im Profil
definiert werden, um den Wrapper auch im interaktiven-Modus ausführen zu
können.

Der Service wird wie folgt gestartet:

> ```
> systemctl start unison@demo
> ```

Ein interaktiver Lauf kann wie folgt gestartet werden:

* `/usr/local/sbin/unison demo`, oder
* `/usr/local/sbin/unison demo -auto`, oder
* `/usr/local/sbin/unison demo -auto -batch`

### Authorized-Keys-Eintrag

Der [Authorized-Keys-Eintrag](#ssh-authorized-key) für den dedizierten privaten
SSH-Schlüssel forciert einen Aufruf des
[Unison-Wrappers](#unison-wrapper-skript).  Unter Anderem erhält das Setup
damit eine Symmetrie aufrecht, die es erlaubt, die primäre und sekundäre Rolle
des Unison-Paares zu vertauschen, sofern die hier beschriebenen Komponenten auf
beiden Seiten ausgerollt worden sind.

### Unison Wrapper

Im Gegensatz zum `unison`-Binary schreibt der Wrapper die Angabe eines Profils
vor, welches auf beiden Systeme in `/var/lib/unison` (`$UNISON`) existieren
muss. Archivdateien werden ebenfalls auf beiden Seiten in `/var/lib/unison`
verwaltet.

Falls ein konkretes Profil auf dem primären aber nicht auf dem sekundären
System existiert, ergibt sich daraus ein nicht-terminierender Fehlerfall
für den primären Unison-Prozess:

[//]: # (@pandoc@\small@)
> ```
> Fatal error: Received unexpected header from the server:
>  expected "Unison RPC\n" but received "Usage: /usr/local/sbin/unison
>  profilename [options]\nProfile foo does not exist\n",
> which differs at "Us".
> This can happen because you have different versions of Unison
> installed on the client and server machines, or because
> your connection is failing and somebody is printing an error
> message, or because your remote login shell is printing
> something itself before starting Unison.
> ```
[//]: # (@pandoc@\normalsize@)

Eine mögliche Maßnahme ist die Aktivierung des
[Servertests](#servertest-skript) innerhalb der
[Service-Unit](#systemd-service-unit).

### Rsync Wrapper

Durch das Auslagern des `--rsh` in einen eigenen Wrapper beinhaltet die
`copyprog`-Option der [`demo.prf`](#demo-profil) keine Leerzeichen, die im
Rahmen einer Evaluierung Probleme bereitet hatten.

### Servertest

`unison` bietet eine `servertest`-Option, die genutzt werden kann, um eine
Fehlerbedingung, die bereits vom [Unison-Wrapper](#unison-wrapper-skript) des
sekundären Systems erkannt wird, an den primären `unison` weiterzugeben.  Das
im Anhang dargestellte [Servertest-Skript](#servertest-skript) sorgt dafür,
dass ein auf dem sekundären System fehlendes Profil zu einem Startfehler des
primären Services eskaliert, während Verbindungsprobleme weiterhin
nichtterminierend bleiben.  Leider kann dieser Fehlerfall von einem temporären
Verbindungsproblem maskiert werden. Zudem lässt sich der Test nicht auf
[Archivdateifehler](#archivdateifehler) verallgemeinern.


### Profile

Das [Demo-Profil](#demo-profil) aktiviert die Übertragung per `rsync` ab einer
Dateigröße von 10MB. Da `unison` mit `root`-Rechten aufgerufen wird, ist eine
Synchronisierung des Eigentümers und der Gruppe möglich, sowie der schreibende
Zugriff auf `/var/log/unison.log`. Mittels der `prefer`-Option werden
Konfliktsituationen automatisch aufgelöst, indem die lokale Seite bevorzugt
wird. In einem produktiven Setup kann dies für manche
Synchronisationsverzeichnise gewünscht oder unerwünscht sein.

# Sonstiges

## Inotify

Die vom `unison-fsmonitor` genutzte `inotify`-Queue hat eine Maximalgröße, die
per `/proc/sys/fs/inotify/max_queued_events` definiert werden kann. Falls ein
Prozess `inotify`-Events nicht schnell genug einliest, kann die Queue
überlaufen und Events verloren gehen. Es ist sinnvoll, den Wert zu erhöhen, um
Lastspitzen besser abzufangen.

Darüber hinaus ist es wichtig `/proc/sys/fs/inotify/max_user_watches`
ausreichend hoch anzusetzen, so dass `unison-fsmonitor` für das gesamte
Synchronisationsverzeichnis (bzw. für alle Synchronisationsverzeichnisse im
Falle mehrere Service-Instanzen) samt seiner Unterverzeichnisse
`inotify`-Watches registrieren kann. Folgender Wert ist das absolute Minimum
für den aktuellen Datenbestand:

> ```
> find /path/to/sync/root -type d | wc -l
> ```

## SSH Keepalive

Es bietet sich an, auf dem SSH-Server `ClientAliveInterval` zu nutzen, damit
der sekundäre Unison-Prozess bei einem harten Absturz des primären Systems
terminiert.

[//]: # (@pandoc@\newpage@)
# Appendix

## Bauanleitung

[//]: # (@pandoc@\small@)

`Dockerfile`:

> ```
> FROM rockylinux:9 AS ocaml-src
>
> RUN yum install -y yum-utils
> RUN yum-config-manager --enable crb
> WORKDIR /
> RUN yumdownloader --source ocaml
>
> FROM rockylinux:8 AS ocaml-bin
>
> RUN yum install -y rpmdevtools rpmlint yum-utils
> COPY --from=ocaml-src /ocaml-4.11.1-5.el9.2.src.rpm /tmp/
> RUN yum-builddep -y /tmp/ocaml-4.11.1-5.el9.2.src.rpm
> RUN rpmbuild --rebuild /tmp/ocaml-4.11.1-5.el9.2.src.rpm
>
> FROM rockylinux:8
>
> RUN yum install -y rpmdevtools yum-utils
> RUN useradd build -d /build
> USER build
> WORKDIR /build
> RUN rpmdev-setuptree
> COPY unison.spec rpmbuild/SPECS/
> RUN spectool -g -R rpmbuild/SPECS/unison.spec
> USER root
> COPY --from=ocaml-bin /root/rpmbuild/RPMS/x86_64/*.rpm rpmbuild/RPMS/
> RUN yum install -y \
>     rpmbuild/RPMS/ocaml-4.11.1-5.el8.2.x86_64.rpm \
>     rpmbuild/RPMS/ocaml-runtime-4.11.1-5.el8.2.x86_64.rpm \
>     rpmbuild/RPMS/ocaml-compiler-libs-4.11.1-5.el8.2.x86_64.rpm
> RUN yum-builddep -y rpmbuild/SPECS/unison.spec
> USER build
> RUN rpmbuild -ba rpmbuild/SPECS/unison.spec
> ```

`unison.spec`:

> ```
> Name:           unison
> Version:        2.53.3
> Release:        1%{?dist}
> Summary:        Unison is a file-synchronization tool for POSIX-compliant systems
>
> License:        GPLv3
> URL:            https://github.com/bcpierce00/unison/
> Source0:        https://github.com/bcpierce00/unison/archive/refs/tags/v%{version}.tar.gz
>
> BuildRequires:  ocaml texlive make
>
> %description
>
> %prep
> %autosetup
>
> %build
> make all docs
>
> %install
> rm -rf $RPM_BUILD_ROOT
> mkdir -p $RPM_BUILD_ROOT/%{_bindir}
> mkdir -p $RPM_BUILD_ROOT/%{_docdir}/unison
> mkdir -p $RPM_BUILD_ROOT/%{_mandir}/man1
> cp %{_builddir}/%{name}-%{version}/src/unison $RPM_BUILD_ROOT/%{_bindir}
> cp %{_builddir}/%{name}-%{version}/src/unison-fsmonitor $RPM_BUILD_ROOT/%{_bindir}
> cp %{_builddir}/%{name}-%{version}/doc/unison-manual.pdf $RPM_BUILD_ROOT/%{_docdir}/unison
> cp %{_builddir}/%{name}-%{version}/man/unison.1 $RPM_BUILD_ROOT/%{_mandir}/man1
> gzip $RPM_BUILD_ROOT/%{_mandir}/man1/unison.1
>
> %files
> %{_bindir}/*
> %{_mandir}/*
> %{_docdir}/*
>
> %clean
> rm -rf %{buildroot} %{_builddir}
> ```
[//]: # (@pandoc@\normalsize@)

## Systemd Service Unit

`/etc/systemd/system/unison@.service`:

[//]: # (@pandoc@\small@)
> ```
> [Unit]
> Description=unison %I sync
> Wants=network.target network-online.target
> After=network.target network-online.target
>
> [Service]
> # Activate servertest script if useful for your setup
> # ExecStartPre=/usr/local/sbin/unison-testserver %I
> ExecStart=/usr/local/sbin/unison %I -repeat watch -silent -auto -batch
>
> [Install]
> WantedBy=default.target
> ```
[//]: # (@pandoc@\normalsize@)

## Unison-Wrapper Skript

`/usr/local/sbin/unison`:

[//]: # (@pandoc@\small@)
> ```
> #!/bin/sh
>
> set -e
>
> export HOME=/var/lib/unison
> export UNISON=$HOME
>
> check_pref () {
>     if ! [ "$1" -a -r "$UNISON/$1.prf" ]
>     then
>         echo "Usage: $0 profilename [options]"
>         echo "Profile $1 does not exist"
>         exit 1
>     fi
> }
>
> if [ "$SSH_ORIGINAL_COMMAND" ] # ssh invocation by unison master
> then
>     eval "set -- $SSH_ORIGINAL_COMMAND"
>     if [ "$1" == "unison-rsync" ]
>     then
>         exec "$@"
>     else
>         check_pref "$(echo "$1" | base64 -d)"
>         shift
>         exec /bin/unison "$@"
>     fi
> else # local systemd or shell invocation
>     check_pref "$1"
>     exec /bin/unison "$@" -servercmd "$(echo $1 | base64 -w0)"
> fi
> ```
[//]: # (@pandoc@\normalsize@)

## Rsync-Wrapper Skript

`/usr/local/sbin/unison-rsync`:

[//]: # (@pandoc@\small@)
> ```
> #!/bin/sh
>
> exec /bin/rsync --rsync-path unison-rsync \
>     --rsh '/bin/ssh -i /etc/unison/id_ed25519' "$@"
> ```
[//]: # (@pandoc@\normalsize@)

## Servertest Skript

`/usr/local/sbin/unison-testserver`:

[//]: # (@pandoc@\small@)
> ```
> #!/bin/sh
>
> TMP="$(mktemp)"
> RC=0
>
> timeout 3 /usr/local/sbin/unison "$1" -testserver -silent -terse > "$TMP" 2>&1
>
> if grep -ql "Fatal error: Received unexpected header from the server" "$TMP" \
> || grep -ql "Profile $1 does not exist" "$TMP" # report locally missing file as well
> then
>     cat "$TMP"
>     RC=1
> fi
>
> rm -f "$TMP"
> exit $RC
> ```
[//]: # (@pandoc@\normalsize@)

## Demo-Profil

`/var/lib/unison/demo.prf`:

[//]: # (@pandoc@\small@)
> ```
> copymax = 4
> copyprog = unison-rsync --inplace --compress
> copyprogrest = unison-rsync --inplace --compress --partial
> copythreshold = 10000
> fastcheck = false
> group = true
> logfile = /var/log/unison.log
> owner = true
> prefer = /srv/sync/
> root = ssh://secondary//srv/sync/
> root = /srv/sync/
> sshargs = -oIdentityFile=/etc/unison/id_ed25519
> times = true
> ```
[//]: # (@pandoc@\normalsize@)

## SSH Authorized Key

`/root/.ssh/authorized_keys`:

[//]: # (@pandoc@\small@)
> ```
> command="/usr/local/sbin/unison" ssh-ed25519 {/etc/unison/id_ed25519.pub-content}
> ```
[//]: # (@pandoc@\normalsize@)
