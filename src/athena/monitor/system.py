"""System monitoring module — CPU, RAM, disk, network metrics collection."""

from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CPUMetrics:
    """CPU usage metrics."""

    overall_percent: float
    per_core_percent: list[float]
    core_count: int
    load_average: tuple[float, float, float]
    frequency_mhz: Optional[float] = None


@dataclass
class RAMMetrics:
    """RAM usage metrics."""

    total_bytes: int
    used_bytes: int
    available_bytes: int
    percent_used: float
    swap_total_bytes: int = 0
    swap_used_bytes: int = 0
    swap_percent: float = 0.0


@dataclass
class DiskMetrics:
    """Disk usage metrics per mount point."""

    mount_point: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent_used: float
    filesystem: str = ""


@dataclass
class NetworkMetrics:
    """Network I/O metrics."""

    bytes_sent: int
    bytes_received: int
    packets_sent: int
    packets_received: int
    errors_in: int = 0
    errors_out: int = 0


@dataclass
class SystemMetrics:
    """Complete system metrics snapshot."""

    timestamp: float
    cpu: CPUMetrics
    ram: RAMMetrics
    disks: list[DiskMetrics]
    network: NetworkMetrics
    process_count: int
    uptime_seconds: float
    platform_info: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "cpu": {
                "overall_percent": self.cpu.overall_percent,
                "per_core_percent": self.cpu.per_core_percent,
                "core_count": self.cpu.core_count,
                "load_average": list(self.cpu.load_average),
                "frequency_mhz": self.cpu.frequency_mhz,
            },
            "ram": {
                "total_bytes": self.ram.total_bytes,
                "used_bytes": self.ram.used_bytes,
                "available_bytes": self.ram.available_bytes,
                "percent_used": self.ram.percent_used,
                "swap_total_bytes": self.ram.swap_total_bytes,
                "swap_used_bytes": self.ram.swap_used_bytes,
                "swap_percent": self.ram.swap_percent,
                "total_human": SystemMonitor.format_bytes(self.ram.total_bytes),
                "used_human": SystemMonitor.format_bytes(self.ram.used_bytes),
                "available_human": SystemMonitor.format_bytes(self.ram.available_bytes),
            },
            "disks": [
                {
                    "mount_point": d.mount_point,
                    "total_bytes": d.total_bytes,
                    "used_bytes": d.used_bytes,
                    "free_bytes": d.free_bytes,
                    "percent_used": d.percent_used,
                    "filesystem": d.filesystem,
                    "total_human": SystemMonitor.format_bytes(d.total_bytes),
                    "used_human": SystemMonitor.format_bytes(d.used_bytes),
                    "free_human": SystemMonitor.format_bytes(d.free_bytes),
                }
                for d in self.disks
            ],
            "network": {
                "bytes_sent": self.network.bytes_sent,
                "bytes_received": self.network.bytes_received,
                "packets_sent": self.network.packets_sent,
                "packets_received": self.network.packets_received,
                "bytes_sent_human": SystemMonitor.format_bytes(self.network.bytes_sent),
                "bytes_received_human": SystemMonitor.format_bytes(self.network.bytes_received),
            },
            "process_count": self.process_count,
            "uptime_seconds": self.uptime_seconds,
            "uptime_human": SystemMonitor.format_uptime(self.uptime_seconds),
            "platform": self.platform_info,
        }


class SystemMonitor:
    """
    Collects real-time system metrics using psutil when available,
    falls back to basic platform metrics otherwise.
    """

    def __init__(self) -> None:
        self._psutil_available: bool = False
        self._psutil: Any = None
        self._start_time: float = time.time()
        self._boot_time: float = self._start_time

        try:
            import psutil  # type: ignore[import-untyped]

            self._psutil = psutil
            self._psutil_available = True
            self._boot_time = psutil.boot_time()
        except ImportError:
            pass

    def get_cpu_metrics(self) -> CPUMetrics:
        """Get CPU usage metrics."""
        if self._psutil_available:
            psutil = self._psutil
            overall = psutil.cpu_percent(interval=None)
            per_core = psutil.cpu_percent(interval=None, percpu=True)
            core_count = psutil.cpu_count(logical=True) or 1
            freq = psutil.cpu_freq()
            load_avg: tuple[float, float, float] = (0.0, 0.0, 0.0)
            if hasattr(os, "getloadavg"):
                try:
                    load_avg = tuple(os.getloadavg())  # type: ignore[assignment]
                except OSError:
                    pass

            return CPUMetrics(
                overall_percent=overall,
                per_core_percent=per_core,
                core_count=core_count,
                load_average=load_avg,
                frequency_mhz=freq.current if freq else None,
            )

        # Fallback
        core_count = os.cpu_count() or 1
        load_avg = (0.0, 0.0, 0.0)
        if hasattr(os, "getloadavg"):
            try:
                load_avg = tuple(os.getloadavg())  # type: ignore[assignment]
            except OSError:
                pass

        return CPUMetrics(
            overall_percent=0.0,
            per_core_percent=[],
            core_count=core_count,
            load_average=load_avg,
        )

    def get_ram_metrics(self) -> RAMMetrics:
        """Get RAM usage metrics."""
        if self._psutil_available:
            mem = self._psutil.virtual_memory()
            swap = self._psutil.swap_memory()

            return RAMMetrics(
                total_bytes=mem.total,
                used_bytes=mem.used,
                available_bytes=mem.available,
                percent_used=mem.percent,
                swap_total_bytes=swap.total,
                swap_used_bytes=swap.used,
                swap_percent=swap.percent,
            )

        return RAMMetrics(
            total_bytes=0,
            used_bytes=0,
            available_bytes=0,
            percent_used=0.0,
        )

    def get_disk_metrics(self) -> list[DiskMetrics]:
        """Get disk usage for all mounted partitions."""
        disks: list[DiskMetrics] = []

        if self._psutil_available:
            for part in self._psutil.disk_partitions(all=False):
                try:
                    usage = self._psutil.disk_usage(part.mountpoint)
                    disks.append(
                        DiskMetrics(
                            mount_point=part.mountpoint,
                            total_bytes=usage.total,
                            used_bytes=usage.used,
                            free_bytes=usage.free,
                            percent_used=usage.percent,
                            filesystem=part.fstype,
                        )
                    )
                except (PermissionError, OSError):
                    continue

        return disks

    def get_network_metrics(self) -> NetworkMetrics:
        """Get network I/O metrics."""
        if self._psutil_available:
            net = self._psutil.net_io_counters()
            return NetworkMetrics(
                bytes_sent=net.bytes_sent,
                bytes_received=net.bytes_recv,
                packets_sent=net.packets_sent,
                packets_received=net.packets_recv,
                errors_in=net.errin,
                errors_out=net.errout,
            )

        return NetworkMetrics(
            bytes_sent=0,
            bytes_received=0,
            packets_sent=0,
            packets_received=0,
        )

    def get_process_count(self) -> int:
        """Get number of running processes."""
        if self._psutil_available:
            return len(self._psutil.pids())
        return 0

    @property
    def uptime_seconds(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self._boot_time

    def get_system_metrics(self) -> SystemMetrics:
        """Get complete system metrics snapshot."""
        return SystemMetrics(
            timestamp=time.time(),
            cpu=self.get_cpu_metrics(),
            ram=self.get_ram_metrics(),
            disks=self.get_disk_metrics(),
            network=self.get_network_metrics(),
            process_count=self.get_process_count(),
            uptime_seconds=self.uptime_seconds,
            platform_info={
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "hostname": platform.node(),
            },
        )

    @staticmethod
    def format_bytes(value: float) -> str:
        """Format bytes to human-readable string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(value) < 1024:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} PB"

    @staticmethod
    def format_uptime(seconds: float) -> str:
        """Format uptime seconds to human-readable string."""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        parts: list[str] = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)


# Global instance
system_monitor = SystemMonitor()
