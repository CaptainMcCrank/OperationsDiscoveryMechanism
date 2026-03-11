# Mac Operations Documentation Generator

A toolkit for generating comprehensive, actionable operations documentation for macOS systems. Stop forgetting how your systems are configured. Start having runbooks that actually help when things break.

## The Problem

You have multiple Macs—a work machine, a home server, a mini running services in a closet. Each one is configured differently. Each one has services you set up months ago and have since forgotten about.

Then something breaks.

You SSH in and wonder: *What's even running on this machine? Where are the logs? What's that process listening on port 7001?*

You dig through browser history, old notes, half-remembered terminal commands. You find a Stack Overflow answer that doesn't quite match your setup. An hour later, you've fixed the problem but learned nothing permanent.

**This project fixes that.**

It generates an `Operations.md` file for each of your Macs—a single document that captures:

- What hardware you're running
- What services are active and how to restart them
- What ports are listening and why
- Where the config files live
- How to check logs
- Common troubleshooting steps

The documentation is generated from actual system data, not memory. It uses macOS-native commands, not Linux equivalents you'll have to mentally translate.

## What You Get

```
Operations.md
├── Quick Reference (status checks, logs, restarts)
├── Architecture Overview (visual map + port table)
├── Services (Homebrew, launchd, Docker)
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
git clone https://github.com/yourusername/mac-ops-docs.git
cd mac-ops-docs

# No dependencies required - uses Python 3 standard library only
python3 --version  # Requires Python 3.9+
```

That's it. No pip install, no virtual environments, no dependency hell.

## Quick Start

### Option 1: Fully Automated (Python Script)

```bash
# Generate Operations.md for this system
python3 generate_operations.py

# Preview without writing
python3 generate_operations.py --dry-run | less

# Custom output location
python3 generate_operations.py -o ~/Documentation/mini-ops.md
```

### Option 2: AI-Assisted (Claude Code)

For richer documentation with context-aware descriptions, use Claude Code with the collected JSON. This approach lets you add explanations, document service purposes, and capture institutional knowledge that scripts can't infer.

**Important:** Always collect data with the script first, then give Claude the structured output. This ensures:
- **Consistency**: The tested, idempotent script gathers data the same way every time
- **Efficiency**: No tokens spent on command execution and output parsing
- **Reliability**: No risk of the agent using unconventional tools or missing data sources

## The Prompt

**Step 1: Collect data (run this first)**

```bash
python3 mac_system_info.py -o system_info.json
```

**Step 2: Use this prompt in Claude Code**

```
Read the system information from system_info.json and the template structure from operations-template.md.

Generate an Operations.md file that:
1. Populates every section with the real data from system_info.json
2. Follows the macOS command conventions in the template (brew services, launchctl, lsof, diskutil, log show, caffeinate)
3. Adds contextual descriptions where you can infer purpose (e.g., "NoMachine on port 4000 - remote desktop access")
4. Flags potential issues in the Known Issues section (NTFS drives, high disk usage, etc.)
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
| Quick documentation refresh | `generate_operations.py` only |
| Routine updates | `generate_operations.py` only |
| CI/CD or automated documentation | `generate_operations.py` only |
| Adding context about *why* services exist | Script + Claude |
| First-time deep documentation with explanations | Script + Claude |
| Troubleshooting using collected data | Script + Claude |

**Why use Claude at all if the script generates markdown?**

The generator produces accurate, structured documentation. Claude adds value when you need:

- **Institutional knowledge**: "This Redis instance caches session data for the web app"
- **Inferred relationships**: "Port 3000 (Node) talks to port 5432 (Postgres)"
- **Custom troubleshooting**: Problems specific to your setup
- **Interactive exploration**: "What's using the most disk space and can I delete it?"

For pure documentation generation, the Python script is faster and deterministic. Use Claude when you need interpretation, not just transcription.

## Reading Operations.md Effectively

A 500-line operations document is only useful if you can find what you need in 10 seconds. Here's how to navigate it.

### Use Markdown Preview

Don't read Operations.md as raw text. Use a markdown viewer:

```bash
# macOS Quick Look (press spacebar in Finder)
# Works if you have a markdown Quick Look plugin installed

# VS Code
code Operations.md  # Use Cmd+Shift+V for preview

# Terminal-based (install with: brew install glow)
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
## Major Section           ← Use Cmd+F to jump between these
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
mac-ops-docs/
├── README.md                    # This file
├── operations-template.md       # Template structure (for reference)
├── mac_system_info.py          # Data collection module
├── generate_operations.py       # Document generator
├── test_mac_system_info.py     # Collector tests (25 tests)
├── test_generate_operations.py # Generator tests (26 tests)
└── Operations.md               # Generated output (gitignored)
```

## Advanced Usage

### Save System Info as JSON

Useful for comparing systems or debugging the generator:

```bash
# Collect and save raw data
python3 mac_system_info.py -o system_info.json

# Generate from saved data (faster iteration on templates)
python3 generate_operations.py --json system_info.json
```

### Run Tests

```bash
# All tests
python3 -m unittest discover -v

# Just collector tests
python3 -m unittest test_mac_system_info -v

# Just generator tests
python3 -m unittest test_generate_operations -v
```

### Extending the Generator

To add a new section:

1. Add a collection method in `mac_system_info.py`:
   ```python
   def collect_new_thing(self) -> list[dict]:
       returncode, stdout, stderr = self.runner.run(["your", "command"])
       # Parse and return structured data
   ```

2. Call it in `collect_all()` and add to the `SystemInfo` dataclass

3. Add a render method in `generate_operations.py`:
   ```python
   def _render_new_thing(self):
       data = self.info.get("new_thing", [])
       self._add("## New Thing")
       # Render markdown
   ```

4. Call it in `render()`

5. Add tests for both

## Multi-Machine Setup

For managing multiple Macs, consider this structure:

```
~/Documentation/
├── machines/
│   ├── mini-server/
│   │   ├── Operations.md
│   │   └── system_info.json
│   ├── macbook-work/
│   │   ├── Operations.md
│   │   └── system_info.json
│   └── imac-home/
│       ├── Operations.md
│       └── system_info.json
└── mac-ops-docs/              # This repo (shared tools)
```

Generate docs for each machine:

```bash
# On each machine
cd ~/Documentation/mac-ops-docs
python3 generate_operations.py -o ../machines/$(hostname -s)/Operations.md
python3 mac_system_info.py -o ../machines/$(hostname -s)/system_info.json
```

## Philosophy

**Document what you'll forget.** You won't forget that you have a Mac mini. You will forget which LaunchAgent runs that backup script.

**Commands over prose.** "Check if PostgreSQL is running" is less useful than `brew services list | grep postgres`.

**Structure enables scanning.** Consistent sections mean you learn the document shape once, then navigate by muscle memory.

**Generate, don't maintain.** Manual documentation rots. Generated documentation can be refreshed in seconds.

**Good enough beats perfect.** A rough Operations.md that exists beats a detailed runbook you'll write someday.

## Contributing

Issues and PRs welcome. Please include tests for new functionality.

## License

MIT
