from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp

class PsrSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PsrSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
		
    # execute at switch registration
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.mac_to_port.setdefault(datapath.id, {}) 
        
        ## default
        # match all packets 
        match = parser.OFPMatch()
        # send to controller
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=0,
                                match=match, instructions=inst)
        datapath.send_msg(mod)
        
        ## switch s1
        if datapath.id == 1:
            match = parser.OFPMatch(eth_type=0x0800, ipv4_dst='10.0.0.2', ip_proto=17, udp_dst=53)
            actions = [
                parser.OFPActionSetField(eth_dst='00:00:00:00:00:03'),
                parser.OFPActionSetField(ipv4_dst='10.0.0.3'),
                parser.OFPActionOutput(2)
                ]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
            mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, instructions=inst)
            datapath.send_msg(mod)

        ## switch s2
        if datapath.id == 2:
            match = parser.OFPMatch(eth_type=0x0800, ipv4_dst='10.0.0.2', ip_proto=6, tcp_dst=80)
            actions = [
                parser.OFPActionSetField(tcp_dst=8080),
                parser.OFPActionOutput(2)
                ]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
            mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, instructions=inst)
            datapath.send_msg(mod)

            match = parser.OFPMatch(eth_type=0x0800, ipv4_src='10.0.0.2', ip_proto=6, tcp_src=8080)
            actions = [
                parser.OFPActionSetField(tcp_src=80),
                parser.OFPActionOutput(1)
                ]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
            mod = parser.OFPFlowMod(datapath=datapath, priority=1, match=match, instructions=inst)
            datapath.send_msg(mod)
                
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        pkt_eth = pkt.protocols[0]
        if len(pkt.protocols) > 1:
            pkt_ipv4 = pkt.protocols[1]
            if len(pkt.protocols) > 2:
                pkt_tp = pkt.protocols[2]

        dst = pkt_eth.dst
        src = pkt_eth.src

        dpid = datapath.id

        self.mac_to_port[dpid][src] = in_port

        out_port = ofproto.OFPP_FLOOD

		if dst in self.mac_to_port[dpid]:
			out_port = self.mac_to_port[dpid][dst]

        actions = [parser.OFPActionOutput(out_port)]

        data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

        # install a flow to avoid packet_in next time
        if (datapath.id == 1 or datapath.id == 2) and len(pkt.protocols) > 2 and isinstance(pkt_tp,tcp.tcp) and out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(eth_src=src, eth_dst=dst, eth_type=0x0800,
                ipv4_src = pkt_ipv4.src, ipv4_dst = pkt_ipv4.dst, ip_proto = 6,
                tcp_src = pkt_tp.src_port, tcp_dst = pkt_tp.dst_port
            )

            priority = 1
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
            datapath.send_msg(mod)