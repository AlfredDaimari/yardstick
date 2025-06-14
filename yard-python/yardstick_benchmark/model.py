from dataclasses import dataclass
import ansible_runner
import tempfile
import shutil
from pathlib import Path
import string
import random
import os
from typing import Optional


@dataclass(frozen=True)
class Node(object):
    host: str
    wd: Path


@dataclass(frozen=True)
class VagrantNode(object):
    name: str
    ansible_host: str
    ansible_user: str
    ansible_ssh_private_key_file: str
    ansible_ssh_common_args: str
    wd: str
    memory: int


def _gen_wd_name(name, node_wd) -> str:
    alphabet = string.ascii_lowercase + string.digits
    hash = "".join(random.choices(alphabet, k=8))
    return str(node_wd / f"{name}-{hash}")


def _gen_inv(name: str, nodes: list[Node] | list[VagrantNode]) -> dict:
    if isinstance(nodes[0], Node):
        hosts = {
            node.host: {"node_wd": str(node.wd), "wd": _gen_wd_name(name, node.wd)}
            for node in nodes
        }

    else:
        hosts = {
            node.name: {
                "ansible_host": node.ansible_host,
                "ansible_user": node.ansible_user,
                "ansible_ssh_private_key_file": node.ansible_ssh_private_key_file,
                "ansible_ssh_common_args": node.ansible_ssh_common_args,
                "wd": node.wd,
                "memory": node.memory
            }
            for node in nodes
        }

    return {"all": {"hosts": hosts}}


class RemoteAction(object):
    def __init__(
        self,
        name: str,
        nodes: list[Node] | list[VagrantNode],
        script: Path,
        envvars: dict = {},
        extravars: dict = {},
        inv: Optional[dict] = None,
    ):
        self.name = name
        if isinstance(nodes[0], Node):
            self.hosts = {
                node.host: {"node_wd": node.wd, "wd": _gen_wd_name(name, node.wd)}
                for node in nodes
            }
        else:
            self.hosts = {
                node.name: {"ansible_host": node.ansible_host, "wd": node.wd}
                for node in nodes
            }
        self.inv = inv if inv is not None else _gen_inv(name, nodes)
        self.script = script
        self.envvars = envvars
        self.extravars = extravars

    def run(self):
        assert self.script.is_file()

        self.private_data_dir = tempfile.mkdtemp(prefix="yardstick-")
        res = ansible_runner.interface.run(
            private_data_dir=self.private_data_dir,
            playbook=str(self.script),
            inventory=self.inv,
            envvars=self.envvars,
            extravars=self.extravars,
            settings={
                "pipelining": True,
                "ssh_args": "-o ControlMaster=auto -o ControlPersist=60s",
                "deprecation_warnings": False,
            },
        )
        shutil.rmtree(self.private_data_dir)
        return res


class RemoteApplication(object):
    def __init__(
        self,
        name: str,
        nodes: list[Node] | list[VagrantNode],
        deploy_script: Path,
        start_script: Path,
        stop_script: Path,
        cleanup_script: Path,
        envvars: dict = {},
        extravars: dict = {},
    ):
        self.nodes = nodes
        self.inv = _gen_inv(name, nodes)
        self.envvars = envvars
        self.extravars = extravars
        self.deploy_action = RemoteAction(
            name, nodes, deploy_script, envvars, extravars, self.inv
        )
        self.start_action = RemoteAction(
            name, nodes, start_script, envvars, extravars, self.inv
        )
        self.stop_action = RemoteAction(
            name, nodes, stop_script, envvars, extravars, self.inv
        )
        self.cleanup_action = RemoteAction(
            name, nodes, cleanup_script, envvars, extravars, self.inv
        )

    def deploy(self):
        return self.deploy_action.run()

    def start(self):
        return self.start_action.run()

    def stop(self):
        return self.stop_action.run()

    def cleanup(self):
        return self.cleanup_action.run()
