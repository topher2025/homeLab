import socket
from dnslib import A, DNSRecord, PTR, QTYPE, RR
from config import UPSTREAM_DNS
from shared_state import memory


class PythonDnsServer:
    def __init__(self, logger):
        self.A = memory.a_records
        self.PTR = memory.ptr_records
        self.logger = logger

    def add_record(self, hostname, ip):
        try:
            self.A[hostname] = ip
            self.PTR[".".join(ip.split(".")[::-1]) + ".in-addr.arpa"] = hostname
            self.logger.info(f"Added DNS record {{'{hostname}':'{ip}'}}")
        except Exception:
            self.logger.exception("Failed to add DNS record for hostname=%s ip=%s", hostname, ip)

    def forward(self, data):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
                upstream.settimeout(3.0)
                upstream.sendto(data, (UPSTREAM_DNS, 53))
                resp_data, _ = upstream.recvfrom(512)
            self.logger.info("Forwarded DNS query to upstream DNS server %s", UPSTREAM_DNS)
            return resp_data
        except Exception:
            self.logger.exception("Failed to forward DNS query to upstream DNS server %s", UPSTREAM_DNS)
            return None

    def start_dns(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", 53))
            self.logger.info("DNS routing server running on port 53")

            while True:
                try:
                    data, addr = sock.recvfrom(512)
                    request = DNSRecord.parse(data)
                except Exception:
                    self.logger.exception("Failed to receive or parse DNS packet")
                    continue

                try:
                    qname_raw = str(request.q.qname)
                    qname = qname_raw.rstrip(".")
                    qtype = request.q.qtype
                    reply = request.reply()

                    if qtype == QTYPE.PTR:
                        self.logger.info("Received DNS PTR for %s from %s", qname, addr)
                        if qname in self.PTR:
                            hostname = self.PTR[qname]
                            reply.add_answer(RR(request.q.qname, QTYPE.PTR, rdata=PTR(hostname)))
                        else:
                            resp = self.forward(data)
                            if resp is not None:
                                sock.sendto(resp, addr)
                            continue
                    else:
                        ip = self.A.get(qname)
                        self.logger.info("Received DNS request for %s from %s", qname, addr)
                        if ip:
                            reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A(ip), ttl=60))
                        else:
                            resp = self.forward(data)
                            if resp is not None:
                                sock.sendto(resp, addr)
                            continue

                    sock.sendto(reply.pack(), addr)
                except Exception:
                    self.logger.exception("Failed to process DNS request from %s", addr)
        except Exception:
            self.logger.exception("DNS server failed to start")
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    self.logger.exception("Failed to close DNS socket")

