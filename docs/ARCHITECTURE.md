# AsusWrt-Merlin.ng 3006 (Gnuton) — Architecture

## Scope

Analysis based on the 3006 firmware line in this repository. Key sources: `AGENTS.md`, `README.md`, `release/src/Makefile`, `release/src/router/Makefile`, `release/src-rt/target.mak`, `release/src-rt/version.conf`, `release/src-rt-5.04behnd.4916/Makefile`, and `release/src/router/{rc,nvram,shared,httpd,www,rom}/`.

> Note: the web UI source is `release/src/router/www/` (not a top-level `www/` directory).

## Diagrams

- [System Architecture](diagrams/system-architecture.mmd) — high-level system context with major applications and purposes.
- [Control Plane](diagrams/control-plane.mmd) — web UI, httpd, rc, NVRAM, shared libraries, and ROMFS interactions.
- [Network Services](diagrams/network-services.mmd) — routing, DHCP/DNS, WAN, firewall/NAT/QoS, VPN, and DPI services.
- [Wireless & AiMesh](diagrams/wireless-amesh.mmd) — WiFi control, AiMesh/roaming, Broadcom WL stack, and kernel interfaces.
- [USB & System Services](diagrams/usb-system-services.mmd) — USB/storage/sharing, discovery, and system daemons.
- [RC Service Connections](diagrams/rc-service-connections.mmd) — boot/init and RC service orchestration.

**Legend:** red-bordered nodes indicate components with prebuilt/proprietary artifacts linked into the firmware (e.g., `.o` files in `prebuild/`/`prebuilt/` or prebuilt binaries/libs). Edge labels describe interaction purpose.

## RC Services

A detailed RC `start_*` service catalog and orchestration overview is available in [rc-services.md](rc-services.md).

## Router Component Catalog

A component-level catalog for `release/src/router` (purpose, connections, NVRAM keys/prefixes, IPC/bus mechanisms, and domain diagrams) is available in [router-components.md](router-components.md).

## 1) System Architecture

This graph shows the major firmware applications/subsystems and their purposes. Edges are labeled with the primary interaction or data flow.

```mermaid
flowchart TB
    classDef proprietary fill:#fff5f5,stroke:#c92a2a,stroke-width:2px,color:#111;
    classDef external fill:#f8f9fa,stroke:#495057,color:#111;

    ADMIN["Admin Browser\nWeb-based router administration UI"]:::external
    EXT["External Services\nFirmware feed, DDNS, NTP, VPN peers, cloud services"]:::external

    subgraph FW["AsusWrt-Merlin.ng 3006 Router Firmware"]
        direction TB
        WEB["Web Management\nhttpd + ASP/CGI UI\nConfiguration and status"]
        CTRL["Control Plane\nrc/init orchestration\nNVRAM config, shared libs, ROMFS defaults"]
        NET["Network Services\nLAN/WAN routing, DHCP/DNS\nFirewall/NAT/QoS, VPN, DPI"]
        WLAN["Wireless & AiMesh\nWiFi control, WPA/WPS\nMesh/roaming, Broadcom WL stack"]
        SYS["Platform Services\nUSB/storage/sharing\nDiscovery/UPnP/mDNS, system daemons"]
        KERN["Kernel & Drivers\nLinux 4.19\nBroadcom platform/WL drivers, boot chain"]
    end

    ADMIN -->|"HTTPS/HTTP admin requests/responses"| WEB
    WEB -->|"NVRAM reads/writes and rc service actions"| CTRL
    CTRL -->|"Service start/stop/restart and config apply"| NET
    CTRL -->|"Wireless service orchestration and config apply"| WLAN
    CTRL -->|"USB/system service orchestration and config apply"| SYS
    NET -->|"Netfilter, sockets, routing, interface control"| KERN
    WLAN -->|"WL ioctl/IOVAR and driver events"| KERN
    SYS -->|"Block/device/filesystem and daemon runtime support"| KERN
    NET <-->|"WAN protocols, VPN tunnels, DNS/NTP/DDNS traffic"| EXT
    WEB <-->|"Firmware update checks and web API integrations"| EXT
    SYS <-->|"USB devices, storage media, mobile peripherals"| EXT
```

## 2) Control Plane

The control plane connects the web UI to persistent configuration and service orchestration.

```mermaid
flowchart LR
    classDef proprietary fill:#fff5f5,stroke:#c92a2a,stroke-width:2px,color:#111;
    classDef external fill:#f8f9fa,stroke:#495057,color:#111;

    ADMIN["Admin Browser\nOperator config/status interface"]:::external
    EXT["External Services\nFirmware feed, cloud/webdav endpoints"]:::external

    subgraph WEBPLANE["Web Management Plane"]
        WWW["Web UI Assets (www/)\nASP pages, JS/CSS/images\nModel-specific UI files"]
        HTTPD["httpd Web Server\nHTTP/CGI/EJ handling\nauth, NVRAM-facing handlers"]
        WEBAPI["Web/API Helpers\nlibwebapi, asuswebstorage\nwebdav_client, webs_scripts"]
    end

    subgraph CTRLPLANE["Control / Configuration Plane"]
        RC["rc Init Orchestrator\nBoot sequencing\nservice start/stop, event handling"]
        NVRAM["NVRAM Config Store\nPersistent key/value config\ndefaults overlay"]
        SHARED["shared Libraries/Utils\nboardapi, nvram wrappers\ncommon helpers, IPC/event utilities"]
        ROMFS["ROMFS Defaults/Scripts\nDefault config, certs\nservice scripts, prebuilt data"]
    end

    ADMIN <-->|"HTTP/HTTPS admin requests and responses"| HTTPD
    HTTPD -->|"Serves ASP/JS/CSS assets"| WWW
    HTTPD -->|"Invokes backend API/helper scripts"| WEBAPI
    HTTPD <-->|"Reads/writes configuration values"| NVRAM
    HTTPD -->|"Triggers apply/restart via rc actions/notify_rc"| RC
    RC <-->|"Reads config and persists runtime state"| NVRAM
    RC <-->|"Uses shared helpers and board/platform APIs"| SHARED
    RC -->|"Loads defaults, certs, and helper scripts"| ROMFS
    WEBAPI <-->|"Reads credentials/settings for cloud/update/webdav"| NVRAM
    WEBAPI <-->|"Calls external web services and firmware feed"| EXT
```

## 3) Network Services

Network and security applications are orchestrated by `rc`, configured through NVRAM, and enforce policy through kernel/netfilter interfaces.

```mermaid
flowchart TB
    classDef proprietary fill:#fff5f5,stroke:#c92a2a,stroke-width:2px,color:#111;
    classDef external fill:#f8f9fa,stroke:#495057,color:#111;

    RC["rc Service Orchestrator\nStarts/stops network daemons and applies config"]
    NVRAM["NVRAM Config Store\nLAN/WAN/DHCP/DNS/firewall/VPN/DPI settings"]

    subgraph CORE["Network Core"]
        NETCORE["Network Core Utilities\nbridge/bridge-utils, vlan, iproute2, ethtool, conntrack\nInterface, route, bridge, and neighbor management"]
    end

    subgraph EDGE["Edge Network Services"]
        DHCPDNS["DHCP/DNS Service\ndnsmasq, udhcpd/dhcpfwd, dns_ping\nAddress assignment and name resolution"]
        WAN["WAN/PPP/Tunnel Services\npppd, rp-pppoe, pptp-client, xl2tpd/l2tp, 6relayd, odhcp6c\nWAN link establishment and IPv6 transition"]
        FWALL["Firewall/NAT/QoS\niptables/ipset/ebtables, rc firewall logic, tc/qos, rstats\nTraffic filtering, NAT, shaping, accounting"]
    end

    subgraph SEC["Security Services"]
        VPN["VPN/Security Services\nOpenVPN, StrongSwan/IPsec, WireGuard, OpenSSL, easy-rsa, acme.sh\nEncrypted tunnels and certificate management"]
        DPI["DPI/Parental Protection\nbwdpi_source, urlfilterd, protect_srv\nTraffic inspection and policy enforcement"]:::proprietary
    end

    KERNEL["Linux Kernel Networking\nnetfilter, routing, interfaces, xfrm/WireGuard"]:::external
    EXT["External Networks/Peers\nISP, DNS servers, VPN peers, web services"]:::external

    RC -->|"starts/restarts daemons and reloads rules"| NETCORE
    RC -->|"generates config and manages DHCP/DNS lifecycle"| DHCPDNS
    RC -->|"controls WAN session setup/teardown"| WAN
    RC -->|"applies firewall/NAT/QoS rules"| FWALL
    RC -->|"manages VPN daemons and cert renewal"| VPN
    RC -->|"starts/stops DPI and filtering services"| DPI

    RC <-->|"reads/writes network service configuration"| NVRAM
    NETCORE -->|"configures links/routes/bridges via netlink/ioctl"| KERNEL
    DHCPDNS -->|"binds UDP/TCP sockets for DHCP/DNS service"| KERNEL
    WAN -->|"creates PPP/tunnel interfaces and routes"| KERNEL
    FWALL -->|"installs netfilter/qdisc rules"| KERNEL
    VPN -->|"creates tunnel interfaces/xfrm state"| KERNEL
    DPI -->|"inspects packets via netfilter/conntrack hooks"| KERNEL

    DHCPDNS <-->|"DNS queries, DHCP leases, RA/DHCPv6"| EXT
    WAN <-->|"PPP/ISP/tunnel control and data traffic"| EXT
    VPN <-->|"Encrypted tunnel traffic to peers"| EXT
```

## 4) Wireless & AiMesh

Wireless services are split between user-space control/mesh daemons and the Broadcom wireless/platform driver stack.

```mermaid
flowchart LR
    classDef proprietary fill:#fff5f5,stroke:#c92a2a,stroke-width:2px,color:#111;
    classDef external fill:#f8f9fa,stroke:#495057,color:#111;

    RC["rc Service Orchestrator\nStarts/stops wireless and mesh services"]
    NVRAM["NVRAM Config Store\nSSID/security/channel/band/AiMesh settings"]

    subgraph WIFI["WiFi Control"]
        WLCTRL["WiFi Control Daemons\nwlceventd, wlc_nt, wps/wsc, 802.1x/eapd, bsd\nStation/AP event handling, WPS, auth, band steering"]:::proprietary
    end

    subgraph MESH["AiMesh / Roaming"]
        AMAS["AiMesh/Roaming Services\namas-utils, mapd, asd/asd2.1\nMesh onboarding, steering, roaming policy"]:::proprietary
    end

    WLDRV["Broadcom WL Driver/SDK\nbcmdrivers/.../net/wl, shared wl interfaces, dhd\nWireless MAC/PHY/driver stack"]:::proprietary
    KERNEL["Linux Kernel / Platform Drivers\nnetdev, cfg80211/ioctl bridge, interrupts"]:::external
    CLIENTS["WiFi Clients / Mesh Nodes\nSTAs, repeaters, AiMesh nodes"]:::external

    RC -->|"starts/stops and configures WiFi daemons"| WLCTRL
    RC -->|"starts/stops and configures AiMesh services"| AMAS
    RC <-->|"reads/writes wireless configuration"| NVRAM
    WLCTRL <-->|"reads/writes WiFi/WPS/security state"| NVRAM
    AMAS <-->|"reads/writes mesh/roaming state"| NVRAM

    WLCTRL -->|"WL ioctl/IOVAR, event sockets, driver control"| WLDRV
    AMAS -->|"topology/steering control via wl/service APIs"| WLDRV
    WLDRV -->|"driver registration, netdev ops, interrupts, DMA"| KERNEL
    WLCTRL <-->|"802.11 management, WPA/WPS signaling"| CLIENTS
    AMAS <-->|"AiMesh discovery, onboarding, roaming coordination"| CLIENTS
```

## 5) USB & System Services

Platform services cover USB/storage sharing, LAN discovery, and general system daemons.

```mermaid
flowchart TB
    classDef proprietary fill:#fff5f5,stroke:#c92a2a,stroke-width:2px,color:#111;
    classDef external fill:#f8f9fa,stroke:#495057,color:#111;

    RC["rc Service Orchestrator\nStarts/stops USB, storage, discovery, and system daemons"]
    NVRAM["NVRAM Config Store\nUSB, sharing, service, LED, and feature settings"]
    KERNEL["Linux Kernel / Device Drivers\nUSB, block, filesystem, netdev, sysfs/procfs"]:::external
    DEVICES["USB/Storage/Mobile Devices\nDisks, printers, modems, peripherals"]:::external
    CLIENTS["LAN/Internet Clients\nSMB/NFS/DLNA/UPnP/mDNS clients"]:::external

    subgraph USB["USB / Storage / Sharing"]
        USBST["USB/Storage/Sharing Services\nusbclient, usb-modeswitch, udev, ntfs-3g/tuxera/e2fs/dosfstools\nsamba, vsftpd, lighttpd, minidlna, nfs\nDevice mounting and file/media sharing"]:::proprietary
    end

    subgraph DISC["Discovery / UPnP / mDNS"]
        DISCOV["Discovery Services\navahi, mDNSResponder, miniupnpd, lldpd, networkmap\nService advertisement, discovery, topology, port mapping"]
    end

    subgraph SYS["System Utilities / Daemons"]
        MISC["System Utilities/Daemons\nbusybox, syslog, ntpclient, cron/sched, sysstate\naura LED, nt_center, infosvr\nGeneral system operation and maintenance"]
    end

    RC -->|"detects devices, mounts volumes, starts sharing services"| USBST
    RC -->|"starts discovery/advertisement/port-mapping services"| DISCOV
    RC -->|"starts system and maintenance daemons"| MISC
    RC <-->|"reads/writes service configuration"| NVRAM

    USBST <-->|"reads/writes USB/share/media settings"| NVRAM
    DISCOV <-->|"reads/writes discovery/UPnP/topology settings"| NVRAM
    MISC <-->|"reads/writes system/feature settings"| NVRAM

    USBST -->|"udev events, block/fs mounts, device I/O"| KERNEL
    DISCOV -->|"network sockets, multicast, netlink/interface state"| KERNEL
    MISC -->|"sysfs/procfs, timers, device control"| KERNEL

    USBST <-->|"USB attach/remove, storage and peripheral access"| DEVICES
    USBST <-->|"SMB/FTP/HTTP/DLNA/NFS file sharing"| CLIENTS
    DISCOV <-->|"mDNS/SSDP/LLDP/UPnP discovery and mapping"| CLIENTS
```

## 6) RC Service Orchestration

The RC layer is the runtime control hub. The detailed `start_*` catalog is in [rc-services.md](rc-services.md).

```mermaid
flowchart TB
    classDef proprietary fill:#fff5f5,stroke:#c92a2a,stroke-width:2px,color:#111;

    INIT["init/rc boot\nSystem initialization and main control loop"]
    SS["start_services()\nCore service orchestrator in services.c"]
    LAN["start_lan()\nLAN/bridge/VLAN/WiFi bringup in lan.c"]
    WAN["start_wan() / start_wan_if()\nWAN interface and protocol bringup in wan.c"]
    USB["start_usb()\nUSB device/storage initialization in usb.c"]
    WL["start_wl() / start_wireless()\nWireless radio/interface initialization"]
    FW["start_firewall()\nNetfilter/firewall/NAT rule application in firewall.c"]
    JFFS["start_jffs2()/start_ubifs()\nPersistent writable filesystem mount"]

    SS -->|"starts/stops core daemons"| CORE["Core/System Services\nsyslogd/klogd/logger, hotplug2, cron, ntp, watchdogs, LEDs"]
    SS -->|"starts/stops network daemons"| NETSVC["Network Services\ndnsmasq, stubby, httpd, upnp, networkmap, wanduck, sshd, snmpd"]
    SS -->|"starts/stops wireless daemons"| WLSVC["Wireless Services\neapd, nas/wpa, wlceventd, bsd, asd, AMAS, wps"]
    SS -->|"starts/stops security daemons"| SECSVC["Security/VPN/DPI\nOpenVPN/WireGuard hooks, BWDPI checks, letsencrypt, conn_diag"]
    SS -->|"starts/stops USB/app daemons"| USBSVC["USB/App Services\nnas_services, samba, ftpd, minidlna/DMS, webdav, timemachine"]
    SS -->|"starts/stops feature daemons"| FEAT["Feature Daemons\naura RGB, AiCloud/awsiot, infosvr, nt_center, sysstate"]

    WLSVC -.->|"includes prebuilt/proprietary components"| PROP["Prebuilt/proprietary examples\nasd, wlceventd, bsd, amas-utils libs"]:::proprietary

    LAN -->|"configures LAN interfaces/bridge/VLAN"| BR["Bridge/VLAN/LAN IF\nstart_vlan, start_lan_port, start_lan_wl, DHCP/DNS reload"]
    WAN -->|"brings up WAN protocol/interface"| WANIF["WAN Interface Bringup\nDHCP/PPPoE/USB modem, start_wan6, 6relayd/dhcp6c/rdisc6"]
    WAN -->|"applies WAN-dependent features"| WANFEAT["WAN Features\nVPN client/server hooks, QoS, firewall, DDNS, UPnP, routes"]
    USB -->|"starts NAS/app stack"| NAS["NAS/App Stack\nstart_nas_services, samba, ftpd, DMS, webdav, timemachine"]

    NVRAM["NVRAM Config Bus\nnvram/* shared/* persistent key-value config"]
    HTTPD["httpd Web Backend\nCGI/ASP handlers in httpd/* serving www/*"]
    RCMD["RC Dispatcher\nrc rc_service / notify_rc event handling"]

    INIT -->|"invokes during boot"| SS
    INIT -->|"invokes during boot"| LAN
    INIT -->|"invokes during boot"| WAN
    INIT -->|"invokes during boot"| USB
    INIT -->|"invokes during boot"| WL
    INIT -->|"invokes during boot"| FW
    INIT -->|"invokes during boot"| JFFS

    NVRAM <-->|"reads/writes service configuration"| SS
    NVRAM <-->|"reads/writes LAN configuration"| LAN
    NVRAM <-->|"reads/writes WAN configuration"| WAN
    NVRAM <-->|"reads/writes UI/config state"| HTTPD
    HTTPD -->|"applies settings via rc service actions"| RCMD
    RCMD -->|"dispatches service start/stop/restart"| SS
    RCMD -->|"dispatches LAN reconfiguration"| LAN
    RCMD -->|"dispatches WAN reconfiguration"| WAN
    RCMD -->|"dispatches firewall reload"| FW
```

## 7) Source Component Map

| Layer | Key paths | Responsibility |
|---|---|---|
| Repo/CI | `.github/workflows/github-actions.yml`, `tools/`, `updates/` | Build matrix, artifact creation, GitHub release, manifest/note feed publication. |
| Shared RT config | `release/src-rt/target.mak`, `version.conf`, `platform.mak`, `profile*.mak` | Model feature flags, versioning, platform/profile build configuration. |
| Primary BE SDK | `release/src-rt-5.04behnd.4916/` | Kernel/drivers/bootloaders/host tools/targets/sysdep and top-level image orchestration for supported 3006 BE models. |
| Common userland | `release/src/router/` | Router applications, daemons, libs, web, scripts, ROMFS content; reused by SDK builds via symlink/overlay. |
| Init/control | `release/src/router/rc/`, `shared/`, `nvram/` | Boot/init, service orchestration, NVRAM/config persistence, shared APIs/utilities. |
| Web UI/backend | `release/src/router/www/`, `httpd/`, `rom/webs_scripts/` | ASP/JS UI, HTTP/CGI/EJ backend, NVRAM-facing handlers, update/cert/web scripts. |
| Networking | `bridge*`, `iproute2*`, `iptables/ipset/ebtables`, `dnsmasq`, `pppd/rp-pppoe`, `quagga`, `6relayd`, `odhcp6c` | LAN/WAN bridging/routing, DHCP/DNS, firewall/NAT, IPv6, routing protocols. |
| Wireless/AiMesh | `wlceventd`, `wlc_nt`, `wps`, `802.1x`, `asd*`, `amas-utils`, `mapd`, SDK `bcmdrivers/.../wl` | WiFi control, roaming/mesh, WPA/WPS, Broadcom wireless driver stack. |
| VPN/Security/DPI | `openvpn`, `strongswan`, `wireguard-tools`, `openssl*`, `bwdpi_source`, `urlfilterd`, `acme.sh` | VPNs, crypto, certificate management, DPI/parental/filtering. |
| USB/Storage/Sharing | `usbclient`, `usb-modeswitch`, `e2fsprogs`, `ntfs-3g/tuxera`, `samba*`, `vsftpd*`, `minidlna`, `nfs-utils` | USB device/storage handling, filesystems, NAS/media/file sharing services. |
| Kernel/platform | `src-rt-5.04behnd.4916/kernel`, `bcmdrivers`, `shared`, `rdp`, `bootloaders`, `targets` | Linux 4.19/Broadcom kernel platform, hardware drivers, acceleration, boot chain, target profiles. |

## 8) Architectural Constraints

- **3006-only line:** `master` is the 3006 line; CI rejects non-`3006.*` tags; update feed is `manifest_3006.txt`.
- **Proprietary/prebuilt components:** many `prebuilt`/binary/vendor areas (ASUS/Broadcom/Trend Micro/Tuxera) are not modifiable as source.
- **Feature-flag driven builds:** model capabilities are composed through `release/src-rt/target.mak` macros and SDK/profile make fragments.
- **Build-layout reality:** legacy `release/src/Makefile` exists, but supported 3006 BE CI builds through `release/src-rt-5.04behnd.4916/Makefile`.
