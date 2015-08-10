from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

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
        # send broadcast
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        priority = 0

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

        # match packets to 10.0.0.2:80
        match = parser.OFPMatch(eth_type=0x0800,ipv4_dst="10.0.0.2",ip_proto=6,tcp_dst=80)
        # send broadcast
        actions = [
		    parser.OFPActionSetField(tcp_dst=8080),
			parser.OFPActionOutput(ofproto.OFPP_FLOOD)
			]
		# higher priority than default
        priority = 1

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)		
		
        # match packets from 10.0.0.2:80
        match = parser.OFPMatch(eth_type=0x0800,ipv4_src="10.0.0.2",ip_proto=6,tcp_src=8080)
        # send broadcast
        actions = [
		    parser.OFPActionSetField(tcp_src=80),
			parser.OFPActionOutput(ofproto.OFPP_FLOOD)
			]
		# higher priority than default
        priority = 1

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)				