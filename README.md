# 🔍 LAN Port Scanner

A fast, multi-threaded LAN port scanner with a live Tkinter progress window.

Scans a range of `192.168.x.x` addresses across configurable ports and reports
open ports in real time — both in the terminal and in a GUI log window.

**A full 192.168.0.0 – 192.168.255.255 sweep (65,535 IPs, single port) completes in ~10 seconds.**

---

## Features

- Multi-threaded scanning (configurable thread count)
- Live GUI progress bar and scrollable log window
- Reverse-DNS hostname resolution for discovered hosts
- Colour-coded terminal output via `colorama`
- Thread-safe by design

---

## Requirements

- Python 3.10+
- `colorama`

Install dependencies:

```bash
pip install colorama
```

> `tkinter` ships with the standard Python installer on Windows and macOS.  
> On Debian/Ubuntu: `sudo apt install python3-tk`

---

## Usage

1. Edit the configuration block near the top of `scanner.py`:

```python
START_IP    = "192.168.1.0"
END_IP      = "192.168.1.255"
PORTS       = (80, 443, 5000)
NUM_SCANNERS = 200    # thread count — keep ≤ 500 to avoid OS limits
TIMEOUT     = 1.0     # seconds per connection attempt
```

2. Run:

```bash
python scanner.py
```

A progress window will open automatically. When the scan finishes the window
stays open until you close it.

---

## Project Structure

```
.
├── scanner.py   # Entry point — Scanner, ScanThread, IPPort
├── log.py       # TkinterLogWindow — thread-safe GUI progress window
└── README.md
```

---

## Performance

For maximum efficiency, set `NUM_SCANNERS = 6000`. At this thread count the
scanner achieves approximately **~6,000 IPs/second**, meaning a full
`192.168.0.0 – 192.168.255.255` sweep (65,535 IPs, single port) completes
in **~10 seconds**.

| Thread count | Speed        | Full subnet scan |
|--------------|--------------|------------------|
| 200          | ~250 IPs/s   | ~4 min           |
| 1000         | ~1,200 IPs/s | ~55 sec          |
| **4000**     | **~4,000 IPs/s** | **< 20 sec** |
| **6000**     | **~6,000 IPs/s** | **~10 sec**  |

> **Note:** 4000+ threads is aggressive and works well on modern hardware.
> If you see errors or instability, your OS may be hitting its open-file or
> thread limit — try `ulimit -n 8192` on Linux/macOS, or reduce the count.

---

## Notes

- Only `192.168.x.x` subnets are supported by the current IP builder. Adjust
  `Scanner._build_target_list()` to support arbitrary CIDR ranges.

---

## License

MIT
