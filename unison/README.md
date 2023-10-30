These playbooks are indended to bootstrap a unison sync pair on RockyLinux 8.
They have been tested on AWS `ami-02f9d4dea18e4d394`.

- `( cd packaging && make )`
- `ansible-playbook -i inventory/aws.example.yml site.yml`

Build dependencies:

- `docker` for building a unison `rpm` locally.
