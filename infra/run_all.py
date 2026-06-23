import threading

from dhcp import PythonDhcpServer
from dns import PythonDnsServer
from nat import PythonForwarder
from logger import get_logger


def run_all():
    DHCP_OPTIONS = {
        "server_listen_port": 67,
        "client_listen_port": 68,
        "listen_address": "0.0.0.0",
    }

    logger = get_logger("router")
    try:
        dns = PythonDnsServer(logger)
    except Exception:
        logger.exception("Failed to initialize DNS server")
        dns = None

    try:
        dhcp = PythonDhcpServer(DHCP_OPTIONS, dns, logger) if dns is not None else None
    except Exception:
        logger.exception("Failed to initialize DHCP server")
        dhcp = None

    try:
        nat = PythonForwarder(logger)
    except Exception:
        logger.exception("Failed to initialize packet forwarder")
        nat = None

    def start_thread(name, target):
        def run_target():
            try:
                target()
            except Exception:
                logger.exception("%s thread crashed", name)

        thread = threading.Thread(target=run_target, daemon=True, name=name)
        thread.start()
        return thread

    threads = []
    if dns is not None:
        threads.append(start_thread("DNS", dns.start_dns))
    if dhcp is not None:
        threads.append(start_thread("DHCP", dhcp.start_dhcp))
    if nat is not None:
        threads.append(start_thread("FORWARDER", nat.start_forwarder))

  

if __name__ == "__main__":
    run_all()
