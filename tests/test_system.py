"""Tests for system monitoring module."""

from __future__ import annotations

import pytest
from athena.monitor.system import SystemMonitor, CPUMetrics, RAMMetrics, DiskMetrics, NetworkMetrics


class TestSystemMonitor:
    """Tests for SystemMonitor class."""

    def test_init(self):
        monitor = SystemMonitor()
        assert monitor is not None

    def test_get_cpu_metrics(self):
        monitor = SystemMonitor()
        cpu = monitor.get_cpu_metrics()
        assert isinstance(cpu, CPUMetrics)
        assert cpu.core_count >= 1
        assert 0 <= cpu.overall_percent <= 100 or cpu.overall_percent == 0.0

    def test_get_ram_metrics(self):
        monitor = SystemMonitor()
        ram = monitor.get_ram_metrics()
        assert isinstance(ram, RAMMetrics)
        assert ram.total_bytes >= 0
        assert ram.used_bytes >= 0
        assert ram.available_bytes >= 0

    def test_get_disk_metrics(self):
        monitor = SystemMonitor()
        disks = monitor.get_disk_metrics()
        assert isinstance(disks, list)
        for disk in disks:
            assert isinstance(disk, DiskMetrics)
            assert disk.total_bytes >= 0
            assert disk.used_bytes >= 0
            assert disk.free_bytes >= 0

    def test_get_network_metrics(self):
        monitor = monitor = SystemMonitor()
        net = monitor.get_network_metrics()
        assert isinstance(net, NetworkMetrics)
        assert net.bytes_sent >= 0
        assert net.bytes_received >= 0

    def test_get_process_count(self):
        monitor = SystemMonitor()
        count = monitor.get_process_count()
        assert count >= 0

    def test_uptime_seconds(self):
        monitor = SystemMonitor()
        uptime = monitor.uptime_seconds
        assert uptime >= 0

    def test_get_system_metrics(self):
        monitor = SystemMonitor()
        metrics = monitor.get_system_metrics()
        assert metrics.cpu is not None
        assert metrics.ram is not None
        assert metrics.network is not None
        assert metrics.process_count >= 0
        assert metrics.uptime_seconds >= 0
        assert "system" in metrics.platform_info

    def test_to_dict(self):
        monitor = SystemMonitor()
        metrics = monitor.get_system_metrics()
        d = metrics.to_dict()
        assert "cpu" in d
        assert "ram" in d
        assert "disks" in d
        assert "network" in d
        assert "process_count" in d
        assert "uptime_seconds" in d
        assert "platform" in d

    def test_format_bytes(self):
        assert SystemMonitor.format_bytes(0) == "0.0 B"
        assert "KB" in SystemMonitor.format_bytes(1024)
        assert "MB" in SystemMonitor.format_bytes(1024 * 1024)
        assert "GB" in SystemMonitor.format_bytes(1024 * 1024 * 1024)

    def test_format_uptime(self):
        assert "s" in SystemMonitor.format_uptime(30)
        assert "m" in SystemMonitor.format_uptime(120)
        assert "h" in SystemMonitor.format_uptime(7200)
        assert "d" in SystemMonitor.format_uptime(172800)


class TestCPUMetrics:
    def test_creation(self):
        cpu = CPUMetrics(
            overall_percent=50.0,
            per_core_percent=[40.0, 60.0],
            core_count=2,
            load_average=(1.0, 0.5, 0.25),
        )
        assert cpu.overall_percent == 50.0
        assert cpu.core_count == 2


class TestRAMMetrics:
    def test_creation(self):
        ram = RAMMetrics(
            total_bytes=16000000000,
            used_bytes=8000000000,
            available_bytes=8000000000,
            percent_used=50.0,
        )
        assert ram.percent_used == 50.0


class TestDiskMetrics:
    def test_creation(self):
        disk = DiskMetrics(
            mount_point="/",
            total_bytes=500000000000,
            used_bytes=250000000000,
            free_bytes=250000000000,
            percent_used=50.0,
        )
        assert disk.mount_point == "/"
        assert disk.percent_used == 50.0


class TestNetworkMetrics:
    def test_creation(self):
        net = NetworkMetrics(
            bytes_sent=1000,
            bytes_received=2000,
            packets_sent=10,
            packets_received=20,
        )
        assert net.bytes_sent == 1000
        assert net.bytes_received == 2000
