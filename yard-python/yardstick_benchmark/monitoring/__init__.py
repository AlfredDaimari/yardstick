from yardstick_benchmark.model import RemoteAction, RemoteApplication, Node, VagrantNode
import os
from enum import Enum
import sys
from pathlib import Path


class Telegraf(RemoteApplication):
    """Runs the Telegraf metric collection tool
    (https://www.influxdata.com/time-series-platform/telegraf/) on remote nodes.
    """

    def __init__(self, nodes: list[Node] | list[VagrantNode]):
        """Create a new instance to run Telegraf on the given nodes.

        Args:
            nodes (list[Node]): The nodes on which to run Telegraf
        """
        super().__init__(
            "telegraf",
            nodes,
            Path(__file__).parent / "telegraf_deploy.yml",
            Path(__file__).parent / "telegraf_start.yml",
            Path(__file__).parent / "telegraf_stop.yml",
            Path(__file__).parent / "telegraf_cleanup.yml",
            extravars={
                "config_template": os.path.join(
                    os.path.dirname(__file__), "telegraf.conf.j2"
                ),
            },
        )

    def add_input_jolokia_agent(self, node: Node | VagrantNode):
        """Configure Telegraf to run the Jolokia agent input on the given node.
        The node should be present in the list of nodes given when constructing
        this Telegraf object.

        Args:
            node (Node): The node on which to run the Jolokia agent input
        """
        assert node in self.nodes
        self.extravars.setdefault("jolokia2_agent", []).append(
            node.host if isinstance(node, Node) else node.name
        )

    def add_input_execd_minecraft_ticks(self, node: Node | VagrantNode):
        """Configure Telegraf to run an execd input on the given node to collect
        the tick duration metric from a Minecraft server.

        Args:
            node (Node): The node on which to run the execd input
        """
        self.extravars.setdefault("execd_minecraft_ticks", []).append(
            node.host if isinstance(node, Node) else node.name
        )
        self.extravars["jolokia_get_minecraft_tick_script_path"] = os.path.join(
            os.path.dirname(__file__), "jolokia_get_minecraft_tick.py"
        )
        this_host = self.inv["all"]["hosts"][
            node.host if isinstance(node, Node) else node.name
        ]
        self.inv.setdefault("minecraft_servers", {}).setdefault("hosts", {})[
            node.host if isinstance(node, Node) else node.name
        ] = this_host


def start_player_distribution_monitoring(nodes: list[VagrantNode]):
    """
    Run the slist command on every worker stdin at 1 second intervals
    """
    RemoteAction(
        "start-player-dist-monitoring", nodes, Path(__file__).parent / "slist_start.yml"
    ).run()


def stop_player_distribution_monitoring(nodes: list[VagrantNode]):
    """
    Stop running the slist command on each worker stdin
    """
    RemoteAction(
        "stop-player-dist-monitoring", nodes, Path(__file__).parent / "slist_stop.yml"
    ).run()
