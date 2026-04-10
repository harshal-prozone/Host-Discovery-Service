"""
Host Discovery Service - SDN Mininet Project
Course: COMPUTER NETWORKS - UE24CS252B
Controller: POX (OpenFlow)

Description:
  - Automatically detects hosts when they join the SDN network
  - Maintains a host database (MAC, IP, switch DPID, port, timestamp)
  - Displays host details and updates dynamically on packet_in events
  - Acts as a Learning Switch + Host Tracker combined
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpid_to_str
import time

log = core.getLogger()

# -------------------------------------------------------
# Global Host Database
# key: mac_address -> dict of host info
# -------------------------------------------------------
host_db = {}

# MAC-to-port learning table per switch: {dpid: {mac: port}}
mac_to_port = {}


def display_host_db():
    """Print the current host database in a formatted table."""
    if not host_db:
        log.info("Host DB is empty.")
        return
    log.info("=" * 70)
    log.info("  HOST DATABASE")
    log.info("=" * 70)
    log.info("  %-20s %-16s %-12s %-6s %s" % ("MAC Address", "IP Address", "Switch", "Port", "Last Seen"))
    log.info("-" * 70)
    for mac, info in host_db.items():
        ts = time.strftime('%H:%M:%S', time.localtime(info['timestamp']))
        log.info("  %-20s %-16s %-12s %-6s %s" % (
            str(mac),
            str(info.get('ip', 'N/A')),
            str(info['dpid']),
            str(info['port']),
            ts
        ))
    log.info("=" * 70)


class HostDiscoverySwitch(EventMixin):
    """
    Per-switch handler. Processes PacketIn events from one switch.
    - Learns MAC->port mappings (learning switch behavior)
    - Records host join/update events in the global host_db
    - Installs OpenFlow flow rules for known destinations
    - Floods for unknown destinations
    """

    def __init__(self, connection, dpid):
        self.connection = connection
        self.dpid = dpid_to_str(dpid)
        self.listenTo(connection)
        log.info("[+] Switch connected: DPID=%s" % self.dpid)

    def _handle_PacketIn(self, event):
        """
        Called on every packet_in event (no matching flow rule on switch).

        Logic:
          1. Extract Ethernet src/dst and incoming port
          2. Learn src MAC -> port in mac_to_port table
          3. Extract IP from ARP or IPv4 payload
          4. Detect new/updated host -> update host_db and display
          5. If dst MAC known -> install flow rule and forward
          6. Else -> flood out all ports
        """
        packet  = event.parsed
        src_mac = packet.src
        dst_mac = packet.dst
        in_port = event.port
        dpid    = self.dpid

        # -- Step 1: Initialize per-switch table --
        if dpid not in mac_to_port:
            mac_to_port[dpid] = {}

        # -- Step 2: Learn source MAC -> port --
        mac_to_port[dpid][src_mac] = in_port

        # -- Step 3: Extract source IP --
        src_ip = "N/A"
        try:
            if packet.type == packet.ARP_TYPE:
                arp_pkt = packet.payload
                if str(arp_pkt.protosrc) != "0.0.0.0":
                    src_ip = str(arp_pkt.protosrc)
            elif packet.type == packet.IP_TYPE:
                ip_pkt = packet.payload
                src_ip = str(ip_pkt.srcip)
            # Also update IP if we previously stored N/A
            if src_mac in host_db and host_db[src_mac].get('ip') == 'N/A' and src_ip != 'N/A':
                host_db[src_mac]['ip'] = src_ip
        except Exception:
            pass

        # -- Step 4: Host Discovery (detect join/update) --
        is_new = src_mac not in host_db
        prev   = host_db.get(src_mac, {})

        if is_new or prev.get('port') != in_port or prev.get('dpid') != dpid:
            host_db[src_mac] = {
                'mac':       str(src_mac),
                'ip':        src_ip,
                'dpid':      dpid,
                'port':      in_port,
                'timestamp': time.time()
            }
            if is_new:
                log.info("[HOST JOIN ] New host -> MAC=%s  IP=%-15s  Switch=%s  Port=%d"
                         % (src_mac, src_ip, dpid, in_port))
            else:
                log.info("[HOST UPDT ] Host moved -> MAC=%s  IP=%-15s  Switch=%s  Port=%d"
                         % (src_mac, src_ip, dpid, in_port))
            display_host_db()

        # -- Step 5: Forwarding --
        if dst_mac in mac_to_port.get(dpid, {}):
            out_port = mac_to_port[dpid][dst_mac]

            # Install flow rule on the switch for future packets
            msg = of.ofp_flow_mod()
            msg.match              = of.ofp_match.from_packet(packet, in_port)
            msg.idle_timeout       = 20   # seconds of inactivity before removal
            msg.hard_timeout       = 60   # absolute timeout
            msg.priority           = 10
            msg.actions.append(of.ofp_action_output(port=out_port))
            msg.data = event.ofp        # include current packet in the flow_mod
            self.connection.send(msg)
            log.debug("[FLOW] Rule installed: %s -> %s  out_port=%d  switch=%s"
                      % (src_mac, dst_mac, out_port, dpid))
        else:
            # Unknown destination: flood
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            msg.data    = event.ofp
            msg.in_port = in_port
            self.connection.send(msg)
            log.debug("[FLOOD] Unknown dst %s, flooding on switch %s" % (dst_mac, dpid))

    def _handle_ConnectionDown(self, event):
        log.info("[-] Switch disconnected: DPID=%s" % self.dpid)
        # Clean up MAC table for this switch
        if self.dpid in mac_to_port:
            del mac_to_port[self.dpid]


class HostDiscoveryService(EventMixin):
    """
    Top-level POX component. Registered with core.
    Listens for new OpenFlow switch connections.
    """

    def __init__(self):
        self.listenTo(core.openflow)
        log.info("[*] Host Discovery Service started. Waiting for switches...")

    def _handle_ConnectionUp(self, event):
        """Spawn a per-switch handler for each newly connected switch."""
        HostDiscoverySwitch(event.connection, event.dpid)


def launch():
    """
    POX entry point. Run with:
        ./pox.py host_discovery
    """
    core.registerNew(HostDiscoveryService)
    log.info("[*] Host Discovery Controller loaded.")