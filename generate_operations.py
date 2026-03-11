#!/usr/bin/env python3
"""
generate_operations.py - Generate Operations.md from system information

This script:
1. Collects system information using mac_system_info.py
2. Renders the data into a Markdown operations document
3. Writes the output to Operations.md

Usage:
    python generate_operations.py                     # Generate Operations.md
    python generate_operations.py -o custom.md        # Custom output file
    python generate_operations.py --json info.json    # Use existing JSON instead of collecting
    python generate_operations.py --dry-run           # Preview without writing
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from mac_system_info import MacSystemInfoCollector, SystemInfo


class OperationsRenderer:
    """Renders SystemInfo into Operations.md format."""

    def __init__(self, info: dict):
        """
        Initialize renderer with system info dictionary.

        Args:
            info: Dictionary from MacSystemInfoCollector.to_dict()
        """
        self.info = info
        self.lines: list[str] = []

    def render(self) -> str:
        """Render the full Operations.md document."""
        self.lines = []

        self._render_header()
        self._render_quick_reference()
        self._render_architecture()
        self._render_services()
        self._render_hardware()
        self._render_disk()
        self._render_standard_operations()
        self._render_scheduled_tasks()
        self._render_remote_access()
        self._render_troubleshooting()
        self._render_network()
        self._render_listening_ports()
        self._render_config_locations()
        self._render_backup()
        self._render_known_issues()
        self._render_changelog()

        return "\n".join(self.lines)

    def _add(self, text: str = ""):
        """Add a line to the output."""
        self.lines.append(text)

    def _render_header(self):
        """Render document header."""
        hw = self.info.get("hardware", {})
        model = hw.get("model_name", "Mac")
        chip = hw.get("chip", "")
        memory = hw.get("memory", "")

        system_desc = f"{model}"
        if chip:
            system_desc += f" ({chip})"

        self._add(f"# Operations Guide - {model}")
        self._add()
        self._add(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}")
        self._add("**Updated By:** generate_operations.py")
        self._add(f"**System:** {system_desc}, {memory} RAM, macOS")
        self._add()
        self._add("---")
        self._add()

    def _render_quick_reference(self):
        """Render quick reference section."""
        self._add("## Quick Reference")
        self._add()
        self._add("### System Status Check")
        self._add("```bash")
        self._add("# One-liner to check critical services")
        self._add('brew services list && launchctl list | grep -v com.apple | head -10')
        self._add("```")
        self._add()
        self._add("### View Logs")
        self._add("```bash")
        self._add("# System logs (last hour, errors only)")
        self._add("log show --predicate 'eventType == logEvent' --style compact --last 1h | grep -i error")
        self._add()
        self._add("# Specific process logs")
        self._add('log show --predicate \'process == "ProcessName"\' --last 1h')
        self._add()
        self._add("# Real-time system log")
        self._add("log stream --predicate 'eventType == logEvent' --style compact")
        self._add()
        self._add("# Crash logs")
        self._add("ls -lt ~/Library/Logs/DiagnosticReports/ | head -10")
        self._add("```")
        self._add()
        self._add("### Restart Services")
        self._add("```bash")
        self._add("# Homebrew service")
        self._add("brew services restart <service_name>")
        self._add()
        self._add("# Application restart")
        self._add('killall "App Name" && open -a "App Name"')
        self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_architecture(self):
        """Render architecture overview with detected services."""
        self._add("## Architecture Overview")
        self._add()

        # Get primary IP
        interfaces = self.info.get("network", {}).get("interfaces", [])
        primary_ip = "127.0.0.1"
        for iface in interfaces:
            if iface.get("ipv4_address") and not iface["ipv4_address"].startswith("127."):
                primary_ip = iface["ipv4_address"]
                break

        hostname = self.info.get("network", {}).get("hostname", "localhost")

        # Build service boxes from listening ports
        ports = self.info.get("listening_ports", [])
        services_by_process = {}
        for port in ports:
            proc = port.get("process", "unknown")
            if proc not in services_by_process:
                services_by_process[proc] = []
            services_by_process[proc].append(port.get("address", ""))

        self._add("```")
        self._add("                        +------------------------+")
        self._add("                        |      LOCAL NETWORK     |")
        self._add("                        +------------------------+")
        self._add("                                      |")
        self._add("+---------------------------------------------------------------------+")
        self._add(f"|                    {hostname.upper():<40}        |")
        self._add(f"|                    {primary_ip:<40}        |")
        self._add("|                                                                     |")

        # Show top services
        top_services = list(services_by_process.items())[:4]
        if top_services:
            service_line = "|   "
            for proc, addrs in top_services:
                port_str = addrs[0] if addrs else ""
                service_line += f"+{proc[:12]:<12}+  "
            self._add(service_line.ljust(70) + "|")

        self._add("+---------------------------------------------------------------------+")
        self._add("```")
        self._add()

        # Components table
        self._add("**Components:**")
        self._add()
        self._add("| Component | Port | Purpose | Type |")
        self._add("|-----------|------|---------|------|")

        for port in ports[:10]:  # Limit to first 10
            process = port.get("process", "unknown")
            address = port.get("address", "")
            port_num = address.split(":")[-1] if ":" in address else address
            purpose = self._infer_purpose(process)
            self._add(f"| {process} | {port_num} | {purpose} | native |")

        self._add()
        self._add("---")
        self._add()

    def _infer_purpose(self, process: str) -> str:
        """Infer service purpose from process name."""
        purposes = {
            "ARDAgent": "Apple Remote Desktop",
            "ControlCe": "AirPlay Receiver",
            "rapportd": "AirDrop/Handoff",
            "nxnode": "NoMachine remote access",
            "nxrunner": "NoMachine session",
            "nxserver": "NoMachine server",
            "node": "Node.js application",
            "python": "Python application",
            "postgres": "PostgreSQL database",
            "redis": "Redis cache",
            "nginx": "Web server",
            "httpd": "Apache web server",
            "Code": "VS Code dev server",
        }
        for key, value in purposes.items():
            if key.lower() in process.lower():
                return value
        return "Application service"

    def _render_services(self):
        """Render services sections."""
        # Homebrew services
        brew_services = self.info.get("homebrew_services", [])
        if brew_services:
            self._add("## Homebrew Services")
            self._add()
            self._add("| Service | Status | User | Plist |")
            self._add("|---------|--------|------|-------|")
            for svc in brew_services:
                self._add(f"| {svc.get('name', '')} | {svc.get('status', '')} | {svc.get('user', '')} | {svc.get('file', '')[:30]} |")
            self._add()
            self._add("### Quick Commands")
            self._add()
            self._add("```bash")
            self._add("# List all Homebrew services")
            self._add("brew services list")
            self._add()
            self._add("# Start/stop/restart a service")
            self._add("brew services start <service>")
            self._add("brew services stop <service>")
            self._add("brew services restart <service>")
            self._add("```")
            self._add()
            self._add("---")
            self._add()

        # Launchd services
        launchd_services = self.info.get("launchd_services", [])
        if launchd_services:
            self._add("## Active Applications (launchd)")
            self._add()
            self._add("Non-Apple services currently registered:")
            self._add()
            self._add("| PID | Label | Status |")
            self._add("|-----|-------|--------|")
            for svc in launchd_services[:15]:  # Limit display
                pid = svc.get("pid", "-")
                label = svc.get("label", "")
                status = svc.get("status", "")
                self._add(f"| {pid} | {label} | {status} |")
            self._add()
            self._add("---")
            self._add()

        # Docker containers
        docker = self.info.get("docker_containers", [])
        self._add("## Docker")
        self._add()
        if docker:
            self._add("| Container | Status | Ports |")
            self._add("|-----------|--------|-------|")
            for container in docker:
                self._add(f"| {container.get('name', '')} | {container.get('status', '')} | {container.get('ports', '')} |")
            self._add()
            self._add("### Quick Commands")
            self._add()
            self._add("```bash")
            self._add("docker ps                    # List running containers")
            self._add("docker logs -f <container>   # Follow container logs")
            self._add("docker restart <container>   # Restart container")
            self._add("docker stats                 # Resource usage")
            self._add("```")
        else:
            self._add("**Status:** Not currently running or installed")
            self._add()
            self._add("```bash")
            self._add("# Start Docker Desktop")
            self._add("open -a Docker")
            self._add()
            self._add("# Verify Docker is running")
            self._add("docker info")
            self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_hardware(self):
        """Render hardware specifications."""
        hw = self.info.get("hardware", {})

        self._add("## Hardware Specifications")
        self._add()
        self._add("| Component | Specification |")
        self._add("|-----------|---------------|")
        self._add(f"| **Model** | {hw.get('model_name', 'Unknown')} ({hw.get('model_identifier', '')}) |")
        self._add(f"| **Model Number** | {hw.get('model_number', '')} |")
        self._add(f"| **Chip** | {hw.get('chip', 'Unknown')} |")
        self._add(f"| **Cores** | {hw.get('total_cores', 'Unknown')} |")
        self._add(f"| **RAM** | {hw.get('memory', 'Unknown')} |")
        self._add(f"| **Firmware** | {hw.get('firmware_version', '')} |")
        self._add(f"| **Serial** | {hw.get('serial_number', '')} |")
        self._add()
        self._add("---")
        self._add()

    def _render_disk(self):
        """Render disk layout and usage."""
        disk = self.info.get("disk", {})
        partitions = disk.get("partitions", [])
        usage = disk.get("usage", [])

        self._add("## Disk Layout")
        self._add()

        if partitions:
            self._add("### Partitions")
            self._add()
            self._add("| Device | Name | Size | Type | Identifier |")
            self._add("|--------|------|------|------|------------|")
            for part in partitions:
                self._add(f"| {part.get('device', '')} | {part.get('name', '')} | {part.get('size', '')} | {part.get('type', '')} | {part.get('identifier', '')} |")
            self._add()

        if usage:
            self._add("### Disk Usage")
            self._add()
            self._add("| Mount | Size | Used | Available | Capacity |")
            self._add("|-------|------|------|-----------|----------|")
            for u in usage:
                mount = u.get("mount_point", "")
                # Truncate long mount points
                if len(mount) > 30:
                    mount = "..." + mount[-27:]
                self._add(f"| {mount} | {u.get('size', '')} | {u.get('used', '')} | {u.get('available', '')} | {u.get('capacity', '')} |")
            self._add()

        self._add("### Storage Guidelines")
        self._add()
        self._add("- Keep system disk usage below 80% for optimal performance")
        self._add("- Use external drives for large files, backups, and archives")
        self._add("- Regularly check disk usage with `df -h`")
        self._add()
        self._add("```bash")
        self._add("# Check disk usage")
        self._add("df -h")
        self._add()
        self._add("# Find large files")
        self._add("find ~ -type f -size +500M 2>/dev/null | head -20")
        self._add()
        self._add("# Interactive disk usage analyzer")
        self._add("# brew install ncdu && ncdu /")
        self._add()
        self._add("# APFS container info")
        self._add("diskutil apfs list")
        self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_standard_operations(self):
        """Render standard operations section."""
        self._add("## Standard Operations")
        self._add()
        self._add("### Health Checks")
        self._add()
        self._add("**Automated Health Check:**")
        self._add("```bash")
        self._add('echo "=== Homebrew Services ===" && brew services list')
        self._add('echo "=== Listening Ports ===" && lsof -iTCP -sTCP:LISTEN -P -n | awk \'{print $1, $9}\' | sort -u')
        self._add('echo "=== Disk Space ===" && df -h / 2>/dev/null')
        self._add('echo "=== Memory Pressure ===" && memory_pressure | head -5')
        self._add('echo "=== CPU Load ===" && sysctl -n vm.loadavg')
        self._add("```")
        self._add()
        self._add("**Manual Verification Checklist:**")
        self._add("- [ ] Disk space available: `df -h`")
        self._add("- [ ] Memory not exhausted: `memory_pressure`")
        self._add("- [ ] No zombie processes: `ps aux | grep Z`")
        self._add("- [ ] Key services running: `brew services list`")
        self._add()
        self._add("### Prevent Sleep During Long Operations")
        self._add()
        self._add("```bash")
        self._add("# Prevent sleep indefinitely (Ctrl+C to cancel)")
        self._add("caffeinate")
        self._add()
        self._add("# Prevent sleep for 2 hours")
        self._add("caffeinate -t 7200")
        self._add()
        self._add("# Prevent sleep while a command runs")
        self._add("caffeinate -s long-running-command")
        self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_scheduled_tasks(self):
        """Render scheduled tasks section."""
        cron_jobs = self.info.get("cron_jobs", [])

        self._add("## Scheduled Tasks (Cron)")
        self._add()

        if cron_jobs:
            self._add("| Schedule | Command |")
            self._add("|----------|---------|")
            for job in cron_jobs:
                parts = job.split(None, 5)
                if len(parts) >= 6:
                    schedule = " ".join(parts[:5])
                    command = parts[5][:50] + "..." if len(parts[5]) > 50 else parts[5]
                    self._add(f"| `{schedule}` | {command} |")
                else:
                    self._add(f"| - | {job[:60]} |")
            self._add()
        else:
            self._add("**Status:** No crontab entries for current user")
            self._add()

        self._add("```bash")
        self._add("# View crontab")
        self._add("crontab -l")
        self._add()
        self._add("# Edit crontab")
        self._add("crontab -e")
        self._add()
        self._add("# View launchd scheduled tasks")
        self._add("ls ~/Library/LaunchAgents/")
        self._add("ls /Library/LaunchAgents/")
        self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_remote_access(self):
        """Render remote access section."""
        self._add("## Remote Access")
        self._add()
        self._add("### Overview")
        self._add()

        # Check for NoMachine
        launchd = self.info.get("launchd_services", [])
        has_nomachine = any("nomachine" in s.get("label", "").lower() for s in launchd)

        # Check for ARD
        ports = self.info.get("listening_ports", [])
        has_ard = any("ARD" in p.get("process", "") for p in ports)

        access_methods = []
        if has_nomachine:
            access_methods.append("NoMachine (NX protocol)")
        if has_ard:
            access_methods.append("Apple Remote Desktop / Screen Sharing")
        access_methods.append("SSH (if enabled)")

        self._add(f"Available remote access methods: {', '.join(access_methods)}")
        self._add()

        self._add("### Access Methods")
        self._add()
        self._add("| Method | Port | Best For |")
        self._add("|--------|------|----------|")
        if has_nomachine:
            self._add("| NoMachine | 4000 | Full desktop, development work |")
        if has_ard:
            self._add("| Screen Sharing | 5900 | Quick admin tasks |")
        self._add("| SSH | 22 | Terminal access, scripts |")
        self._add()

        if has_nomachine:
            self._add("### NoMachine Commands")
            self._add()
            self._add("```bash")
            self._add("# Check NoMachine status")
            self._add("launchctl list | grep nomachine")
            self._add()
            self._add("# Restart NoMachine")
            self._add("/etc/NXServer/nxserver --restart")
            self._add()
            self._add("# View NoMachine logs")
            self._add('tail -f /Library/Application\\ Support/NoMachine/var/log/nxserver.log')
            self._add("```")
            self._add()

        self._add("---")
        self._add()

    def _render_troubleshooting(self):
        """Render troubleshooting guide."""
        self._add("## Troubleshooting Guide")
        self._add()
        self._add("### Service Won't Start")
        self._add("```bash")
        self._add("# Check logs for specific process")
        self._add('log show --predicate \'process == "ServiceName"\' --last 1h')
        self._add()
        self._add("# Check disk space")
        self._add("df -h")
        self._add()
        self._add("# Check permissions")
        self._add("ls -la /path/to/service")
        self._add("```")
        self._add()
        self._add("### High Resource Usage")
        self._add("```bash")
        self._add("# Top processes by CPU")
        self._add("ps aux | sort -nrk 3 | head -10")
        self._add()
        self._add("# Top processes by memory")
        self._add("ps aux | sort -nrk 4 | head -10")
        self._add()
        self._add("# Memory pressure")
        self._add("memory_pressure")
        self._add()
        self._add("# System load")
        self._add("sysctl -n vm.loadavg")
        self._add("```")
        self._add()
        self._add("### Application Crashes")
        self._add("```bash")
        self._add("# View recent crash reports")
        self._add("ls -lt ~/Library/Logs/DiagnosticReports/ | head -10")
        self._add()
        self._add("# Read a crash report")
        self._add("cat ~/Library/Logs/DiagnosticReports/AppName_*.crash | head -100")
        self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_network(self):
        """Render network information."""
        net = self.info.get("network", {})
        interfaces = net.get("interfaces", [])
        dns = net.get("dns_resolvers", [])

        self._add("## Network Information")
        self._add()

        if interfaces:
            self._add("| Interface | IP Address | Flags |")
            self._add("|-----------|------------|-------|")
            for iface in interfaces:
                ip = iface.get("ipv4_address", "")
                if ip or "UP" in iface.get("flags", ""):
                    flags = iface.get("flags", "")[:30]
                    self._add(f"| {iface.get('name', '')} | {ip or 'no IP'} | {flags} |")
            self._add()

        self._add(f"**Hostname:** {net.get('hostname', 'unknown')}")
        self._add()

        if dns:
            primary_dns = dns[0] if dns else {}
            nameservers = primary_dns.get("nameservers", [])
            if nameservers:
                self._add(f"**DNS Servers:** {', '.join(nameservers)}")
                self._add()

        self._add("### Network Commands")
        self._add()
        self._add("```bash")
        self._add("# Show all interfaces")
        self._add("ifconfig")
        self._add()
        self._add("# Show routing table")
        self._add("netstat -rn")
        self._add()
        self._add("# DNS lookup")
        self._add("scutil --dns")
        self._add()
        self._add("# Test connectivity")
        self._add("ping -c 4 8.8.8.8")
        self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_listening_ports(self):
        """Render listening ports section."""
        ports = self.info.get("listening_ports", [])

        self._add("## Listening Ports")
        self._add()

        if ports:
            self._add("| Process | User | Address |")
            self._add("|---------|------|---------|")
            for port in ports:
                self._add(f"| {port.get('process', '')} | {port.get('user', '')} | {port.get('address', '')} |")
            self._add()

        self._add("```bash")
        self._add("# Refresh this list")
        self._add("lsof -iTCP -sTCP:LISTEN -P -n | awk '{print $1, $3, $9}' | sort -u")
        self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_config_locations(self):
        """Render configuration locations."""
        configs = self.info.get("config_files", [])

        self._add("## Configuration Locations")
        self._add()
        self._add("| Config | Location | Exists |")
        self._add("|--------|----------|--------|")

        for cfg in configs:
            path = cfg.get("path", "")
            exists = "Yes" if cfg.get("exists", False) else "No"
            name = Path(path).name
            self._add(f"| {name} | `{path}` | {exists} |")

        # Add standard locations
        self._add("| Homebrew | `/opt/homebrew/` | - |")
        self._add("| User LaunchAgents | `~/Library/LaunchAgents/` | - |")
        self._add("| System LaunchDaemons | `/Library/LaunchDaemons/` | - |")
        self._add()
        self._add("---")
        self._add()

    def _render_backup(self):
        """Render backup recommendations."""
        self._add("## Backup Recommendations")
        self._add()
        self._add("**Critical Data to Backup:**")
        self._add("1. Home directory: `~`")
        self._add("2. SSH keys: `~/.ssh/`")
        self._add("3. Development projects: `~/Development/`")
        self._add("4. Application preferences: `~/Library/Preferences/`")
        self._add("5. Homebrew package list")
        self._add()
        self._add("**Backup Commands:**")
        self._add("```bash")
        self._add("# Export Homebrew packages")
        self._add("brew bundle dump --file=~/Brewfile")
        self._add()
        self._add("# Backup SSH keys")
        self._add("cp -r ~/.ssh /path/to/backup/ssh-$(date +%Y%m%d)/")
        self._add()
        self._add("# Create compressed archive of home")
        self._add("tar -czf /path/to/backup/home-$(date +%Y%m%d).tar.gz -C ~ .")
        self._add()
        self._add("# Time Machine backup (if configured)")
        self._add("tmutil startbackup")
        self._add("```")
        self._add()
        self._add("---")
        self._add()

    def _render_known_issues(self):
        """Render known issues section."""
        self._add("## Known Issues")
        self._add()

        # Detect potential issues from collected data
        issues = []

        # Check for NTFS drives
        partitions = self.info.get("disk", {}).get("partitions", [])
        for part in partitions:
            if "NTFS" in part.get("type", "") or "Windows" in part.get("type", ""):
                issues.append({
                    "title": f"External drive '{part.get('name', '')}' is NTFS formatted",
                    "description": "Read-only by default on macOS without additional tools",
                    "workaround": "Install ntfs-3g via Homebrew for write access, or reformat to APFS/exFAT"
                })

        # Check for high disk usage
        usage = self.info.get("disk", {}).get("usage", [])
        for u in usage:
            cap = u.get("capacity", "0%").replace("%", "")
            try:
                if int(cap) > 85:
                    issues.append({
                        "title": f"High disk usage on {u.get('mount_point', '')}",
                        "description": f"Currently at {u.get('capacity', '')} capacity",
                        "workaround": "Review large files with `ncdu` or move data to external storage"
                    })
            except ValueError:
                pass

        if issues:
            for i, issue in enumerate(issues, 1):
                self._add(f"{i}. **{issue['title']}**")
                self._add(f"   - {issue['description']}")
                self._add(f"   - Workaround: {issue['workaround']}")
                self._add()
        else:
            self._add("No known issues detected.")
            self._add()

        self._add("---")
        self._add()

    def _render_changelog(self):
        """Render changelog section."""
        self._add("## Changelog")
        self._add()
        timestamp = self.info.get("collection_timestamp", datetime.now().isoformat())
        date_str = timestamp.split("T")[0] if "T" in timestamp else timestamp[:10]

        self._add(f"### {date_str} - generate_operations.py: Auto-generated")
        self._add("- Created Operations.md from system profiling")

        hw = self.info.get("hardware", {})
        if hw.get("model_name"):
            self._add(f"- Documented hardware specs ({hw.get('model_name')}, {hw.get('chip', '')}, {hw.get('memory', '')})")

        disk = self.info.get("disk", {})
        if disk.get("partitions"):
            self._add(f"- Mapped disk layout ({len(disk['partitions'])} partitions)")

        ports = self.info.get("listening_ports", [])
        if ports:
            self._add(f"- Catalogued {len(ports)} listening ports")

        self._add()
        self._add("---")


def collect_system_info() -> dict:
    """Collect system information and return as dictionary."""
    collector = MacSystemInfoCollector()
    info = collector.collect_all()
    return collector.to_dict(info)


def load_json_info(path: str) -> dict:
    """Load system info from existing JSON file."""
    return json.loads(Path(path).read_text())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Operations.md from system information"
    )
    parser.add_argument(
        "--output", "-o",
        default="Operations.md",
        help="Output file path (default: Operations.md)"
    )
    parser.add_argument(
        "--json", "-j",
        help="Use existing JSON file instead of collecting fresh data"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Print output without writing file"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress messages"
    )

    args = parser.parse_args()

    import sys

    # Get system info
    if args.json:
        if not args.quiet:
            print(f"Loading system info from {args.json}...", file=sys.stderr)
        info = load_json_info(args.json)
    else:
        if not args.quiet:
            print("Collecting system information...", file=sys.stderr)
        info = collect_system_info()

    # Render document
    if not args.quiet:
        print("Rendering Operations.md...", file=sys.stderr)

    renderer = OperationsRenderer(info)
    output = renderer.render()

    # Output
    if args.dry_run:
        print(output)
    else:
        Path(args.output).write_text(output)
        if not args.quiet:
            print(f"Written to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    exit(main())
