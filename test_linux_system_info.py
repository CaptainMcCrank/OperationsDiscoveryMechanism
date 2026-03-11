#!/usr/bin/env python3
"""
Unit tests for linux_system_info.py

Run with: python -m pytest test_linux_system_info.py -v
Or: python -m unittest test_linux_system_info -v
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from linux_system_info import (
    LinuxSystemInfoCollector,
    CommandRunner,
    HardwareInfo,
    DiskInfo,
    NetworkInfo,
    SystemInfo,
)


class MockCommandRunner(CommandRunner):
    """Mock command runner for testing."""

    def __init__(self):
        self.responses = {}
        self.calls = []

    def set_response(self, command_key: str, returncode: int, stdout: str, stderr: str = ""):
        """Set the response for a command."""
        self.responses[command_key] = (returncode, stdout, stderr)

    def run(self, command: list[str], timeout: int = 30) -> tuple[int, str, str]:
        """Return mocked response based on command."""
        self.calls.append(command)

        # Try exact match first, then first two elements, then first element
        key = " ".join(command)
        if key in self.responses:
            return self.responses[key]
        
        key = " ".join(command[:2]) if len(command) > 1 else command[0]
        if key in self.responses:
            return self.responses[key]
        
        key = command[0]
        if key in self.responses:
            return self.responses[key]

        return -1, "", f"Command not found: {command[0]}"


class TestHardwareCollection(unittest.TestCase):
    """Tests for hardware information collection."""

    SAMPLE_HOSTNAMECTL_OUTPUT = """   Static hostname: ai
         Icon name: computer-desktop
           Chassis: desktop
        Machine ID: abc123
           Boot ID: def456
  Operating System: Pop!_OS 22.04 LTS
            Kernel: Linux 6.5.0-generic
      Architecture: x86-64
   Hardware Vendor: System76
    Hardware Model: Thelio
  Firmware Version: 1.0.0
"""

    SAMPLE_LSCPU_OUTPUT = """Architecture:            x86_64
  CPU op-mode(s):        32-bit, 64-bit
  Address sizes:         48 bits physical, 48 bits virtual
  Byte Order:            Little Endian
CPU(s):                  32
  On-line CPU(s) list:   0-31
Vendor ID:               AuthenticAMD
  Model name:            AMD RYZEN AI MAX+ 395 w/ Radeon 8060S
    CPU family:          26
    Model:               4
    Thread(s) per core:  2
    Core(s) per socket:  16
    Socket(s):           1
"""

    SAMPLE_FREE_OUTPUT = """              total        used        free      shared  buff/cache   available
Mem:           30Gi       5.2Gi        20Gi       512Mi       5.0Gi        24Gi
Swap:          16Gi          0B        16Gi
"""

    SAMPLE_OS_RELEASE = """NAME="Pop!_OS"
VERSION="22.04 LTS"
ID=pop
VERSION_ID="22.04"
"""

    def test_parse_hardware_info(self):
        """Test parsing of hardware info from various commands."""
        runner = MockCommandRunner()
        runner.set_response("hostnamectl", 0, self.SAMPLE_HOSTNAMECTL_OUTPUT)
        runner.set_response("lscpu", 0, self.SAMPLE_LSCPU_OUTPUT)
        runner.set_response("free -h", 0, self.SAMPLE_FREE_OUTPUT)
        runner.set_response("cat /etc/os-release", 0, self.SAMPLE_OS_RELEASE)

        collector = LinuxSystemInfoCollector(runner)
        hw = collector.collect_hardware()

        self.assertEqual(hw.hostname, "ai")
        self.assertEqual(hw.os_name, "Pop!_OS 22.04 LTS")
        self.assertEqual(hw.kernel, "Linux 6.5.0-generic")
        self.assertEqual(hw.architecture, "x86-64")
        self.assertEqual(hw.cpu_model, "AMD RYZEN AI MAX+ 395 w/ Radeon 8060S")
        self.assertEqual(hw.cpu_threads, "32")
        self.assertEqual(hw.memory_total, "30Gi")

    def test_hardware_command_failure(self):
        """Test handling of command failures."""
        runner = MockCommandRunner()
        runner.set_response("hostnamectl", 1, "", "Permission denied")
        runner.set_response("lscpu", 1, "", "Error")
        runner.set_response("free -h", 1, "", "Error")
        runner.set_response("cat /etc/os-release", 1, "", "Error")

        collector = LinuxSystemInfoCollector(runner)
        hw = collector.collect_hardware()

        self.assertEqual(hw.hostname, "")
        self.assertGreater(len(collector.errors), 0)


class TestDiskCollection(unittest.TestCase):
    """Tests for disk information collection."""

    SAMPLE_LSBLK_OUTPUT = """sda       500G disk
├─sda1    100M part  /boot/efi vfat
├─sda2    450G part  /         ext4
└─sda3     50G part  /home     ext4
nvme0n1     2T disk
└─nvme0n1p1   2T part  /data     ext4
"""

    SAMPLE_DF_OUTPUT = """Filesystem     Size  Used Avail Use% Mounted on
/dev/sda2      450G  120G  310G  28% /
/dev/sda1      100M   20M   80M  20% /boot/efi
/dev/sda3       50G   10G   38G  21% /home
/dev/nvme0n1p1   2T  500G  1.5T  25% /data
"""

    def test_parse_lsblk(self):
        """Test parsing of lsblk output."""
        runner = MockCommandRunner()
        runner.set_response("lsblk", 0, self.SAMPLE_LSBLK_OUTPUT)
        runner.set_response("df -h", 0, self.SAMPLE_DF_OUTPUT)

        collector = LinuxSystemInfoCollector(runner)
        disk = collector.collect_disk()

        self.assertGreater(len(disk.partitions), 0)
        
        # Find root partition
        root = next((p for p in disk.partitions if p.get("mountpoint") == "/"), None)
        self.assertIsNotNone(root)

    def test_parse_df_output(self):
        """Test parsing of df -h output."""
        runner = MockCommandRunner()
        runner.set_response("lsblk", 0, self.SAMPLE_LSBLK_OUTPUT)
        runner.set_response("df -h", 0, self.SAMPLE_DF_OUTPUT)

        collector = LinuxSystemInfoCollector(runner)
        disk = collector.collect_disk()

        self.assertEqual(len(disk.usage), 4)

        root = next((u for u in disk.usage if u["mount_point"] == "/"), None)
        self.assertIsNotNone(root)
        self.assertEqual(root["size"], "450G")
        self.assertEqual(root["use_percent"], "28%")


class TestNetworkCollection(unittest.TestCase):
    """Tests for network information collection."""

    SAMPLE_IP_ADDR_OUTPUT = """1: lo    inet 127.0.0.1/8 scope host lo\       valid_lft forever preferred_lft forever
1: lo    inet6 ::1/128 scope host \       valid_lft forever preferred_lft forever
2: enp0s3    inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic enp0s3\       valid_lft 86400sec preferred_lft 86400sec
2: enp0s3    inet6 fe80::1234:5678:abcd:ef00/64 scope link \       valid_lft forever preferred_lft forever
"""

    SAMPLE_RESOLV_CONF = """# Generated by NetworkManager
nameserver 8.8.8.8
nameserver 8.8.4.4
search home.local
"""

    SAMPLE_IP_ROUTE_DEFAULT = """default via 192.168.1.1 dev enp0s3 proto dhcp metric 100
"""

    def test_parse_ip_addr(self):
        """Test parsing of ip addr output."""
        runner = MockCommandRunner()
        runner.set_response("hostname", 0, "testhost\n")
        runner.set_response("ip -o", 0, self.SAMPLE_IP_ADDR_OUTPUT)
        runner.set_response("ip route", 0, self.SAMPLE_IP_ROUTE_DEFAULT)
        runner.set_response("cat /etc/resolv.conf", 0, self.SAMPLE_RESOLV_CONF)

        collector = LinuxSystemInfoCollector(runner)
        net = collector.collect_network()

        self.assertEqual(net.hostname, "testhost")
        self.assertGreater(len(net.interfaces), 0)

        # Check loopback
        lo = next((i for i in net.interfaces if i["name"] == "lo"), None)
        self.assertIsNotNone(lo)
        self.assertEqual(lo["ipv4_address"], "127.0.0.1")

        # Check enp0s3
        eth = next((i for i in net.interfaces if i["name"] == "enp0s3"), None)
        self.assertIsNotNone(eth)
        self.assertEqual(eth["ipv4_address"], "192.168.1.100")

    def test_parse_resolv_conf(self):
        """Test parsing of /etc/resolv.conf."""
        runner = MockCommandRunner()
        runner.set_response("hostname", 0, "testhost\n")
        runner.set_response("ip -o", 0, self.SAMPLE_IP_ADDR_OUTPUT)
        runner.set_response("ip route", 0, self.SAMPLE_IP_ROUTE_DEFAULT)
        runner.set_response("cat /etc/resolv.conf", 0, self.SAMPLE_RESOLV_CONF)

        collector = LinuxSystemInfoCollector(runner)
        net = collector.collect_network()

        self.assertIn("8.8.8.8", net.dns["nameservers"])
        self.assertIn("8.8.4.4", net.dns["nameservers"])
        self.assertEqual(net.default_gateway, "192.168.1.1")


class TestSystemdServices(unittest.TestCase):
    """Tests for systemd services collection."""

    SAMPLE_SYSTEMCTL_OUTPUT = """ssh.service loaded active running OpenBSD Secure Shell server
docker.service loaded active running Docker Application Container Engine
NetworkManager.service loaded active running Network Manager
"""

    def test_parse_systemctl_list(self):
        """Test parsing of systemctl list-units output."""
        runner = MockCommandRunner()
        runner.set_response("systemctl list-units", 0, self.SAMPLE_SYSTEMCTL_OUTPUT)

        collector = LinuxSystemInfoCollector(runner)
        services = collector.collect_systemd_services()

        self.assertEqual(len(services), 3)

        ssh = next((s for s in services if "ssh" in s["unit"]), None)
        self.assertIsNotNone(ssh)
        self.assertEqual(ssh["active"], "active")

        docker = next((s for s in services if "docker" in s["unit"]), None)
        self.assertIsNotNone(docker)


class TestDockerContainers(unittest.TestCase):
    """Tests for Docker container collection."""

    SAMPLE_DOCKER_OUTPUT = """nginx	Up 2 hours	0.0.0.0:80->80/tcp
postgres	Up 2 hours	5432/tcp
redis	Up 2 hours	6379/tcp
"""

    def test_parse_docker_ps(self):
        """Test parsing of docker ps output."""
        runner = MockCommandRunner()
        runner.set_response("docker ps", 0, self.SAMPLE_DOCKER_OUTPUT)

        collector = LinuxSystemInfoCollector(runner)
        containers = collector.collect_docker_containers()

        self.assertEqual(len(containers), 3)

        nginx = next((c for c in containers if c["name"] == "nginx"), None)
        self.assertIsNotNone(nginx)
        self.assertIn("Up", nginx["status"])

    def test_docker_not_running(self):
        """Test handling when Docker is not running."""
        runner = MockCommandRunner()
        runner.set_response("docker ps", 1, "", "Cannot connect to the Docker daemon")

        collector = LinuxSystemInfoCollector(runner)
        containers = collector.collect_docker_containers()

        self.assertEqual(containers, [])
        self.assertEqual(len(collector.errors), 0)

    def test_docker_permission_denied(self):
        """Test handling when Docker permission denied."""
        runner = MockCommandRunner()
        runner.set_response("docker ps", 1, "", "permission denied")

        collector = LinuxSystemInfoCollector(runner)
        containers = collector.collect_docker_containers()

        self.assertEqual(containers, [])
        self.assertEqual(len(collector.errors), 0)


class TestListeningPorts(unittest.TestCase):
    """Tests for listening ports collection."""

    # Real ss -tlnp output format (note: Process column may be empty or have users:)
    SAMPLE_SS_OUTPUT = """State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*     users:(("sshd",pid=1234,fd=3))
LISTEN 0      128          0.0.0.0:80         0.0.0.0:*     users:(("nginx",pid=5678,fd=6))
LISTEN 0      128        127.0.0.1:5432       0.0.0.0:*     users:(("postgres",pid=9012,fd=5))
"""

    def test_parse_ss_output(self):
        """Test parsing of ss listening ports."""
        runner = MockCommandRunner()
        runner.set_response("ss -tlnp", 0, self.SAMPLE_SS_OUTPUT)

        collector = LinuxSystemInfoCollector(runner)
        ports = collector.collect_listening_ports()

        self.assertEqual(len(ports), 3)

        # Find SSH by address
        ssh = next((p for p in ports if "22" in p["local_address"]), None)
        self.assertIsNotNone(ssh)
        self.assertEqual(ssh["process"], "sshd")
        self.assertEqual(ssh["pid"], "1234")

        # Find nginx by address
        nginx = next((p for p in ports if "80" in p["local_address"]), None)
        self.assertIsNotNone(nginx)
        self.assertEqual(nginx["process"], "nginx")

    def test_no_listening_ports(self):
        """Test handling when no ports are listening."""
        runner = MockCommandRunner()
        runner.set_response("ss -tlnp", 0, "State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process\n")

        collector = LinuxSystemInfoCollector(runner)
        ports = collector.collect_listening_ports()

        self.assertEqual(ports, [])

    def test_ports_without_process_info(self):
        """Test handling ports without process info (no root access)."""
        sample = """State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*
LISTEN 0      128          0.0.0.0:80         0.0.0.0:*
"""
        runner = MockCommandRunner()
        runner.set_response("ss -tlnp", 0, sample)

        collector = LinuxSystemInfoCollector(runner)
        ports = collector.collect_listening_ports()

        # Should still capture the ports even without process info
        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0]["process"], "")


class TestCronJobs(unittest.TestCase):
    """Tests for cron job collection."""

    SAMPLE_CRONTAB = """# Backup every day at 2am
0 2 * * * /usr/local/bin/backup.sh

# Cleanup temp files weekly
0 3 * * 0 find /tmp -mtime +7 -delete
"""

    def test_parse_crontab(self):
        """Test parsing of crontab output."""
        runner = MockCommandRunner()
        runner.set_response("crontab -l", 0, self.SAMPLE_CRONTAB)

        collector = LinuxSystemInfoCollector(runner)
        jobs = collector.collect_cron_jobs()

        self.assertEqual(len(jobs), 2)
        self.assertIn("backup.sh", jobs[0])

    def test_no_crontab(self):
        """Test handling when no crontab exists."""
        runner = MockCommandRunner()
        runner.set_response("crontab -l", 1, "", "no crontab for user")

        collector = LinuxSystemInfoCollector(runner)
        jobs = collector.collect_cron_jobs()

        self.assertEqual(jobs, [])
        self.assertEqual(len(collector.errors), 0)


class TestFullCollection(unittest.TestCase):
    """Tests for full system info collection."""

    def test_collect_all_returns_system_info(self):
        """Test that collect_all returns a complete SystemInfo object."""
        runner = MockCommandRunner()

        runner.set_response("hostnamectl", 0, "Static hostname: test")
        runner.set_response("lscpu", 0, "Model name: Test CPU")
        runner.set_response("free -h", 0, "Mem: 16Gi")
        runner.set_response("cat /etc/os-release", 0, "VERSION=\"22.04\"")
        runner.set_response("lsblk", 0, "")
        runner.set_response("df -h", 0, "")
        runner.set_response("hostname", 0, "test-host")
        runner.set_response("ip -o", 0, "")
        runner.set_response("ip route", 0, "")
        runner.set_response("cat /etc/resolv.conf", 0, "")
        runner.set_response("systemctl list-units", 0, "")
        runner.set_response("docker ps", -1, "", "not installed")
        runner.set_response("ss -tlnp", 0, "")
        runner.set_response("crontab -l", 1, "", "no crontab")

        collector = LinuxSystemInfoCollector(runner)
        info = collector.collect_all()

        self.assertIsInstance(info, SystemInfo)
        self.assertIsNotNone(info.collection_timestamp)
        self.assertIsInstance(info.hardware, HardwareInfo)
        self.assertIsInstance(info.disk, DiskInfo)
        self.assertIsInstance(info.network, NetworkInfo)

    def test_to_json_output(self):
        """Test JSON serialization of system info."""
        runner = MockCommandRunner()

        runner.set_response("hostnamectl", 0, "Static hostname: test")
        runner.set_response("lscpu", 0, "")
        runner.set_response("free -h", 0, "")
        runner.set_response("cat /etc/os-release", 0, "")
        runner.set_response("lsblk", 0, "")
        runner.set_response("df -h", 0, "")
        runner.set_response("hostname", 0, "test")
        runner.set_response("ip -o", 0, "")
        runner.set_response("ip route", 0, "")
        runner.set_response("cat /etc/resolv.conf", 0, "")
        runner.set_response("systemctl list-units", 0, "")
        runner.set_response("docker ps", -1, "", "")
        runner.set_response("ss -tlnp", 0, "")
        runner.set_response("crontab -l", 1, "", "no crontab")

        collector = LinuxSystemInfoCollector(runner)
        info = collector.collect_all()
        json_str = collector.to_json(info)

        parsed = json.loads(json_str)

        self.assertIn("hardware", parsed)
        self.assertIn("disk", parsed)
        self.assertIn("network", parsed)
        self.assertIn("collection_timestamp", parsed)


class TestIdempotency(unittest.TestCase):
    """Tests to verify idempotent behavior."""

    def test_multiple_collections_same_result(self):
        """Test that running collection multiple times gives same structure."""
        runner = MockCommandRunner()

        runner.set_response("hostnamectl", 0, "Static hostname: test")
        runner.set_response("lscpu", 0, "Model name: CPU")
        runner.set_response("free -h", 0, "Mem: 16Gi")
        runner.set_response("cat /etc/os-release", 0, "VERSION=\"22.04\"")
        runner.set_response("lsblk", 0, "sda 100G disk")
        runner.set_response("df -h", 0, "Filesystem Size\n/dev/sda 100G")
        runner.set_response("hostname", 0, "testhost")
        runner.set_response("ip -o", 0, "1: lo inet 127.0.0.1/8")
        runner.set_response("ip route", 0, "default via 192.168.1.1")
        runner.set_response("cat /etc/resolv.conf", 0, "nameserver 8.8.8.8")
        runner.set_response("systemctl list-units", 0, "ssh.service loaded active running SSH")
        runner.set_response("docker ps", 0, "nginx\tUp\t80/tcp")
        runner.set_response("ss -tlnp", 0, "State Local\nLISTEN 0.0.0.0:22 users:((\"sshd\",pid=123,fd=3))")
        runner.set_response("crontab -l", 0, "0 * * * * echo test")

        collector = LinuxSystemInfoCollector(runner)

        info1 = collector.collect_all()
        info2 = collector.collect_all()
        info3 = collector.collect_all()

        d1 = collector.to_dict(info1)
        d2 = collector.to_dict(info2)
        d3 = collector.to_dict(info3)

        del d1["collection_timestamp"]
        del d2["collection_timestamp"]
        del d3["collection_timestamp"]

        d1["errors"] = []
        d2["errors"] = []
        d3["errors"] = []

        self.assertEqual(d1, d2)
        self.assertEqual(d2, d3)

    def test_no_side_effects(self):
        """Test that collection doesn't modify system state."""
        runner = MockCommandRunner()

        runner.set_response("hostnamectl", 0, "")
        runner.set_response("lscpu", 0, "")
        runner.set_response("free -h", 0, "")
        runner.set_response("cat /etc/os-release", 0, "")
        runner.set_response("lsblk", 0, "")
        runner.set_response("df -h", 0, "")
        runner.set_response("hostname", 0, "")
        runner.set_response("ip -o", 0, "")
        runner.set_response("ip route", 0, "")
        runner.set_response("cat /etc/resolv.conf", 0, "")
        runner.set_response("systemctl list-units", 0, "")
        runner.set_response("docker ps", 0, "")
        runner.set_response("ss -tlnp", 0, "")
        runner.set_response("crontab -l", 0, "")

        collector = LinuxSystemInfoCollector(runner)
        collector.collect_all()

        readonly_commands = {
            "hostnamectl", "lscpu", "free", "cat", "lsblk", "df",
            "hostname", "ip", "systemctl", "docker", "ss", "crontab"
        }

        for call in runner.calls:
            cmd = call[0]
            self.assertIn(cmd, readonly_commands, f"Unexpected command: {cmd}")


class TestCommandRunner(unittest.TestCase):
    """Tests for the CommandRunner class."""

    def test_real_command_execution(self):
        """Test that CommandRunner can execute real commands."""
        runner = CommandRunner()
        returncode, stdout, stderr = runner.run(["echo", "test"])

        self.assertEqual(returncode, 0)
        self.assertEqual(stdout.strip(), "test")

    def test_command_not_found(self):
        """Test handling of non-existent commands."""
        runner = CommandRunner()
        returncode, stdout, stderr = runner.run(["nonexistent_command_xyz"])

        self.assertEqual(returncode, -1)
        self.assertIn("not found", stderr.lower())

    def test_command_timeout(self):
        """Test command timeout handling."""
        runner = CommandRunner()
        returncode, stdout, stderr = runner.run(["sleep", "10"], timeout=1)

        self.assertEqual(returncode, -1)
        self.assertIn("timed out", stderr.lower())


if __name__ == "__main__":
    unittest.main()
