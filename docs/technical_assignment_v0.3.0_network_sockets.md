# Linux Runtime Blackbox — Technical Assignment v0.3.0

## Release Theme

**v0.3.0 — Network Socket Enrichment**

The goal of v0.3.0 is to teach Linux Runtime Blackbox to enrich socket file descriptors with human-readable network information.

At the end of the release, reports produced by `blackbox inspect` and `blackbox run` should no longer show sockets only as raw `socket:[inode]` values. The tool should resolve socket inodes through `/proc/net/*` and show protocol, local address, remote address, state, inode, and path for UNIX sockets where available.

This release remains procfs-only. Do not add eBPF, daemon mode, REST API, database, web UI, OpenTelemetry, packet capture, or DNS resolution.

---

## Current State

The project already has:

- `blackbox inspect --pid <pid>` from v0.1.
- `blackbox run -- <command> [args...]` from v0.2.
- JSON and pretty output.
- Procfs collectors for process metadata, resources, file descriptors, mappings, namespaces, and cgroups.
- Best-effort collection model with warnings instead of hard crashes.
- Workload scripts:
  - `scripts/workload_open_files.py`
  - `scripts/workload_children.sh`
  - `scripts/workload_network.py`

Known limitation:

- Socket file descriptors are currently classified at the file-descriptor level only.
- A socket FD appears as something like `socket:[123456]`, but the report does not explain whether it is TCP, UDP, UNIX, listening, established, local, remote, etc.

---

## Main Objective

Implement socket enrichment by mapping socket inode values from `/proc/<pid>/fd/*` to entries in:

- `/proc/net/tcp`
- `/proc/net/tcp6`
- `/proc/net/udp`
- `/proc/net/udp6`
- `/proc/net/unix`

For every FD that points to `socket:[inode]`, the report should attempt to attach structured socket information.

---

## User-Facing Behavior

### Existing commands must keep working

```bash
blackbox inspect --pid <pid>
blackbox inspect --pid <pid> --pretty
blackbox inspect --pid <pid> --output /tmp/report.json

blackbox run -- sleep 1
blackbox run --output /tmp/run-report.json -- sleep 1
```

### Expected pretty output change

Before v0.3.0:

```text
File descriptors (5)
  3 socket       socket:[123456]
```

After v0.3.0:

```text
File descriptors (5)
  3 socket       tcp 127.0.0.1:54322 -> 127.0.0.1:5432 ESTABLISHED inode=123456
```

For listening TCP sockets:

```text
  4 socket       tcp 0.0.0.0:8080 LISTEN inode=123457
```

For UDP sockets:

```text
  5 socket       udp 127.0.0.1:5353 inode=123458
```

For UNIX sockets:

```text
  6 socket       unix STREAM CONNECTED /run/user/1000/bus inode=123459
```

If enrichment fails, the original FD target must still be shown:

```text
  7 socket       socket:[123460] unresolved
```

---

## Report Model Changes

Extend the FD model with an optional socket details structure.

Suggested model:

```go
type FileDescriptor struct {
    FD      int            `json:"fd"`
    Type    string         `json:"type"`
    Target  string         `json:"target"`
    Socket  *SocketDetails `json:"socket,omitempty"`
}

type SocketDetails struct {
    Inode         string `json:"inode"`
    Protocol      string `json:"protocol"`      // tcp, tcp6, udp, udp6, unix
    Family        string `json:"family"`        // inet, inet6, unix
    Type          string `json:"type,omitempty"` // STREAM, DGRAM, etc. Mainly for unix when available.
    State         string `json:"state,omitempty"`
    LocalAddress  string `json:"local_address,omitempty"`
    LocalPort     int    `json:"local_port,omitempty"`
    RemoteAddress string `json:"remote_address,omitempty"`
    RemotePort    int    `json:"remote_port,omitempty"`
    Path          string `json:"path,omitempty"` // unix socket path when available
    RawLine       string `json:"raw_line,omitempty"`
}
```

Exact field names can differ if the existing model has a better convention, but JSON output must be stable, explicit, and easy to inspect with `jq`.

---

## Parser Requirements

### TCP and UDP parsers

Implement parsing for:

- `/proc/net/tcp`
- `/proc/net/tcp6`
- `/proc/net/udp`
- `/proc/net/udp6`

The parser must:

1. Skip the header line.
2. Parse local address and port.
3. Parse remote address and port.
4. Parse TCP/UDP state.
5. Parse inode.
6. Return a map keyed by inode.

Example `/proc/net/tcp` address format:

```text
0100007F:1F90
```

This means:

```text
127.0.0.1:8080
```

Important: IPv4 addresses in `/proc/net/tcp` are little-endian hex.

TCP state values must be translated to human-readable names:

```text
01 ESTABLISHED
02 SYN_SENT
03 SYN_RECV
04 FIN_WAIT1
05 FIN_WAIT2
06 TIME_WAIT
07 CLOSE
08 CLOSE_WAIT
09 LAST_ACK
0A LISTEN
0B CLOSING
0C NEW_SYN_RECV
```

For UDP, state translation can be minimal. Unknown states should be preserved as raw hex and not crash parsing.

### UNIX socket parser

Implement parsing for:

- `/proc/net/unix`

The parser must:

1. Skip the header line.
2. Parse socket type where possible.
3. Parse state where possible.
4. Parse inode.
5. Parse path if present.
6. Return a map keyed by inode.

UNIX socket paths may be absent. Abstract UNIX socket names may start with `@` or may appear in kernel-specific form. Preserve them as seen.

---

## Collector Behavior

The collector should:

1. Collect FD list as before.
2. Identify FDs whose target matches `socket:[<inode>]`.
3. Build a socket table by reading `/proc/net/tcp`, `/proc/net/tcp6`, `/proc/net/udp`, `/proc/net/udp6`, and `/proc/net/unix`.
4. Attach socket details to matching FDs.
5. Preserve the original FD target even when enrichment succeeds.
6. If one `/proc/net/*` file cannot be read, add a warning and continue.
7. If a socket inode cannot be resolved, add a warning only if useful; do not spam warnings for every unresolved socket unless the count is small.

Suggested warning IDs:

```text
socket_enrichment_partial
socket_inode_unresolved
proc_net_read_failed
proc_net_parse_failed
```

The report should remain best-effort. Socket enrichment must never break `inspect` or `run`.

---

## CLI Changes

No new top-level command is required.

Optional flag:

```bash
blackbox inspect --pid <pid> --no-socket-enrichment
blackbox run --no-socket-enrichment -- <command>
```

This flag is optional. If it complicates the implementation, skip it for v0.3.0.

Default behavior should be enrichment enabled.

---

## Pretty Output Requirements

Pretty output should remain readable and not turn into a packet dump.

For FD list:

- If FD is not a socket, keep current output.
- If FD is an enriched socket, show one compact line.
- If FD is unresolved socket, show original `socket:[inode]`.

Suggested format:

```text
File descriptors (8)
  0 file         /dev/pts/3
  1 file         /dev/pts/3
  2 file         /dev/pts/3
  3 socket       tcp 127.0.0.1:41020 -> 93.184.216.34:80 ESTABLISHED inode=123456
  4 socket       unix STREAM CONNECTED /run/user/1000/bus inode=123457
```

If there are many sockets, do not introduce complex grouping in v0.3.0. Keep the FD-centric view.

---

## JSON Output Requirements

JSON reports must include socket details under each file descriptor.

Example:

```json
{
  "fd": 3,
  "type": "socket",
  "target": "socket:[123456]",
  "socket": {
    "inode": "123456",
    "protocol": "tcp",
    "family": "inet",
    "state": "ESTABLISHED",
    "local_address": "127.0.0.1",
    "local_port": 41020,
    "remote_address": "93.184.216.34",
    "remote_port": 80
  }
}
```

---

## Workload Scripts

Update or add workload scripts to make socket enrichment easy to verify.

### `scripts/workload_tcp_server.py`

A local TCP server that listens for several seconds.

Expected behavior:

```bash
blackbox run -- python3 scripts/workload_tcp_server.py
```

Report should show a TCP socket in `LISTEN` state.

### `scripts/workload_tcp_client.py`

A local TCP client that connects to a local server, or a self-contained script that starts a server thread and then connects to it.

Expected behavior:

```bash
blackbox run -- python3 scripts/workload_tcp_client.py
```

Report should show TCP sockets in `ESTABLISHED` state if collection catches them while active.

### `scripts/workload_unix_socket.py`

A script that creates a UNIX socket and keeps it open for several seconds.

Expected behavior:

```bash
blackbox run -- python3 scripts/workload_unix_socket.py
```

Report should show a UNIX socket with path.

The existing `scripts/workload_network.py` can be kept, but local workloads are preferable for deterministic tests. Avoid relying on external internet access in tests.

---

## Tests

Add unit tests for parsers.

Required parser tests:

1. Parse IPv4 TCP line.
2. Parse IPv4 UDP line.
3. Parse TCP state hex to name.
4. Parse UNIX socket line with path.
5. Parse UNIX socket line without path.
6. Ignore malformed lines without crashing.
7. Preserve raw line for debugging if the model includes `RawLine`.

Recommended package:

```text
internal/procfs/net_test.go
```

Add collector-level tests where possible:

- Given an FD target `socket:[123456]` and a socket table containing inode `123456`, FD receives socket details.
- Given an unresolved socket inode, FD remains valid and collection does not fail.

Do not write tests that depend on current machine network state. Use parser fixtures and deterministic fake data.

---

## Verification Commands

After implementation, these commands must pass:

```bash
go test ./...

go run ./cmd/blackbox inspect --pid $$ --pretty

go run ./cmd/blackbox run -- python3 scripts/workload_tcp_server.py

go run ./cmd/blackbox run -- python3 scripts/workload_unix_socket.py

go run ./cmd/blackbox run --output /tmp/blackbox-network.json -- python3 scripts/workload_tcp_server.py

jq '.run // .target' /tmp/blackbox-network.json
jq '.. | objects | select(.socket? != null) | .socket' /tmp/blackbox-network.json
```

Expected result:

- Tests pass.
- Existing v0.1 and v0.2 commands still work.
- At least one workload report contains enriched socket details.
- JSON output can be inspected with `jq`.
- Pretty output remains readable.

---

## Non-Goals for v0.3.0

Do not implement:

- eBPF.
- Packet capture.
- DNS reverse lookup.
- TLS inspection.
- Process tree tracking.
- Child-process lifetime tracking.
- Daemon mode.
- Watch mode.
- Database storage.
- REST API.
- Web UI.
- OpenTelemetry exporter.
- Root-only behavior as a requirement.

Process tree tracking is a good candidate for v0.4.0.

---

## Suggested Internal Structure

Possible files:

```text
internal/procfs/net.go
internal/procfs/net_test.go
internal/procfs/socket.go
internal/procfs/socket_test.go
internal/model/socket.go
```

If the current codebase has a better structure, follow the existing style. Do not introduce unnecessary abstractions.

---

## Acceptance Criteria

v0.3.0 is complete when:

1. Socket FDs are enriched for TCP, TCP6, UDP, UDP6, and UNIX sockets where possible.
2. JSON report includes structured socket details.
3. Pretty report displays readable socket information.
4. Parser unit tests cover deterministic `/proc/net/*` fixtures.
5. Existing v0.1 and v0.2 commands keep working.
6. `go test ./...` passes.
7. At least two local network workloads demonstrate the feature.
8. Release notes for v0.3.0 are added.
9. README and Russian README are updated with socket enrichment examples.

---

## Recommended Release Notes Draft

```markdown
## v0.3.0 - Network Socket Enrichment

Added socket enrichment for Linux Runtime Blackbox reports.

### Added

- Socket inode resolution for file descriptors like `socket:[inode]`.
- Parsers for:
  - `/proc/net/tcp`
  - `/proc/net/tcp6`
  - `/proc/net/udp`
  - `/proc/net/udp6`
  - `/proc/net/unix`
- Structured socket details in JSON reports.
- Human-readable socket information in pretty reports.
- TCP state translation.
- Local deterministic network workload scripts.
- Parser tests for procfs network tables.

### Notes

- v0.3.0 remains procfs-only.
- Socket enrichment is best-effort and does not fail the report if `/proc/net/*` cannot be read or parsed.
- DNS resolution, packet capture, eBPF, process tree tracking, daemon mode, and web UI are intentionally not included.
```

---

## Recommended Next Version After v0.3.0

Recommended v0.4.0 theme:

**Process Tree Tracking**

Goal:

- Track child processes launched by `blackbox run`.
- Collect snapshots for the root process and its children.
- Show process tree in pretty and JSON reports.

This should come after socket enrichment because socket enrichment improves both existing `inspect` and `run`, while process tree tracking changes the runtime model more deeply.
