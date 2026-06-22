"""Shared in-memory state for infra services.

This module intentionally exposes one singleton object so DNS, DHCP,
and NAT can share runtime state when running in the same Python process.
"""

from config import A as A_TABLE, PTR as PTR_TABLE


class SharedState:
    def __init__(self):
        self.a_records = A_TABLE
        self.ptr_records = PTR_TABLE
        self.nat_table = {}  # (lan_ip, lan_port) -> public_port
        self.next_port = 40000


memory = SharedState()
