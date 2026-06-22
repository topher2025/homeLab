# dhcp.py
from pydhcplib.dhcp_network import DhcpServer
from pydhcplib.type_ipv4 import ipv4
from config import DHCP_RANGE
from dns import PythonDnsServer


DHCP_OPTIONS = {
    "server_listen_port": 67,
    "client_listen_port": 68,
    "listen_address": "0.0.0.0",
}

class PythonDhcpServer(DhcpServer):
    def __init__(self, options, dns):
        super().__init__(options)
        self.pool_start = ipv4(DHCP_RANGE[0])
        self.pool_end = ipv4(DHCP_RANGE[1])
        self.leases = {}
        self.dns = dns

    def HandleDhcpDiscover(self, packet):
        offer = self.CreateDhcpOffer(packet)
        self.SendDhcpPacketTo(offer, ipv4("255.255.255.255"))

    def HandleDhcpRequest(self, packet):
        ack = self.CreateDhcpAck(packet)
        self.SendDhcpPacketTo(ack, ipv4("255.255.255.255"))

        hostname = packet.GetOption("host_name")
        yiaddr = packet.GetOption("yiaddr")
        if hostname and yiaddr:
            name = hostname.decode()
            ip = ".".join(map(str, yiaddr))
            self.dns.add_record(hostname=name, ip=ip)


def create_dhcp_server(dns=None):
    dns_server = dns or PythonDnsServer()
    return PythonDhcpServer(DHCP_OPTIONS, dns_server)


def start_dhcp():
    server = create_dhcp_server()
    server.BindToAddress()
    server.Listen()


if __name__ == "__main__":
    start_dhcp()