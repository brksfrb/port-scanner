"""
scanner.py — Multi-threaded LAN port scanner.

Scans a range of 192.168.x.x addresses across a configurable set of ports,
reporting open ports to stdout and a live Tkinter progress window.
"""

import socket
import time
from threading import Thread, Lock

from colorama import Fore, init as colorama_init

from log import TkinterLogWindow

colorama_init(autoreset=True)

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

scanned_ips: dict[int, list[str]] = {}
scan_lock = Lock()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

START_IP = "192.168.1.0"
END_IP = "192.168.255.255"
PORTS = (80,)
NUM_SCANNERS = 4000  # Thread count — keep ≤ 500 to avoid OS limits
TIMEOUT = 1.0       # Per-connection timeout in seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_two_octets(ip: str) -> tuple[int, int]:
    """Return the (subnet, host) octets of a 192.168.x.x address."""
    parts = ip.split(".")
    return int(parts[2]), int(parts[3])


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class IPPort:
    """Pairs an IP address with a specific port to scan."""

    def __init__(self, ip: str, port: int) -> None:
        self._ip = ip
        self._port = port

    @property
    def value(self) -> str:
        return self._ip

    @property
    def port(self) -> int:
        return self._port

    @property
    def subnet(self) -> int:
        return _last_two_octets(self._ip)[0]

    @property
    def host(self) -> int:
        return _last_two_octets(self._ip)[1]

    def __repr__(self) -> str:
        return f"IPPort({self._ip}:{self._port})"


# ---------------------------------------------------------------------------
# Port checking
# ---------------------------------------------------------------------------

def check_port(ip: str, port: int, timeout: float = TIMEOUT) -> dict:
    """
    Attempt a TCP connection to *ip*:*port*.

    Returns::

        {
            "open": bool,
            "host": str,   # reverse-DNS hostname or "unknown"
        }
    """
    open_ = False
    hostname = "unknown"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        if sock.connect_ex((ip, port)) == 0:
            open_ = True
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                pass

    return {"open": open_, "host": hostname}


# ---------------------------------------------------------------------------
# Threading
# ---------------------------------------------------------------------------

class ScanThread:
    """Scans a subset of IPPort targets in a background daemon thread."""

    def __init__(self, targets: list[IPPort], log_window: TkinterLogWindow) -> None:
        self._targets = targets
        self._log = log_window
        self._thread = Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        for target in self._targets:
            # Register subnet bucket (thread-safe)
            with scan_lock:
                scanned_ips.setdefault(target.subnet, [])

            result = check_port(target.value, target.port)

            with scan_lock:
                scanned_ips[target.subnet].append(target.value)

            if result["open"]:
                msg = f"Open port {target.port} on {target.value} ({result['host']})"
                print(Fore.GREEN + msg)
                self._log.update_log(msg)

            self._log.update_progress()


class Scanner:
    """Builds the target list and distributes work across ScanThreads."""

    def __init__(
        self,
        start_ip: str,
        end_ip: str,
        ports: tuple[int, ...],
        num_threads: int,
        log_window: TkinterLogWindow,
    ) -> None:
        self._start = IPPort(start_ip, ports[0])
        self._end = IPPort(end_ip, ports[0])
        self._ports = ports
        self._num_threads = num_threads
        self._log = log_window

        self.targets = self._build_target_list()
        self._threads: list[ScanThread] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Partition targets across threads and launch them."""
        self._threads = self._create_threads()
        print(f"Launching {len(self._threads)} scanner thread(s) "
              f"across {len(self.targets)} target(s)…")
        for t in self._threads:
            t.start()

    @property
    def total(self) -> int:
        return len(self.targets)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_target_list(self) -> list[IPPort]:
        targets: list[IPPort] = []
        start_subnet, start_host = self._start.subnet, self._start.host
        end_subnet, end_host = self._end.subnet, self._end.host

        for subnet in range(start_subnet, end_subnet + 1):
            h_start = start_host if subnet == start_subnet else 0
            h_end = end_host if subnet == end_subnet else 255
            for host in range(h_start, h_end + 1):
                for port in self._ports:
                    targets.append(IPPort(f"192.168.{subnet}.{host}", port))

        return targets

    def _create_threads(self) -> list[ScanThread]:
        n = min(self._num_threads, len(self.targets))
        chunk = len(self.targets) // n
        remainder = len(self.targets) % n
        threads: list[ScanThread] = []
        idx = 0
        for i in range(n):
            end = idx + chunk + (1 if i < remainder else 0)
            threads.append(ScanThread(self.targets[idx:end], self._log))
            idx = end
        return threads


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    log_window = TkinterLogWindow()

    scanner = Scanner(
        start_ip=START_IP,
        end_ip=END_IP,
        ports=PORTS,
        num_threads=NUM_SCANNERS,
        log_window=log_window,
    )

    log_window.set_total_ips(scanner.total)
    scanner.start()

    print(f"IP range   : {START_IP} – {END_IP}")
    print(f"Ports      : {PORTS}")
    print(f"Targets    : {scanner.total}")
    print(f"Threads    : {NUM_SCANNERS}")

    # Progress loop — runs until every target has been checked
    while True:
        with scan_lock:
            completed = sum(len(v) for v in scanned_ips.values())
        print(f"Progress   : {completed} / {scanner.total}")
        if completed >= scanner.total:
            print("Scan complete.")
            break
        time.sleep(1)

    # Keep the GUI open until the user closes it
    log_window._thread.join()


if __name__ == "__main__":
    main()