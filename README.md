# 🌐 Host Discovery Service using SDN (Mininet + POX)

---

## 📌 Overview

This project implements a **Host Discovery Service** in a Software Defined Networking (SDN) environment using **Mininet** as the network emulator and the **POX controller** for centralized network control. The controller dynamically detects hosts via `packet_in` events, maintains a live host database, and installs OpenFlow flow rules to enable efficient, scalable packet forwarding — demonstrating core SDN principles end-to-end.

---

## 📌 Objectives

- Dynamically detect and register hosts as they join the network
- Maintain a real-time host database (MAC, IP, switch DPID, port, timestamp)
- Implement learning switch behavior at the controller level
- Install and verify OpenFlow flow rules for efficient forwarding
- Demonstrate SDN controller–switch interaction using Mininet

---

## 📌 Network Topology

```
  h1 ─┐                    ┌─ h4
  h2 ─┼─── s1 ──────── s2 ─┼─ h5
  h3 ─┘                    └─────
```

| Component | Details |
|-----------|---------|
| **Switches** | `s1`, `s2` |
| **Hosts on s1** | `h1`, `h2`, `h3` |
| **Hosts on s2** | `h4`, `h5` |
| **Inter-switch link** | `s1 ↔ s2` |
| **Controller** | POX (OpenFlow 1.0) |

---

## 📌 Prerequisites

Make sure the following are installed on your system (tested on Ubuntu 20.04+):

```bash
sudo apt-get install mininet python3
```

- [Mininet](https://mininet.org/) — network emulator
- [POX Controller](https://github.com/noxrepo/pox) — Python-based OpenFlow controller
- Open vSwitch (`ovs-ofctl`) — for flow table inspection

Clone this repository into your POX `ext/` directory so the controller module is discoverable:

```bash
cp host_discovery.py ~/pox/ext/
```

---

## 📌 Project Structure

```
.
├── host_discovery.py     # POX controller module
├── topology.py           # Mininet custom topology
├── README.md
└── screenshots/
    ├── 1.png             # Controller output – host discovery
    ├── 2.png             # pingall result – full connectivity
    ├── 3.png             # Failure scenario output
    ├── 4.png             # Flow table dump (s1 & s2)
    └── 5.png             # Host database / results summary
```

---

## 📌 Setup and Execution

### Step 1 — Start the POX Controller

```bash
cd ~/pox
./pox.py host_discovery
```

The controller will start listening for OpenFlow connections from switches.

### Step 2 — Launch the Mininet Topology

In a **separate terminal**:

```bash
sudo python3 topology.py
```

This creates the two-switch, five-host topology and connects all switches to the POX controller.

### Step 3 — Trigger Host Discovery

Inside the Mininet CLI:

```
mininet> pingall
```

This generates ICMP traffic across all host pairs, triggering `packet_in` events that allow the controller to discover and register all hosts.

---

## 📌 SDN Logic & Flow Rule Implementation

### Controller Workflow

```
Packet arrives at switch
        │
        ▼
  Flow rule match? ──YES──► Forward via switch (no controller involvement)
        │
        NO
        ▼
  packet_in event → Controller
        │
        ├─► Learn source MAC + port → update host database
        │
        ├─► Destination MAC known?
        │       ├─ YES → Install flow rule → forward
        │       └─ NO  → Flood packet
        ▼
  [Host DB updated with MAC, IP, switch, port, timestamp]
```

### Flow Rule Parameters

| Parameter | Value |
|-----------|-------|
| **Match** | Source/Destination MAC, IP, Input Port |
| **Action** | Output to specific port |
| **Priority** | 10 |
| **Idle Timeout** | 20 seconds |
| **Hard Timeout** | 60 seconds |

After initial communication, flow rules reside in the switch's TCAM, so subsequent packets bypass the controller entirely — reducing latency and control-plane load.

---

## 📌 Scenario 1 — Host Discovery and Full Connectivity

**Command:**
```
mininet> pingall
```

**Expected Output:**
```
*** Results: 0% dropped (20/20 received)
```

**Controller Log:**
```
[HOST JOIN] New host → MAC=00:00:00:00:00:01  IP=10.0.0.1  Switch=s1  Port=1
[HOST JOIN] New host → MAC=00:00:00:00:00:02  IP=10.0.0.2  Switch=s1  Port=2
...
```

**What's happening:** Every host's first packet triggers a `packet_in` event. The controller logs the host, installs a bidirectional flow rule, and subsequent pings are handled entirely by the switch.

![Scenario 1 – Controller host discovery output](screenshots/1.png)

![Scenario 1 – pingall full connectivity](screenshots/2.png)

---

## 📌 Scenario 2 — Failure Scenario (Host Unreachable)

**Commands:**
```
mininet> h2 ifconfig h2-eth0 down
mininet> h1 ping h2
```

**Expected Output:**
```
From 10.0.0.1 icmp_seq=1 Destination Host Unreachable
```

**What's happening:** Bringing the interface down simulates a host failure. Since `h2` is no longer sending or receiving, ARP requests go unanswered and ICMP packets cannot be delivered. The idle timeout (20s) will eventually flush the stale flow rule from `s1`.

![Scenario 2 – Host failure / unreachable](screenshots/3.png)

---

## 📌 Scenario 3 — Flow Table Verification

**Commands (run in a separate terminal while Mininet is active):**
```bash
sudo ovs-ofctl dump-flows s1
sudo ovs-ofctl dump-flows s2
```

**Sample Output:**
```
cookie=0x0, duration=5.3s, table=0, n_packets=5, priority=10,
  ip,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2 actions=output:2

cookie=0x0, duration=5.3s, table=0, n_packets=5, priority=10,
  ip,in_port=2,nw_src=10.0.0.2,nw_dst=10.0.0.1 actions=output:1
```

**What's happening:** After `pingall`, the controller has installed per-flow rules into each switch. Traffic no longer needs to traverse the controller — it's forwarded at line rate by the switch hardware.

![Scenario 3 – Flow table dump](screenshots/4.png)

---

## 📌 Performance Observations

| Metric | First Packet | Subsequent Packets |
|--------|-------------|-------------------|
| **Path** | Host → Switch → Controller → Switch → Host | Host → Switch → Host |
| **Latency** | Higher (controller round-trip) | Lower (hardware forwarding) |
| **Controller load** | High (packet_in per flow) | None (flow rule match) |

- **RTT on first ping** is noticeably higher due to the `packet_in` processing overhead.
- After flow rule installation, **RTT drops significantly** as the switch forwards directly.
- Flow table entry count **increases after `pingall`** and decreases after idle timeout expiry.

---

## 📌 Results Summary

| Objective | Status |
|-----------|--------|
| Dynamic host discovery | ✅ Achieved |
| Host database maintenance | ✅ Achieved |
| OpenFlow flow rule installation | ✅ Achieved |
| Learning switch behavior | ✅ Achieved |
| Failure handling | ✅ Verified |
| Efficient forwarding post-discovery | ✅ Confirmed |

![Results – Host database and flow summary](screenshots/5.png)

---

## 📌 Validation

The system was tested under the following conditions:

- ✅ **Normal operation** — `pingall` confirms 0% packet loss and complete host discovery
- ✅ **Failure condition** — host interface brought down; unreachability confirmed
- ✅ **Flow table inspection** — rules verified via `ovs-ofctl` on both switches
- ✅ **Timeout behavior** — idle/hard timeouts cause rule eviction as expected

---

## 📌 Conclusion

This project successfully demonstrates a fully functional **SDN Host Discovery Service** built with Mininet and POX. Key SDN principles validated include:

- **Separation of control and data planes** — POX handles all logic; OvS handles forwarding
- **Reactive flow installation** — rules are installed on demand, not pre-provisioned
- **Centralized network visibility** — the controller maintains a global view of all hosts
- **Scalable forwarding** — after initial discovery, the data plane operates autonomously

---

## 📌 References

- [Mininet Official Site](https://mininet.org/)
- [Mininet GitHub Repository](https://github.com/mininet/mininet)
- [POX Controller (noxrepo)](https://github.com/noxrepo/pox)
- [OpenFlow 1.0 Specification](https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf)
- [Open vSwitch Documentation](https://www.openvswitch.org/)