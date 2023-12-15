#!/usr/bin/make

pdfs = $(patsubst %.md,%.pdf,$(wildcard *.md))

all: clean $(pdfs)

clean:
	rm -f *.pdf

%.pdf:
	$(eval MD := $(patsubst %.pdf,%.md,$@) )
	sed -E 's/.*@pandoc@([^@]+)@.*/\1/g' $(MD) > .$(MD)
	pandoc -V links-as-notes -V lang=de -V geometry:margin=1in --toc .$(MD) -o $@
	rm .$(MD)
