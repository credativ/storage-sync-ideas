Unison 2.53 cannot be built with OCaml shipped with RockyLinux 8 PowerTools.
This Makefile rebuilds OCaml from RockyLinux 9 CRB for RockyLinux 8, then
builds Unison 2.53 with it.

```
$ make
docker build . --tag unisonbuild
...
Successfully tagged unisonbuild:latest
...
$ ls -l rpms
total 110584
-rw-r--r-- 1 demo demo 75045904  8. Nov 10:23 ocaml-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo 14028984  8. Nov 10:23 ocaml-compiler-libs-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo  8707756  8. Nov 10:23 ocaml-debuginfo-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo  1602740  8. Nov 10:23 ocaml-debugsource-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo   574728  8. Nov 10:23 ocaml-docs-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo  4046360  8. Nov 10:23 ocaml-ocamldoc-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo  1224312  8. Nov 10:23 ocaml-ocamldoc-debuginfo-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo  2975828  8. Nov 10:23 ocaml-runtime-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo   907240  8. Nov 10:23 ocaml-runtime-debuginfo-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo   169228  8. Nov 10:23 ocaml-source-4.11.1-5.el8.2.x86_64.rpm
-rw-r--r-- 1 demo demo  1405478  8. Nov 10:23 unison-2.53.3-1.el8.src.rpm
-rw-r--r-- 1 demo demo  1879272  8. Nov 10:23 unison-2.53.3-1.el8.x86_64.rpm
-rw-r--r-- 1 demo demo   367088  8. Nov 10:23 unison-debuginfo-2.53.3-1.el8.x86_64.rpm
-rw-r--r-- 1 demo demo   274116  8. Nov 10:23 unison-debugsource-2.53.3-1.el8.x86_64.rpm
```
