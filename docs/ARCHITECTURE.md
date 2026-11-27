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

## RC Services

A detailed RC `start_*` service catalog and orchestration overview is available in [rc-services.md](rc-services.md).

## Router Component Catalog

A component-level catalog for `release/src/router` (purpose, connections, NVRAM keys/prefixes, IPC/bus mechanisms, and domain diagrams) is available in [router-components.md](router-components.md).

## 1) System Architecture

This graph shows the major firmware applications/subsystems and their purposes. Edges are labeled with the primary interaction or data flow.

```mermaid
flowchart TB
    ADMIN["Admin Browser\nWeb-based router administration UI"]
    EXT["External Services\nFirmware feed, DDNS, NTP, VPN peers, cloud services"]

    subgraph FW["AsusWrt-Merlin.ng 3006 Router Firmware"]
        WEB["Web Management\nhttpd + ASP/CGI UI for configuration and status"]
        CTRL["Control Plane\nrc/init orchestration, NVRAM config, shared libs, ROMFS defaults"]
        NET["Network Services\nLAN/WAN routing, DHCP/DNS, firewall/NAT/QoS, VPN, DPI"]
        WLAN["Wireless & AiMesh\nWiFi control, WPA/WPS, mesh/roaming, Broadcom WL stack"]
        SYS["Platform Services\nUSB/storage/sharing, discovery/UPnP/mDNS, system daemons"]
        KERN["Kernel & Drivers\nLinux 4.19, Broadcom platform/WL drivers, boot chain"]
    end

    ADMIN -->|"HTTPS/HTTP requests for status and configuration"| WEB
    WEB -->|"NVRAM reads/writes and rc service actions"| CTRL
    CTRL -->|"Service start/stop/restart and config application"| NET
    CTRL -->|"Wireless service orchestration and config application"| WLAN
    CTRL -->|"USB/system service orchestration and config application"| SYS
    NET -->|"Netfilter, sockets, routing, and interface control"| KERN
    WLAN -->|"WL ioctl/IOVAR and driver events"| KERN
    SYS -->|"Block/device/filesystem and daemon runtime support"| KERN
    NET <-->|"WAN protocols, VPN tunnels, DNS/NTP/DDNS traffic"| EXT
    WEB <-->|"Firmware update checks and web API integrations"| EXT
    SYS <-->|"USB devices, storage media, and mobile peripherals"| EXT
```

## 2) Control Plane

The control plane connects the web UI to persistent configuration and service orchestration.

```mermaid
flowchart LR
    ADMIN["Admin Browser\nOperator config/status interface"]

    subgraph WEBPLANE["Web Management Plane"]
        WWW["Web UI Assets (www/)\nASP pages, JS/CSS/images, model-specific UI files"]
        HTTPD["httpd Web Server\nHTTP/CGI/EJ handling, auth, NVRAM-facing handlers"]
        WEBAPI["Web/API Helpers\nlibwebapi, asuswebstorage, webdav_client, webs_scripts"]
    end

    subgraph CTRLPLANE["Control / Configuration Plane"]
        RC["rc Init Orchestrator\nBoot sequencing, service start/stop, event handling"]
        NVRAM["NVRAM Config Store\nPersistent key/value configuration and defaults overlay"]
        SHARED["Shared Libraries/Utils\nboardapi, nvram wrappers, common helpers, IPC/event utilities"]
        ROMFS["ROMFS Defaults/Scripts\nDefault config, certs, service scripts, prebuilt data"]
    end

    ADMIN <-->|"HTTP/HTTPS admin requests and responses"| HTTPD
    HTTPD -->|"Serves ASP/JS/CSS assets"| WWW
    HTTPD -->|"Invokes backend API/helper scripts"| WEBAPI
    HTTPD <-->|"Reads/writes configuration values"| NVRAM
    HTTPD -->|"Triggers apply/restart via rc actions/notify_rc"| RC
    RC <-->|"Reads config and persists runtime state"| NVRAM
    RC <-->|"Uses shared helpers and board/platform APIs"| SHARED
    RC -->|"Loads defaults, certs, and helper scripts"| ROMFS
    WEBAPI <-->|"Reads credentials/settings for cloud/update/webdav features"| NVRAM
    WEBAPI <-->|"Calls external web services and firmware feed"| EXT["External Services\nFirmware feed, cloud/webdav endpoints"]
```

## 3) Network Services

Network and security applications are orchestrated by `rc`, configured through NVRAM, and enforce policy through kernel/netfilter interfaces.

```mermaid
flowchart LR
    RC["rc Init Orchestrator\nStarts/stops network and security services"]
    NVRAM["NVRAM Config Store\nService enablement, WAN/LAN/firewall/VPN settings"]
    KERN["Linux Kernel / Netfilter\nInterfaces, routing, conntrack, iptables hooks"]
    EXT["External Network Peers\nISP/WAN, VPN peers, DDNS/NTP/DNS services"]

    subgraph NET["Networking & Security Services"]
        NETCORE["Network Core\nbridge/bridge-utils, vlan, iproute2, ethtool, conntrack tools"]
        DHCPDNS["DHCP/DNS Services\ndnsmasq, udhcpd/dhcpfwd, dns_ping, stubby"]
        WAN["WAN/PPP/Tunnel Services\npppd, rp-pppoe, pptp-client, xl2tpd/l2tp, 6relayd, odhcp6c"]
        FWALL["Firewall/NAT/QoS\niptables/ipset/ebtables rules, tc/qos, traffic monitor/rstats"]
        VPN["VPN/Security Services\nOpenVPN, StrongSwan/IPsec, WireGuard, OpenSSL, easy-rsa, acme.sh"]
        DPI["DPI/Parental/Protection\nbwdpi_source, urlfilterd, protect_srv, AiProtection hooks"]
    end

    RC -->|"Applies config and starts/stops daemons"| NETCORE
    RC -->|"Applies config and starts/stops daemons"| DHCPDNS
    RC -->|"Applies config and starts/stops daemons"| WAN
    RC -->|"Regenerates rules and starts monitors"| FWALL
    RC -->|"Starts VPN daemons and cert/keys workflows"| VPN
    RC -->|"Starts DPI/filter engines and policy hooks"| DPI

    NETCORE <-->|"Reads interface/bridge/VLAN settings"| NVRAM
    DHCPDNS <-->|"Reads lease/DNS/DHCP settings"| NVRAM
    WAN <-->|"Reads WAN protocol/credentials/settings"| NVRAM
    FWALL <-->|"Reads firewall/NAT/QoS/port-forward settings"| NVRAM
    VPN <-->|"Reads VPN keys/policies/server-client settings"| NVRAM
    DPI <-->|"Reads parental control/AiProtection settings"| NVRAM

    NETCORE -->|"Configures links, bridges, VLANs, routes via ip/sysfs"| KERN
    DHCPDNS -->|"Binds UDP/TCP DNS/DHCP sockets"| KERN
    WAN -->|"Creates PPP/tunnel interfaces and routes"| KERN
    FWALL -->|"Installs iptables/ipset/ebtables/tc rules"| KERN
    VPN -->|"Creates tunnel interfaces and crypto sockets"| KERN
    DPI -->|"Hooks packet inspection and policy enforcement"| KERN

    WAN <-->|"PPP/DHCP/IPv6 WAN connectivity"| EXT
    DHCPDNS <-->|"Upstream DNS/DoT queries and NTP-assisted resolution dependencies"| EXT
    VPN <-->|"Encrypted tunnels to VPN peers"| EXT
    FWALL <-->|"NAT/port forwarding of inbound/outbound traffic"| EXT
```

## 4) Wireless & AiMesh

Wireless services are split between user-space control/mesh daemons and the Broadcom wireless/platform driver stack.

```mermaid
flowchart LR
    RC["rc Init Orchestrator\nStarts wireless, WPA/WPS, and AiMesh services"]
    NVRAM["NVRAM Config Store\nSSID, security, radio, band-steering, AiMesh settings"]
    KERN["Linux Kernel\nNetlink, sockets, interface state"]
    BRCMDRV["Broadcom Platform Drivers\nbcmdrivers, shared, RDP, ethernet/switch/accelerator"]
    WLDRV["Broadcom WL Driver Stack\nbcmdrivers/.../net/wl, shared WL interfaces, dhd"]

    subgraph WLAN["Wireless & AiMesh Services"]
        WLCTRL["WiFi Control\nwlceventd, wlc_nt, wps/wsc, 802.1x/eapd, bsd"]
        AMAS["AiMesh/Roaming\namas-utils, mapd, asd/asd2.1, steering/mesh policy"]
    end

    RC -->|"Starts/restarts wireless and mesh daemons"| WLCTRL
    RC -->|"Starts/restarts AiMesh and roaming daemons"| AMAS
    WLCTRL <-->|"Reads radio/security/WPS configuration"| NVRAM
    AMAS <-->|"Reads mesh topology, steering, and node settings"| NVRAM

    WLCTRL -->|"Configures AP/STA/VIF via wl ioctl/IOVAR"| WLDRV
    AMAS -->|"Controls roaming/steering/mesh via WL and service interfaces"| WLDRV
    WLCTRL <-->|"Receives wireless events and interface state notifications"| KERN
    AMAS <-->|"Uses network sockets for mesh/backhaul coordination"| KERN
    WLDRV -->|"Uses Broadcom driver/platform APIs"| BRCMDRV
    BRCMDRV -->|"Registers devices and handles hardware interrupts/data paths"| KERN
```

## 5) USB & System Services

Platform services cover USB/storage sharing, LAN discovery, and general system daemons.

```mermaid
flowchart LR
    RC["rc Init Orchestrator\nStarts USB, storage, discovery, and system daemons"]
    NVRAM["NVRAM Config Store\nUSB/NAS/service enablement and policy settings"]
    KERN["Linux Kernel / Sysfs / Udev\nBlock devices, USB stack, filesystems, process/runtime"]
    EXT["External Devices/Clients\nUSB disks/modems/printers, LAN clients, mobile devices"]

    subgraph SYS["Platform & Peripheral Services"]
        USB["USB/Storage/Sharing\nusbclient/modeswitch, udev, ntfs/tuxera/e2fs/dosfstools, samba/vsftpd/lighttpd/minidlna/nfs"]
        DISC["Discovery/UPnP/mDNS\navahi, mDNSResponder, miniupnpd, lldpd, networkmap"]
        MISC["System Utilities/Daemons\nbusybox, syslog, ntpclient, cron/sched, sysstate, aura LED, nt_center, infosvr"]
    end

    RC -->|"Starts/stops storage and sharing services"| USB
    RC -->|"Starts/stops discovery and network advertisement services"| DISC
    RC -->|"Starts/stops system utilities and monitors"| MISC

    USB <-->|"Reads share, mount, modem, and app settings"| NVRAM
    DISC <-->|"Reads UPnP/mDNS/discovery settings"| NVRAM
    MISC <-->|"Reads system, logging, LED, and schedule settings"| NVRAM

    USB -->|"Mounts filesystems, manages devices, serves file/media protocols"| KERN
    DISC -->|"Opens multicast/unicast sockets and advertises services"| KERN
    MISC -->|"Runs scheduled jobs, logging, timers, and device control"| KERN

    USB <-->|"USB mass storage, printers, modems, file/media access"| EXT
    DISC <-->|"UPnP/mDNS/LLDP/service discovery with LAN clients"| EXT
    MISC <-->|"NTP/syslog/infosvr interactions as configured"| EXT
```

## 6) RC Service Orchestration

The RC layer is the runtime control hub. The detailed `start_*` catalog is in [rc-services.md](rc-services.md).

```mermaid
flowchart TB
    BOOT["Boot / Init\ninit.c and rc.c early system initialization"]
    SS["Service Orchestrator\nstart_services()/stop_services() in services.c"]
    LAN["LAN Orchestrator\nstart_lan() in lan.c"]
    WAN["WAN Orchestrator\nstart_wan()/start_wan_if() in wan.c"]
    USB["USB Orchestrator\nstart_usb() in usb.c"]
    WL["Wireless Init\nstart_wl()/start_wireless() in lan.c/rc"]
    FW["Firewall Orchestrator\nstart_firewall() in firewall.c"]
    JFFS["Persistent Storage Init\nstart_jffs2()/start_ubifs() in jffs2.c/ubifs.c"]

    CORE["Core System Services\nsyslogd/klogd, hotplug2, cron, ntp, watchdogs, LEDs"]
    NETSVC["Network Services\ndnsmasq, stubby, httpd, UPnP, networkmap, wanduck, SSH/telnet, LLDP/Avahi"]
    WLSVC["Wireless Services\neapd/nas/wpa, wlceventd, bsd, asd/amas, roamast, WPS, DCS/ACSD"]
    SECSVC["Security/VPN/DPI Services\nOpenVPN/VPNC/WireGuard hooks, BWDPI checks, letsencrypt, conn_diag"]
    USBSVC["USB/App Services\nnas_services, Samba, FTP, minidlna/DMS, WebDAV, Timemachine, diskmon"]
    FEAT["Feature Daemons\naura RGB, AiCloud/awsiot, aae/mastiff/natnl, infosvr, notification_center"]

    BR["LAN Bridge/VLAN Setup\nstart_vlan, start_lan_port, start_lan_wl, DHCP/DNS reload"]
    WANIF["WAN Interface Bringup\nDHCP/PPPoE/USB modem, start_wan6, 6relayd/dhcp6c/rdisc6"]
    WANFEAT["WAN Feature Hooks\nVPN client/server hooks, QoS, firewall, DDNS, UPnP, routes"]
    NAS["NAS/App Stack\nstart_nas_services, Samba/FTP/DMS/WebDAV/Timemachine"]

    NVRAM["NVRAM Config Store\nnvram/* and shared/* configuration/state"]
    HTTPD["Web Control Backend\nhttpd CGI/ASP in httpd/* and www/*"]
    RCMD["RC Command Interface\nrc_service/notify_rc service action dispatcher"]

    BOOT -->|"Invokes core service startup"| SS
    BOOT -->|"Initializes LAN interfaces and bridge"| LAN
    BOOT -->|"Initializes WAN interfaces and protocols"| WAN
    BOOT -->|"Initializes USB/storage subsystem"| USB
    BOOT -->|"Initializes wireless interfaces"| WL
    BOOT -->|"Applies initial firewall policy"| FW
    BOOT -->|"Mounts persistent user partition"| JFFS

    SS -->|"Starts/stops core daemons"| CORE
    SS -->|"Starts/stops network-facing daemons"| NETSVC
    SS -->|"Starts/stops wireless control daemons"| WLSVC
    SS -->|"Starts/stops security and VPN-related daemons"| SECSVC
    SS -->|"Starts/stops USB/NAS application daemons"| USBSVC
    SS -->|"Starts/stops product feature daemons"| FEAT

    LAN -->|"Configures bridge/VLAN/ports and reloads LAN services"| BR
    WAN -->|"Brings up WAN link/protocol and IPv6"| WANIF
    WAN -->|"Applies WAN-dependent features and policies"| WANFEAT
    USB -->|"Starts NAS/media/sharing application stack"| NAS

    NVRAM <-->|"Reads service configuration and writes runtime state"| SS
    NVRAM <-->|"Reads LAN/bridge/VLAN/wireless settings"| LAN
    NVRAM <-->|"Reads WAN/protocol/firewall/feature settings"| WAN
    NVRAM <-->|"Reads web settings and persists UI changes"| HTTPD
    HTTPD -->|"Requests service restart/apply after config changes"| SS
    HTTPD -->|"Issues rc service actions for targeted changes"| RCMD
    RCMD -->|"Dispatches service start/stop/restart commands"| SS
    RCMD -->|"Dispatches LAN reconfiguration actions"| LAN
    RCMD -->|"Dispatches WAN reconfiguration actions"| WAN
    RCMD -->|"Dispatches firewall rebuild actions"| FW
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
