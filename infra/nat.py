import threading
from scapy.all import IP, TCP, UDP, sendp, sniff

from config import PUBLIC_IP, LAN_IF, WAN_IF
from shared_state import memory


class PythonNat:
    def __init__(self):
        self.nat_table = memory.nat_table

    def nat_outbound(self, pkt):
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

    def nat_inbound(self, pkt):
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


class PythonForwarder:
    def __init__(self):
        self.nat = PythonNat()

    def forward_lan_to_wan(self):
        def handle(pkt):
            pkt = self.nat.nat_outbound(pkt)
            sendp(pkt, iface=WAN_IF, verbose=False)

        sniff(iface=LAN_IF, prn=handle, store=False)

    def forward_wan_to_lan(self):
        def handle(pkt):
            pkt = self.nat.nat_inbound(pkt)
            sendp(pkt, iface=LAN_IF, verbose=False)

        sniff(iface=WAN_IF, prn=handle, store=False)

def start_forwarder():
    forwarder = PythonForwarder()

    t1 = threading.Thread(target=forwarder.forward_lan_to_wan, daemon=True)
    t2 = threading.Thread(target=forwarder.forward_wan_to_lan, daemon=True)
    t1.start()
    t2.start()

    t1.join()
    t2.join()