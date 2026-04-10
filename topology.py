#!/usr/bin/env python3
"""
custom_topology.py  \E2\80\93  Host Discovery Service Topology
Course: COMPUTER NETWORKS - UE24CS252B

Topology:
         h1
          \
    h3 -- s1 -- h2
          |
          s2
         / \
       h4   h5

Two switches (s1, s2) connected together.
s1 has hosts h1, h2, h3.
s2 has hosts h4, h5.
Remote POX controller on 127.0.0.1:6633.
"""

from mininet.topo import Topo
from mininet.net  import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli  import CLI
from mininet.log  import setLogLevel, info


class HostDiscoveryTopo(Topo):
    """Custom two-switch topology with five hosts."""

    def build(self):
        # Add switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Add hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        h4 = self.addHost('h4', ip='10.0.0.4/24')
        h5 = self.addHost('h5', ip='10.0.0.5/24')

        # Connect hosts to s1
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s1)

        # Connect hosts to s2
        self.addLink(h4, s2)
        self.addLink(h5, s2)

        # Inter-switch link
        self.addLink(s1, s2)


def run():
    setLogLevel('info')
    topo = HostDiscoveryTopo()
    net  = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633),
        switch=OVSSwitch,
        autoSetMacs=True
    )
    net.start()
    info('\n*** Topology started.\n')
    info('*** Hosts: h1(10.0.0.1), h2(10.0.0.2), h3(10.0.0.3), '
         'h4(10.0.0.4), h5(10.0.0.5)\n')
    info('*** Run "pingall" to trigger host discovery.\n')
    CLI(net)
    net.stop()


if __name__ == '__main__':
    run()