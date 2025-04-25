# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
#from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.ofproto import ether
#from ryu.lib.packet import ipv4
#from ryu.lib.packet import icmp
from ryu.lib.packet import ethernet, ipv4, icmp, arp


class L3Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L3Switch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.router_mac = {
            '10.0.0.1': '70:88:99:00:00:01',
            '10.0.1.1': '70:88:99:10:00:02',
        }
        
    def forward_actions(self, parser, ofproto, port, src_mac, dst_mac):
        """Acciones para reenviar un paquete con ajustes de cabecera L3."""
        return [
            parser.OFPActionDecNwTtl(),
            parser.OFPActionSetField(eth_src=src_mac),
            parser.OFPActionSetField(eth_dst=dst_mac),
            parser.OFPActionOutput(port),              
        ]   
    
    def drop_actions(self, parser, ofproto):
        """Acciones para descartar un paquete."""
        return []
    
    def send_to_controller_actions(self, parser, ofproto):
        """Acciones para enviar un paquete al controlador."""
        return [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
    
    
    
    

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        

        # Quitar LLDP
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_LLDP)
        self.add_flow(datapath, 10000, match, self.drop_actions(parser, ofproto))
        
        #Quitar trafico IPv6
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IPV6)
        self.add_flow(datapath, 10000, match, self.drop_actions(parser, ofproto))
        
        
        match =parser.OFPMatch(
            eth_type=ether.ETH_TYPE_IP,
            ipv4_dst=('10.0.0.1', '255.255.255.255')
        )
        self.add_flow(datapath, 5000, match, self.send_to_controller_actions(parser, ofproto))
        
        
        match = parser.OFPMatch(
            eth_type=ether.ETH_TYPE_IP,
            ipv4_dst=('10.0.1.1', '255.255.255.255')
        )
        self.add_flow(datapath, 5000, match, self.send_to_controller_actions(parser, ofproto))
        
        
        #IPv4
        match = parser.OFPMatch(
            eth_type=ether.ETH_TYPE_IP,
            ipv4_dst=('10.0.0.0', '255.255.255.0')
        )
        actions = self.forward_actions(
            parser, ofproto, 1,
            '70:88:99:00:00:01',  # MAC origen
            '00:00:00:00:00:01'   # MAC destino = h1
        )
        
        self.add_flow(datapath, 1000, match, actions)
        
        # IPv4
        match = parser.OFPMatch(
            eth_type=ether.ETH_TYPE_IP,
            ipv4_dst=('10.0.1.0', '255.255.255.0')
        )
        actions = self.forward_actions(
            parser, ofproto, 2,
            '70:88:99:10:00:02',  # MAC origen
            '00:00:00:00:00:02'   # MAC destino
        )
        self.add_flow(datapath, 1000, match, actions)
        
        # 3. Regla por defecto: enviar al controlador (prioridad 0)
        match = parser.OFPMatch()
        self.add_flow(datapath, 0, match, self.send_to_controller_actions(parser, ofproto))
        
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        port = msg.match['in_port']
        pkt = packet.Packet(data=msg.data)
        self.logger.info("packet-in %s" % (pkt,))
        pkt_ethernet = pkt.get_protocol(ethernet.ethernet)
        if not pkt_ethernet:
            return
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            self._handle_arp(datapath, port, pkt_ethernet, pkt_arp)
            return
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        pkt_icmp = pkt.get_protocol(icmp.icmp)
        if pkt_icmp:
            self._handle_icmp(datapath, port, pkt_ethernet, pkt_ipv4, pkt_icmp)
            return

        
    def _handle_icmp(self, datapath, port, pkt_ethernet, pkt_ipv4, pkt_icmp):
        if pkt_icmp.type != icmp.ICMP_ECHO_REQUEST:
            return
        
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_ethernet.src,
                                           src=self.router_mac.get(pkt_ipv4.dst)))
        pkt.add_protocol(ipv4.ipv4(dst=pkt_ipv4.src,
                                   src=pkt_ipv4.dst,
                                   proto=pkt_ipv4.proto))
        pkt.add_protocol(icmp.icmp(type_=icmp.ICMP_ECHO_REPLY,
                                   code=icmp.ICMP_ECHO_REPLY_CODE,
                                   csum=0,
                                   data=pkt_icmp.data))
        #self.send_to_controller_actions(parser, ofproto)
        self._send_packet(datapath,port,pkt)
 
    def _handle_arp(self, datapath, port, pkt_ethernet, pkt_arp):
        if pkt_arp.opcode != arp.ARP_REQUEST:
            return
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_ethernet.src,
                                           src=self.router_mac.get(pkt_arp.dst_ip))) ######
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=self.router_mac.get(pkt_arp.dst_ip),
                                 src_ip=pkt_arp.dst_ip,
                                 dst_mac=pkt_arp.src_mac,
                                 dst_ip=pkt_arp.src_ip))
        self._send_packet(datapath, port, pkt) 
 
 
 
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)
        
    def _send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        self.logger.info("packet-out %s" % (pkt,))
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
                             
        datapath.send_msg(out) 
        
        
