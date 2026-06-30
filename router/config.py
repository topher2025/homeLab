from dataclasses import dataclass
from typing import Literal
from os import PathLike
from ipaddress import IPv4Address
import logging
import redis
from logging.handlers import RotatingFileHandler



# ====================
# Setup
# ====================
class Setup:
    @staticmethod
    def setup_logging(cfg: Base):
        if not cfg.LOG_FILE:
            handler = logging.StreamHandler()
        else:
            handler = RotatingFileHandler(
                filename=cfg.LOG_FILE,
                maxBytes=5_000_000,
                backupCount=10
            )

        formatter = logging.Formatter(cfg.LOG_FORMAT)
        handler.setFormatter(formatter)
        root = logging.getLogger()

        if not root.handlers:
            root.addHandler(handler)

        root.setLevel(getattr(logging, cfg.LOG_LEVEL))


    @staticmethod
    def redis():
        return redis.Redis(host="localhost", port=6379, decode_responses=True)

# ====================
# Base
# ====================
@dataclass(frozen=True)
class Base:
    WAN_IFACE: str = "eht1"
    LAN_IFACE: str = "eth0"
    API: str = "192.168.0.1:8000/api"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: str = "%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
    LOG_FILE: str|PathLike[str]|None = None
    ROUTER_IP: IPv4Address = IPv4Address("192.168.0.1")



# ====================
# DHCP
# ====================
@dataclass(frozen=True)
class DhcpConfig(Base):
    LOG_FILE = "dhcp.log"
    DHCP_IP: IPv4Address = IPv4Address("192.168.0.1")
    POOL_START: IPv4Address = IPv4Address("192.168.0.2")
    POOL_END: IPv4Address = IPv4Address("192.168.0.50")
    LEASE_TIME: int = 3600
    OFFER_TIME: int = 15
    DNS_IP: IPv4Address = IPv4Address("192.168.0.1") # Linked to DNS
    DOMAIN_NAME: str = "lab"
    SUBNET_MASK: IPv4Address = IPv4Address("255.255.255.0")
    LEASE_FILE: str|PathLike[str] = "leases.json"


# ====================
# DNS
# ====================
@dataclass(frozen=True)
class DnsConfig(Base):
    LOG_FILE = "dns.log"
    UPSTREAM: IPv4Address = IPv4Address("8.8.8.8")
    DNS_FILE: str|PathLike[str] = "dns_table.json"
    MIN_TTL: int = 60
    MAX_TTL: int = 3600


# ====================
# DNS
# ====================
@dataclass(frozen=True)
class NatConfig(Base):
    LOG_FILE = "nat.log"
    POOL_START: int = 10_000
    POOL_END: int = 65_000
    WAN_ADDR: IPv4Address = IPv4Address("192.168.50.106")
    TCP_TTL: int = 1800
    UDP_TTL: int = 60
    ICMP_TTL: int = 45
