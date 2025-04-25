#!/usr/bin/env python3

import sys
from mininet.node import Host
from mininet.topo import Topo
from mininet.util import quietRun
from mininet.log import error
from mininet.node import RemoteController, OVSSwitch
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.topo import SingleSwitchTopo
from mininet.log import setLogLevel

from functools import partial



class LineTopo(Topo):
    def build(self):
        switch = self.addSwitch('s1')
        h1=self.addHost('h1', ip='10.0.0.2/24', mac="00:00:00:00:00:01", defaultRoute=('via 10.0.0.1'))
        h2=self.addHost('h2', ip='10.0.1.2/24', mac="00:00:00:00:00:02", defaultRoute=('via 10.0.1.1'))
        self.addLink(h1, switch)
        self.addLink(h2, switch)

def exampleCustomTags():
    setLogLevel( 'info' )
    net = Mininet( topo=LineTopo(), waitConnected=True, switch=partial(OVSSwitch, protocols="OpenFlow13"), controller=partial(RemoteController, ip="127.0.0.1"))
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__': 
    exampleCustomTags()
    
    

