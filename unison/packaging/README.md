```
$ make
docker build . --tag unisonbuild
...
Successfully tagged unisonbuild:latest
...
$ ls -l rpms
total 3404
-rw-r--r-- 1 demo demo 1343327 30. Okt 09:09 unison-2.52.1-1.el8.src.rpm
-rw-r--r-- 1 demo demo 1594040 30. Okt 09:09 unison-2.52.1-1.el8.x86_64.rpm
-rw-r--r-- 1 demo demo  295400 30. Okt 09:09 unison-debuginfo-2.52.1-1.el8.x86_64.rpm
-rw-r--r-- 1 demo demo  242176 30. Okt 09:09 unison-debugsource-2.52.1-1.el8.x86_64.rpm
```
