#!/usr/bin/env python3
"""
mac_system_info.py - Idempotent macOS system information gatherer

Collects hardware, disk, network, services, and configuration data
from a macOS system. Safe to run multiple times with consistent results.

Usage:
    python mac_system_info.py                    # Print JSON to stdout
    python mac_system_info.py --output info.json # Write to file
    python mac_system_info.py --format yaml      # Output as YAML (requires PyYAML)
"""

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class HardwareInfo:
    model_name: str = ""
    model_identifier: str = ""
    model_number: str = ""
    chip: str = ""
    total_cores: str = ""
    memory: str = ""
    serial_number: str = ""
    firmware_version: str = ""


@dataclass
class DiskPartition:
    device: str = ""
    name: str = ""
    size: str = ""
    type: str = ""
    identifier: str = ""


@dataclass
class DiskUsage:
    filesystem: str = ""
    size: str = ""
    used: str = ""
    available: str = ""
    capacity: str = ""
    mount_point: str = ""


@dataclass
class DiskInfo:
    partitions: list = field(default_factory=list)
    usage: list = field(default_factory=list)


@dataclass
class NetworkInterface:
    name: str = ""
    flags: str = ""
    mtu: str = ""
    ipv4_address: str = ""
    netmask: str = ""
    broadcast: str = ""


@dataclass
class DNSResolver:
    nameservers: list = field(default_factory=list)
    interface: str = ""
    domain: str = ""


@dataclass
class NetworkInfo:
    interfaces: list = field(default_factory=list)
    dns_resolvers: list = field(default_factory=list)
    hostname: str = ""


@dataclass
class HomebrewService:
    name: str = ""
    status: str = ""
    user: str = ""
    file: str = ""


@dataclass
class LaunchdService:
    pid: str = ""
    status: str = ""
    label: str = ""


@dataclass
class DockerContainer:
    name: str = ""
    status: str = ""
    ports: str = ""


@dataclass
class ListeningPort:
    process: str = ""
    user: str = ""
    address: str = ""


@dataclass
class ConfigFile:
    path: str = ""
    exists: bool = False
    size: int = 0
    content_preview: str = ""


@dataclass
class SystemInfo:
    hardware: HardwareInfo = field(default_factory=HardwareInfo)
    disk: DiskInfo = field(default_factory=DiskInfo)
    network: NetworkInfo = field(default_factory=NetworkInfo)
    homebrew_services: list = field(default_factory=list)
    launchd_services: list = field(default_factory=list)
    docker_containers: list = field(default_factory=list)
    listening_ports: list = field(default_factory=list)
    cron_jobs: list = field(default_factory=list)
    config_files: list = field(default_factory=list)
    platform: str = "darwin"
    collection_timestamp: str = ""
    errors: list = field(default_factory=list)


class CommandRunner:
    """Abstraction for running shell commands. Enables testing via dependency injection."""

    def run(self, command: list[str], timeout: int = 30) -> tuple[int, str, str]:
        """
        Run a command and return (returncode, stdout, stderr).

        Args:
            command: Command and arguments as a list
            timeout: Timeout in seconds

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return -1, "", f"Command not found: {command[0]}"
        except Exception as e:
            return -1, "", str(e)


class MacSystemInfoCollector:
    """Collects system information from a macOS system."""

    def __init__(self, runner: Optional[CommandRunner] = None):
        """
        Initialize the collector.

        Args:
            runner: CommandRunner instance for executing commands.
                   If None, creates a default CommandRunner.
        """
        self.runner = runner or CommandRunner()
        self.errors: list[str] = []

    def collect_all(self) -> SystemInfo:
        """
        Collect all system information.

        Returns:
            SystemInfo dataclass with all collected data
        """
        from datetime import datetime

        info = SystemInfo()
        info.collection_timestamp = datetime.now().isoformat()

        info.hardware = self.collect_hardware()
        info.disk = self.collect_disk()
        info.network = self.collect_network()
        info.homebrew_services = self.collect_homebrew_services()
        info.launchd_services = self.collect_launchd_services()
        info.docker_containers = self.collect_docker_containers()
        info.listening_ports = self.collect_listening_ports()
        info.cron_jobs = self.collect_cron_jobs()
        info.config_files = self.collect_config_files()
        info.errors = self.errors.copy()

        return info

    def collect_hardware(self) -> HardwareInfo:
        """Collect hardware information using system_profiler."""
        hw = HardwareInfo()

        returncode, stdout, stderr = self.runner.run(
            ["system_profiler", "SPHardwareDataType"]
        )

        if returncode != 0:
            self.errors.append(f"Hardware collection failed: {stderr}")
            return hw

        field_map = {
            "Model Name": "model_name",
            "Model Identifier": "model_identifier",
            "Model Number": "model_number",
            "Chip": "chip",
            "Total Number of Cores": "total_cores",
            "Memory": "memory",
            "Serial Number (system)": "serial_number",
            "System Firmware Version": "firmware_version",
        }

        for line in stdout.splitlines():
            line = line.strip()
            for key, attr in field_map.items():
                if line.startswith(f"{key}:"):
                    value = line.split(":", 1)[1].strip()
                    setattr(hw, attr, value)
                    break

        return hw

    def collect_disk(self) -> DiskInfo:
        """Collect disk layout and usage information."""
        disk_info = DiskInfo()

        # Get partition layout with diskutil list
        returncode, stdout, stderr = self.runner.run(["diskutil", "list"])
        if returncode == 0:
            disk_info.partitions = self._parse_diskutil_list(stdout)
        else:
            self.errors.append(f"diskutil list failed: {stderr}")

        # Get disk usage with df -h
        returncode, stdout, stderr = self.runner.run(["df", "-h"])
        if returncode == 0:
            disk_info.usage = self._parse_df_output(stdout)
        else:
            self.errors.append(f"df -h failed: {stderr}")

        return disk_info

    def _parse_diskutil_list(self, output: str) -> list[dict]:
        """Parse diskutil list output into structured data."""
        partitions = []
        current_disk = ""
        current_disk_info = ""

        for line in output.splitlines():
            # Match disk header lines like "/dev/disk0 (internal, physical):"
            disk_match = re.match(r'^(/dev/\w+)\s+\(([^)]+)\):', line)
            if disk_match:
                current_disk = disk_match.group(1)
                current_disk_info = disk_match.group(2)
                continue

            # Match partition lines
            part_match = re.match(
                r'^\s+(\d+):\s+(\S+)\s+(.+?)\s+([\d.]+\s*[KMGT]?B)\s+(\S+)$',
                line
            )
            if part_match:
                partitions.append(asdict(DiskPartition(
                    device=current_disk,
                    type=part_match.group(2),
                    name=part_match.group(3).strip(),
                    size=part_match.group(4),
                    identifier=part_match.group(5),
                )))

        return partitions

    def _parse_df_output(self, output: str) -> list[dict]:
        """Parse df -h output into structured data."""
        usage = []
        lines = output.strip().splitlines()

        if not lines:
            return usage

        # Skip header line
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:
                # Handle mount points with spaces by joining remaining parts
                mount = " ".join(parts[8:]) if len(parts) > 8 else parts[-1]
                usage.append(asdict(DiskUsage(
                    filesystem=parts[0],
                    size=parts[1],
                    used=parts[2],
                    available=parts[3],
                    capacity=parts[4],
                    mount_point=mount,
                )))

        return usage

    def collect_network(self) -> NetworkInfo:
        """Collect network interface and DNS information."""
        net_info = NetworkInfo()

        # Get hostname
        returncode, stdout, stderr = self.runner.run(["hostname"])
        if returncode == 0:
            net_info.hostname = stdout.strip()

        # Get interface info with ifconfig
        returncode, stdout, stderr = self.runner.run(["ifconfig"])
        if returncode == 0:
            net_info.interfaces = self._parse_ifconfig(stdout)
        else:
            self.errors.append(f"ifconfig failed: {stderr}")

        # Get DNS info with scutil
        returncode, stdout, stderr = self.runner.run(["scutil", "--dns"])
        if returncode == 0:
            net_info.dns_resolvers = self._parse_scutil_dns(stdout)
        else:
            self.errors.append(f"scutil --dns failed: {stderr}")

        return net_info

    def _parse_ifconfig(self, output: str) -> list[dict]:
        """Parse ifconfig output into structured data."""
        interfaces = []
        current_iface = None

        for line in output.splitlines():
            # Match interface header
            iface_match = re.match(r'^(\w+):\s+flags=\d+<([^>]*)>\s+mtu\s+(\d+)', line)
            if iface_match:
                if current_iface:
                    interfaces.append(asdict(current_iface))
                current_iface = NetworkInterface(
                    name=iface_match.group(1),
                    flags=iface_match.group(2),
                    mtu=iface_match.group(3),
                )
                continue

            # Match inet line for IPv4
            if current_iface:
                inet_match = re.match(
                    r'^\s+inet\s+([\d.]+)\s+netmask\s+(\S+)(?:\s+broadcast\s+([\d.]+))?',
                    line
                )
                if inet_match:
                    current_iface.ipv4_address = inet_match.group(1)
                    current_iface.netmask = inet_match.group(2)
                    current_iface.broadcast = inet_match.group(3) or ""

        if current_iface:
            interfaces.append(asdict(current_iface))

        return interfaces

    def _parse_scutil_dns(self, output: str) -> list[dict]:
        """Parse scutil --dns output into structured data."""
        resolvers = []
        current_resolver = None

        for line in output.splitlines():
            if line.startswith("resolver #"):
                if current_resolver:
                    resolvers.append(asdict(current_resolver))
                current_resolver = DNSResolver()
                continue

            if current_resolver:
                line = line.strip()
                if line.startswith("nameserver"):
                    match = re.match(r'nameserver\[\d+\]\s*:\s*([\d.]+)', line)
                    if match:
                        current_resolver.nameservers.append(match.group(1))
                elif line.startswith("domain"):
                    current_resolver.domain = line.split(":", 1)[1].strip()
                elif line.startswith("if_index"):
                    match = re.search(r'\((\w+)\)', line)
                    if match:
                        current_resolver.interface = match.group(1)

        if current_resolver:
            resolvers.append(asdict(current_resolver))

        return resolvers

    def collect_homebrew_services(self) -> list[dict]:
        """Collect Homebrew services list."""
        returncode, stdout, stderr = self.runner.run(["brew", "services", "list"])

        if returncode != 0:
            if "command not found" not in stderr.lower():
                self.errors.append(f"brew services failed: {stderr}")
            return []

        services = []
        lines = stdout.strip().splitlines()

        # Skip header
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2:
                services.append(asdict(HomebrewService(
                    name=parts[0],
                    status=parts[1] if len(parts) > 1 else "",
                    user=parts[2] if len(parts) > 2 else "",
                    file=parts[3] if len(parts) > 3 else "",
                )))

        return services

    def collect_launchd_services(self) -> list[dict]:
        """Collect non-Apple launchd services."""
        returncode, stdout, stderr = self.runner.run(["launchctl", "list"])

        if returncode != 0:
            self.errors.append(f"launchctl list failed: {stderr}")
            return []

        services = []
        lines = stdout.splitlines()

        for line in lines:
            # Skip header line and Apple services
            if line.startswith("PID") or "com.apple" in line:
                continue

            parts = line.split("\t")
            if len(parts) >= 3:
                services.append(asdict(LaunchdService(
                    pid=parts[0] if parts[0] != "-" else "",
                    status=parts[1],
                    label=parts[2],
                )))

        return services

    def collect_docker_containers(self) -> list[dict]:
        """Collect running Docker containers."""
        returncode, stdout, stderr = self.runner.run([
            "docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"
        ])

        if returncode != 0:
            # Docker not running is not an error, just means no containers
            if "cannot connect" not in stderr.lower() and "command not found" not in stderr.lower():
                self.errors.append(f"docker ps failed: {stderr}")
            return []

        containers = []
        for line in stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 1:
                containers.append(asdict(DockerContainer(
                    name=parts[0],
                    status=parts[1] if len(parts) > 1 else "",
                    ports=parts[2] if len(parts) > 2 else "",
                )))

        return containers

    def collect_listening_ports(self) -> list[dict]:
        """Collect listening TCP ports."""
        returncode, stdout, stderr = self.runner.run([
            "lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"
        ])

        if returncode != 0 and stdout == "":
            # Empty output with error likely means no listening ports or permission issue
            if stderr:
                self.errors.append(f"lsof failed: {stderr}")
            return []

        ports = []
        seen = set()

        for line in stdout.splitlines()[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 9:
                key = (parts[0], parts[2], parts[8])
                if key not in seen:
                    seen.add(key)
                    ports.append(asdict(ListeningPort(
                        process=parts[0],
                        user=parts[2],
                        address=parts[8],
                    )))

        return ports

    def collect_cron_jobs(self) -> list[str]:
        """Collect crontab entries for current user."""
        returncode, stdout, stderr = self.runner.run(["crontab", "-l"])

        if returncode != 0:
            # "no crontab" is not an error
            if "no crontab" not in stderr.lower():
                self.errors.append(f"crontab -l failed: {stderr}")
            return []

        jobs = []
        for line in stdout.splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                jobs.append(line)

        return jobs

    def collect_config_files(self) -> list[dict]:
        """Check for common configuration files."""
        home = Path.home()

        config_paths = [
            home / ".ssh" / "config",
            home / ".zshrc",
            home / ".bashrc",
            home / ".bash_profile",
            Path("/etc/hosts"),
            home / ".gitconfig",
            home / ".npmrc",
            home / ".pypirc",
        ]

        configs = []
        for path in config_paths:
            config = ConfigFile(path=str(path))

            if path.exists():
                config.exists = True
                try:
                    config.size = path.stat().st_size
                    # Read first few lines as preview (don't read sensitive files)
                    if path.name not in (".pypirc", ".npmrc") and config.size < 10000:
                        content = path.read_text(errors="replace")
                        lines = content.splitlines()[:5]
                        config.content_preview = "\n".join(lines)
                except (PermissionError, OSError):
                    pass

            configs.append(asdict(config))

        return configs

    def to_dict(self, info: SystemInfo) -> dict:
        """Convert SystemInfo to a dictionary."""
        return asdict(info)

    def to_json(self, info: SystemInfo, indent: int = 2) -> str:
        """Convert SystemInfo to JSON string."""
        return json.dumps(self.to_dict(info), indent=indent)


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Collect macOS system information"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "yaml"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress messages"
    )

    args = parser.parse_args()

    collector = MacSystemInfoCollector()

    if not args.quiet:
        print("Collecting system information...", file=__import__("sys").stderr)

    info = collector.collect_all()

    if args.format == "yaml":
        try:
            import yaml
            output = yaml.dump(collector.to_dict(info), default_flow_style=False)
        except ImportError:
            print("PyYAML not installed. Use: pip install pyyaml", file=__import__("sys").stderr)
            return 1
    else:
        output = collector.to_json(info)

    if args.output:
        Path(args.output).write_text(output)
        if not args.quiet:
            print(f"Output written to {args.output}", file=__import__("sys").stderr)
    else:
        print(output)

    if info.errors and not args.quiet:
        print(f"\nWarnings: {len(info.errors)} issues encountered", file=__import__("sys").stderr)
        for error in info.errors:
            print(f"  - {error}", file=__import__("sys").stderr)

    return 0


if __name__ == "__main__":
    exit(main())
