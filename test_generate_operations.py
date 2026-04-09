#!/usr/bin/env python3
"""
Unit tests for generate_operations.py

Run with: python -m unittest test_generate_operations -v
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from generate_operations import (
    OperationsRenderer, collect_system_info, load_json_info,
    gpg_available, gpg_sign_file, gpg_verify_file,
)


class TestOperationsRenderer(unittest.TestCase):
    """Tests for the OperationsRenderer class."""

    def get_sample_info(self) -> dict:
        """Return sample system info for testing."""
        return {
            "hardware": {
                "model_name": "Mac mini",
                "model_identifier": "Mac16,10",
                "model_number": "MU9D3LL/A",
                "chip": "Apple M4",
                "total_cores": "10 (4 Performance and 6 Efficiency)",
                "memory": "16 GB",
                "serial_number": "ABC123",
                "firmware_version": "1.0.0"
            },
            "disk": {
                "partitions": [
                    {
                        "device": "/dev/disk0",
                        "name": "Macintosh HD",
                        "size": "245 GB",
                        "type": "APFS",
                        "identifier": "disk0s2"
                    },
                    {
                        "device": "/dev/disk1",
                        "name": "External",
                        "size": "1 TB",
                        "type": "Windows_NTFS",
                        "identifier": "disk1s1"
                    }
                ],
                "usage": [
                    {
                        "filesystem": "/dev/disk0s2",
                        "size": "228Gi",
                        "used": "57Gi",
                        "available": "146Gi",
                        "capacity": "29%",
                        "mount_point": "/"
                    }
                ]
            },
            "network": {
                "hostname": "test-mac",
                "interfaces": [
                    {
                        "name": "lo0",
                        "flags": "UP,LOOPBACK,RUNNING",
                        "mtu": "16384",
                        "ipv4_address": "127.0.0.1",
                        "netmask": "0xff000000",
                        "broadcast": ""
                    },
                    {
                        "name": "en0",
                        "flags": "UP,BROADCAST,RUNNING",
                        "mtu": "1500",
                        "ipv4_address": "192.168.1.100",
                        "netmask": "0xffffff00",
                        "broadcast": "192.168.1.255"
                    }
                ],
                "dns_resolvers": [
                    {
                        "nameservers": ["8.8.8.8", "8.8.4.4"],
                        "interface": "en0",
                        "domain": ""
                    }
                ]
            },
            "homebrew_services": [
                {
                    "name": "postgresql@14",
                    "status": "started",
                    "user": "testuser",
                    "file": "~/Library/LaunchAgents/homebrew.mxcl.postgresql@14.plist"
                },
                {
                    "name": "redis",
                    "status": "none",
                    "user": "",
                    "file": ""
                }
            ],
            "launchd_services": [
                {
                    "pid": "1234",
                    "status": "0",
                    "label": "com.test.service"
                },
                {
                    "pid": "",
                    "status": "0",
                    "label": "com.nomachine.server"
                }
            ],
            "docker_containers": [
                {
                    "name": "nginx",
                    "status": "Up 2 hours",
                    "ports": "0.0.0.0:80->80/tcp"
                }
            ],
            "listening_ports": [
                {
                    "process": "nginx",
                    "user": "root",
                    "address": "*:80"
                },
                {
                    "process": "postgres",
                    "user": "testuser",
                    "address": "*:5432"
                }
            ],
            "cron_jobs": [
                "0 2 * * * /usr/local/bin/backup.sh"
            ],
            "config_files": [
                {
                    "path": "/Users/test/.ssh/config",
                    "exists": True,
                    "size": 100,
                    "content_preview": "Host *"
                },
                {
                    "path": "/Users/test/.zshrc",
                    "exists": True,
                    "size": 500,
                    "content_preview": ""
                },
                {
                    "path": "/Users/test/.bashrc",
                    "exists": False,
                    "size": 0,
                    "content_preview": ""
                }
            ],
            "collection_timestamp": "2024-01-15T10:30:00",
            "errors": []
        }

    def test_render_returns_string(self):
        """Test that render returns a non-empty string."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIsInstance(output, str)
        self.assertGreater(len(output), 0)

    def test_render_contains_header(self):
        """Test that output contains proper header."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("# Operations Guide", output)
        self.assertIn("Mac mini", output)
        self.assertIn("Apple M4", output)

    def test_render_contains_hardware_section(self):
        """Test that hardware section is rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Hardware Specifications", output)
        self.assertIn("16 GB", output)
        self.assertIn("10 (4 Performance and 6 Efficiency)", output)

    def test_render_contains_disk_section(self):
        """Test that disk section is rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Disk Layout", output)
        self.assertIn("Macintosh HD", output)
        self.assertIn("245 GB", output)

    def test_render_contains_network_section(self):
        """Test that network section is rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Network Information", output)
        self.assertIn("192.168.1.100", output)
        self.assertIn("test-mac", output)

    def test_render_contains_homebrew_services(self):
        """Test that Homebrew services are rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Homebrew Services", output)
        self.assertIn("postgresql@14", output)
        self.assertIn("started", output)

    def test_render_contains_docker_section(self):
        """Test that Docker section is rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Docker", output)
        self.assertIn("nginx", output)
        self.assertIn("Up 2 hours", output)

    def test_render_empty_docker(self):
        """Test Docker section when no containers."""
        info = self.get_sample_info()
        info["docker_containers"] = []
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Docker", output)
        self.assertIn("Not currently running", output)

    def test_render_contains_listening_ports(self):
        """Test that listening ports are rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Listening Ports", output)
        self.assertIn("*:80", output)
        self.assertIn("*:5432", output)

    def test_render_contains_cron_jobs(self):
        """Test that cron jobs are rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Scheduled Tasks", output)
        self.assertIn("backup.sh", output)

    def test_render_empty_cron(self):
        """Test cron section when no jobs."""
        info = self.get_sample_info()
        info["cron_jobs"] = []
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("No crontab entries", output)

    def test_render_contains_config_locations(self):
        """Test that config locations are rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Configuration Locations", output)
        self.assertIn(".ssh/config", output)
        self.assertIn(".zshrc", output)

    def test_render_contains_troubleshooting(self):
        """Test that troubleshooting section is rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Troubleshooting Guide", output)
        self.assertIn("memory_pressure", output)

    def test_render_contains_backup_section(self):
        """Test that backup section is rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Backup Recommendations", output)
        self.assertIn("brew bundle dump", output)

    def test_render_detects_ntfs_issue(self):
        """Test that NTFS drives are flagged as known issues."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Known Issues", output)
        self.assertIn("NTFS", output)

    def test_render_detects_nomachine(self):
        """Test that NoMachine is detected for remote access."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Remote Access", output)
        self.assertIn("NoMachine", output)

    def test_render_contains_changelog(self):
        """Test that changelog section is rendered."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Changelog", output)
        self.assertIn("Auto-generated", output)

    def test_render_is_valid_markdown(self):
        """Test that output contains valid markdown structure."""
        info = self.get_sample_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        # Check for markdown headers
        self.assertIn("# ", output)
        self.assertIn("## ", output)
        self.assertIn("### ", output)

        # Check for code blocks
        self.assertIn("```bash", output)
        self.assertIn("```", output)

        # Check for tables
        self.assertIn("|", output)
        self.assertIn("|-", output)


class TestInferPurpose(unittest.TestCase):
    """Tests for the _infer_purpose method."""

    def test_known_processes(self):
        """Test purpose inference for known processes."""
        renderer = OperationsRenderer({})

        self.assertIn("Remote Desktop", renderer._infer_purpose("ARDAgent"))
        self.assertIn("AirPlay", renderer._infer_purpose("ControlCenter"))
        self.assertIn("PostgreSQL", renderer._infer_purpose("postgres"))
        self.assertIn("Redis", renderer._infer_purpose("redis-server"))
        self.assertIn("NoMachine", renderer._infer_purpose("nxnode"))

    def test_unknown_process(self):
        """Test purpose inference for unknown process."""
        renderer = OperationsRenderer({})

        purpose = renderer._infer_purpose("unknown_service")
        self.assertIn("Application", purpose)


class TestLoadJsonInfo(unittest.TestCase):
    """Tests for loading JSON info from file."""

    def test_load_valid_json(self):
        """Test loading valid JSON file."""
        test_data = {
            "hardware": {"model_name": "Test"},
            "disk": {"partitions": []},
            "network": {"hostname": "test"},
            "homebrew_services": [],
            "launchd_services": [],
            "docker_containers": [],
            "listening_ports": [],
            "cron_jobs": [],
            "config_files": [],
            "collection_timestamp": "2024-01-01T00:00:00",
            "errors": []
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            f.flush()

            loaded = load_json_info(f.name)

            self.assertEqual(loaded["hardware"]["model_name"], "Test")
            self.assertEqual(loaded["network"]["hostname"], "test")

        Path(f.name).unlink()

    def test_load_invalid_json(self):
        """Test loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json {")
            f.flush()

            with self.assertRaises(json.JSONDecodeError):
                load_json_info(f.name)

        Path(f.name).unlink()


class TestIdempotency(unittest.TestCase):
    """Tests for idempotent rendering."""

    def test_same_input_same_output(self):
        """Test that same input produces same output structure."""
        info = {
            "hardware": {"model_name": "Test", "chip": "M1", "memory": "8 GB"},
            "disk": {"partitions": [], "usage": []},
            "network": {"hostname": "test", "interfaces": [], "dns_resolvers": []},
            "homebrew_services": [],
            "launchd_services": [],
            "docker_containers": [],
            "listening_ports": [],
            "cron_jobs": [],
            "config_files": [],
            "collection_timestamp": "2024-01-01T00:00:00",
            "errors": []
        }

        renderer1 = OperationsRenderer(info)
        renderer2 = OperationsRenderer(info)

        output1 = renderer1.render()
        output2 = renderer2.render()

        # Outputs should be identical for same input
        # Note: We use same timestamp so dates match
        self.assertEqual(output1, output2)

    def test_different_inputs_different_outputs(self):
        """Test that different inputs produce different outputs."""
        info1 = {
            "hardware": {"model_name": "Mac mini", "chip": "M4", "memory": "16 GB"},
            "disk": {"partitions": [], "usage": []},
            "network": {"hostname": "mini", "interfaces": [], "dns_resolvers": []},
            "homebrew_services": [],
            "launchd_services": [],
            "docker_containers": [],
            "listening_ports": [],
            "cron_jobs": [],
            "config_files": [],
            "collection_timestamp": "2024-01-01T00:00:00",
            "errors": []
        }

        info2 = {
            "hardware": {"model_name": "MacBook Pro", "chip": "M3", "memory": "32 GB"},
            "disk": {"partitions": [], "usage": []},
            "network": {"hostname": "mbp", "interfaces": [], "dns_resolvers": []},
            "homebrew_services": [],
            "launchd_services": [],
            "docker_containers": [],
            "listening_ports": [],
            "cron_jobs": [],
            "config_files": [],
            "collection_timestamp": "2024-01-01T00:00:00",
            "errors": []
        }

        renderer1 = OperationsRenderer(info1)
        renderer2 = OperationsRenderer(info2)

        output1 = renderer1.render()
        output2 = renderer2.render()

        self.assertNotEqual(output1, output2)
        self.assertIn("Mac mini", output1)
        self.assertIn("MacBook Pro", output2)


class TestEmptyData(unittest.TestCase):
    """Tests for handling empty or minimal data."""

    def test_empty_everything(self):
        """Test rendering with minimal data."""
        info = {
            "hardware": {},
            "disk": {"partitions": [], "usage": []},
            "network": {"hostname": "", "interfaces": [], "dns_resolvers": []},
            "homebrew_services": [],
            "launchd_services": [],
            "docker_containers": [],
            "listening_ports": [],
            "cron_jobs": [],
            "config_files": [],
            "collection_timestamp": "2024-01-01T00:00:00",
            "errors": []
        }

        renderer = OperationsRenderer(info)
        output = renderer.render()

        # Should still produce valid output
        self.assertIn("# Operations Guide", output)
        self.assertIn("## Hardware", output)
        self.assertIn("## Disk", output)

    def test_missing_keys(self):
        """Test handling of missing dictionary keys."""
        info = {
            "collection_timestamp": "2024-01-01T00:00:00"
        }

        renderer = OperationsRenderer(info)

        # Should not raise exceptions
        output = renderer.render()
        self.assertIsInstance(output, str)


class TestGPGSigning(unittest.TestCase):
    """Tests for GPG signing and verification functions."""

    @patch("generate_operations.shutil.which", return_value=None)
    def test_gpg_available_no_gpg(self, mock_which):
        """Test gpg_available returns False when gpg is not installed."""
        self.assertFalse(gpg_available())

    @patch("generate_operations.subprocess.run")
    @patch("generate_operations.shutil.which", return_value="/usr/bin/gpg")
    def test_gpg_available_no_key(self, mock_which, mock_run):
        """Test gpg_available returns False when no secret key exists."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        self.assertFalse(gpg_available())

    @patch("generate_operations.subprocess.run")
    @patch("generate_operations.shutil.which", return_value="/usr/bin/gpg")
    def test_gpg_available_with_key(self, mock_which, mock_run):
        """Test gpg_available returns True when a secret key exists."""
        mock_run.return_value = MagicMock(
            stdout="sec   rsa4096/ABCDEF1234567890 2024-01-01 [SC]", returncode=0
        )
        self.assertTrue(gpg_available())

    @patch("generate_operations.gpg_available", return_value=False)
    def test_sign_file_no_gpg(self, mock_avail):
        """Test gpg_sign_file returns False when gpg is not available."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"test content")
            f.flush()
            result = gpg_sign_file(f.name, quiet=True)
            self.assertFalse(result)
        Path(f.name).unlink()

    @patch("generate_operations.subprocess.run")
    @patch("generate_operations.gpg_available", return_value=True)
    def test_sign_file_success(self, mock_avail, mock_run):
        """Test gpg_sign_file returns True on successful signing."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"test content")
            f.flush()
            result = gpg_sign_file(f.name, quiet=True)
            self.assertTrue(result)
        Path(f.name).unlink()

    @patch("generate_operations.subprocess.run")
    @patch("generate_operations.gpg_available", return_value=True)
    def test_sign_file_failure(self, mock_avail, mock_run):
        """Test gpg_sign_file returns False on GPG failure."""
        mock_run.return_value = MagicMock(returncode=2, stderr="gpg: signing failed")
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"test content")
            f.flush()
            result = gpg_sign_file(f.name, quiet=True)
            self.assertFalse(result)
        Path(f.name).unlink()

    def test_verify_file_unsigned(self):
        """Test gpg_verify_file returns 2 when no .asc file exists."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"test content")
            f.flush()
            result = gpg_verify_file(f.name)
            self.assertEqual(result, 2)
        Path(f.name).unlink()

    @patch("generate_operations.shutil.which", return_value="/usr/bin/gpg")
    @patch("generate_operations.subprocess.run")
    def test_verify_file_valid(self, mock_run, mock_which):
        """Test gpg_verify_file returns 0 when signature is valid."""
        mock_run.return_value = MagicMock(returncode=0, stderr="Good signature")
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"test content")
            f.flush()
            # Create a fake .asc file
            asc_path = f.name + ".asc"
            Path(asc_path).write_text("fake signature")
            result = gpg_verify_file(f.name)
            self.assertEqual(result, 0)
        Path(f.name).unlink()
        Path(asc_path).unlink()

    @patch("generate_operations.shutil.which", return_value="/usr/bin/gpg")
    @patch("generate_operations.subprocess.run")
    def test_verify_file_invalid(self, mock_run, mock_which):
        """Test gpg_verify_file returns 1 when signature is invalid."""
        mock_run.return_value = MagicMock(returncode=1, stderr="BAD signature")
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"test content")
            f.flush()
            asc_path = f.name + ".asc"
            Path(asc_path).write_text("fake signature")
            result = gpg_verify_file(f.name)
            self.assertEqual(result, 1)
        Path(f.name).unlink()
        Path(asc_path).unlink()

    @patch("generate_operations.shutil.which", return_value=None)
    def test_verify_file_no_gpg_with_asc(self, mock_which):
        """Test gpg_verify_file returns 1 when gpg missing but .asc exists."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"test content")
            f.flush()
            asc_path = f.name + ".asc"
            Path(asc_path).write_text("fake signature")
            result = gpg_verify_file(f.name)
            self.assertEqual(result, 1)
        Path(f.name).unlink()
        Path(asc_path).unlink()


class TestLinuxRendering(unittest.TestCase):
    """Tests for Linux-specific rendering."""

    def get_linux_info(self) -> dict:
        """Return sample Linux system info for testing."""
        return {
            "platform": "linux",
            "hardware": {
                "hostname": "webserver",
                "os_name": "Debian GNU/Linux 13 (trixie)",
                "os_version": "13 (trixie)",
                "kernel": "Linux 6.12.47+rpt-rpi-v8",
                "architecture": "arm64",
                "cpu_model": "Cortex-A72",
                "cpu_cores": "",
                "cpu_threads": "4",
                "memory_total": "7.6Gi",
                "memory_available": "7.4Gi",
                "virtualization": "",
            },
            "disk": {
                "partitions": [
                    {
                        "name": "mmcblk0p2",
                        "size": "118.9G",
                        "type": "part",
                        "mountpoint": "/",
                        "fstype": "ext4",
                    }
                ],
                "usage": [
                    {
                        "filesystem": "/dev/mmcblk0p2",
                        "size": "118G",
                        "used": "5.8G",
                        "available": "107G",
                        "use_percent": "6%",
                        "mount_point": "/",
                    }
                ],
            },
            "network": {
                "hostname": "webserver",
                "interfaces": [
                    {
                        "name": "eth0",
                        "flags": "UP,BROADCAST,RUNNING,MULTICAST",
                        "ipv4_address": "192.168.110.147",
                    },
                    {
                        "name": "lo",
                        "flags": "UP,LOOPBACK,RUNNING",
                        "ipv4_address": "127.0.0.1",
                    },
                ],
                "dns_resolvers": [],
            },
            "systemd_services": [
                {
                    "unit": "nginx.service",
                    "load": "loaded",
                    "active": "active",
                    "sub": "running",
                    "description": "A high performance web server and a reverse proxy server",
                },
                {
                    "unit": "media-gallery.service",
                    "load": "loaded",
                    "active": "active",
                    "sub": "running",
                    "description": "Media Gallery Flask Application",
                },
                {
                    "unit": "ssh.service",
                    "load": "loaded",
                    "active": "active",
                    "sub": "running",
                    "description": "OpenBSD Secure Shell server",
                },
            ],
            "docker_containers": [],
            "listening_ports": [
                {
                    "protocol": "tcp",
                    "local_address": "0.0.0.0:22",
                    "process": "sshd",
                    "pid": "839",
                },
                {
                    "protocol": "tcp",
                    "local_address": "0.0.0.0:80",
                    "process": "nginx",
                    "pid": "855",
                },
                {
                    "protocol": "tcp",
                    "local_address": "127.0.0.1:5000",
                    "process": "python",
                    "pid": "828",
                },
            ],
            "cron_jobs": [],
            "config_files": [
                {"path": "/home/pi/.bashrc", "exists": True, "size": 100, "content_preview": ""},
                {"path": "/home/pi/.gitconfig", "exists": True, "size": 50, "content_preview": ""},
            ],
            "collection_timestamp": "2026-04-09T15:44:00",
            "errors": [],
        }

    def test_detects_linux_platform(self):
        """Test that Linux platform is detected from platform field."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        self.assertTrue(renderer.is_linux)

    def test_detects_linux_from_systemd(self):
        """Test that Linux is detected from systemd_services when platform field missing."""
        info = self.get_linux_info()
        del info["platform"]
        renderer = OperationsRenderer(info)
        self.assertTrue(renderer.is_linux)

    def test_detects_macos_by_default(self):
        """Test that macOS is detected when homebrew_services present."""
        info = {"homebrew_services": [{"name": "test"}]}
        renderer = OperationsRenderer(info)
        self.assertFalse(renderer.is_linux)

    def test_linux_header(self):
        """Test that Linux header uses correct fields."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("# Operations Guide - webserver", output)
        self.assertIn("Debian GNU/Linux 13", output)
        self.assertIn("7.6Gi RAM", output)
        self.assertNotIn("macOS", output)

    def test_linux_quick_reference_uses_systemctl(self):
        """Test that Linux quick reference uses systemctl, not brew."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("systemctl", output)
        self.assertIn("journalctl", output)
        self.assertNotIn("brew services", output)
        self.assertNotIn("launchctl", output)

    def test_linux_renders_systemd_services(self):
        """Test that systemd services are rendered."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Systemd Services", output)
        self.assertIn("nginx.service", output)
        self.assertIn("media-gallery.service", output)
        self.assertIn("ssh.service", output)

    def test_linux_listening_ports_uses_local_address(self):
        """Test that Linux ports render with local_address field."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Listening Ports", output)
        self.assertIn("0.0.0.0:80", output)
        self.assertIn("0.0.0.0:22", output)
        self.assertIn("127.0.0.1:5000", output)
        self.assertIn("nginx", output)
        self.assertIn("sshd", output)

    def test_linux_architecture_shows_components(self):
        """Test that architecture table includes detected services."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Architecture Overview", output)
        self.assertIn("| Component | Port | Purpose | Type |", output)
        # nginx on port 80 should appear
        self.assertIn("nginx", output)
        self.assertIn("80", output)
        self.assertIn("Web server", output)

    def test_linux_hardware_fields(self):
        """Test that Linux hardware uses correct field names."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("Cortex-A72", output)
        self.assertIn("arm64", output)
        self.assertIn("7.6Gi", output)

    def test_linux_disk_shows_mountpoint(self):
        """Test that Linux disk partitions show mountpoint."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("Mount Point", output)
        self.assertIn("ext4", output)

    def test_linux_config_locations(self):
        """Test that Linux config locations use Linux paths."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("/etc/systemd/system/", output)
        self.assertIn("/etc/nginx/", output)
        self.assertNotIn("LaunchAgents", output)
        self.assertNotIn("/opt/homebrew", output)

    def test_linux_troubleshooting(self):
        """Test that Linux troubleshooting uses journalctl."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("journalctl", output)
        self.assertIn("systemctl --failed", output)
        self.assertNotIn("memory_pressure", output)
        self.assertNotIn("DiagnosticReports", output)

    def test_linux_backup_commands(self):
        """Test that Linux backup uses Linux-specific commands."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("dpkg --get-selections", output)
        self.assertNotIn("brew bundle dump", output)
        self.assertNotIn("tmutil", output)

    def test_linux_network_commands(self):
        """Test that Linux network section uses ip command."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("ip addr show", output)
        self.assertIn("ip route show", output)
        self.assertNotIn("scutil --dns", output)

    def test_linux_ss_refresh_command(self):
        """Test that Linux listening ports suggest ss, not lsof."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("sudo ss -tlnp", output)
        self.assertNotIn("lsof -iTCP", output)

    def test_linux_remote_access_detects_ssh(self):
        """Test that SSH is detected from systemd services."""
        info = self.get_linux_info()
        renderer = OperationsRenderer(info)
        output = renderer.render()

        self.assertIn("## Remote Access", output)
        self.assertIn("SSH", output)


class TestLinuxPlatformDetection(unittest.TestCase):
    """Tests for platform detection heuristics."""

    def test_explicit_platform_linux(self):
        """Test explicit platform=linux detection."""
        renderer = OperationsRenderer({"platform": "linux"})
        self.assertTrue(renderer.is_linux)

    def test_explicit_platform_darwin(self):
        """Test explicit platform=darwin detection."""
        renderer = OperationsRenderer({"platform": "darwin"})
        self.assertFalse(renderer.is_linux)

    def test_kernel_heuristic(self):
        """Test detection from kernel string."""
        renderer = OperationsRenderer({"hardware": {"kernel": "Linux 6.1.0"}})
        self.assertTrue(renderer.is_linux)

    def test_empty_data_defaults_macos(self):
        """Test that empty data defaults to macOS (backwards compatibility)."""
        renderer = OperationsRenderer({})
        self.assertFalse(renderer.is_linux)


if __name__ == "__main__":
    unittest.main()
