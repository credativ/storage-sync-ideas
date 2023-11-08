#!/bin/bin/make

build: rpm

dockerimage:
	docker build . --tag unisonbuild

rpm: dockerimage
	mkdir -p rpms
	docker run --rm --entrypoint /bin/sh -v $(shell pwd)/rpms:/rpms unisonbuild -c 'find -name *.rpm -execdir cp -t /rpms {} +'
