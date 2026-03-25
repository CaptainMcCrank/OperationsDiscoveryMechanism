# Operations Guide - [System Name]

**Last Updated:** [Date]
**Updated By:** [Name or tool]
**System:** [Hardware summary]

---

## Quick Reference

### System Status Check
```bash
# One-liner to check all critical services
systemctl status [service1] [service2] [service3] --no-pager | grep -E "Active:|●"
```

### View Logs
```bash
# [Service 1] logs
journalctl -u [service1] -f

# [Service 2] logs (Docker)
docker logs -f [container_name]

# [Service 3] logs
journalctl -u [service3] -f

# Error logs only (last hour)
journalctl -p err --since "1 hour ago" --no-pager
```

### Restart Services
```bash
# [Service 1]
sudo systemctl restart [service1]

# [Service 2] (Docker-based)
sudo systemctl restart [service2]

# [Service 3]
sudo systemctl restart [service3]

# All Docker containers
docker restart [container1] [container2]
```

---

## Architecture Overview

```
                        +------------------------+
                        |      INTERNET          |
                        +------------------------+
                                      |
                        +------------------------+
                        |   [Ingress Method]     |
                        |   [public hostname]    |
                        +------------------------+
                                      |
+---------------------------------------------------------------------+
|                    [SYSTEM NAME]                                     |
|                    [IP Address]                                      |
|                                                                     |
|   +---------------+     +--------------+     +--------------+       |
|   | [Service 1]   |     | [Service 2]  |     | [Service 3]  |       |
|   | :[port]       |     | :[port]      |     | :[port]      |       |
|   | ([type])      |     | ([type])     |     | ([type])     |       |
|   +---------------+     +------+-------+     +--------------+       |
|                                |                                    |
|                         +------+-------+                            |
|                         | [Backend]    |                            |
|                         | :[port]      |                            |
|                         | ([type])     |                            |
|                         +--------------+                            |
+---------------------------------------------------------------------+
```

**Components:**

| Component | Port | Purpose | Type |
|-----------|------|---------|------|
| [Service name] | [port] | [What it does] | systemd / Docker / native |
| [Service name] | [port] | [What it does] | systemd / Docker / native |
| [Service name] | [port] | [What it does] | systemd / Docker / native |

**Data Flow:**
1. [Describe how external requests enter the system]
2. [Describe how internal requests route between services]
3. [Describe how the primary backend processes requests]

---

## [Service Group or Stack Name]

[One or two sentences: what this group of services does and where it lives on disk.]

**Location:** `[path]`

### Services

| Service | URL | Local Port | Container | Purpose |
|---------|-----|------------|-----------|---------|
| [Name] | [URL] | [port] | [container] | [Purpose] |
| [Name] | [URL] | [port] | [container] | [Purpose] |

**Databases:**

| Database | Container | Purpose |
|----------|-----------|---------|
| [Type + version] | [container] | [What it stores] |

### Quick Commands

```bash
# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}" | grep [prefix]

# View logs
docker logs [container] --tail 50

# Restart all services in this group
cd [path] && docker compose restart

# Restart a specific service
cd [path] && docker compose restart [service]

# Force recreate (to apply .env changes)
cd [path] && docker compose up -d --force-recreate [service]
```

### Backup

```bash
# Backup database
docker exec [db_container] [dump_command] | gzip > [backup_path]/[name]_$(date +%Y%m%d).sql.gz
```

### Troubleshooting

#### [Common Problem Title]

1. [First diagnostic step with command]
2. [Second diagnostic step]
3. [Likely fix]

#### [Another Common Problem Title]

1. [First diagnostic step with command]
2. [Second diagnostic step]
3. [Likely fix]

---

<!--
Repeat the section above for each service group or standalone service.
Each section should follow the same pattern:

  ## [Service Name]
  [Description]
  ### Quick Commands (status, logs, restart, start, stop)
  ### Backup
  ### Troubleshooting

Consistency across sections matters more than completeness within any one section.
Once someone reads one section, they know the shape of every other section.
-->

## [Standalone Service Name]

[One or two sentences: what this service does, when it was deployed, and any context about why it exists.]

**Location:** `[path]`
**Public URL:** `[URL]` (if applicable)
**Local URL:** `http://127.0.0.1:[port]`
**Container:** `[container name]` (if Docker)

### Quick Commands

```bash
# Check status
systemctl status [service]

# View logs
journalctl -u [service] -f

# Restart
sudo systemctl restart [service]

# Stop
sudo systemctl stop [service]

# Start
sudo systemctl start [service]

# Verify the service responds
curl -s http://localhost:[port]/[health_endpoint]
```

### Backup

```bash
# Backup data
tar -czf [backup_path]/[service]-data-$(date +%Y%m%d).tar.gz -C [data_path] .

# Backup config
cp [config_path] [backup_path]/[service]-config-$(date +%Y%m%d)
```

### Troubleshooting

#### [Problem Title]

**Symptom:** [What the operator sees]

**Diagnosis:**
```bash
# [Diagnostic command with explanation]
[command]
```

**Root Cause:** [What actually went wrong]

**Fix:**
```bash
# [Fix command with explanation]
[command]
```

---

## Hardware Specifications

| Component | Specification |
|-----------|---------------|
| **Model** | [Model name] |
| **CPU** | [CPU model] |
| **Cores/Threads** | [count] |
| **RAM** | [amount] |
| **Swap** | [amount] |
| **Primary Disk** | [size and type] |
| **GPU** | [model, or "None"] |

---

## Disk Layout

| Mount | Size | Used | Available | Use% |
|-------|------|------|-----------|------|
| / | | | | |
| /home | | | | |
| /boot/efi | | | | |

### Storage Guidelines

Store large application data, models, and backups outside of `/home` if the home partition is small. Document which directories live where and why.

---

## Standard Operations

### Health Checks

**Automated Health Check:**
```bash
# Check all critical services
for svc in [service1] [service2] [service3]; do
  systemctl is-active --quiet $svc && echo "OK $svc" || echo "FAIL $svc"
done

# Check Docker containers
docker ps --format "{{.Names}}: {{.Status}}"

# Check listening ports
ss -tlnp | grep -E ":([port1]|[port2]|[port3]) "
```

**Manual Verification Checklist:**
- [ ] All services running: `systemctl status [service1] [service2] [service3]`
- [ ] Docker containers healthy: `docker ps`
- [ ] Ports listening: `ss -tlnp`
- [ ] Disk space available: `df -h`
- [ ] No errors in logs: `journalctl -p err --since "1 hour ago"`
- [ ] [Primary service] responds: `curl -s localhost:[port]/[endpoint]`

---

## Scheduled Tasks (Cron)

| Schedule | Task | Description |
|----------|------|-------------|
| [cron expression in words] | [task name] | [what it does] |
| [cron expression in words] | [task name] | [what it does] |

```bash
# View crontab
crontab -l

# Edit crontab
crontab -e

# View cron logs
grep CRON /var/log/syslog
```

---

## Ingress / Tunnel / Reverse Proxy

**Configuration:** `[path to config]`

[Describe how traffic enters the system from the internet. Include the configuration if it fits, or reference the file path.]

**Hosted Services:**

| Hostname | Service | Port | Access Control |
|----------|---------|------|----------------|
| [hostname] | [service] | [port] | [auth method or "None"] |
| [hostname] | [service] | [port] | [auth method or "None"] |

**Commands:**
```bash
# Check tunnel/proxy status
systemctl status [tunnel_service]

# View logs
journalctl -u [tunnel_service] -f

# Restart
sudo systemctl restart [tunnel_service]
```

---

## Remote Access

### Overview

[Describe how remote access works, what authentication is required, and which devices can connect.]

### Access Methods

| Method | Device | Connection Target | Best For |
|--------|--------|-------------------|----------|
| [Method] | [Device] | [Target] | [Use case] |
| [Method] | [Device] | [Target] | [Use case] |

### Client Configuration

[Step-by-step setup instructions for each access method, with commands where applicable.]

### Remote Access Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| [What you see] | [Why] | [What to do] |
| [What you see] | [Why] | [What to do] |

---

## Troubleshooting Guide

### Service Won't Start
1. Check logs: `journalctl -u [service] -n 50`
2. Verify dependencies: `systemctl list-dependencies [service]`
3. Check disk space: `df -h`
4. Check permissions: `ls -la [service_path]`

### Docker Container Issues
1. Check container status: `docker ps -a`
2. View container logs: `docker logs [container_name]`
3. Restart container: `docker restart [container_name]`
4. Inspect container: `docker inspect [container_name]`

### High Resource Usage
1. Top processes: `ps aux --sort=-%mem | head -10`
2. Docker stats: `docker stats --no-stream`
3. System load: `uptime`

### [Specific Incident Title]

**Symptom:** [What the operator observes]

**Diagnosis Steps:**
```bash
# [Step 1 with explanation]
[command]

# [Step 2 with explanation]
[command]
```

**Root Cause:** [What caused the problem]

**Fix:**
```bash
# [Fix with explanation]
[command]
```

**Lessons Learned:** [What to check first next time, what wrong turns to skip]

<!--
Add troubleshooting entries as incidents occur.
Organize by symptom, not by cause.
Include the wrong turns: if you spent time investigating the wrong thing
before finding the real cause, document that sequence so future operators
check the right thing first.
-->

---

## Configuration Locations

| Config | Location |
|--------|----------|
| [Service] config | `[path]` |
| [Service] override | `[path]` |
| [Tunnel/proxy] config | `[path]` |
| SSL certificate | `[path]` |
| SSL key | `[path]` |
| Docker volumes | `/var/lib/docker/volumes/` |

---

## Network Information

| Interface | IP Address | Notes |
|-----------|------------|-------|
| [interface] | [IP] | Primary |
| [interface] | [IP or DOWN] | [Notes] |
| docker0 | 172.17.0.1 | Docker bridge |

**Hostname:** [hostname]
**External Access:** [list of public URLs]

---

## Backup Recommendations

**Critical Data to Backup:**
1. Docker volumes: [list volume names]
2. Service configurations: [list paths]
3. Credentials and keys: [list paths]
4. Application data: [list paths]

**Backup Commands:**
```bash
# Backup Docker volumes
docker run --rm -v [volume]:/source -v [backup_dir]:/backup alpine \
  tar czf /backup/[volume]_$(date +%Y%m%d).tar.gz -C /source .

# Backup configs
tar czf [backup_dir]/configs_$(date +%Y%m%d).tar.gz \
  [config_path_1] \
  [config_path_2] \
  [config_path_3]
```

---

## Known Issues

1. **[Issue title]** (since [date])
   - [Description of the issue]
   - [Impact on operations]
   - [Current workaround]

2. **[Issue title]** (since [date])
   - [Description of the issue]
   - [Impact on operations]
   - [Current workaround]

<!--
Be specific. "Disk space is tight" helps nobody.
Document which partition, what its capacity is, what consumes the most space,
and what the procedure is when it fills up.
-->

---

## Document Integrity

This Operations.md is GPG-signed. A detached signature file (`Operations.md.asc`) should exist alongside it. Verify before trusting:

```bash
gpg --verify Operations.md.asc Operations.md
```

Three outcomes:
- **Exit 0** — Signature valid. Proceed normally.
- **Exit non-zero** — Signature INVALID. This document may have been modified after signing. Do NOT trust its contents.
- **No `.asc` file** — Unsigned. This document may pre-date the signing convention, or may have been tampered with. Treat with reduced confidence.

---

## Changelog

### [Date] - [Author]: [Summary]
- [What changed]
- [Why it changed]
- [What was learned in the process]

### [Date] - [Author]: [Summary]
- [What changed]
- [Why it changed]
- [What was learned in the process]

<!--
Update this section during maintenance, not after.
When you add a service, add it to the inventory before moving on.
When you solve a problem, write the entry while details are fresh.
When you discover a constraint, add it to Known Issues immediately.

The emphasis belongs on reasoning. Why a decision was made decays
faster in memory than any other detail. Capture it at the time of the decision.

Format for future entries:
### [Timestamp] - [Author]: [Summary]
-->

---

## Disk Partitioning

| Partition | Size | Type | Mount | Purpose |
|-----------|------|------|-------|---------|
| [partition] | [size] | [type] | [mount] | [purpose] |
| [partition] | [size] | [type] | [mount] | [purpose] |

### Storage Guidelines

- [Rule about where to store large files]
- [Rule about what belongs in /home vs. elsewhere]
- [Any symlink or offloading strategies in use]

```bash
# Check disk usage
df -h
ncdu [path]

# Find large files
find [path] -type f -size +100M 2>/dev/null
```
