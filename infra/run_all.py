import threading

from dhcp import create_dhcp_server, start_dhcp
from dns import PythonDnsServer
from nat import start_forwarder


def run_all():
    dns = PythonDnsServer()
    dhcp = create_dhcp_server(dns)


    dns_thread = threading.Thread(target=dns.start_dns, daemon=True)
    dhcp_thread = threading.Thread(target=start_dhcp, daemon=True)
    nat_thread = threading.Thread(target=start_forwarder, daemon=True)

    dns_thread.start()
    dhcp_thread.start()
    nat_thread.start()


if __name__ == "__main__":
    run_all()
