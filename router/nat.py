from scapy.all import sendp, sniff, AsyncSniffer
from scapy.layers.inet import IP, TCP, UDP, ICMP
from random import randint
from time import time, sleep
import logging

from config import Setup, NatConfig


class NATPython:
    def __init__(self, cfg: NatConfig, logger):
        self.logger = logger
        self.cfg = cfg
        self.nat_table = {}

    def _allocate_port(self):
        start = randint(self.cfg.POOL_START, self.cfg.POOL_END)
        port = start
        while True:
            if port not in self.nat_table:
                return port
            if port == self.cfg.POOL_END:
                port = self.cfg.POOL_START
            else:
                port += 1
            if port == start:
                self.logger.warning("Could not find free port")


    def add_entry(self, private_ip, private_port, protocol):
        if protocol not in (6, 17, 1):
            self.logger.warning(f"Unsuported protocol {protocol}")
            return
        public_port = self._allocate_port()
        if protocol != 1:
            self.nat_table[public_port] = {
                "private_ip": private_ip,
                "private_port": private_port,
                "protocol": protocol,
                "time": time()
            }
        else:
            self.nat_table[public_port] = {
                "private_ip": private_ip,
                "private_id": private_port,
                "protocol": protocol,
                "time": time()
            }

        self.logger.info(f"Added NAT entry {public_port} : {self.nat_table[public_port]}")
        return public_port
    
    def find_entry(self, public_port):
        return self.nat_table.get(public_port)
    
    def nat_outbound(self, pkt):
        transport = pkt[TCP] or pkt[UDP] or pkt[ICMP]
        if pkt.haslayer(TCP):
            transport.sport = self.add_entry(pkt[IP].src, transport.sport, pkt[IP].proto)
            del pkt[TCP].chksum
            
        elif pkt.haslayer(UDP):
            transport.sport = self.add_entry(pkt[IP].src, transport.sport, pkt[IP].proto)
            del pkt[UDP].chksum
            
        else:
            transport.id = self.add_entry(pkt[IP].src, pkt[ICMP].id, pkt[IP].proto)
            del pkt[ICMP].chksum
            
        pkt[IP].src = str(self.cfg.WAN_ADDR)    
        del pkt[IP].len
        del pkt[IP].chksum

        return pkt

    def nat_inbound(self, pkt):
        transport = pkt[TCP] or pkt[UDP] or pkt[ICMP]
        if pkt.haslayer(ICMP):
            entry = self.find_entry(pkt[ICMP].id)
        else:
            entry = self.find_entry(transport.dport)
        if entry is None:
            self.logger.warning(f"Couldn't find match for {transport.dport} in NAT table")
            return None
        
        pkt[IP].dst = entry["private_ip"]
        
        if pkt.haslayer(TCP):
            transport.dport = entry["private_port"]
            del pkt[TCP].chksum
        elif pkt.haslayer(UDP):
            transport.dport = entry["private_port"]
            del pkt[UDP].chksum
        else:
            transport.id = entry["private_id"]
            del pkt[ICMP].chksum
        
        del pkt[IP].chksum
        del pkt[IP].len
        return pkt

    def handle_packet(self, pkt):
        if not (pkt.haslayer(IP) or pkt.haslayer(TCP) or pkt.haslayer(UDP)):
            self.logger.warning("Packet wasn't using a supported protocol")

        if pkt.sniffed_on == self.cfg.WAN_IFACE:
            p = self.nat_inbound(pkt)
            self.logger.info("Rewrote inbound packet")
        elif pkt.sniffed_on == self.cfg.LAN_IFACE:
            p = self.nat_outbound(pkt)
            self.logger.info("Rewrote outbound packet")
        else:
            self.logger.warning("Packet wasn't on an excepted interface")
            return
        if not p:
            return
        
        sendp(p, iface=pkt.sniffed_on)

    def remove_expired(self):
        now = time()
        delete = []

        for key, entry in self.nat_table.items():
            if entry["protocol"] == 1 and now - entry["time"] > self.cfg.ICMP_TTL:
                delete.append(key)   
            elif entry["protocol"] == 6 and now - entry["time"] > self.cfg.TCP_TTL:
                delete.append(key)
            elif entry["protocol"] == 17 and now - entry["time"] > self.cfg.UDP_TTL:
                delete.append(key)
        
        for key in delete:
            del self.nat_table[key]
            
    def cleanup(self):
        self.logger.info("Stopping NAT server")
        self.sniffer.stop()
        self.end = True


    def run(self):
        self.sniffer = AsyncSniffer(
            iface = [self.cfg.LAN_IFACE, self.cfg.WAN_IFACE],
            prn=self.handle_packet,
            store=False,
            filter="ip"
        )
        self.sniffer.start()
        self.logger.info("NAT server started")
        self.end = False

        while not self.end:
            sleep(15)
            self.remove_expired()


def main():
    cfg = NatConfig()
    Setup.setup_logging(cfg)
    logger = logging.getLogger("DNS")
    server = NATPython(cfg, logger)

    try:
        server.run()
    finally:
        server.cleanup()


if __name__ == "__main__":
    main()
