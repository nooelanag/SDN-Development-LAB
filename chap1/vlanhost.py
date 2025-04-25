#!/usr/bin/env python3
"""
vlanhost.py: Host subclass that uses a VLAN tag for the default interface.

Dependencies:
    This class depends on the "vlan" package
    $ sudo apt-get install vlan

Usage (example uses VLAN ID=1000):
    From the command line:
        sudo mn --custom vlanhost.py --host vlan,vlan=1000

    From a script (see exampleUsage function below):
        from functools import partial
        from vlanhost import VLANHost

        ....

        host = partial( VLANHost, vlan=1000 )
        net = Mininet( host=host, ... )

    Directly running this script:
        sudo python vlanhost.py 1000

"""

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

class ARPHost( Host ):
    "Host connected to ARP interface"

    # Alternatively, one could define
    # def config(self, vlan=None, **params)
    # and avoid the
    # vlan = params.pop('vlan' None)
    # pylint: disable=arguments-differ
    def config( self, **params ):
        """Configure ARPHost according to (optional) parameters:
           arp: ARP ID for default interface"""

        arp = params.pop('arp', None)
        assert arp is not None, 'ARPHost without arp in instantiation'
        mac, ip=arp
        r = super().config(**params)
        self.setARP(ip, mac)

        return r

class LineTopo(Topo):
    def build(self):
        switch = self.addSwitch('s1')
        h1=self.addHost('h1', cls=ARPHost, arp=('70:88:99:00:00:01','10.0.0.1'),ip='10.0.0.2/24', mac="00:00:00:00:00:01", defaultRoute=('via 10.0.0.1'))
        h2=self.addHost('h2', cls=ARPHost, arp=('70:88:99:10:00:02','10.0.1.1'),ip='10.0.1.2/24', mac="00:00:00:00:00:02", defaultRoute=('via 10.0.1.1'))
        self.addLink(h1, switch)
        self.addLink(h2, switch)

def exampleCustomTags():
    setLogLevel( 'info' )
    """Simple example that exercises LineTopo"""
    net = Mininet( topo=LineTopo(), waitConnected=True, switch=partial(OVSSwitch, protocols="OpenFlow13"), controller=partial(RemoteController, ip="127.0.0.1"))
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__': 
    exampleCustomTags()
    
    
    #h1 ip a s
    #h1 ip route
    #h1 arp -n    x
