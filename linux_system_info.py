#!/usr/bin/env python3
"""
linux_system_info.py - Idempotent Linux system information gatherer

Collects hardware, disk, network, services, and configuration data
from a Linux system. Safe to run multiple times with consistent results.

Usage:
    python linux_system_info.py                    # Print JSON to stdout
    python linux_system_info.py --output info.json # Write to file
    python linux_system_info.py --format yaml      # Output as YAML (requires PyYAML)
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
    hostname: str = ""
    os_name: str = ""
    os_version: str = ""
    kernel: str = ""
    architecture: str = ""
    cpu_model: str = ""
    cpu_cores: str = ""
    cpu_threads: str = ""
    memory_total: str = ""
    memory_available: str = ""
    virtualization: str = ""


@dataclass
class DiskPartition:
    name: str = ""
    size: str = ""
    type: str = ""
    mountpoint: str = ""
    fstype: str = ""


@dataclass
class DiskUsage:
    filesystem: str = ""
    size: str = ""
    used: str = ""
    available: str = ""
    use_percent: str = ""
    mount_point: str = ""


@dataclass
class DiskInfo:
    partitions: list = field(default_factory=list)
    usage: list = field(default_factory=list)


@dataclass
class NetworkInterface:
    name: str = ""
    state: str = ""
    ipv4_address: str = ""
    ipv6_address: str = ""
    mac_address: str = ""


@dataclass
class DNSResolver:
    nameservers: list = field(default_factory=list)
    search_domains: list = field(default_factory=list)


@dataclass
class NetworkInfo:
    interfaces: list = field(default_factory=list)
    dns: dict = field(default_factory=dict)
    hostname: str = ""
    default_gateway: str = ""


@dataclass
class SystemdService:
    unit: str = ""
    load: str = ""
    active: str = ""
    sub: str = ""
    description: str = ""


@dataclass
class DockerContainer:
    name: str = ""
    status: str = ""
    ports: str = ""


@dataclass
class ListeningPort:
    protocol: str = ""
    local_address: str = ""
    process: str = ""
    pid: str = ""


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
    systemd_services: list = field(default_factory=list)
    docker_containers: list = field(default_factory=list)
    listening_ports: list = field(default_factory=list)
    cron_jobs: list = field(default_factory=list)
    config_files: list = field(default_factory=list)
    platform: str = "linux"
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


class LinuxSystemInfoCollector:
    """Collects system information from a Linux system."""

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
        info.systemd_services = self.collect_systemd_services()
        info.docker_containers = self.collect_docker_containers()
        info.listening_ports = self.collect_listening_ports()
        info.cron_jobs = self.collect_cron_jobs()
        info.config_files = self.collect_config_files()
        info.errors = self.errors.copy()

        return info

    def collect_hardware(self) -> HardwareInfo:
        """Collect hardware information using hostnamectl, lscpu, and free."""
        hw = HardwareInfo()

        # Get hostname and OS info from hostnamectl
        returncode, stdout, stderr = self.runner.run(["hostnamectl"])
        if returncode == 0:
            for line in stdout.splitlines():
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if "static hostname" in key:
                        hw.hostname = value
                    elif "operating system" in key:
                        hw.os_name = value
                    elif "kernel" in key:
                        hw.kernel = value
                    elif "architecture" in key:
                        hw.architecture = value
                    elif "virtualization" in key:
                        hw.virtualization = value
        else:
            self.errors.append(f"hostnamectl failed: {stderr}")

        # Get CPU info from lscpu
        returncode, stdout, stderr = self.runner.run(["lscpu"])
        if returncode == 0:
            for line in stdout.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "model name":
                        hw.cpu_model = value
                    elif key == "cpu(s)":
                        hw.cpu_threads = value
                    elif key == "core(s) per socket":
                        cores = value
                    elif key == "socket(s)":
                        sockets = value
            
            # Calculate total cores
            try:
                if 'cores' in dir() and 'sockets' in dir():
                    hw.cpu_cores = str(int(cores) * int(sockets))
            except:
                pass
        else:
            self.errors.append(f"lscpu failed: {stderr}")

        # Get memory info from free
        returncode, stdout, stderr = self.runner.run(["free", "-h"])
        if returncode == 0:
            lines = stdout.splitlines()
            for line in lines:
                if line.startswith("Mem:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        hw.memory_total = parts[1]
                    if len(parts) >= 7:
                        hw.memory_available = parts[6]
        else:
            self.errors.append(f"free failed: {stderr}")

        # Get OS version from /etc/os-release
        returncode, stdout, stderr = self.runner.run(["cat", "/etc/os-release"])
        if returncode == 0:
            for line in stdout.splitlines():
                if line.startswith("VERSION="):
                    hw.os_version = line.split("=", 1)[1].strip('"')
                    break

        return hw

    def collect_disk(self) -> DiskInfo:
        """Collect disk layout and usage information."""
        disk_info = DiskInfo()

        # Get partition layout with lsblk
        returncode, stdout, stderr = self.runner.run([
            "lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE", "-n"
        ])
        if returncode == 0:
            disk_info.partitions = self._parse_lsblk(stdout)
        else:
            self.errors.append(f"lsblk failed: {stderr}")

        # Get disk usage with df -h
        returncode, stdout, stderr = self.runner.run(["df", "-h"])
        if returncode == 0:
            disk_info.usage = self._parse_df_output(stdout)
        else:
            self.errors.append(f"df -h failed: {stderr}")

        return disk_info

    def _parse_lsblk(self, output: str) -> list[dict]:
        """Parse lsblk output into structured data."""
        partitions = []
        
        for line in output.splitlines():
            # Remove tree characters
            clean_line = re.sub(r'^[├└│─\s]+', '', line)
            parts = clean_line.split(None, 4)
            
            if len(parts) >= 3:
                partitions.append(asdict(DiskPartition(
                    name=parts[0],
                    size=parts[1] if len(parts) > 1 else "",
                    type=parts[2] if len(parts) > 2 else "",
                    mountpoint=parts[3] if len(parts) > 3 else "",
                    fstype=parts[4] if len(parts) > 4 else "",
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
                # Handle mount points with spaces
                mount = " ".join(parts[5:]) if len(parts) > 6 else parts[5]
                usage.append(asdict(DiskUsage(
                    filesystem=parts[0],
                    size=parts[1],
                    used=parts[2],
                    available=parts[3],
                    use_percent=parts[4],
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

        # Get interface info with ip addr
        returncode, stdout, stderr = self.runner.run(["ip", "-o", "addr"])
        if returncode == 0:
            net_info.interfaces = self._parse_ip_addr(stdout)
        else:
            self.errors.append(f"ip addr failed: {stderr}")

        # Get default gateway
        returncode, stdout, stderr = self.runner.run(["ip", "route", "show", "default"])
        if returncode == 0 and stdout.strip():
            parts = stdout.split()
            if len(parts) >= 3:
                net_info.default_gateway = parts[2]

        # Get DNS info from /etc/resolv.conf
        returncode, stdout, stderr = self.runner.run(["cat", "/etc/resolv.conf"])
        if returncode == 0:
            net_info.dns = self._parse_resolv_conf(stdout)
        else:
            self.errors.append(f"resolv.conf read failed: {stderr}")

        return net_info

    def _parse_ip_addr(self, output: str) -> list[dict]:
        """Parse ip -o addr output into structured data."""
        interfaces = {}
        
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                iface_name = parts[1]
                addr_type = parts[2]  # inet or inet6
                address = parts[3].split('/')[0]
                
                if iface_name not in interfaces:
                    interfaces[iface_name] = NetworkInterface(name=iface_name)
                
                if addr_type == "inet":
                    interfaces[iface_name].ipv4_address = address
                elif addr_type == "inet6":
                    interfaces[iface_name].ipv6_address = address

        return [asdict(iface) for iface in interfaces.values()]

    def _parse_resolv_conf(self, output: str) -> dict:
        """Parse /etc/resolv.conf into structured data."""
        dns = DNSResolver()
        
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("nameserver"):
                parts = line.split()
                if len(parts) >= 2:
                    dns.nameservers.append(parts[1])
            elif line.startswith("search"):
                dns.search_domains = line.split()[1:]

        return asdict(dns)

    def collect_systemd_services(self) -> list[dict]:
        """Collect systemd services (running only for brevity)."""
        returncode, stdout, stderr = self.runner.run([
            "systemctl", "list-units", "--type=service", "--state=running",
            "--no-pager", "--no-legend"
        ])

        if returncode != 0:
            self.errors.append(f"systemctl failed: {stderr}")
            return []

        services = []
        for line in stdout.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 4:
                services.append(asdict(SystemdService(
                    unit=parts[0],
                    load=parts[1],
                    active=parts[2],
                    sub=parts[3],
                    description=parts[4] if len(parts) > 4 else "",
                )))

        return services

    def collect_docker_containers(self) -> list[dict]:
        """Collect running Docker containers."""
        returncode, stdout, stderr = self.runner.run([
            "docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"
        ])

        if returncode != 0:
            # Docker not running is not an error
            if "cannot connect" not in stderr.lower() and "command not found" not in stderr.lower():
                if "permission denied" not in stderr.lower():
                    self.errors.append(f"docker ps failed: {stderr}")
            return []

        containers = []
        for line in stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 1 and parts[0]:
                containers.append(asdict(DockerContainer(
                    name=parts[0],
                    status=parts[1] if len(parts) > 1 else "",
                    ports=parts[2] if len(parts) > 2 else "",
                )))

        return containers

    def collect_listening_ports(self) -> list[dict]:
        """Collect listening TCP/UDP ports using ss.

        Tries sudo ss first for full process visibility (processes owned
        by other users like root/www-data are hidden without privileges).
        Falls back to unprivileged ss if sudo is unavailable.
        """
        # Try sudo first — without it, ss only shows processes owned by the current user
        returncode, stdout, stderr = self.runner.run([
            "sudo", "-n", "ss", "-tlnp"
        ])

        if returncode != 0:
            # Fall back to unprivileged ss (partial process info)
            returncode, stdout, stderr = self.runner.run([
                "ss", "-tlnp"
            ])

        if returncode != 0:
            self.errors.append(f"ss failed: {stderr}")
            return []

        ports = []
        lines = stdout.strip().splitlines()

        # Skip header
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 5:
                local_addr = parts[3]
                process_info = parts[5] if len(parts) > 5 else ""

                # Parse process info like users:(("sshd",pid=1234,fd=3))
                process = ""
                pid = ""
                match = re.search(r'\("([^"]+)",pid=(\d+)', process_info)
                if match:
                    process = match.group(1)
                    pid = match.group(2)

                ports.append(asdict(ListeningPort(
                    protocol="tcp",
                    local_address=local_addr,
                    process=process,
                    pid=pid,
                )))

        return ports

    def collect_cron_jobs(self) -> list[str]:
        """Collect crontab entries for current user."""
        returncode, stdout, stderr = self.runner.run(["crontab", "-l"])

        if returncode != 0:
            if "no crontab" not in stderr.lower():
                self.errors.append(f"crontab -l failed: {stderr}")
            return []

        jobs = []
        for line in stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                jobs.append(line)

        return jobs

    def collect_config_files(self) -> list[dict]:
        """Check for common configuration files."""
        home = Path.home()

        config_paths = [
            home / ".ssh" / "config",
            home / ".bashrc",
            home / ".zshrc",
            home / ".profile",
            Path("/etc/hosts"),
            Path("/etc/resolv.conf"),
            home / ".gitconfig",
            Path("/etc/systemd/system"),
            Path("/etc/docker/daemon.json"),
        ]

        configs = []
        for path in config_paths:
            config = ConfigFile(path=str(path))

            if path.exists():
                config.exists = True
                try:
                    if path.is_file():
                        config.size = path.stat().st_size
                        # Read first few lines as preview
                        if config.size < 10000:
                            content = path.read_text(errors="replace")
                            lines = content.splitlines()[:5]
                            config.content_preview = "\n".join(lines)
                    else:
                        config.size = 0  # Directory
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
        description="Collect Linux system information"
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

    collector = LinuxSystemInfoCollector()

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
