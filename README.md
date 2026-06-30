# homeLab
Stuff for my home lab


## `infra/`
### First Time Install:
1. SSH into Router
    ```bash
    ssh user@router.lab
    ```
2. Create System User and Group
    ```bash
    sudo groupadd lab-managers
    sudo useradd -m -s /bin/bash labbot
    sudo usermod -aG lab-managers labbot
    ```
3. Create Directory Structure
    ```bash
    sudo mkdir -p /srv/lab/releases
    sudo mkdir -p /srv/lab/current/router
    sudo chown -R labbot:lab-managers /srv/lab
    sudo chmod -R 750 /srv/lab
    ```
4. Load Release
    ```bash
    # SCP folder transfer from dev machine to router
    scp -r JohnDoe@192.168.0.5:/home/Documents/Github/lab/releases/1.0.1 /srv/lab/releases/1.0.1/
    # Or use Git
    git clone --depth 1 --branch v1.0.1 https://github.com/topher2025/homeLab.git /srv/lab/releases/1.0.1/
    ```
    You'll probably also need to change the [iface names](#network-interfaces) and/or the [IP addresses](#ip-addresses)
5. Install Dependencies
    ```bash
    python3 -m venv /srv/lab/current/router/venv
    source /srv/lab/current/router/venv/bin/activate
    pip install -r requirements.txt
    ```

5. Activate Symlink
    ```bash
    ln -sfn /srv/lab/releases/1.0.1 /srv/lab/current
    ```
6. Move Systemd Service Files
    ```bash
    sudo cp /srv/lab/current/router/systemd/*.service /etc/systemd/system
    sudo systemctl daemon-reload
    ```
7. Enable Services
    ```bash
    sudo systemctl enable python-dns.service
    sudo systemctl enable python-dhcp.service
    sudo systemctl enable python-nat.service
    ```
8. Start Services
    ```bash
    sudo systemctl start python-dns python-dhcp python-nat
    ```

### Updates:
1. SSH into Router
    ```bash
    ssh user@router.lab
    ```
2. Load Release
    ```bash
    # SCP Folder transfer from dev machine to router
    scp -r JohnDoe@192.168.0.5:/home/Documents/Github/lab/releases/1.0.2 /srv/lab/releases/1.0.2/
    # Or use Git
    git clone --depth 1 --branch v1.0.2 https://github.com/topher2025/homeLab.git /srv/lab/releases/1.0.2/
    ```
3. Update Symlink
    ```bash
    ln -sfn /srv/lab/releases/1.0.2 /srv/lab/current
    ```
    If you made changes to `config.py`, see [4. Changelogs](#changelogs)
4. Reload Services
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now python-dns.service python-dhcp.service python-nat.service
    ```

### Logs:
1. Systemd Logs
    ```bash
    # Live log stream
    journalctl -u python-dns -f
    # Non-interactive
    journalctl -u python-dns --no-pager
    ```
2. File Logs

    This only works if file logging is configured in `config.py` [see Advanced](#Advanced)
    ```bash
    # Use your prefered pager to open a log file:
    cat /srv/lab/current/router/dhcp.log
    batcat /srv/lab/current/router/dns.log
    less /srv/lab/current/router/nat.log
    ```

### Advanced
1. `config.py`
    `config.py` is structured to have a shared base config class, and then separate config classes for each service. These classes are built as frozen dataclasses, so the services can't change these settings during runtime. This makes these classes similar to JSON config files, but each field has typing incorporated, which is its biggest advantage of a `.json` config file. It also has the advantage of each service only importing the configuration it needs. Each service gets its own config class that inherits from the base configuration class, but each child class can also locally overwrite the settings in the parent class, making it easy to deploy different services on different devices.
2. `.service` files
    `.service` files are built to run each python service as a systemd service. This makes them easy to start, stop, and update. While any of these files can change, a lot of the settings were put in place in order to prevent race-time conditions, dependency issues, and privilage problems. Do not change anything in these files unless you understand the implications of the changes
3. Common Changes in `cofig.py`
    1. Network Interfaces
        ```python
        @dataclass(frozen=True)
        class Base:
            WAN_IFACE: str = "eth1" # Interface to ISP
            LAN_IFACE: str = "eth0" # Interface for inside the network
        ```
        The interface names can be found using 
        ```bash
        ip a
        ip -br a
        lo               UNKNOWN        127.0.0.1/8 ::1/128 
        eth1             UP             192.168.50.10/24 2001:db8:50:1::10/64 # You might have an IPv6 address on you WAN iface
        eth0             UP             192.168.0.1/24 # This is your LAN iface

        ```
    2. IP Addresses
        ```python
        dataclass(frozen=True)
        class DhcpConfig(Base):
            # A lot of IPs are repeated, incase you choose to run different services on different machines
            DHCP_IP: IPv4Address = IPv4Address("192.168.0.1")

            # This is the pool for assignable IPs
            POOL_START: IPv4Address = IPv4Address("192.168.0.2") # Inclusive
            POOL_END: IPv4Address = IPv4Address("192.168.0.100") # Exclusive

            # Sometimes, IPs are linked to IPs for other services
            DNS_IP: IPv4Address = IPv4Address("192.168.0.1")

            # Don't forget to change the subnet if you change the pool too much
            SUBNET_MASK: IPv4Address = IPv4Address("255.255.255.0")

        
        # There are a lot of other IPs that can be changed, just be sure to keep things consistent
        ```
    3. Files
        ```python
        @dataclass(frozen=True)
        class DnsConfig(Base):
            LOG_FILE = "dns.log" # Logging file, overwritten from `Base` The logging setup will handle this being none.
            DNS_FILE: str|PathLike[str] = "dns_table.json" # Save file for the dns table
        ```
    4. Logging
        ```python
        class Setup:
        @staticmethod
        def setup_logging(cfg: Base):
            # By default, logging is sent to stdout, unless there is a logging file configured. You could change the logging handler to a different file handler, or to a different type of handler entirely.
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
            # This function essentially build a root handler, and all the services' loggers are children of this single root.
            if not root.handlers:
                root.addHandler(handler)

            root.setLevel(getattr(logging, cfg.LOG_LEVEL))

        @dataclass(frozen=True)
        class Base:
            # LOG_LEVEL show the options that the logging class will accept
            LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
            # This is the format for all logs. It can be changed per config class
            LOG_FORMAT: str = "%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
            # This should generally not be changed in `Base` unless each service has its own working directory. If multiple services try to write to the same log file, the output will be mixed and difficult to understand.
            LOG_FILE: str|PathLike[str]|None = None
        ```

    5. Restart Services:
        After modifying  `config.py`, restart the affected service(s):
        ```bash
        sudo systemctl restart python-dns
        sudo systemctl restart python-dhcp
        sudo systemctl restart python-nat
        ```
4. Changelog
    Unless a release specifically changes `config.py` or the `.service` files, you can usually copy your existing configuration into the new release directory. When configuration changes are required, compare the old and new versions using a merge tool such as `vimdiff`, `nvim -d`, or `meld`.





```
# from downloading machine
scp -r infra/ user@target:/opt/homeLab/infra/

# from target machine
cd /opt/homeLab/infra
python -m pip install --no-index --find-links=wheelhouse -r requirements.txt
sudo python run_all.py
```
## Goals
Olama
Webserver

## Postgres
Run a minimal local Postgres container with:

```bash
docker compose up -d postgres
```

It uses `postgres/password`, database `mydb`, and exposes port `5432`.


