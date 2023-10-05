all: verify.fio

clean:
	rm -vf verify.fio

verify.fio: write.fio
	sed -e 's/^#verify_only/verify_only/' -e 's/do_verify=0/do_verify=1/' $< > $@

.PHONY: clean all
