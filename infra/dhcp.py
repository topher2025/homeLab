# dhcp.py
from pydhcplib.dhcp_network import DhcpServer
from pydhcplib.type_ipv4 import ipv4
from config import DHCP_RANGE
from dns import PythonDnsServer
import ipaddress





class PythonDhcpServer(DhcpServer):
    def __init__(self, options, dns, logger):
        self.logger = logger
        self.dns = dns
        self.leases = {}

        try:
            base_init = getattr(super(), "__init__", None)
            if callable(base_init):
                base_init(options)
            self.pool_start = ipv4(DHCP_RANGE[0])
            self.client_port = options.get("client_listen_port", 68)
        except Exception:
            self.logger.exception("Failed to initialize DHCP server")
            raise

    def _send_broadcast(self, packet, action):
        try:
            self.SendDhcpPacketTo(packet, ipv4("255.255.255.255"), self.client_port)
        except Exception:
            self.logger.exception("Failed to send DHCP %s response", action)
            raise

    def HandleDhcpDiscover(self, packet):
        try:
            offer = self.CreateDhcpOffer(packet)
            self._send_broadcast(offer, "discover")
            self.logger.info("Received DHCP Discover")
        except Exception:
            self.logger.exception("Failed to handle DHCP Discover")

    def HandleDhcpRequest(self, packet):
        try:
            ack = self.CreateDhcpAck(packet)
            self._send_broadcast(ack, "request")
            self.logger.info("Received DHCP Request")

            hostname = packet.GetOption("host_name")
            yiaddr = ack.GetOption("yiaddr")
            ip = str(ipaddress.IPv4Address(yiaddr))
            if hostname:
                name = hostname.decode()
                self.logger.info("Gave %s to %s", ip, name)
                self.dns.add_record(hostname=str(name), ip=ip)
            else:
                self.logger.warning("DHCP Request was missing hostname")
                self.logger.info("Gave %s", ip)
        except Exception:
            self.logger.exception("Failed to handle DHCP Request")

    def start_dhcp(self):
        try:
            self.BindToAddress()
            self.logger.info("Started DHCP server")
            self.Listen()
        except Exception:
            self.logger.exception("DHCP server stopped")

