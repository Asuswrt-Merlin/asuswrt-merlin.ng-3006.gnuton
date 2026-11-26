# AsusWrt-Merlin.ng 3006 (Gnuton) — Architecture

## Scope

Analysis based on the 3006 firmware line in this repository. Key sources: `AGENTS.md`, `README.md`, `.github/workflows/github-actions.yml`, `updates/`, `release/src/Makefile`, `release/src/router/Makefile`, `release/src-rt/target.mak`, `release/src-rt/version.conf`, `release/src-rt-5.04behnd.4916/Makefile`, and `release/src/router/{rc,nvram,shared,httpd,www,rom}/`.

> Note: the web UI source is `release/src/router/www/` (not a top-level `www/` directory).

## Diagrams

- [System Architecture](diagrams/system-architecture.mmd)
- [Runtime Architecture](diagrams/runtime-architecture.mmd)
- [Build and Release Pipeline](diagrams/build-release-pipeline.mmd)
- [RC Service Connections](diagrams/rc-service-connections.mmd)

## RC Services

A detailed RC `start_*` service catalog and orchestration overview is available in [rc-services.md](rc-services.md).

## 1) High-Level System Architecture

```mermaid
flowchart TB
    subgraph REPO["Repository / Source of Truth"]
        DOCS["Docs & Metadata\nAGENTS.md, README*, Changelog-3006.txt\nLicense, SUPPORT.md"]
        TOOLS["Repo Tools\ntools/\n- get-last-notes.py\n- copy-prebuilt*\n- make-model-prebuild.sh\n- make-www-sysdep.sh\n- bootloaders-copy.sh"]
        UPDATES["Update Feed\nupdates/\n- manifest_3006.txt\n- 3006_*_note.txt"]
        CI["CI/CD\n.github/workflows/github-actions.yml"]
        SRC["Firmware Source\nrelease/"]
    end

    subgraph SRC_TREE["release/ Source Tree"]
        SRC_COMMON["release/src/\nCommon userland/build helpers\nrouter/, btools/, ctools/, lzma*,\nasustools/, shared libs/tools"]
        SRC_RT_SHARED["release/src-rt/\nShared RT config/fragments\ntarget.mak, version.conf,\nplatform.mak, profile*.mak"]
        SDK_BE["release/src-rt-5.04behnd.4916/\nPrimary BE SDK (CI)\nkernel, bcmdrivers, bootloaders,\nhostTools, targets, userspace,\nrouter-sysdep*, make*.mak"]
        SDK_OTHER["Other SDK trees\nsrc-rt-5.02axhnd*\nsrc-rt-5.04axhnd.675x\n(legacy/other platform baselines)"]
        IMG["release/image/\nImage output area"]
    end

    CI -->|builds model matrix| SDK_BE
    CI -->|reads/writes version/feed metadata| SRC_RT_SHARED
    CI -->|publishes release assets + manifest| UPDATES
    TOOLS --> CI
    SRC --> SRC_COMMON
    SRC --> SRC_RT_SHARED
    SRC --> SDK_BE
    SRC --> SDK_OTHER
    SRC --> IMG
```

## 2) Firmware Runtime / Component Architecture

```mermaid
flowchart LR
    USER["Admin/User Browser"]
    EXT["External Services\nASUS/Merlin update feed,\nDDNS, cloud, NTP, VPN peers,\nUSB/mobile/storage devices"]

    subgraph FW["Router Firmware Runtime (on device)"]
        subgraph UI["Web Management Plane"]
            WWW["Web UI Assets\nrelease/src/router/www/\n*.asp, js/, css/, images/\naimesh/, dashboard/\nsysdep/<MODEL>/"]
            HTTPD["Embedded HTTPD/Backend\nrelease/src/router/httpd/\nhttpd.c, cgi.c, ej.c,\nnvram_f.c, sysdeps/"]
            WEBAPI["Web/API Helpers\nlibwebapi/, asuswebstorage/\nwebdav_client/, rom/webs_scripts/"]
        end

        subgraph CTRL["Control / Configuration Plane"]
            RC["rc/init Orchestrator\nrelease/src/router/rc/\nrc.c, service startup,\nnetwork/firewall/wireless/usb,\nwatchdogs, buttons/LEDs, events"]
            NVRAM["NVRAM Config Store\nrelease/src/router/nvram/\nnvram.c, nvram_linux.c,\nnvram_convert.c"]
            SHARED["Shared Libraries/Utils\nrelease/src/router/shared/\nboardapi, common utils,\nnvram wrappers, bcm utils,\nevent/IPC helpers"]
            ROMFS["ROMFS / Defaults / Scripts\nrelease/src/router/rom/\nwebs_scripts/, certs, defaults,\napps_scripts/, prebuilt data"]
        end

        subgraph NET["Networking & Security Services"]
            NETCORE["Network Core\nbridge/bridge-utils, vlan,\niproute2, ethtool, conntrack"]
            DHCPDNS["DHCP/DNS\ndnsmasq, udhcpd/dhcpfwd,\ndns_ping, stubby/DNS privacy"]
            WAN["WAN/PPP/Tunnel\npppd, rp-pppoe, pptp-client,\nxl2tpd/l2tp, 6relayd, odhcp6c"]
            FWALL["Firewall/NAT/QoS\niptables/ipset/ebtables,\nrc firewall logic, tc/qos,\ntraffic monitor/rstats"]
            VPN["VPN/Security\nOpenVPN, StrongSwan/IPsec,\nWireGuard, OpenSSL, easy-rsa,\nacme.sh/LETSENCRYPT"]
            DPI["DPI/Parental/Protection\nbwdpi_source, urlfilterd,\nprotect_srv, AiProtection hooks"]
        end

        subgraph WLAN["Wireless / AiMesh"]
            WLCTRL["WiFi Control\nwlceventd, wlc_nt, wps/wsc,\n802.1x/eapd, bsd"]
            AMAS["AiMesh/Roaming\namas-utils, mapd, asd/asd2.1,\nsteering/mesh policy"]
            WLDRV["Broadcom WL Drivers/SDK\nbcmdrivers/.../net/wl,\nshared wl interfaces, dhd"]
        end

        subgraph SYS["System / Platform Services"]
            USB["USB/Storage/Sharing\nusbclient/modeswitch, udev,\nntfs/tuxera/e2fs/dosfstools,\nsamba/vsftpd/lighttpd/minidlna/nfs"]
            DISC["Discovery/UPnP/mDNS\navahi, mDNSResponder,\nminiupnpd, lldpd, networkmap"]
            MISC["Utilities/Daemons\nbusybox, syslog, ntpclient,\ncron/sched, sysstate,\naura LED, nt_center, infosvr"]
        end

        subgraph KERNEL["Kernel / Platform Layer"]
            LINUX["Linux Kernel\nsrc-rt-5.04behnd.4916/kernel/\nlinux-4.19, bcmkernel, dts"]
            BRCMDRV["Broadcom Platform Drivers\nbcmdrivers/, shared/, rdp/,\nethernet/switch/accelerator"]
            BOOT["Boot/Platform\nbootloaders/CFE/TF-A,\ntargets/<PROFILE>, hostTools outputs"]
        end
    end

    USER <--> HTTPD
    HTTPD --> WWW
    HTTPD --> WEBAPI
    HTTPD <--> NVRAM
    HTTPD --> RC

    RC <--> NVRAM
    RC <--> SHARED
    RC --> ROMFS
    RC --> NETCORE
    RC --> DHCPDNS
    RC --> WAN
    RC --> FWALL
    RC --> VPN
    RC --> DPI
    RC --> WLCTRL
    RC --> AMAS
    RC --> USB
    RC --> DISC
    RC --> MISC

    WLCTRL <--> NVRAM
    AMAS <--> NVRAM
    NETCORE --> LINUX
    FWALL --> LINUX
    WLCTRL --> WLDRV
    AMAS --> WLDRV
    WLDRV --> BRCMDRV
    BRCMDRV --> LINUX
    USB --> LINUX
    DISC --> NETCORE
    MISC --> SHARED
    BOOT --> LINUX
    EXT <--> WAN
    EXT <--> WEBAPI
    EXT <--> VPN
    EXT <--> USB
```

## 3) Build, Packaging, and Release Pipeline

```mermaid
flowchart TB
    DEV["Developer / Tag / Manual Dispatch"]
    GH["GitHub Actions\n.github/workflows/github-actions.yml"]

    subgraph PREP["prepare-job"]
        MATRIX["Select matrix\nmodel/sdk/ui\nvalidate workflow_dispatch model"]
    end

    subgraph BUILD["build-job (container: gnuton/asuswrt-merlin-toolchains-docker)"]
        CLONE["Clone repo into /project/repo"]
        VER["Tag build: patch release/src-rt/version.conf\nSERIALNO / EXTENDNO"]
        NOTES["Default UI: tools/get-last-notes.py\n-> CHANGELOG"]
        ENV["Source SDK toolchain env\nBE 4916: bcm-hnd-ax-4.19be_soft.sh"]
        UI["Optional UI toggle\nrelease/src-rt/target.mak\nROG_UI / TUF_UI"]
        MAKE["cd release/${SDK}\nmake ${MODEL}"]
        ART["Collect artifacts\n*.w, *.squashfs.pkgtb, *.md5,\nCHANGELOG"]
    end

    subgraph SDKBUILD["SDK Build Orchestration"]
        SDKMK["release/src-rt-5.04behnd.4916/Makefile\nprofile/chip/target detection\nall/image/clean targets"]
        RTCONF["release/src-rt/target.mak + version.conf\nmodel feature flags, version"]
        ROUTERMK["release/src/router/Makefile\nuserland component build/install"]
        SYSDEP["targets/<PROFILE>\nrouter-sysdep/<model>\nprebuilt/model overlays"]
        KERNEL["kernel/linux-4.19 + bcmdrivers\nbootloaders + hostTools + userspace"]
        PACK["Image packaging\nbtools/lzma/asustools/hostTools\nTRX/W/PKGTB generation"]
    end

    subgraph REL["Tag-only Release Jobs"]
        RELEASE["release-job\ncreate draft GitHub release\nattach artifacts"]
        MANIFEST["manifest-job (stable tags)\nupdate updates/manifest_3006.txt\ncopy versioned *_note.txt\npush to master"]
    end

    FEED["Firmware Update Feed\nraw.githubusercontent.com/.../updates/\nmanifest_3006.txt + release notes"]
    ROUTERUPD["On-router updater\nrom/webs_scripts/merlin_webs_update.sh\nreads manifest/note from feed"]

    DEV --> GH --> PREP --> BUILD
    CLONE --> VER --> NOTES --> ENV --> UI --> MAKE --> ART
    MAKE --> SDKMK
    SDKMK --> RTCONF
    SDKMK --> ROUTERMK
    SDKMK --> SYSDEP
    SDKMK --> KERNEL
    ROUTERMK --> PACK
    KERNEL --> PACK
    ART --> RELEASE
    ART --> MANIFEST
    RELEASE --> FEED
    MANIFEST --> FEED
    FEED --> ROUTERUPD
```

## 4) Source Component Map

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

## 5) Architectural Constraints

- **3006-only line:** `master` is the 3006 line; CI rejects non-`3006.*` tags; update feed is `manifest_3006.txt`.
- **Proprietary/prebuilt components:** many `prebuilt`/binary/vendor areas (ASUS/Broadcom/Trend Micro/Tuxera) are not modifiable as source.
- **Feature-flag driven builds:** model capabilities are composed through `release/src-rt/target.mak` macros and SDK/profile make fragments.
- **Build-layout reality:** legacy `release/src/Makefile` exists, but supported 3006 BE CI builds through `release/src-rt-5.04behnd.4916/Makefile`.
