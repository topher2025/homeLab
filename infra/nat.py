import threading
from scapy.all import IP, TCP, UDP, sendp, sniff

from config import PUBLIC_IP, LAN_IF, WAN_IF
from shared_state import memory


class PythonNat:
    def __init__(self):
        self.nat_table = memory.nat_table

    def nat_outbound(self, pkt):
        try:
            if IP not in pkt:
                return pkt

            ip = pkt[IP]
            if TCP in pkt:
                l4 = pkt[TCP]
            elif UDP in pkt:
                l4 = pkt[UDP]
            else:
                return pkt

            key = (ip.src, l4.sport)
            if key not in self.nat_table:
                self.nat_table[key] = memory.next_port
                memory.next_port += 1

            public_port = self.nat_table[key]
            ip.src = PUBLIC_IP
            l4.sport = public_port
            del ip.chksum
            del l4.chksum
            return pkt
        except Exception:
            return pkt

    def nat_inbound(self, pkt):
        try:
            if IP not in pkt:
                return pkt

            ip = pkt[IP]
            if TCP in pkt:
                l4 = pkt[TCP]
            elif UDP in pkt:
                l4 = pkt[UDP]
            else:
                return pkt

            for (lan_ip, lan_port), public_port in self.nat_table.items():
                if l4.dport == public_port:
                    ip.dst = lan_ip
                    l4.dport = lan_port
                    del ip.chksum
                    del l4.chksum
                    break

            return pkt
        except Exception:
            return pkt


class PythonForwarder:
    def __init__(self, logger):
        self.nat = PythonNat()
        self.logger = logger

    def forward_lan_to_wan(self):
        def handle(pkt):
            try:
                pkt = self.nat.nat_outbound(pkt)
                sendp(pkt, iface=WAN_IF, verbose=False)
            except Exception:
                self.logger.exception("Failed to forward packet from LAN to WAN")

        self.logger.info("Forwarding packets from LAN to WAN")
        try:
            sniff(iface=LAN_IF, prn=handle, store=False)
        except Exception:
            self.logger.exception("LAN to WAN forwarder stopped")

    def forward_wan_to_lan(self):
        def handle(pkt):
            try:
                pkt = self.nat.nat_inbound(pkt)
                sendp(pkt, iface=LAN_IF, verbose=False)
            except Exception:
                self.logger.exception("Failed to forward packet from WAN to LAN")

        self.logger.info("Forwarding packets from WAN to LAN")
        try:
            sniff(iface=WAN_IF, prn=handle, store=False)
        except Exception:
            self.logger.exception("WAN to LAN forwarder stopped")

    def start_forwarder(self):
        try:
            t1 = threading.Thread(target=self.forward_lan_to_wan, daemon=True, name="L2W")
            t2 = threading.Thread(target=self.forward_wan_to_lan, daemon=True, name="W2L")
            t1.start()
            t2.start()

        except Exception:
            self.logger.exception("Packet forwarder failed to start")