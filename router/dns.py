from scapy.all import mac2str, sendp, sniff, sr1, AsyncSniffer
from scapy.layers.dns import DNS, DNSQR, DNSRR
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
import logging
from json import dump, dumps, loads
import threading
from time import time


from config import DnsConfig, Setup

class DNSPython():
    def __init__(self, cfg: DnsConfig, logger):
        self.logger = logger
        self.cfg = cfg
        self.dns_table = {}
        self.r = Setup.redis()
        self.pubsub = self.r.pubsub()
        self.pubsub.subscribe("dns_updates")

    def _normalize_ttl(self, ttl=300):
        return max(self.cfg.MIN_TTL, min(ttl, self.cfg.MAX_TTL))


    def listener(self, stop_event):
        self.logger.info("Redis listener started")

        while not stop_event.is_set():
            msg = self.pubsub.get_message(timeout=1)

            if msg is None:
                continue
            if msg["type"] != "message":
                continue

            try:
                data = loads(msg["data"])
                if data["type"] == "lease":
                    self.add_record(data["domain"], data["ip"], data["ttl"])
            except Exception as e:
                self.logger.error(f"Redis parse error: {e}")
    

    def handle_packet(self, pkt):
        if pkt.haslayer(DNS):
            if pkt[DNS].qr == 0:
                qname = pkt[DNS][DNSQR].qname.decode()
                resp = self.local(qname)
                if not resp:
                    resp =self.forward(qname)
                if resp:
                    self.send_reply(pkt, resp)
                else:
                    return

    def send_reply(self, pkt, ip):
        reply = IP(dst=pkt[IP].src, src=pkt[IP].dst) / UDP(
            dport=pkt[UDP].sport,
            sport=53
        ) / DNS(
            id=pkt.id,
            qr=1,
            aa=1,
            qd=pkt.qd,
            an=DNSRR(rrname=pkt[DNS][DNSQR].qname.decode(), rdata=ip)
        )

        sendp(reply, verbose=0)

    def local(self, qname):
        a = self.dns_table.get(str(qname))
        if a and time()-a["time"] < a["ttl"]:
            return str(a["ip"])
        return None

    def forward(self, qname):
        pkt = (
            IP(dst=self.cfg.UPSTREAM) /
            UDP(dport=53) /
            DNS(
                rd=1,
                qd=DNSQR(qname=qname)
            )
        )

        resp = sr1(pkt, timeout=2, verbose=0)
        if resp and resp.haslayer(DNS) and resp[DNS].an:
            ttl = resp[DNSRR].ttl
            ip = resp[DNS].an.rdata
            self.add_record(qname, ip, ttl)
            return ip
        
        return None
    
    def add_record(self, domain, ip, ttl):
        if not ip and domain:
            return
        
        self.dns_table[str(domain)] = {"ip": str(ip), "ttl": self._normalize_ttl(int(ttl)), "now": int(time())}
        self.logger.info(f"Added record {str(domain)} : {self.dns_table[str(domain)]}")

    def cleanup(self):
        self.logger.info("Stopping DHCP server")

        if hasattr(self, "stop_event"):
            self.stop_event.set()
        if hasattr(self, "redis_thread"):
            self.redis_thread.join(timeout=2)
        if hasattr(self, "sniffer"):
            self.sniffer.stop()

        with open(self.cfg.DNS_FILE, 'w') as f:
            dump(self.dns_table, f)
        self.logger.info(f"Dumped leases into {self.cfg.DNS_FILE}")


    def run(self):
        self.stop_event = threading.Event()
        self.redis_thread = threading.Thread(
            target=self.listener,
            args=(self.stop_event,),
            daemon=True
        )
        self.redis_thread.start()

        self.sniffer = AsyncSniffer(
            iface=self.cfg.LAN_IFACE,
            filter="udp port 53",
            prn=self.handle_packet,
            store=False
        )
        self.sniffer.start()

        self.logger.info("DNS server started")
        self.stop_event.wait()
        

def main():
    cfg = DnsConfig()
    Setup.setup_logging(cfg)
    logger = logging.getLogger("DNS")
    server = DNSPython(cfg, logger)

    try:
        server.run()
    finally:
        server.cleanup()


if __name__ == "__main__":
    main()
