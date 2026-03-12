# Operations Documentation Generator

A toolkit for generating comprehensive, actionable operations documentation for macOS and Linux systems. Stop forgetting how your systems are configured. Start having runbooks that actually help when things break.

## The Problem

You have multiple machines—a Mac mini running services, a Linux server hosting containers, a laptop for development. Each one is configured differently. Each one has services you set up months ago and have since forgotten about.

Then something breaks.

You SSH in and wonder: *What's even running on this machine? Where are the logs? What's that process listening on port 7001?*

You dig through browser history, old notes, half-remembered terminal commands. You find a Stack Overflow answer that doesn't quite match your setup. An hour later, you've fixed the problem but learned nothing permanent.

**This project fixes that.**

It generates an `Operations.md` file for each of your systems—a single document that captures:

- What hardware you're running
- What services are active and how to restart them
- What ports are listening and why
- Where the config files live
- How to check logs
- Common troubleshooting steps

The documentation is generated from actual system data, not memory. It uses platform-native commands—no mental translation required.

## Supported Platforms

| Platform | Collector Script | Tests |
|----------|-----------------|-------|
| macOS | `mac_system_info.py` | 25 |
| Linux (Debian/Ubuntu/Pop!_OS) | `linux_system_info.py` | 22 |

## What You Get

```
Operations.md
├── Quick Reference (status checks, logs, restarts)
├── Architecture Overview (visual map + port table)
├── Services (Homebrew/systemd, launchd, Docker)
├── Hardware Specifications
├── Disk Layout & Usage
├── Network Configuration
├── Listening Ports
├── Scheduled Tasks
├── Remote Access Setup
├── Troubleshooting Guide
├── Configuration Locations
├── Backup Recommendations
├── Known Issues
└── Changelog
```

Every section contains real data from your system. Every command is copy-paste ready.

## Installation

```bash
# Clone the repository
git clone https://github.com/CaptainMcCrank/OperationsDiscoveryMechanism.git
cd OperationsDiscoveryMechanism

# No dependencies required - uses Python 3 standard library only
python3 --version  # Requires Python 3.9+
```

That's it. No pip install, no virtual environments, no dependency hell.

## Quick Start

### macOS

```bash
# Collect system data
python3 mac_system_info.py -o system_info.json

# Generate Operations.md
python3 generate_operations.py

# Or do both with one command
python3 generate_operations.py -o Operations.md
```

### Linux

```bash
# Collect system data
python3 linux_system_info.py -o system_info.json

# Preview the collected data
python3 linux_system_info.py | less

# Save to a specific location
python3 linux_system_info.py -o ~/ops/$(hostname)-info.json
```

> **Note:** The `generate_operations.py` renderer currently uses macOS command conventions. For Linux systems, collect data with `linux_system_info.py` and use Claude to render platform-appropriate documentation (see AI-Assisted section below).

## Platform-Specific Commands

### macOS Data Collection

| Category | Commands Used |
|----------|--------------|
| Hardware | `system_profiler SPHardwareDataType` |
| Disk | `diskutil list`, `df -h` |
| Network | `ifconfig`, `scutil --dns` |
| Services | `brew services list`, `launchctl list` |
| Ports | `lsof -iTCP -sTCP:LISTEN` |
| Logs | `log show --predicate` |

### Linux Data Collection

| Category | Commands Used |
|----------|--------------|
| Hardware | `hostnamectl`, `lscpu`, `free -h` |
| Disk | `lsblk`, `df -h` |
| Network | `ip addr`, `ip route`, `/etc/resolv.conf` |
| Services | `systemctl list-units` |
| Ports | `ss -tlnp` |
| Logs | `journalctl` |

## AI-Assisted Documentation (Claude Code)

For richer documentation with context-aware descriptions, use Claude Code with the collected JSON. This approach lets you add explanations, document service purposes, and capture institutional knowledge that scripts can't infer.

**Important:** Always collect data with the script first, then give Claude the structured output. This ensures:
- **Consistency**: The tested, idempotent script gathers data the same way every time
- **Efficiency**: No tokens spent on command execution and output parsing
- **Reliability**: No risk of the agent using unconventional tools or missing data sources

### The Prompt

**Step 1: Collect data (run this first)**

```bash
# macOS
python3 mac_system_info.py -o system_info.json

# Linux
python3 linux_system_info.py -o system_info.json
```

**Step 2: Use this prompt in Claude Code**

```
Read the system information from system_info.json and the template structure from operations-template.md.

Generate an Operations.md file that:
1. Populates every section with the real data from system_info.json
2. Uses platform-appropriate commands:
   - macOS: brew services, launchctl, lsof, diskutil, log show, caffeinate
   - Linux: systemctl, journalctl, ss, lsblk, ip
3. Adds contextual descriptions where you can infer purpose (e.g., "nginx on port 80 - web server")
4. Flags potential issues in the Known Issues section (high disk usage, etc.)
5. Includes copy-paste ready commands for every operational task

If a section has no applicable data (e.g., no Docker containers), keep the section header with a note that it's not currently in use.

Write the completed Operations.md to the current directory.
```

---

**Step 3 (optional): Add institutional knowledge**

After the initial generation, follow up with context the script can't capture:

```
Update Operations.md with this additional context:
- The PostgreSQL database stores [describe what]
- The backup script at /usr/local/bin/backup.sh runs nightly and writes to [location]
- Port 8080 is used by [project name] during development
- [Add any other context about why services exist]
```

---

### When to Use Each Option

| Scenario | Recommended Approach |
|----------|---------------------|
| Quick documentation refresh | Script only |
| Routine updates | Script only |
| CI/CD or automated documentation | Script only |
| Adding context about *why* services exist | Script + Claude |
| First-time deep documentation with explanations | Script + Claude |
| Troubleshooting using collected data | Script + Claude |

**Why use Claude at all if the script collects data?**

The collector produces accurate, structured JSON. Claude adds value when you need:

- **Institutional knowledge**: "This Redis instance caches session data for the web app"
- **Inferred relationships**: "Port 3000 (Node) talks to port 5432 (Postgres)"
- **Custom troubleshooting**: Problems specific to your setup
- **Interactive exploration**: "What's using the most disk space and can I delete it?"
- **Platform-appropriate rendering**: Convert JSON to markdown with the right commands

For pure data collection, the Python script is faster and deterministic. Use Claude when you need interpretation, not just transcription.

## Reading Operations.md Effectively

A 500-line operations document is only useful if you can find what you need in 10 seconds. Here's how to navigate it.

### Use Markdown Preview

Don't read Operations.md as raw text. Use a markdown viewer:

```bash
# VS Code
code Operations.md  # Use Cmd+Shift+V (Mac) or Ctrl+Shift+V (Linux) for preview

# Terminal-based
# macOS: brew install glow
# Linux: sudo apt install glow (or snap install glow)
glow Operations.md

# Or use GitHub/GitLab's web interface
```

### Navigation Patterns

**"Something is broken right now"**
→ Jump to **Quick Reference** at the top. Copy-paste the status check command.

**"What's using port 8080?"**
→ Search for `## Listening Ports`. Find the process. Check the Components table for context.

**"How do I restart the thing?"**
→ Search for the service name. Each service section has a Quick Commands block.

**"What's this machine even for?"**
→ Read the **Architecture Overview** diagram and Components table.

**"Where's the config file?"**
→ Jump to **Configuration Locations** table.

### Markdown Structure as Navigation

The document uses consistent heading levels:

```
# Title                    ← One per document
## Major Section           ← Use Cmd+F / Ctrl+F to jump between these
### Subsection             ← Details within a section
#### Problem Title         ← Troubleshooting entries
```

In VS Code or any editor with outline view, you can see all `##` headings at a glance and click to jump.

### Quick Search Patterns

| To find... | Search for... |
|------------|---------------|
| Any service | Service name (e.g., `postgres`, `nginx`) |
| Port information | `:8080` or `Port` |
| How to restart | `restart` |
| Log locations | `log` or `logs` |
| Disk space | `df -h` or `Disk` |
| Network config | `192.` or `Network` |

## Project Structure

```
OperationsDiscoveryMechanism/
├── README.md                    # This file
├── operations-template.md       # Template structure (for reference)
├── mac_system_info.py          # macOS data collector
├── linux_system_info.py        # Linux data collector
├── generate_operations.py       # Markdown renderer (macOS-focused)
├── test_mac_system_info.py     # macOS collector tests (25 tests)
├── test_linux_system_info.py   # Linux collector tests (22 tests)
├── test_generate_operations.py # Renderer tests (26 tests)
├── todo.txt                    # Project roadmap
└── Operations.md               # Generated output (gitignored)
```

## Advanced Usage

### Save System Info as JSON

Useful for comparing systems or debugging:

```bash
# macOS
python3 mac_system_info.py -o macos_info.json

# Linux
python3 linux_system_info.py -o linux_info.json

# Compare two systems
diff <(jq -S . mac1.json) <(jq -S . mac2.json)
```

### Run Tests

```bash
# All tests
python3 -m unittest discover -v

# macOS collector tests
python3 -m unittest test_mac_system_info -v

# Linux collector tests
python3 -m unittest test_linux_system_info -v

# Renderer tests
python3 -m unittest test_generate_operations -v
```

### Extending the Collectors

To add a new data source:

1. Add a collection method:
   ```python
   def collect_new_thing(self) -> list[dict]:
       returncode, stdout, stderr = self.runner.run(["your", "command"])
       # Parse and return structured data
   ```

2. Call it in `collect_all()` and add to the `SystemInfo` dataclass

3. Add tests for the parser

4. Update the renderer if needed

## Multi-Machine Setup

For managing multiple systems:

```
~/Documentation/
├── machines/
│   ├── mac-mini/
│   │   ├── Operations.md
│   │   └── system_info.json
│   ├── linux-server/
│   │   ├── Operations.md
│   │   └── system_info.json
│   └── dev-laptop/
│       ├── Operations.md
│       └── system_info.json
└── OperationsDiscoveryMechanism/   # This repo (shared tools)
```

Generate docs for each machine:

```bash
# On macOS
python3 mac_system_info.py -o ../machines/$(hostname -s)/system_info.json

# On Linux
python3 linux_system_info.py -o ../machines/$(hostname -s)/system_info.json
```

## Philosophy

**Document what you'll forget.** You won't forget that you have a server. You will forget which systemd unit runs that backup script.

**Commands over prose.** "Check if PostgreSQL is running" is less useful than `systemctl status postgresql`.

**Structure enables scanning.** Consistent sections mean you learn the document shape once, then navigate by muscle memory.

**Generate, don't maintain.** Manual documentation rots. Generated documentation can be refreshed in seconds.

**Good enough beats perfect.** A rough Operations.md that exists beats a detailed runbook you'll write someday.

## Contributing

Issues and PRs welcome. Please include tests for new functionality.

## License

MIT
