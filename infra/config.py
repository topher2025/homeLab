LAN_IF = "eth1"
WAN_IF = "eth0"

LAN_NET = "192.168.50.0/24"
LAN_GATEWAY = "192.168.50.1"

DHCP_RANGE = ("192.168.0.5", "192.168.0.50")
UPSTREAM_DNS = "1.1.1.1"
PUBLIC_IP = "192.168.0.0"  # TODO get an actuall ip adress


A = {
    "router.lab": LAN_GATEWAY
}


PTR = {
    ".".join(LAN_GATEWAY.split(".")[::-1]) + ".in-addr.arpa": "router.lab"
}
