These playbooks are indended to bootstrap a gluster pair on RockyLinux 8.
They have been tested on AWS `ami-02f9d4dea18e4d394`.

- `ansible-playbook -i inventory/aws.example site.yml`
- `ansible-playbook -i inventory/aws.example benchmark.yml`

If your setup does not support ipv6, declare `glusterd_disable_ipv6=true` in
your inventory, otherwise peer discovery will probably fail.

Dependencies:

- [Gluster.Gluster](https://docs.ansible.com/ansible/latest/collections/gluster/gluster/)
