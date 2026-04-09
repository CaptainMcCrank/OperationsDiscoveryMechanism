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
| Linux (Debian/Ubuntu/Pop!_OS) | `linux_system_info.py` | 22+ |

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

# Generate Operations.md (signed with GPG by default)
python3 generate_operations.py
# Produces: Operations.md + Operations.md.asc

# Or do both with one command
python3 generate_operations.py -o Operations.md

# Skip signing (CI/testing without GPG)
python3 generate_operations.py -o Operations.md --no-sign

# Verify an existing document
python3 generate_operations.py --verify Operations.md
```

### Linux

```bash
# Collect system data and generate Operations.md (one step)
python3 generate_operations.py -o Operations.md --no-sign

# Or collect and generate separately
python3 linux_system_info.py -o system_info.json
python3 generate_operations.py --json system_info.json -o Operations.md --no-sign
```

> **Note:** The `linux_system_info.py` collector tries `sudo -n ss -tlnp` first to get full process visibility for all listening ports. Without sudo, ports owned by other users (e.g., nginx running as root) will show up but without process names. To enable this, ensure the collecting user has passwordless sudo for `ss`, or run the collector as root.

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
| Ports | `sudo -n ss -tlnp` (falls back to `ss -tlnp`) |
| Logs | `journalctl` |

> **Port detection note:** Without sudo, `ss -tlnp` only shows process names for ports owned by the current user. Services like nginx (root/www-data) or sshd (root) will appear as listening ports but without process identification. The collector tries non-interactive `sudo -n` first for full visibility, falling back gracefully if unavailable.

## AI-Assisted Documentation (Claude Code)

The renderer (`generate_operations.py`) now handles both macOS and Linux natively, auto-detecting the platform from the collected JSON. For most use cases, the script is all you need.

However, for richer documentation with context-aware descriptions, you can also use Claude Code with the collected JSON. This approach lets you add explanations, document service purposes, and capture institutional knowledge that scripts can't infer.

**Important:** Always collect data with the script first, then give Claude the structured output. This ensures:
- **Consistency**: The tested, idempotent script gathers data the same way every time
- **Efficiency**: No tokens spent on command execution and output parsing
- **Reliability**: No risk of the agent using unconventional tools or missing data sources

### The Prompt

**Step 1: Collect and generate (run this first)**

```bash
# One-step: collect data and generate Operations.md
python3 generate_operations.py -o Operations.md --no-sign

# Or two-step: collect separately, then render
python3 mac_system_info.py -o system_info.json   # macOS
python3 linux_system_info.py -o system_info.json  # Linux
python3 generate_operations.py --json system_info.json -o Operations.md --no-sign
```

**Step 2 (optional): Use Claude Code to enrich the documentation**

```
Read system_info.json and the generated Operations.md.

Enhance the document by:
1. Adding contextual descriptions for each service (e.g., "nginx reverse-proxies to the Flask app on :5000")
2. Documenting relationships between services
3. Adding environment-specific troubleshooting steps
4. Flagging any security or operational concerns you notice

Keep all existing data and commands intact — only add context.
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

**Why use Claude at all if the script generates docs automatically?**

The renderer produces accurate, platform-appropriate Operations.md. Claude adds value when you need:

- **Institutional knowledge**: "This Redis instance caches session data for the web app"
- **Inferred relationships**: "Port 3000 (Node) talks to port 5432 (Postgres)"
- **Custom troubleshooting**: Problems specific to your setup
- **Interactive exploration**: "What's using the most disk space and can I delete it?"

For pure data collection and rendering, the Python scripts are faster and deterministic. Use Claude when you need interpretation, not just transcription.

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

## Document Signing

Operations.md files are GPG-signed to protect against tampering. After generation, a detached signature (`Operations.md.asc`) is created alongside the document.

### How It Works

Signing is **on by default** when generating via the Python script:

```bash
# Generate and sign (default)
python3 generate_operations.py -o Operations.md

# Skip signing (CI/testing without GPG)
python3 generate_operations.py -o Operations.md --no-sign
```

### Verifying a Document

```bash
# Verify using the script
python3 generate_operations.py --verify Operations.md

# Or verify directly with gpg
gpg --verify Operations.md.asc Operations.md
```

Three outcomes:
- **VALID** — Signature matches. Proceed normally.
- **UNSIGNED** — No `.asc` file found. The document may pre-date signing or may have been tampered with. Treat with reduced confidence.
- **INVALID** — Signature exists but verification failed. The document may have been modified after signing. Do not trust.

### Graceful Degradation

If `gpg` is not installed or no secret key is available, the script warns but does not fail. Signing is best-effort — the document is always written regardless.

### For AI Agents

When an agent (Claude Code or similar) reads an Operations.md, it should check for a `.asc` file and verify the signature before trusting the contents. This prevents agents from acting on tampered or forged documents. See the verification flow in `operations-template.md`.

## Project Structure

```
OperationsDiscoveryMechanism/
├── README.md                    # This file
├── operations-template.md       # Template structure (for reference)
├── mac_system_info.py          # macOS data collector
├── linux_system_info.py        # Linux data collector
├── generate_operations.py       # Markdown renderer (auto-detects platform)
├── test_mac_system_info.py     # macOS collector tests (25 tests)
├── test_linux_system_info.py   # Linux collector tests (22 tests)
├── test_generate_operations.py # Renderer tests (56 tests, macOS + Linux)
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

## Cross-Host Workflow (Collect Remotely, Render Locally)

Not every target system needs Python installed, or you may prefer to manage all documentation from a single workstation. The two-stage architecture (collect → render) supports this naturally because:

1. **Collection** only needs the platform-specific collector script and Python 3.9+
2. **Rendering** only needs the JSON output — it auto-detects the platform from the data

### Step 1: Deploy the collector to the target

Copy only the collector script the target needs. No other files are required:

```bash
# For a Linux target
scp linux_system_info.py user@target-host:~/

# For a macOS target
scp mac_system_info.py user@target-host:~/
```

### Step 2: Collect data on the target

```bash
# SSH in and run the collector
ssh user@target-host "python3 ~/linux_system_info.py -o ~/system_info.json"
```

For full port visibility on Linux, the collecting user should have passwordless sudo for `ss`. Add this to `/etc/sudoers.d/operations-discovery` on the target:

```
username ALL=(ALL) NOPASSWD: /usr/bin/ss
```

### Step 3: Pull the JSON back to your workstation

```bash
scp user@target-host:~/system_info.json ./machines/target-host/system_info.json
```

### Step 4: Render locally

The renderer auto-detects the platform from the JSON data (via the `platform` field or by inspecting which service keys are present):

```bash
python3 generate_operations.py --json ./machines/target-host/system_info.json \
    -o ./machines/target-host/Operations.md --no-sign
```

### One-liner for remote collection

Combine steps 2–4 into a single command:

```bash
# Collect on remote host and render locally
ssh user@target-host "python3 ~/linux_system_info.py" > machines/target-host/system_info.json \
    && python3 generate_operations.py --json machines/target-host/system_info.json \
       -o machines/target-host/Operations.md --no-sign
```

### Script to refresh all machines

```bash
#!/bin/bash
# refresh-all-docs.sh — Collect from all targets, render locally

declare -A HOSTS=(
    ["web-server"]="pi@webserver.local"
    ["dev-laptop"]="user@dev.local"
    # Add more hosts here
)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for name in "${!HOSTS[@]}"; do
    host="${HOSTS[$name]}"
    dir="machines/$name"
    mkdir -p "$dir"
    echo "Collecting from $name ($host)..."
    ssh "$host" "python3 ~/linux_system_info.py" > "$dir/system_info.json" 2>/dev/null \
        || ssh "$host" "python3 ~/mac_system_info.py" > "$dir/system_info.json" 2>/dev/null
    python3 "$SCRIPT_DIR/generate_operations.py" --json "$dir/system_info.json" \
        -o "$dir/Operations.md" --no-sign --quiet
    echo "  → $dir/Operations.md"
done
```

### When to use cross-host vs. local

| Scenario | Approach |
|----------|----------|
| Target has Python 3.9+ and you can SSH in | Run everything on the target |
| Target is minimal (no Python, embedded, IoT) | Copy collector, collect, pull JSON, render locally |
| You want centralized documentation management | Cross-host: collect everywhere, render on your workstation |
| CI/CD automated doc generation | Local on each host, commit to a shared repo |
| Target is air-gapped or access-restricted | Copy collector via USB, run, copy JSON out, render elsewhere |

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
