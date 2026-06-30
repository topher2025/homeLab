from json import dump, load, dumps
from ipaddress import IPv4Address
import logging
import time
from os.path import exists, isfile

from scapy.all import mac2str, sendp, sniff
from scapy.layers.dhcp import BOOTP, DHCP
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether

from config import DhcpConfig, Setup


class DHCPPython:
    def __init__(self, cfg: DhcpConfig, logger):
        self.logger = logger
        self.r = Setup.redis()
        self.cfg = cfg
        self.ips = {
            "leases": {},
            "offered": {},
            "available": [],
        }
        self._fill_available()
        self.remove_expired()

    def _publish_lease(self, domain, ip, ttl, sender="dhcp"):
        msg = {
            "type": "lease",
            "domain": domain,
            "ip": str(ip),
            "ttl": ttl,
            "sender": sender
        }

        self.r.publish("dns_updates", dumps(msg))    

    def _fill_available(self):
        if exists(self.cfg.LEASE_FILE) and isfile(self.cfg.LEASE_FILE):
            with open(self.cfg.LEASE_FILE, 'r') as f:
                data = load(f)
                self.ips = self._deserialize_json(data)
            return
        
        for ip in range(int(self.cfg.POOL_START), int(self.cfg.POOL_END)+1):
            self.ips["available"].append(IPv4Address(ip))

    def _serialize_ips(self):
        return {
            "leases": {
                str(ip): lease
                for ip, lease in self.ips["leases"].items()
            },
            "offered": {
                str(ip): offer
                for ip, offer in self.ips["offered"].items()
            },
            "available": [
                str(ip)
                for ip in self.ips["available"]
            ]
        }

    def _deserialize_json(self, data):
        return {
            "leases": {
                IPv4Address(ip): lease
                for ip, lease in data["leases"].items()
            },
            "offered": {
                IPv4Address(ip): offer
                for ip, offer in data["offered"].items()
            },
            "available": [
                IPv4Address(ip)
                for ip in data["available"]
            ]
        }


    def handle_packet(self, pkt):
        if DHCP not in pkt:
            return
        
        options = dict(
            (opt[0], opt[1])
            for opt in pkt[DHCP].options
            if isinstance(opt, tuple)
        )
        
        msg_type = options.get("message-type")
        if msg_type==1 or msg_type==3:
            client_mac = pkt[Ether].src
            xid = pkt[BOOTP].xid

            self.remove_expired()
            
            if msg_type == 1:
                self.logger.info(f"Discover from {client_mac}")
                self.send_offer(client_mac, xid)
            elif msg_type == 3:
                requested_ip = options.get("requested_addr")
                if not requested_ip:
                    requested_ip = pkt[BOOTP].ciaddr
            
                self.lease_ip(client_mac, IPv4Address(requested_ip), xid)

    def send_offer(self, client_mac, xid):
        if not self.ips["availavle"]:
            self.logger.warning("No available ips")
            return
        ip = self.ips["available"].pop(0)
        self.ips["offered"][ip] = {
            "time": time.time(),
            "mac": client_mac,
            "xid": xid
            }

        offer = (
            Ether(dst="ff:ff:ff:ff:ff:ff") /
            IP(src=self.cfg.DHCP_IP, dst="255.255.255.255") /
            UDP(sport=67, dport=68) /
            BOOTP(
                op=2,
                yiaddr=ip,
                siaddr=self.cfg.DHCP_IP,
                chaddr=mac2str(client_mac),
                xid=xid
            ) /
            DHCP(options=[
                ("message-type", "offer"),
                ("server_id", self.cfg.DHCP_IP),
                ("subnet_mask", self.cfg.SUBNET_MASK),
                ("router", self.cfg.ROUTER_IP),
                ("name_server", self.cfg.DNS_IP),
                ("lease_time", self.cfg.LEASE_TIME),
                "end"
            ])
        )
        
        sendp(offer, iface=self.cfg.LAN_IFACE)
        self.logger.info(f"Offered {ip} to {client_mac}")

    def lease_ip(self, client_mac, ip, xid):
        if ip in self.ips["leases"]:
            if self.ips["leases"][ip]["mac"] == client_mac:
                self.ips["leases"][ip]["time"] = time.time()
                self.send_ack(client_mac, ip, xid)
                self.logger.info(f"Renewed lease for {ip} to {client_mac}")
                return
        elif ip in self.ips["offered"]:
            if self.ips["offered"][ip]["mac"] == client_mac:
                self.ips["leases"][ip] = self.ips["offered"][ip]
                self.ips["offered"].pop(ip)
                self.ips["leases"][ip]["time"] = time.time()
                self.ips["leases"][ip].pop("xid")
                self.send_ack(client_mac, ip, xid)
                self.logger.info(f"Confirmed lease for {ip} to {client_mac}")
                return
        elif ip in self.ips["available"]:
            self.ips["available"].remove(ip)
            self.ips["leases"][ip] = {"time": time.time(), "mac": client_mac}
            self.send_ack(client_mac, ip, xid)
            self.logger.info(f"Created new lease for {ip} to {client_mac}")
            return
        
        self.logger.warning(f"Failed to lease {ip} to {client_mac}")
        self.send_nak(client_mac, xid)

    def send_ack(self, client_mac, ip, xid):
        ack = (
            Ether(dst="ff:ff:ff:ff:ff:ff") /
            IP(src=self.cfg.DHCP_IP, dst="255.255.255.255") /
            UDP(sport=67, dport=68) /
            BOOTP(
                op=2,
                yiaddr=str(ip),
                siaddr=self.cfg.DHCP_IP,
                chaddr=mac2str(client_mac),
                xid=xid
            ) /
            DHCP(options=[
                ("message-type", "ack"),
                ("server_id", self.cfg.DHCP_IP),
                ("subnet_mask", self.cfg.SUBNET_MASK),
                ("router", self.cfg.ROUTER_IP),
                ("name_server", self.cfg.DNS_IP),
                ("lease_time", self.cfg.LEASE_TIME),
                "end"
            ])
        )

        sendp(ack, iface=self.cfg.LAN_IFACE)

    def send_nak(self, client_mac, xid):
        nak = (
            Ether(dst="ff:ff:ff:ff:ff:ff") /
            IP(src=self.cfg.DHCP_IP, dst="255.255.255.255") /
            UDP(sport=67, dport=68) /
            BOOTP(
                op=2,
                yiaddr="0.0.0.0",
                siaddr=self.cfg.DHCP_IP,
                chaddr=mac2str(client_mac),
                xid=xid
            ) /
            DHCP(options=[
                ("message-type", "nak"),
                ("server_id", self.cfg.DHCP_IP),
                "end"
            ])
        )

        sendp(nak, iface=self.cfg.LAN_IFACE)

    def remove_expired(self):
        now = time.time()

        for ip, offer in list(self.ips["offered"].items()):
            if now-offer["time"] > self.cfg.OFFER_TIME:
                del self.ips["offered"][ip]
                self.ips["available"].append(ip)

        for ip, lease in list(self.ips["leases"].items()):
            if now - lease["time"] > self.cfg.LEASE_TIME:
                del self.ips["leases"][ip]
                self.ips["available"].append(ip)

    def cleanup(self):
        self.logger.info("Stopping DHCP server")
        with open(self.cfg.LEASE_FILE, 'w') as f:
            dump(self._serialize_ips, f)
        self.logger.info(f"Dumped leases into {self.cfg.LEASE_FILE}")


    def run(self):
        sniff(
            iface = self.cfg.LAN_IFACE,
            filter="udp and (port 67 or port 68)",
            prn=self.handle_packet,
            store=False
        )
        

def main():
    cfg = DhcpConfig()
    Setup.setup_logging(cfg)
    logger = logging.getLogger("DHCP")
    server = DHCPPython(cfg, logger)

    try:
        server.run()
    finally:
        server.cleanup()


if __name__ == "__main__":
    main()
