import socket
from dnslib import A, DNSRecord, PTR, QTYPE, RR
from config import UPSTREAM_DNS
from shared_state import memory


class PythonDnsServer:
    def __init__(self):
        self.A = memory.a_records
        self.PTR = memory.ptr_records

    def add_record(self, hostname, ip):
        self.A[hostname] = ip
        self.PTR[".".join(ip.split(".")[::-1]) + ".in-addr.arpa"] = hostname

    def forward(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
            upstream.sendto(data, (UPSTREAM_DNS, 53))
            resp_data, _ = upstream.recvfrom(512)
        return resp_data

    def start_dns(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 53))

        print("DNS routing server running on port 53...")

        while True:
            data, addr = sock.recvfrom(512)
            request = DNSRecord.parse(data)

            qname_raw = str(request.q.qname)
            qname = qname_raw.rstrip(".")
            qtype = request.q.qtype

            reply = request.reply()
            if qtype == QTYPE.PTR:
                if qname in self.PTR:
                    hostname = self.PTR[qname]
                    reply.add_answer(RR(request.q.qname, QTYPE.PTR, rdata=PTR(hostname)))
                else:
                    resp = self.forward(data)
                    sock.sendto(resp, addr)
                    continue
            else:
                ip = self.A.get(qname)
                if ip:
                    reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A(ip), ttl=60))
                else:
                    resp = self.forward(data)
                    sock.sendto(resp, addr)
                    continue

            sock.sendto(reply.pack(), addr)





def start_dns():
    dns = PythonDnsServer()
    dns.start_dns()


if __name__ == "__main__":
    start_dns()