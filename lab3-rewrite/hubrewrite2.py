from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from array import array

class PsrHubRewrite(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # execute at switch registration
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # match all packets 
        match = parser.OFPMatch()
        # send to controller
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        priority = 0

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(data=msg.data)
        
        if len(pkt.protocols)>=3 and isinstance( pkt.protocols[1], ipv4.ipv4 ) and isinstance( pkt.protocols[2], tcp.tcp ):
            pkt_ethernet = pkt.protocols[0]
            pkt_ipv4 = pkt.protocols[1]
            pkt_tcp = pkt.protocols[2]

            if pkt_ipv4.dst=='10.0.0.2' and pkt_tcp.dst_port==80:
                self.logger.info("pkt1a %s", pkt.protocols[2])
                pkt_tcp.dst_port=8080
                pkt_tcp.csum=0 # il checksum va ricalcolato
                self.logger.info("pkt1b %s", pkt.protocols[2])
                pkt.serialize()
            elif pkt_ipv4.src=='10.0.0.2' and pkt_tcp.src_port==8080:
                self.logger.info("pkt2a %s", pkt.protocols[2])
                pkt_tcp.src_port=80
                pkt_tcp.csum=0 # il checksum va ricalcolato
                self.logger.info("pkt2b %s", pkt.protocols[2])                    
                pkt.serialize()
                        
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]

        data = pkt.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

