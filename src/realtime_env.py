import os
import platform
import re as _re
import subprocess
from typing import Any, Dict


def _run_safe(args, timeout=5, shell=False):
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=shell,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def collect_realtime_env() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "hostname": platform.node(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "os_name": "",
        "kernel": "",
        "uptime": "",
        "load_avg": "",
        "cpu_percent": None,
        "memory": {},
        "disk": [],
        "network": [],
        "process_count": 0,
    }

    if platform.system() == "Linux":
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", encoding="utf-8") as handle:
                    for line in handle:
                        if line.startswith("PRETTY_NAME="):
                            info["os_name"] = line.split("=", 1)[1].strip().strip('"')
                            break
        except Exception:
            pass

        info["kernel"] = _run_safe(["uname", "-r"])

        uptime_raw = _run_safe(["uptime", "-p"])
        info["uptime"] = uptime_raw.replace("up ", "", 1) if uptime_raw else ""

        try:
            with open("/proc/loadavg", encoding="utf-8") as handle:
                parts = handle.read().split()
                info["load_avg"] = f"{parts[0]} {parts[1]} {parts[2]}"
        except Exception:
            pass

        try:
            mem: Dict[str, int] = {}
            with open("/proc/meminfo", encoding="utf-8") as handle:
                for line in handle:
                    parts = line.split()
                    key = parts[0].rstrip(":")
                    if key in ("MemTotal", "MemAvailable"):
                        mem[key] = int(parts[1])
            if "MemTotal" in mem and "MemAvailable" in mem:
                total_kb = mem["MemTotal"]
                avail_kb = mem["MemAvailable"]
                used_kb = total_kb - avail_kb
                total_mb = total_kb // 1024
                used_mb = used_kb // 1024
                info["memory"] = {
                    "total_mb": total_mb,
                    "used_mb": used_mb,
                    "percent": round(used_mb / total_mb * 100, 1) if total_mb > 0 else 0,
                    "total_str": f"{total_mb / 1024:.1f}GB" if total_mb >= 1024 else f"{total_mb}MB",
                    "used_str": f"{used_mb / 1024:.1f}GB" if used_mb >= 1024 else f"{used_mb}MB",
                }
        except Exception:
            pass

        try:
            import time as _time

            def _read_cpu():
                with open("/proc/stat", encoding="utf-8") as handle:
                    line = handle.readline()
                values = [int(item) for item in line.split()[1:8]]
                return sum(values), values[3]

            t1_total, t1_idle = _read_cpu()
            _time.sleep(0.2)
            t2_total, t2_idle = _read_cpu()
            dt = t2_total - t1_total
            di = t2_idle - t1_idle
            info["cpu_percent"] = round((1 - di / dt) * 100, 1) if dt > 0 else 0.0
        except Exception:
            pass

        disk_output = _run_safe(["df", "-h", "--output=target,size,used,avail,pcent"])
        skip_mounts = ("/proc", "/sys", "/dev", "/run", "/snap", "tmpfs", "udev", "cgroupfs")
        for line in disk_output.split("\n")[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue
            mount = parts[0]
            if any(mount.startswith(prefix) for prefix in skip_mounts):
                continue
            try:
                pct = int(parts[4].rstrip("%"))
            except ValueError:
                pct = 0
            info["disk"].append(
                {
                    "mount": mount,
                    "size": parts[1],
                    "used": parts[2],
                    "avail": parts[3],
                    "percent": pct,
                }
            )
            if len(info["disk"]) >= 5:
                break

        ip_brief = _run_safe(["ip", "-brief", "addr"])
        if ip_brief:
            for line in ip_brief.split("\n"):
                parts = line.split()
                if len(parts) < 3:
                    continue
                iface = parts[0]
                for addr_part in parts[2:]:
                    if "/" in addr_part:
                        ip = addr_part.split("/")[0]
                        if not ip.startswith("127.") and ":" not in ip:
                            info["network"].append({"iface": iface, "ip": ip})
        else:
            ip_out = _run_safe(["ip", "addr"])
            matches = _re.findall(
                r"inet\s+(\d+\.\d+\.\d+\.\d+)/\d+[^\n]*\s+\w+\s+(\w+)$",
                ip_out,
                _re.MULTILINE,
            )
            for ip, iface in matches:
                if not ip.startswith("127."):
                    info["network"].append({"iface": iface, "ip": ip})

        proc_out = _run_safe(["bash", "-c", "ps -e --no-header | wc -l"])
        if proc_out.strip().isdigit():
            info["process_count"] = int(proc_out.strip())

    elif platform.system() == "Windows":
        info["os_name"] = f"Windows {platform.version()}"
        info["kernel"] = platform.release()

    return info
