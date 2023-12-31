# Benchmarking instructions

To benchmark the proposed storage solutions, we use FIO to induce load and measure the disk utilization during the test. Once fio finished creating load, we continue to record disk utilization on the opposing side until no significant utilization remains. We assume that the utilization will sharply decline after each benchmark, thus giving a clear indication of when the test ended.

We are interested in these metrics:

* Throughput while writing
* Throughput while reading
* Time until changes are synchronized (either measuring from start of the writing process, or from reconnection after a test with a severed connection)
* Disk utilization during the test on the backing disk of the synchronized data

The benchmarks should model these scenarios:

* Writing on one side and reading on the other with a working connection
* Writing on both sides and reading on both sides with a working connection
* Writing on one side with no working connection, then re-connecting and reading after the sync
* Writing on both sides with no connection, then re-connecting and reading after the sync

In the descriptions of the test scenarios, `$HOST1` and `$HOST2` are used to
refer to the two hosts used for benchmarking, `$IP1` and `$IP2` to their
respective IP addresses they use fro communicating to each other., `$SYNCDIR`
refers to the directory that is synchronized between the two hosts, and
`$SYNCDISK` refers to the block device of the physical disk backing `$SYNCDIR`.
It is also assumed that `verify.fio` has been generated using `make verify.fio`
and both `verify.fio` and `write.fio` from this directory have been copied to
`~/` on both hosts.

Some steps of the scenario will require waiting until synchronization of
previously written data completes. How exactly this is done, depends on the
underlying synchronization mechanism.  For unison, it involves checking that
disk io of the synced-to disk sinks to negligible levels, checking the log for
inactivity and comparing the number of files on both synchronized systems.

## Benchmark scenarios

### Scenario 1: Writing on one side, reading on the other, working connection

1. Start recording disk utilization on both hosts:
   ```
   root@$HOST1:/$ iostat -d -t -o JSON 1 $SYNCDISK > ~/write-one.disk-utilization.host1.json &
   root@$HOST2:/$ iostat -d -t -o JSON 1 $SYNCDISK | tee -i ~/write-one.disk-utilization.host2.json # Leave running in foreground
   ```
2. Create load on one side:

   ```
   root@$HOST1:$SYNCDIR$ fio --output-format json ~/write.fio > ~/write-one.fio-write.host1.json # Wait until all writes completed
   ```
3. Wait until synchronization completes.
4. Verify the written data on `$HOST2`:
   ```
   root@$HOST2:$SYNCDIR$ fio  --output-format json ~/verify.fio > ~/write-one.fio-verify.host2.json
   ```
5. Stop recording disk utilization on `$HOST2` with Ctrl+C and on `$HOST1` with `kill %+`.

### Scenario 2: Writing on both sides, reading on both sides, working connection

1. Start recording disk utilization on both hosts:
   ```
   root@$HOST1:/$ iostat -d -t -o JSON 1 $SYNCDISK | tee -i ~/write-both.disk-utilization.host1.json # Leave running in foreground
   root@$HOST2:/$ iostat -d -t -o JSON 1 $SYNCDISK | tee -i ~/write-both.disk-utilization.host2.json # Leave running in foreground
   ```
2. Create per-host write directories
   ```
   root@$HOST1:$SYNCDIR$ mkdir host1 && cd host1
   root@$HOST2:$SYNCDIR$ mkdir host2 && cd host2
   ```
3. Create load on both sides, try to start both commands at the same time
    ```
    root@$HOST1:$SYNCDIR/host1$ fio --output-format json ~/write.fio > ~/write-both.fio-write.host1.json
    root@$HOST2:$SYNCDIR/host2$ fio --output-format json ~/write.fio > ~/write-both.fio-write.host2.json
    ```
4. Wait until synchronization completes.
5. Verify the written data each host. Try to run both commands at the same time
   ```
   root@$HOST1:$SYNCDIR/host2$ fio --output-format json ~/verify.fio > ~/write-both.fio-verify.host1.json
   root@$HOST2:$SYNCDIR/host1$ fio --output-format json ~/verify.fio > ~/write-both.fio-verify.host2.json
   ```
6. Stop recording disk utilization on both hosts with Ctrl+C.

### Scenario 3: Writing on one side, reading on the other, broken connection

1. Prevent the hosts from connecting to each other (exact command may vary if legacy ip is used):
   ```
   root@$HOST1:/$ ip -6 r add blackhole $IP2
   ```
2. Start recording disk utilization on both hosts:
   ```
   root@$HOST1:/$ iostat -d -t -o JSON 1 $SYNCDISK > ~/write-one-broken.disk-utilization.host1.json &
   root@$HOST2:/$ iostat -d -t -o JSON 1 $SYNCDISK | tee -i ~/write-one-broken.disk-utilization.host2.json # Leave running in foreground
   ```
3. Create load on one side:

   ```
   root@$HOST1:$SYNCDIR$ fio --output-format json ~/write.fio > ~/write-one-broken.fio-write.host1.json # Wait until all writes completed
   ```
4. Allow hosts to re-connect:
   ```
   root@$HOST1:/$ ip -6 r add blackhole $IP2
   ```
5. Wait until synchronization completes.
6. Verify the written data on `$HOST2`:
   ```
   root@$HOST2:$SYNCDIR$ fio  --output-format json ~/verify.fio > ~/write-one-broken.fio-verify.host2.json
   ```
7. Stop recording disk utilization on `$HOST2` with Ctrl+C and on `$HOST1` with `kill %+`.

### Scenario 4: Writing on both sides, reading on both sides, broken connection

1. Prevent the hosts from connecting to each other (exact command may vary if legacy ip is used):
   ```
   root@$HOST1:/$ ip -6 r add blackhole $IP2
   ```
2. Start recording disk utilization on both hosts:
   ```
   root@$HOST1:/$ iostat -d -t -o JSON 1 $SYNCDISK | tee -i ~/write-both-broken.disk-utilization.host1.json # Leave running in foreground
   root@$HOST2:/$ iostat -d -t -o JSON 1 $SYNCDISK | tee -i ~/write-both-broken.disk-utilization.host2.json # Leave running in foreground
   ```
3. Create per-host write directories
   ```
   root@$HOST1:$SYNCDIR$ mkdir host1 && cd host1
   root@$HOST2:$SYNCDIR$ mkdir host2 && cd host2
   ```
4. Create load on both sides, try to start both commands at the same time
    ```
    root@$HOST1:$SYNCDIR/host1$ fio --output-format json ~/write.fio > ~/write-both-broken.fio-write.host1.json
    root@$HOST2:$SYNCDIR/host2$ fio --output-format json ~/write.fio > ~/write-both-broken.fio-write.host2.json
    ```
5. Allow hosts to re-connect:
   ```
   root@$HOST1:/$ ip -6 r add blackhole $IP2
   ```
6. Wait until synchronization completes.
7. Verify the written data each host. Try to run both commands at the same time
   ```
   root@$HOST1:$SYNCDIR/host2$ fio --output-format json ~/verify.fio > ~/write-both-broken.fio-verify.host1.json
   root@$HOST2:$SYNCDIR/host1$ fio --output-format json ~/verify.fio > ~/write-both-broken.fio-verify.host2.json
   ```
8. Stop recording disk utilization on both hosts with Ctrl+C.

## Creating a benchmark report

TBD
