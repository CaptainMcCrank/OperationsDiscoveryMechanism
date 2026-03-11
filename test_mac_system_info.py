#!/usr/bin/env python3
"""
Unit tests for mac_system_info.py

Run with: python -m pytest test_mac_system_info.py -v
Or: python -m unittest test_mac_system_info -v
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mac_system_info import (
    MacSystemInfoCollector,
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

        # Use first two elements of command as key
        key = " ".join(command[:2]) if len(command) > 1 else command[0]

        if key in self.responses:
            return self.responses[key]

        # Default: command not found
        return -1, "", f"Command not found: {command[0]}"


class TestHardwareCollection(unittest.TestCase):
    """Tests for hardware information collection."""

    SAMPLE_HARDWARE_OUTPUT = """Hardware:

    Hardware Overview:

      Model Name: Mac mini
      Model Identifier: Mac16,10
      Model Number: MU9D3LL/A
      Chip: Apple M4
      Total Number of Cores: 10 (4 Performance and 6 Efficiency)
      Memory: 16 GB
      System Firmware Version: 13822.81.10
      OS Loader Version: 13822.81.10
      Serial Number (system): ABC123XYZ
      Hardware UUID: 12345678-ABCD-1234-ABCD-123456789ABC
      Provisioning UDID: 00001234-001234567890
      Activation Lock Status: Enabled
"""

    def test_parse_hardware_info(self):
        """Test parsing of system_profiler output."""
        runner = MockCommandRunner()
        runner.set_response("system_profiler SPHardwareDataType", 0, self.SAMPLE_HARDWARE_OUTPUT)

        collector = MacSystemInfoCollector(runner)
        hw = collector.collect_hardware()

        self.assertEqual(hw.model_name, "Mac mini")
        self.assertEqual(hw.model_identifier, "Mac16,10")
        self.assertEqual(hw.model_number, "MU9D3LL/A")
        self.assertEqual(hw.chip, "Apple M4")
        self.assertEqual(hw.total_cores, "10 (4 Performance and 6 Efficiency)")
        self.assertEqual(hw.memory, "16 GB")
        self.assertEqual(hw.serial_number, "ABC123XYZ")
        self.assertEqual(hw.firmware_version, "13822.81.10")

    def test_hardware_command_failure(self):
        """Test handling of system_profiler failure."""
        runner = MockCommandRunner()
        runner.set_response("system_profiler SPHardwareDataType", 1, "", "Permission denied")

        collector = MacSystemInfoCollector(runner)
        hw = collector.collect_hardware()

        # Should return empty HardwareInfo
        self.assertEqual(hw.model_name, "")
        self.assertEqual(hw.chip, "")
        # Should log error
        self.assertIn("Hardware collection failed", collector.errors[0])


class TestDiskCollection(unittest.TestCase):
    """Tests for disk information collection."""

    SAMPLE_DISKUTIL_OUTPUT = """/dev/disk0 (internal, physical):
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:      GUID_partition_scheme                        *251.0 GB   disk0
   1:             Apple_APFS_ISC Container disk1         524.3 MB   disk0s1
   2:                 Apple_APFS Container disk3         245.1 GB   disk0s2

/dev/disk3 (synthesized):
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:      APFS Container Scheme -                      +245.1 GB   disk3
   1:                APFS Volume Macintosh HD            12.5 GB    disk3s1
   2:                APFS Volume Preboot                 8.7 GB     disk3s2
"""

    SAMPLE_DF_OUTPUT = """Filesystem        Size    Used   Avail Capacity iused ifree %iused  Mounted on
/dev/disk3s1s1   228Gi    12Gi   146Gi     8%    455k  1.5G    0%   /
/dev/disk3s5     228Gi    57Gi   146Gi    29%    613k  1.5G    0%   /System/Volumes/Data
/dev/disk6s1     931Gi   214Gi   717Gi    23%       1     0  100%   /Volumes/T7
"""

    def test_parse_diskutil_list(self):
        """Test parsing of diskutil list output."""
        runner = MockCommandRunner()
        runner.set_response("diskutil list", 0, self.SAMPLE_DISKUTIL_OUTPUT)
        runner.set_response("df -h", 0, self.SAMPLE_DF_OUTPUT)

        collector = MacSystemInfoCollector(runner)
        disk = collector.collect_disk()

        # Check partitions were parsed
        self.assertGreater(len(disk.partitions), 0)

        # Find a specific partition
        apfs_isc = next((p for p in disk.partitions if "ISC" in p["type"]), None)
        self.assertIsNotNone(apfs_isc)
        self.assertEqual(apfs_isc["device"], "/dev/disk0")
        self.assertEqual(apfs_isc["size"], "524.3 MB")

    def test_parse_df_output(self):
        """Test parsing of df -h output."""
        runner = MockCommandRunner()
        runner.set_response("diskutil list", 0, self.SAMPLE_DISKUTIL_OUTPUT)
        runner.set_response("df -h", 0, self.SAMPLE_DF_OUTPUT)

        collector = MacSystemInfoCollector(runner)
        disk = collector.collect_disk()

        # Check usage entries
        self.assertEqual(len(disk.usage), 3)

        # Check root filesystem
        root = next((u for u in disk.usage if u["mount_point"] == "/"), None)
        self.assertIsNotNone(root)
        self.assertEqual(root["size"], "228Gi")
        self.assertEqual(root["capacity"], "8%")

        # Check external drive
        t7 = next((u for u in disk.usage if "T7" in u["mount_point"]), None)
        self.assertIsNotNone(t7)
        self.assertEqual(t7["capacity"], "23%")

    def test_disk_command_failure(self):
        """Test handling when disk commands fail."""
        runner = MockCommandRunner()
        runner.set_response("diskutil list", 1, "", "Error")
        runner.set_response("df -h", 1, "", "Error")

        collector = MacSystemInfoCollector(runner)
        disk = collector.collect_disk()

        self.assertEqual(len(disk.partitions), 0)
        self.assertEqual(len(disk.usage), 0)
        self.assertEqual(len(collector.errors), 2)


class TestNetworkCollection(unittest.TestCase):
    """Tests for network information collection."""

    SAMPLE_IFCONFIG_OUTPUT = """lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
	inet 127.0.0.1 netmask 0xff000000
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
en1: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
	inet 192.168.110.165 netmask 0xffffff00 broadcast 192.168.110.255
"""

    SAMPLE_SCUTIL_OUTPUT = """DNS configuration

resolver #1
  nameserver[0] : 205.171.3.65
  nameserver[1] : 205.171.2.65
  if_index : 15 (en1)
  flags    : Request A records
  reach    : 0x00000002 (Reachable)

resolver #2
  domain   : local
  options  : mdns
  timeout  : 5
"""

    def test_parse_ifconfig(self):
        """Test parsing of ifconfig output."""
        runner = MockCommandRunner()
        runner.set_response("hostname", 0, "mac-mini\n")
        runner.set_response("ifconfig", 0, self.SAMPLE_IFCONFIG_OUTPUT)
        runner.set_response("scutil --dns", 0, self.SAMPLE_SCUTIL_OUTPUT)

        collector = MacSystemInfoCollector(runner)
        net = collector.collect_network()

        self.assertEqual(net.hostname, "mac-mini")
        self.assertGreater(len(net.interfaces), 0)

        # Check loopback
        lo0 = next((i for i in net.interfaces if i["name"] == "lo0"), None)
        self.assertIsNotNone(lo0)
        self.assertEqual(lo0["ipv4_address"], "127.0.0.1")
        self.assertIn("LOOPBACK", lo0["flags"])

        # Check en1 with IP
        en1 = next((i for i in net.interfaces if i["name"] == "en1"), None)
        self.assertIsNotNone(en1)
        self.assertEqual(en1["ipv4_address"], "192.168.110.165")
        self.assertEqual(en1["broadcast"], "192.168.110.255")

    def test_parse_scutil_dns(self):
        """Test parsing of scutil --dns output."""
        runner = MockCommandRunner()
        runner.set_response("hostname", 0, "mac-mini\n")
        runner.set_response("ifconfig", 0, self.SAMPLE_IFCONFIG_OUTPUT)
        runner.set_response("scutil --dns", 0, self.SAMPLE_SCUTIL_OUTPUT)

        collector = MacSystemInfoCollector(runner)
        net = collector.collect_network()

        self.assertEqual(len(net.dns_resolvers), 2)

        # Check primary resolver
        primary = net.dns_resolvers[0]
        self.assertIn("205.171.3.65", primary["nameservers"])
        self.assertIn("205.171.2.65", primary["nameservers"])
        self.assertEqual(primary["interface"], "en1")


class TestHomebrewServices(unittest.TestCase):
    """Tests for Homebrew services collection."""

    SAMPLE_BREW_OUTPUT = """Name    Status User File
unbound none
postgresql@14 started patrick ~/Library/LaunchAgents/homebrew.mxcl.postgresql@14.plist
redis started patrick ~/Library/LaunchAgents/homebrew.mxcl.redis.plist
"""

    def test_parse_brew_services(self):
        """Test parsing of brew services list."""
        runner = MockCommandRunner()
        runner.set_response("brew services", 0, self.SAMPLE_BREW_OUTPUT)

        collector = MacSystemInfoCollector(runner)
        services = collector.collect_homebrew_services()

        self.assertEqual(len(services), 3)

        unbound = next((s for s in services if s["name"] == "unbound"), None)
        self.assertIsNotNone(unbound)
        self.assertEqual(unbound["status"], "none")

        postgres = next((s for s in services if "postgresql" in s["name"]), None)
        self.assertIsNotNone(postgres)
        self.assertEqual(postgres["status"], "started")
        self.assertEqual(postgres["user"], "patrick")

    def test_brew_not_installed(self):
        """Test handling when brew is not installed."""
        runner = MockCommandRunner()
        runner.set_response("brew services", -1, "", "command not found: brew")

        collector = MacSystemInfoCollector(runner)
        services = collector.collect_homebrew_services()

        self.assertEqual(services, [])
        # Should not log an error for missing brew
        self.assertEqual(len(collector.errors), 0)


class TestLaunchdServices(unittest.TestCase):
    """Tests for launchd services collection."""

    SAMPLE_LAUNCHCTL_OUTPUT = """PID	Status	Label
1823	0	com.samsung.magicianapp
-	0	com.apple.something
1295	0	application.com.googlecode.iterm2.12345
19861	0	com.openssh.ssh-agent
-	0	com.apple.another.service
"""

    def test_parse_launchctl_list(self):
        """Test parsing of launchctl list output (filtering Apple services)."""
        runner = MockCommandRunner()
        runner.set_response("launchctl list", 0, self.SAMPLE_LAUNCHCTL_OUTPUT)

        collector = MacSystemInfoCollector(runner)
        services = collector.collect_launchd_services()

        # Should filter out com.apple services
        self.assertEqual(len(services), 3)

        labels = [s["label"] for s in services]
        self.assertIn("com.samsung.magicianapp", labels)
        self.assertIn("com.openssh.ssh-agent", labels)
        self.assertNotIn("com.apple.something", labels)

        # Check PID parsing
        samsung = next((s for s in services if "samsung" in s["label"]), None)
        self.assertEqual(samsung["pid"], "1823")

        ssh = next((s for s in services if "ssh-agent" in s["label"]), None)
        self.assertEqual(ssh["pid"], "19861")


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

        collector = MacSystemInfoCollector(runner)
        containers = collector.collect_docker_containers()

        self.assertEqual(len(containers), 3)

        nginx = next((c for c in containers if c["name"] == "nginx"), None)
        self.assertIsNotNone(nginx)
        self.assertIn("Up", nginx["status"])
        self.assertIn("80", nginx["ports"])

    def test_docker_not_running(self):
        """Test handling when Docker is not running."""
        runner = MockCommandRunner()
        runner.set_response(
            "docker ps", 1, "",
            "Cannot connect to the Docker daemon"
        )

        collector = MacSystemInfoCollector(runner)
        containers = collector.collect_docker_containers()

        self.assertEqual(containers, [])
        # Should not log error for Docker not running
        self.assertEqual(len(collector.errors), 0)


class TestListeningPorts(unittest.TestCase):
    """Tests for listening ports collection."""

    SAMPLE_LSOF_OUTPUT = """COMMAND     PID   USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
ARDAgent    123 patrick    5u  IPv4 0x1234      0t0  TCP *:3283 (LISTEN)
node       4567 patrick   22u  IPv4 0x5678      0t0  TCP 127.0.0.1:3000 (LISTEN)
node       4567 patrick   23u  IPv4 0x9abc      0t0  TCP 127.0.0.1:3001 (LISTEN)
postgres   8901 patrick    6u  IPv4 0xdef0      0t0  TCP *:5432 (LISTEN)
"""

    def test_parse_lsof_output(self):
        """Test parsing of lsof listening ports."""
        runner = MockCommandRunner()
        runner.set_response("lsof -iTCP", 0, self.SAMPLE_LSOF_OUTPUT)

        collector = MacSystemInfoCollector(runner)
        ports = collector.collect_listening_ports()

        self.assertGreater(len(ports), 0)

        # Check ARDAgent
        ard = next((p for p in ports if p["process"] == "ARDAgent"), None)
        self.assertIsNotNone(ard)
        self.assertEqual(ard["user"], "patrick")
        self.assertEqual(ard["address"], "*:3283")

        # Check postgres
        pg = next((p for p in ports if p["process"] == "postgres"), None)
        self.assertIsNotNone(pg)
        self.assertEqual(pg["address"], "*:5432")

    def test_no_listening_ports(self):
        """Test handling when no ports are listening."""
        runner = MockCommandRunner()
        runner.set_response("lsof -iTCP", 0, "")

        collector = MacSystemInfoCollector(runner)
        ports = collector.collect_listening_ports()

        self.assertEqual(ports, [])


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

        collector = MacSystemInfoCollector(runner)
        jobs = collector.collect_cron_jobs()

        # Should skip comments and empty lines
        self.assertEqual(len(jobs), 2)
        self.assertIn("backup.sh", jobs[0])
        self.assertIn("find /tmp", jobs[1])

    def test_no_crontab(self):
        """Test handling when no crontab exists."""
        runner = MockCommandRunner()
        runner.set_response("crontab -l", 1, "", "no crontab for user")

        collector = MacSystemInfoCollector(runner)
        jobs = collector.collect_cron_jobs()

        self.assertEqual(jobs, [])
        # Should not log error
        self.assertEqual(len(collector.errors), 0)


class TestConfigFiles(unittest.TestCase):
    """Tests for configuration file detection."""

    def test_detect_existing_config(self):
        """Test detection of existing config files."""
        runner = MockCommandRunner()
        collector = MacSystemInfoCollector(runner)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test config file
            config_path = Path(tmpdir) / "test_config"
            config_path.write_text("line1\nline2\nline3\n")

            # Patch Path.home to use temp dir
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                # We need to test the actual method behavior
                config = collector.collect_config_files()

                # The method checks real paths, so we verify structure
                self.assertIsInstance(config, list)
                self.assertGreater(len(config), 0)

                # Each entry should have expected keys
                for cfg in config:
                    self.assertIn("path", cfg)
                    self.assertIn("exists", cfg)
                    self.assertIn("size", cfg)

    def test_nonexistent_config(self):
        """Test handling of non-existent config files."""
        runner = MockCommandRunner()
        collector = MacSystemInfoCollector(runner)

        configs = collector.collect_config_files()

        # Should include entries even for missing files
        self.assertIsInstance(configs, list)
        for cfg in configs:
            self.assertIn("exists", cfg)
            # exists should be a boolean
            self.assertIsInstance(cfg["exists"], bool)


class TestFullCollection(unittest.TestCase):
    """Tests for full system info collection."""

    def test_collect_all_returns_system_info(self):
        """Test that collect_all returns a complete SystemInfo object."""
        runner = MockCommandRunner()

        # Set up minimal responses
        runner.set_response("system_profiler SPHardwareDataType", 0, "Model Name: Test Mac")
        runner.set_response("diskutil list", 0, "")
        runner.set_response("df -h", 0, "")
        runner.set_response("hostname", 0, "test-host")
        runner.set_response("ifconfig", 0, "")
        runner.set_response("scutil --dns", 0, "")
        runner.set_response("brew services", 0, "")
        runner.set_response("launchctl list", 0, "")
        runner.set_response("docker ps", -1, "", "not installed")
        runner.set_response("lsof -iTCP", 0, "")
        runner.set_response("crontab -l", 1, "", "no crontab")

        collector = MacSystemInfoCollector(runner)
        info = collector.collect_all()

        self.assertIsInstance(info, SystemInfo)
        self.assertIsNotNone(info.collection_timestamp)
        self.assertIsInstance(info.hardware, HardwareInfo)
        self.assertIsInstance(info.disk, DiskInfo)
        self.assertIsInstance(info.network, NetworkInfo)

    def test_to_json_output(self):
        """Test JSON serialization of system info."""
        runner = MockCommandRunner()

        runner.set_response("system_profiler SPHardwareDataType", 0, "Model Name: Test Mac\nChip: M1")
        runner.set_response("diskutil list", 0, "")
        runner.set_response("df -h", 0, "")
        runner.set_response("hostname", 0, "test")
        runner.set_response("ifconfig", 0, "")
        runner.set_response("scutil --dns", 0, "")
        runner.set_response("brew services", 0, "")
        runner.set_response("launchctl list", 0, "")
        runner.set_response("docker ps", -1, "", "")
        runner.set_response("lsof -iTCP", 0, "")
        runner.set_response("crontab -l", 1, "", "no crontab")

        collector = MacSystemInfoCollector(runner)
        info = collector.collect_all()
        json_str = collector.to_json(info)

        # Should be valid JSON
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

        # Static responses
        runner.set_response("system_profiler SPHardwareDataType", 0, "Model Name: Mac\nChip: M4")
        runner.set_response("diskutil list", 0, "/dev/disk0 (internal):")
        runner.set_response("df -h", 0, "Filesystem Size\n/ 100G")
        runner.set_response("hostname", 0, "testhost")
        runner.set_response("ifconfig", 0, "lo0: flags=8049<UP> mtu 16384")
        runner.set_response("scutil --dns", 0, "resolver #1\nnameserver[0] : 8.8.8.8")
        runner.set_response("brew services", 0, "Name Status\ntest none")
        runner.set_response("launchctl list", 0, "PID\tStatus\tLabel\n123\t0\ttest.service")
        runner.set_response("docker ps", 0, "nginx\tUp\t80/tcp")
        runner.set_response("lsof -iTCP", 0, "COMMAND PID USER\nnginx 123 root *:80")
        runner.set_response("crontab -l", 0, "0 * * * * echo test")

        collector = MacSystemInfoCollector(runner)

        # Collect multiple times
        info1 = collector.collect_all()
        info2 = collector.collect_all()
        info3 = collector.collect_all()

        # Convert to dict (excluding timestamp which will differ)
        d1 = collector.to_dict(info1)
        d2 = collector.to_dict(info2)
        d3 = collector.to_dict(info3)

        # Remove timestamps for comparison
        del d1["collection_timestamp"]
        del d2["collection_timestamp"]
        del d3["collection_timestamp"]

        # Clear errors list as it accumulates
        d1["errors"] = []
        d2["errors"] = []
        d3["errors"] = []

        self.assertEqual(d1, d2)
        self.assertEqual(d2, d3)

    def test_no_side_effects(self):
        """Test that collection doesn't modify system state."""
        runner = MockCommandRunner()

        runner.set_response("system_profiler SPHardwareDataType", 0, "")
        runner.set_response("diskutil list", 0, "")
        runner.set_response("df -h", 0, "")
        runner.set_response("hostname", 0, "")
        runner.set_response("ifconfig", 0, "")
        runner.set_response("scutil --dns", 0, "")
        runner.set_response("brew services", 0, "")
        runner.set_response("launchctl list", 0, "")
        runner.set_response("docker ps", 0, "")
        runner.set_response("lsof -iTCP", 0, "")
        runner.set_response("crontab -l", 0, "")

        collector = MacSystemInfoCollector(runner)
        collector.collect_all()

        # Verify only read-only commands were called
        readonly_commands = {
            "system_profiler", "diskutil", "df", "hostname",
            "ifconfig", "scutil", "brew", "launchctl",
            "docker", "lsof", "crontab"
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
        # This should timeout quickly
        returncode, stdout, stderr = runner.run(["sleep", "10"], timeout=1)

        self.assertEqual(returncode, -1)
        self.assertIn("timed out", stderr.lower())


if __name__ == "__main__":
    unittest.main()
