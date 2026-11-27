# Router Components (`release/src/router`)

## Scope

This document catalogs components under `release/src/router` (347 top-level entries) by purpose, key connections, NVRAM settings/prefixes, and IPC/bus mechanisms. It is based on source/Makefile/header inspection and RC integration points; some components are prebuilt/proprietary and are marked accordingly.

## Diagrams

- [Core Control Plane](diagrams/router/core-control-plane.mmd)
- [Networking Services](diagrams/router/network-services.mmd)
- [Wireless and AiMesh](diagrams/router/wireless-amesh.mmd)
- [USB, Storage, and Apps](diagrams/router/usb-storage-apps.mmd)
- [VPN, Security, and DPI](diagrams/router/vpn-security-dpi.mmd)
- [IPC / NVRAM Bus Map](diagrams/router/ipc-nvram-bus.mmd)

## Legend

- **Red-bordered box (`proprietary`)**: component directory contains prebuilt/proprietary artifacts linked into the firmware (e.g., `.o` files in `prebuild/`/`prebuilt/`, prebuilt binaries/libs). Treat as source-limited unless corresponding source is present.
- **Normal box**: source available in tree or normal open-source package integration (still may depend on external toolchain/libs).
- **Edge labels**: primary interaction purpose (config read/write, service control, IPC/socket, netlink/ioctl, file/config generation, network protocol).

## Cross-Cutting IPC / Bus Mechanisms

| Mechanism | Purpose | Key evidence/components |
|---|---|---|
| **NVRAM config bus** | Persistent/shared configuration state read/written by most components. | `nvram/` (`/dev/nvram`, ioctl+mmap); `shared/` NVRAM helpers; `httpd`, `rc`, services, wireless, USB, VPN all use `nvram_get/set/unset/match`. |
| **notify_rc / rc service bus** | Request service start/stop/restart/apply actions through `rc`. | `shared/notify_rc.h`; `rc/services.c` `notify_rc()`; `rc/init.c` handles `SIGUSR1` -> `handle_notifications()`. |
| **Signals** | Daemon lifecycle, reload, shutdown, watchdog. | `init.c` handles `SIGUSR1/SIGUSR2/SIGHUP/SIGINT/SIGTERM/SIGQUIT`; many daemons stopped via `killall_tk`, `kill_pidfile_s`. |
| **PID files / process control** | Track running daemons and send signals. | `/var/run/*.pid`, `shared/shutils.h` pid helpers, `xstart/_eval/kill_pidfile*`. |
| **Unix domain sockets** | Local IPC between daemons/helpers. | `cfg_mnt` `/var/run/cfgmnt_ipc_socket`; `aaews` `/var/run/aaews_ipc_socket`; `nt_center` event socket API; `networkmap`/local control sockets in some components. |
| **Netlink / ioctl / wl IOVAR** | Kernel/network/wireless control and events. | iptables/iproute2/tc netlink; wireless wl ioctl/IOVAR; RT_WIFI private ioctl in 802.1x; hotplug2/udev netlink uevents. |
| **Shared memory / files** | Fast local state sharing and generated config. | `networkmap` SHM keys and `/tmp`/`/jffs` JSON/lock files; generated configs in `/etc`, `/tmp`, `/var/run`; dnsmasq/miniupnpd/samba/vsftpd configs. |
| **HTTP/CGI/local APIs** | Admin UI and local service APIs. | `httpd` serves `www/`; backend handlers call NVRAM/rc; some daemons expose local HTTP/status interfaces. |

## Core Control Plane

| Directory | Application(s) | Purpose | Key connections | NVRAM keys/prefixes | IPC / bus |
|---|---|---|---|---|---|
| `rc/` | `rc` (multi-call), service handlers | Central init/service orchestrator; boot, service lifecycle, firewall/network/wireless/USB orchestration. | Invokes/controls almost all daemons; called by `notify_rc`, httpd/CLI/scripts; reads kernel/proc/sysfs. | Global config bus consumer: `wl*`, `wan*`, `lan*`, `dhcp*`, `ddns*`, `vpn*`, `usb*`, `fw_*`, feature flags; many service-specific keys. | `notify_rc`, signals (`SIGUSR1` notifications), pidfiles, `eval/xstart`, scripts in `/tmp`/`/etc`, NVRAM. |
| `nvram/` | `libnvram.so`, `libnvram.a`, `nvram` CLI | NVRAM user-space access library and CLI. | Linked by nearly all components; kernel nvram driver. | Owns all NVRAM key/value storage generically. | `/dev/nvram` or MTD char device, ioctl, `mmap(MAP_SHARED)`, NVRAM_MAGIC. |
| `shared/` | `libshared`, `notify_rc.o`, `tcode.o` | Common utility/library: NVRAM helpers, process control, notify_rc, board/model helpers. | Linked by rc/httpd/networkmap/infosvr/nt_center/cfg_mnt/sysstate and many others. | NVRAM helper APIs/defaults; no single prefix owner. | `notify_rc` API, pidfile/signal helpers, semaphores/file locks, shared utilities. |
| `httpd/` | `httpd` | Embedded web admin server, CGI/ASP/EJ, auth, config pages. | Serves `www/`; reads/writes NVRAM; triggers rc service actions; uses shared/libs. | UI/config NVRAM fields via `nvram_f.c`; auth/session/page-specific keys. | HTTP/HTTPS sockets, CGI/ASP in-process, NVRAM, notify_rc/rc commands, `/tmp` state files. |
| `www/` | ASP/HTML/JS/CSS assets | Web UI pages/templates. | Rendered by `httpd`; form posts to httpd handlers. | Page-driven NVRAM fields. | HTTP to `httpd`; no daemon IPC. |
| `rom/` | ROMFS payload/scripts/certs | Static image content installed to rootfs. | Consumed by rc/httpd/services; `webs_scripts/merlin_webs_update.sh` updater. | Runtime scripts may read/write NVRAM. | File-based payload; runtime via scripts/NVRAM/rc. |
| `cfg_mnt/` | `cfg_server`, `cfg_client`, `cfg_reportstatus`, `libcfgmnt.so` | AiMesh/config sync/management (capability, param, event, onboarding, etc.). | Links shared/nvram/json-c/openssl/networkmap/nt_center/wlc_nt/amas/lldpd as configured. | Domain-specific config; NVRAM + JSON payloads. | Unix socket `/var/run/cfgmnt_ipc_socket`, JSON, SSL/pthread, file locks. |
| `sysstate/` | `sysstate`, `asuslog` | System state/log/status helpers (prebuilt). | Linked with shared/nvram/json-c; queried by UI/services. | System/log state; NVRAM via shared libs. | `respipc.o` suggests IPC; files/procfs/sysinfo; prebuilt. |
| `networkmap/` | `networkmap`, `asusdiscovery`, `arpstorm`, `find_cap` | Client discovery/topology/network map. | UI/AiMesh; links shared/nvram/json-c/openssl/sqlite/cfg_mnt/bwdpi as configured. | NVRAM via shared; state in files/DB/SHM. | Shared memory keys (`SHMKEY_*`), `/tmp`/`/jffs` JSON/lock files, ARP/network scanning. |
| `infosvr/` | `infosvr` | ASUS device discovery responder. | Discovery utilities/apps; links shared/nvram. | `lan_hwaddr`, `lan_netmask`, `firmver`, `buildno`, model/product, AMAS-related. | UDP datagram socket port 9999, signals. |
| `nt_center/` | `nt_center`, `Notify_Event2NC`, `nt_monitor`, `libnt` | Notification Center event/storage/push/mail. | Started by rc; used by httpd/UI and components emitting notifications. | Notification settings via NVRAM/shared. | Event socket API `send_notify_event/socketpath`, sqlite DB, file locks, daemon processes. |
| `eventd/` | `eventd` | Event daemon (prebuilt). | Started by rc on BCM builds. | NVRAM-driven (not source-visible). | Daemon IPC (prebuilt). |
| `asus_rbd/` | `asus_rbd` | ASUS Router Boost daemon (prebuilt). | Started by rc when RouterBoost/QoS/AiMesh conditions allow. | `re_rb_enable`, RouterBoost/QoS/AiMesh state. | Process managed by rc; internal IPC prebuilt. |
| `libbcm/` | `libbcm.so` | Broadcom non-GPL shared platform helpers. | Linked by rc and Broadcom components. | No direct owner. | Shared library calls. |
| `libbcmcrypto/` | `libbcmcrypto.so` | Broadcom crypto shared library. | Linked by security/network/platform components. | No NVRAM owner. | Shared library calls. |

## Networking Services

| Directory | Application(s) | Purpose | Key connections | NVRAM keys/prefixes | IPC / bus |
|---|---|---|---|---|---|
| `dnsmasq/` | `dnsmasq` | DNS forwarder/cache, DHCPv4/v6, RA. | rc start/stop/restart; WAN/LAN/UDHCPC/OpenVPN/WireGuard/dnsfilter/stubby hooks. | `dhcp_*`, `dhcpd_*`, `lan_*`, `dns_*`, `dnssec_*`, `ipv6_*`, `dnsfilter_*`, `yadns_*`. | notify_rc, pid `/var/run/dnsmasq.pid`, `/etc/dnsmasq.conf`, `/tmp/resolv.*`, DHCP script, script-arp. |
| `dhcpfwd/` | `dhcpfwd` | DHCP forwarding/relay (CHT/WAN scenarios). | Started by rc WAN logic. | `lan_ifname`, WAN interface. | Process spawn/kill. |
| `pppd/` | `pppd` | PPP daemon for PPPoE/PPTP/L2TP/3G. | rc WAN, rp-pppoe/xl2tpd/pptp plugins, firewall/WAN state. | `wan%d_*` PPP/auth/MTU/MRU/idle. | pidfiles, `/tmp/ppp*`/`/etc/ppp`, signals. |
| `rp-pppoe/` | pppoe plugin/relay | PPPoE userland/plugin/relay. | pppd PPPoE sessions; rc pppoe relay. | `wan*_pppoe_*`, `pppoerelay_*`. | pppd plugin/process. |
| `rp-l2tp/` | L2TP components | L2TP userspace implementation. | WAN/VPN L2TP flows (build-dependent). | `wan*_proto`, L2TP/VPN keys. | config/pid/sockets (build-dependent). |
| `xl2tpd/` | `xl2tpd` | L2TP daemon/control. | pppd, firewall, rc VPN/WAN. | `l2tp*`, VPN/WAN keys. | control socket/pidfile/config. |
| `accel-pptp/`, `accel-pptpd/` | PPTP accel modules/server | Accelerated PPTP/PPTP VPN server. | rc VPN server integration. | `pptpd_*`. | config in `/tmp/pptpd/*`, signals. |
| `pptpd/` | `pptpd` | PPTP VPN server. | `rc/vpn.c`, `services.c`. | `pptpd_enable/clientlist/chap/mppe/radius/*`. | `/tmp/pptpd/*.conf`, pid/log files. |
| `odhcp6c/` | `odhcp6c` | DHCPv6 client/PD. | rc udhcpc/wan/multiwan IPv6. | `ipv6_*`, `wan*_ipv6_*`. | pid `/var/run/odhcp6c.<if>.pid`, script `/tmp/dhcp6c`. |
| `6relayd/` | `6relayd` | IPv6 relay/ND proxy/server helper. | rc WAN/multiwan IPv6/service. | `ipv6_service`, `lan_ifname`, multilan/SDN mappings. | pid `/var/run/6relayd.<if>.pid`, process signals. |
| `ndisc6/` | `ndisc6`, `rdisc6` | IPv6 ND utilities. | diagnostics/scripts. | CLI args/WAN state. | CLI tools. |
| `igmpproxy/` | `igmpproxy` | IGMP multicast proxy. | rc WAN, udpxy, firewall multicast rules. | `mr_enable_x`, `mr_altnet_x`, `udpxy_*`, `switch_stb_x`. | `/tmp/igmpproxy.conf`, postconf hooks, process kill. |
| `udpxy/` | `udpxy` | UDP-to-HTTP multicast proxy. | started by igmpproxy flow; firewall rules. | `udpxy_enable_x/if_alt/clients`. | spawned process, killall_tk. |
| `miniupnpd/`, `miniupnpd-igdv2/` | `miniupnpd` | UPnP IGD/NAT-PMP/PCP. | rc services, firewall PUPNP/FUPNP/VUPNP, WAN selection. | `upnp_*`, `vts_*`, `http/https` ports, `aurasync_enable`. | notify_rc, `/etc/upnp/config`, `/tmp/upnp.leases`, SIGUSR1 reload. |
| `lldpd*` | `lldpd`, `lldpcli` | LLDP discovery; AiMesh/Ethernet backhaul/MAP. | rc services/lan, amas/MAP role. | `lan_ifname(s)`, `sw_mode`, `cfg_master`. | lldpd process, lldpcli configure, signals. |
| `avahi/` | `avahi-daemon` | mDNS/DNS-SD. | rc services, USB/timemachine/media discovery. | mdns/timemachine/media keys. | avahi-daemon.conf, postconf, process signals. |
| `mDNSResponder/` | `mDNSResponder` | Apple mDNS/DNS-SD alternative. | feature/build-specific. | build-specific. | Unix control sockets/process. |
| `iptables*` | `iptables`, `ip6tables`, `iptables-restore` | IPv4/IPv6 firewall/NAT/mangle. | rc/firewall.c central; VPN, UPnP, DPI, parental control. | `fw_*`, `vts_*`, `upnp_*`, `mr_enable_x`, WAN/LAN keys. | netfilter netlink, rule files in `/tmp`, restore commands. |
| `ipset*` | `ipset` | IP set management for firewall/DPI. | firewall/DNSFilter/AiProtection/bwdpi. | feature-dependent set names/keys. | ipset CLI, consumed by iptables. |
| `ebtables*` | `ebtables` | Bridge frame filtering/NAT/marking. | rc common/gn_wbl, guest/WSS isolation. | `lan_ipaddr`, guest/WL interface, gn_wbl/WSS settings. | ebtables commands, kernel bridge netfilter. |
| `iproute2*` | `ip`, `tc`, `bridge`, `ss` | Routing, interfaces, QoS/tc. | rc network/qos/scripts. | routing/QoS/WAN/LAN keys. | netlink. |
| `conntrack/` | conntrack tools | Conntrack inspection/management. | diagnostics/firewall helpers. | N/A. | nf_conntrack netlink/procfs. |
| `bridge*`, `vlan/` | `brctl`, vlan tools | Bridge/VLAN config. | LAN/guest/VLAN/SDN setup. | `lan_ifname(s)`, `vlan_*`, `switch_wantag`. | ioctl/netlink. |
| `tcpdump*`, `traceroute*`, `ethtool*`, `netstat-nat`, `dns_ping/` | diagnostics tools | Packet capture, path/link/NAT/DNS diagnostics. | UI/rc/scripts. | debug/capture args. | CLI, procfs/netlink/ioctl. |
| `rstats/` | `rstats` | Bandwidth/statistics collection. | rc services, UI. | `rstats_new`, rstats enable/path settings. | pid/process, stats files in tmp/JFFS/USB. |
| `ifenslave/` | `ifenslave` | Interface bonding. | bonding/LACP setups. | bonding config. | ioctl/netlink. |
| `quagga/`, `zebra/` | routing daemons | Optional dynamic routing. | build/config dependent. | routing config keys. | vty sockets, pidfiles, config files. |

## Wireless and AiMesh

| Directory | Application(s) | Purpose | Key connections | NVRAM keys/prefixes | IPC / bus |
|---|---|---|---|---|---|
| `802.1x/` | `rtdot1xd` | RT_WIFI IEEE 802.1X authenticator/relay to external RADIUS. | rc `start_8021x/stop_8021x`; RT_WIFI driver; RADIUS server. | No direct nvram; driver config via ioctl/OID; RADIUS params in driver config. | RT_PRIV_IOCTL, raw `PF_PACKET` sockets (ETH_P_ALL/PRE_AUTH), UDP RADIUS, eloop. |
| `asd/` | `asd`, `libasd.so` (prebuilt) | ASUS security/feature daemon (prebuilt; feature domain not fully source-visible). | rc `start_asd/stop_asd`; loads `libasd.so`. | NVRAM likely (links libnvram), not source-visible. | Process start/stop, pid `/var/run/asd.pid`, shared lib plugin API. |
| `asd2.1/` | prebuilt variant | Model-specific ASD 2.1 variant (prebuilt). | packaging/build selection. | Unknown (prebuilt). | Unknown (prebuilt). |
| `amas-utils/` | `libamas-utils`/helpers | AiMesh AMAS utility/library APIs (onboarding, role/cost/RSSI, LLDP binding, misc info). | rc AMAS services, cfg_mnt, nt_center, conn_diag, lldpd. | `amas_bdlkey`, `amas_bhctrl_service_ready`, `amas_lanctrl_service_ready`, `amas_misc_service_ready`, `amas_bdl_wanstate`, raw `amas_bdl`. | Library calls, `/tmp/misc.json`, conn_diag IPC socket via `amas_cd_ipc_send_event`. |
| `aaews/` | `aaews`, `mastiff`, `aaeuac` (prebuilt) | AAE/AiCloud/web service component. | rc aaews commands; nt_center/sqlite/json-c/curl/openssl. | nat_nvram/aaews-related (prebuilt). | Unix IPC `/var/run/aaews_ipc_socket`, pid `/tmp/aaews.pid`, internal queues. |
| `mapd/` | `mapd` | Mediatek MAP/EasyMesh 1905 + WAPP/steering daemon (source present). | 1905 interface, WAPP interface, dot11 interface; MTK scripts. | Scripted MTK keys: `MapEnable`, `ApCliEnable`, `BssidNum`, `MboSupport`, `PMFMFPC`, `MapR2Enable`, `HT_*`. | Unix/global ctrl, eloop, WAPP user interface, 1905 lib, config `/etc/map/*`, `/etc/mapd_strng.conf`. |
| `wlceventd/` | `wlceventd` (prebuilt) | Broadcom wireless event daemon. | rc start/stop; wlceventd/wlc_nt/nt_center integration. | NVRAM via libnvram (prebuilt). | eventfd/local loopback, Broadcom wl private events, process signals. |
| `wlc_nt/` | `wlc_nt`, `wlc_monitor`, `libwlc_nt_client.so` | Wireless notification/monitor component. | rc start/stop; wlceventd/rc link `libwlc_nt_client`. | NVRAM via libnvram (prebuilt). | client library IPC, process control. |
| `wpa_supplicant/` | `wpa_supplicant`, `wpa_cli` | WPA/802.1X supplicant. | rc hostapd/wpasupp/wisp flows; wireless auth. | `hapd_enable`, WISP/wan ifnames, wireless security keys. | wpa_supplicant control sockets, signals, process orchestration. |
| `wsc_upnp/` | `wsc_upnpd`/WPS UPnP | Ralink WPS UPnP module. | wireless driver/kernel, UPnP CP/device. | WPS state in RC/sysdeps (`wps_cli_state`). | ioctl socket, netlink/msg queue, UPnP/libupnp, pthread. |
| `bsd/` | `bsd` (prebuilt) | Broadcom Band Steering Daemon. | rc start/stop; Broadcom wl/wlcsm; AMASDB/policy hooks. | NVRAM via libnvram (prebuilt). | process control, Broadcom wl/wlcsm/shared libs. |
| `dhd/` | prebuilt DHD support | Broadcom DHD userspace/support artifact (prebuilt). | dhd_monitor/wireless stack. | Unknown (prebuilt). | driver/userspace interaction (prebuilt). |

## USB, Storage, and Apps

| Directory | Application(s) | Purpose | Key connections | NVRAM keys/prefixes | IPC / bus |
|---|---|---|---|---|---|
| `libdisk/` | libdisk helpers | USB disk init/mount/share/account/permission, Samba/WebDAV config generation. | rc/usb.c, vsftpd, lighttpd, webdav_client. | `acc_*`, `st_samba_mode/force`, `st_ftp_mode`, `st_webdav_mode`, usb node prefixes, `usb_path*_fs_path*`. | var files, generated configs, `/tmp/usb.log`, sysfs/proc. |
| `usbclient/` | `usbclient` (prebuilt) | ASUS USB client utility. | USB client mode. | prebuilt/unknown. | prebuilt. |
| `usb-modeswitch/` | `usb_modeswitch`, dispatcher | WWAN USB mode switching. | hotplug/udev/rc modem flows. | N/A (upstream). | udev/hotplug rules, dispatcher scripts. |
| `usbmode/` | usbmode | Simple USB mode switching utility. | USB/modem insertion. | minimal. | CLI/device operations. |
| `hotplug2/` | `hotplug2` | Hotplug event daemon. | rc start/stop; kernel events trigger rule actions. | N/A directly. | netlink hotplug events, fork/exec rule actions, pid. |
| `udev/`, `udev-173/` | udevd/udevadm | Device manager/rules. | device node creation, hotplug. | N/A directly. | netlink uevents, udev sockets/rules. |
| `samba-3.5.8/`, `samba-3.6.x_opwrt/`, `sambaclient/` | smbd/nmbd/smbclient | SMB/CIFS file sharing/client. | rc/usb.c start/stop; libdisk smb.conf generation; Avahi. | `enable_samba`, `st_samba_*`, `acc_*`, `smbd_cset`. | notify_rc, pid checks, smb.conf, signals. |
| `vsftpd/`, `vsftpd-3.x/` | `vsftpd` | FTP server. | rc/usb.c start_ftpd; libdisk accounts. | `enable_ftp`, `st_ftp_mode/force`, `acc_*`. | notify_rc, pid, SIGHUP/kill, `/etc/vsftpd.conf`. |
| `minidlna/` | `minidlna` | DLNA media server. | rc USB/media flow. | `dms_*`, `territory_code`, `CoBrand`. | config/db files, process control, filesystem scan. |
| `nfs-utils-1.3.4/` | rpc.nfsd/exportfs/mountd | NFS server utilities. | rc/usb.c start_nfsd. | `nfsd_enable`, export/share keys. | kernel nfsd RPC, `/proc/fs/nfsd`, `/etc/exports`, exportfs. |
| `ntfs-3g/` | ntfs-3g | NTFS userspace driver/tools. | rc mount path. | `usb_fs_ntfs`, `usb_fs_ntfs_sparse`, `usb_ntfs_opt`. | mount/FUSE. |
| `tuxera/` | Tuxera fs drivers | Proprietary filesystem stack. | rc mount/fs, build-gated. | fs-related USB keys (build-gated). | kernel modules/userspace tools (prebuilt/proprietary). |
| `e2fsprogs/` | mkfs/fsck/tune2fs | ext filesystem utilities. | disk formatting/checking. | N/A. | CLI tools. |
| `mtd-utils/`, `mtd/` | mtd/ubi tools | Flash/MTD/UBI maintenance. | firmware upgrade, JFFS/flash. | N/A. | `/dev/mtd*`, UBI, CLI. |
| `webdav_client/` | `webdav_client` | WebDAV/cloud sync client. | AiCloud/WebDAV features. | webdav/cloud sync keys. | nvram/shared libs, pidfiles/config. |
| `asuswebstorage/` | `asuswebstorage` | ASUS WebStorage client. | cloud sync/backup UI. | cloud credential/settings keys. | curl/openssl, config files, process control. |
| `dropbox_client/` | `dropbox_client` (prebuilt) | Dropbox sync client. | cloud sync feature. | prebuilt/unknown. | prebuilt process. |
| `lighttpd-1.4.39/` | `lighttpd` | HTTP/WebDAV server for storage/UI features. | rc start_webdav; libdisk webdav conf. | `st_webdav_mode`, webdav enable/settings. | HTTP/WebDAV sockets, pid/signal, generated config. |
| `ftpclient/` | ftpclient | FTP transfer utility. | web UI/rc/scripts. | caller-provided. | CLI/process. |
| `netatalk-3.0.5/` | afpd/netatalk | AFP/Time Machine support. | rc timemachine/afpd/avahi. | `timemachine_enable`, `daapd_enable`. | Avahi service files, daemons, pid checks. |
| `diskdev_cmds-332.14/` | disk/fs utils | Disk/filesystem utilities (HFS/Apple-related). | disk management. | N/A. | CLI tools. |
| `LPRng/` | lpd/print spooler | USB printer sharing/LPD. | USB printer/U2EC busy coordination. | `lprng_baseport`, `lpnrg_lpdport`, `MFP_busy`, `u2ec_busyip`, `lan_ipaddr*`. | TCP LPD sockets, NVRAM busy-state coordination. |

## VPN, Security, and DPI

| Directory | Application(s) | Purpose | Key connections | NVRAM keys/prefixes | IPC / bus |
|---|---|---|---|---|---|
| `openvpn/` | `openvpn` | OpenVPN client/server. | rc/openvpn.c, vpn.c, ovpn.c; firewall/routes/DNS. | `vpn_*_errno/state`, `vpn_server_unit`, `vpn_client_unit`, `vpnc_unit`, `vpn_*`. | management/socket (upstream), pidfiles, config in /etc/openvpn/tmp, NVRAM status writes. |
| `strongswan/` | charon/starter/swanctl | IKE/IPsec VPN suite. | rc/rc_ipsec.c, firewall/xfrm. | `ipsec_*`, `ca_manage_profile`, profile prefixes, `ddns_*`, `wans_mode`. | VICI/control socket, generated config, pidfiles, kernel xfrm/netfilter. |
| `wireguard-tools/` | `wg`, wg-quick tools | WireGuard userspace tools. | rc/wireguard.c, firewall/routing/DNS. | `wgn_*`, `wgs_*`, vpn/wg unit keys. | wg netlink, ip/iptables/ip6tables, config in /tmp/etc, notify_rc. |
| `bwdpi_source/` | BWDPI/DPI engines (partly prebuilt) | Trend Micro DPI/AiProtection/Traffic Analyzer/QoS. | rc services bwdpi checks; firewall; UI. | `bwdpi_rsa_check`, `sig_update_update`, `sig_state_flag`, `bwdpi_*`, `wrs_*`, `qos_*`. | DPI daemons/libs, netfilter/conntrack hooks, signature DB, unix sockets/pidfiles (partly prebuilt). |
| `urlfilterd/` | `urlfilterd` | URL filtering daemon via NFQUEUE. | firewall/parental control rules. | rule/config pushed by rc/web; minimal direct NVRAM in source. | libnetfilter_queue, `/var/url_list`, daemon process. |
| `protect_srv/` | `protect_srv`, ptcsrv helpers | AiProtection/protection service (prebuilt fallback). | BWDPI, nt_center, sqlite. | nvram via libs; protection settings. | unix sockets/local commands, notification center DB, pidfiles (prebuilt). |
| `acme.sh/` | `acme.sh`, dns_asusapi.sh | ACME/Let's Encrypt cert issuance/renewal. | rc/web UI DDNS/LE cert flow. | cert/DDNS settings via rc wrappers. | shell scripts, cert files, external ACME endpoints. |
| `openssl-1.1/`, `openssl-3.5/`, `openssl11-compat/` | libssl/libcrypto/openssl | TLS/crypto libraries and compat. | httpd, lighttpd, openvpn, curl, strongswan, webdav/cloud. | N/A. | library/CLI, cert files. |
| `tor/` | `tor` | Tor anonymity daemon. | rc start_tor/service control. | `tor_*` (rc glue; verify exact keys). | torrc, SOCKS/control ports, pidfiles. |
| `net-snmp*` | `snmpd`, snmp tools | SNMP agent. | rc/snmpd.c, services.c. | `snmpd_enable`, `http_username`, `v3_*`, `roCommunity/rwCommunity`, `sysName/Location/Contact`. | UDP/TCP SNMP sockets, generated snmpd.conf, pid/signals. |
| `stubby/`, `dnscrypt*` | not present in this tree | DNS privacy components requested but not found as dirs. | N/A. | N/A. | N/A. |

## Notes

- **Prebuilt/proprietary components**: several dirs contain prebuilt binaries or no local source (`asd`, `asd2.1`, `aaews`, `wlceventd`, `wlc_nt`, `bsd`, `dhd`, `eventd`, `asus_rbd`, `networkmap` binaries, `cfg_mnt` binaries/libs, `sysstate`, `usbclient`, `dropbox_client`, parts of `protect_srv`/`bwdpi_source`). NVRAM/IPC details for these are inferred from Makefiles, strings, headers, and rc integration.
- **Third-party libraries**: many `release/src/router` entries are upstream libraries/tools (openssl, curl, sqlite, busybox, iptables, samba, etc.). They are cataloged where they have direct router service behavior; others act as supporting dependencies.
- **NVRAM as bus**: NVRAM is the dominant config bus; rc is the dominant lifecycle/orchestration bus; `notify_rc` + signals + pidfiles are the common service control mechanism.

## Other Router Directories (compact inventory)

The table above covers major service components. The remaining directories are mostly third-party libraries, utilities, platform/prebuilt artifacts, or supporting packages. They are listed here for completeness; inspect each directory's Makefile/README/source for exact behavior.

### Libraries/support

| Directory | Notes |
|---|---|
| `curl` | README |
| `dbus-1.8.8` | README.wince |
| `expat` | Makefile |
| `expat-2.0.1` | README |
| `glib-2.59.0` | README |
| `jansson` | README.rst |
| `jansson-2.7` | README.rst |
| `jpeg` | README |
| `json-c` | README |
| `libasc` | Makefile, prebuilt |
| `libasuslog` | Makefile, prebuilt |
| `libcap-ng` | README.md |
| `libcodb` | Makefile |
| `libconfuse` | README.md |
| `libdaemon` | README |
| `libestr` | README |
| `libev-4.33` | README |
| `libevent-2.0.21` | README |
| `libexif` | README |
| `libfapi-0.1` | Makefile |
| `libfastjson` | README |
| `libffi-3.0.11` | README |
| `libgcrypt-1.5.1` | README.GIT |
| `libgdbm` | README |
| `libgpg-error-1.10` | README |
| `libhelper-1.4.0.2` | Makefile, README |
| `libhostapi` | Makefile, prebuilt |
| `libical-2.0.0` | ReadMe.txt |
| `libiconv-1.14` | README.djgpp |
| `libid3tag` | README |
| `libimobiledevice-1.3.0` | README.md |
| `libjwt` | README.cmake.md |
| `libletsencrypt` | Makefile, prebuilt |
| `libmms-0.6.2` | Makefile, README |
| `libmnl-1.0.4` | README |
| `libnetfilter_conntrack-1.0.7` | README |
| `libnetfilter_cttimeout-1.0.0` | README |
| `libnetfilter_queue` | directory present |
| `libnfnetlink-1.0.1` | README |
| `libnfnetlink-1.0.2` | README |
| `libnl` | directory present |
| `libnl-bf` | Makefile |
| `libnmp` | Makefile |
| `libnss-mdns` | README.md |
| `libogg` | README.md |
| `libovpn` | Makefile |
| `libpasswd` | Makefile |
| `libpcap` | README.sita |
| `libplist-2.2.0` | README.md |
| `libpng` | README |
| `libsoup-2.41.2` | Makefile, README |
| `libssh2` | README |
| `libubox` | Makefile |
| `libupnp-1.3.1` | README |
| `libusb` | README |
| `libusb-0.1.12` | README.in |
| `libusb10` | README |
| `libusbmuxd-2.0.2` | README.md |
| `libvorbis` | README |
| `libwebapi` | Makefile, prebuilt |
| `libxml2` | README.tests |
| `libyaml` | README |
| `ncurses-6.3` | README |
| `nettle` | README |
| `pcre-8.31` | README |
| `readline-6.2` | README |
| `sqlite` | README.txt |
| `talloc-2.1.1` | Makefile |
| `traffic_limiter` | Makefile |
| `zlib` | Makefile, README |

### Network services

| Directory | Notes |
|---|---|
| `aupnpc` | Makefile |
| `dnsqd` | Makefile, prebuilt |
| `dnsspoof` | Makefile, prebuilt |
| `dproxy` | Makefile, README |
| `drvlogs_scripts` | Makefile |
| `getdns` | README.md |
| `httpdshared` | Makefile |
| `miniupnpc` | Makefile, README |
| `miniupnpc-new` | Makefile, README |
| `ntpclient` | Makefile, README |
| `openlldp` | README |
| `phddns` | README |
| `scripts` | Makefile |

### Other/misc

| Directory | Notes |
|---|---|
| `APP-IPK` | directory present |
| `PMS_DBapis` | Makefile |
| `ahs` | Makefile, prebuilt |
| `asm1042` | Makefile |
| `asusnatnl` | Makefile, prebuilt |
| `aura_rgb_nt` | Makefile |
| `aura_sw` | Makefile, prebuilt |
| `aws-iot` | Makefile |
| `batctl-2016.0` | Makefile, README |
| `bled` | Makefile |
| `bluez-5.56` | Makefile, README, prebuilt |
| `bonnie` | Makefile, readme.html |
| `bpalogin` | Makefile, README |
| `btconfig` | Makefile, README, prebuilt |
| `calc_nvram` | Makefile |
| `comad` | Makefile |
| `compressed` | Makefile |
| `config` | Makefile, README.Menuconfig |
| `coovachilli` | README |
| `db-4.8.30` | README |
| `dblog` | Makefile |
| `dhrystone` | Makefile |
| `dupvif` | Makefile |
| `easy-rsa` | directory present |
| `ecmh` | Makefile, README |
| `email-3.1.3` | README |
| `ethswbox` | Makefile, prebuilt |
| `ffmpeg` | Makefile, README.md |
| `flac` | README |
| `flash` | Makefile |
| `flex` | Makefile, README |
| `fltr` | Makefile, readme.txt |
| `fprobe-1.1` | Makefile, README |
| `freeradius-server-3.0.0` | Makefile, README.rst |
| `fsmd` | Makefile, prebuilt |
| `google_client` | Makefile |
| `haveged` | README |
| `hns` | Makefile, prebuilt |
| `hotplug-e2-helper` | README |
| `hub-ctrl` | Makefile |
| `inadyn` | README.md |
| `inotify` | Makefile, prebuilt |
| `ipaddr` | Makefile, README.md |
| `ivictl` | Makefile |
| `iw` | Makefile |
| `iwevent` | Makefile |
| `iwinfo` | Makefile |
| `ixia_endpoint` | Makefile, README |
| `jitterentropy-rngd` | Makefile, README.md |
| `jq-1.7.1` | README.md |
| `lacp` | Makefile |
| `lanauth` | Makefile |
| `layer7` | directory present |
| `lldt` | Makefile |
| `lltdc` | Makefile |
| `lm-sensors-master` | Makefile, README |
| `lsof` | README.lsof_4.82 |
| `lz4` | Makefile, README.md |
| `lzo` | README |
| `lzo-2.10` | README |
| `mak` | directory present |
| `memaccess` | Makefile |
| `ministun` | Makefile |
| `misc` | directory present |
| `mt-daapd` | Makefile, README |
| `nano` | README |
| `neon` | README |
| `netconf` | Makefile |
| `nfcm` | Makefile |
| `nmp-api` | directory present |
| `nuc029ctrl` | Makefile |
| `nvram_all` | Makefile |
| `onig-6.9.9` | README |
| `openpam` | README |
| `others` | Makefile |
| `p910nd` | Makefile |
| `portmap` | Makefile, README.5 |
| `procps-3.2.8` | Makefile, README.top |
| `psictl` | Makefile |
| `pstree` | Makefile, README |
| `push_log` | Makefile |
| `qmacc` | Makefile |
| `qrencode` | README |
| `quicksec-6.0` | Makefile |
| `reg` | Makefile |
| `rstpd` | Makefile |
| `rsyslog` | README |
| `rtl_bin` | Makefile, prebuilt |
| `sch_cake` | README.org |
| `scsi-idle` | Makefile |
| `sd-idle` | directory present |
| `smartsync_api` | Makefile |
| `snooper` | Makefile |
| `socat` | README.FIPS |
| `sqlCipher` | README.md |
| `stress` | Makefile, prebuilt |
| `stress-1.x` | README |
| `sw-hw-auth` | Makefile, prebuilt |
| `sysstat-10.0.3` | README |
| `taskset` | Makefile |
| `tcpreplay` | directory present |
| `termcap` | README |
| `u2ec` | Makefile, prebuilt |
| `uploader` | Makefile |
| `vpmstats` | Makefile, prebuilt |
| `wapp` | Makefile |
| `wb` | Makefile, prebuilt |
| `wget` | README |
| `wsdd2` | Makefile, README.md |
| `wtfast` | Makefile |

### Platform/prebuilt

| Directory | Notes |
|---|---|
| `aqr107_image` | Makefile |
| `arm_4916hnd` | directory present |
| `lltd.arm` | Makefile |
| `sdparm-1.02` | README |

### Security/VPN

| Directory | Notes |
|---|---|
| `bcm_sslconf` | directory present |
| `dropbear` | README.md |
| `mssl` | Makefile |

### Storage/sharing

| Directory | Notes |
|---|---|
| `tftp` | Makefile |
| `tftp-hpa` | Makefile, README.security |

### USB/modem/mobile

| Directory | Notes |
|---|---|
| `comgt-0.32` | Makefile |
| `uqmi` | Makefile |
| `usb-gobi` | Makefile |
| `usbmuxd-1.1.1` | README.md |

### Utilities/debug

| Directory | Notes |
|---|---|
| `bcm_util` | Makefile |
| `brcmssp_util` | Makefile |
| `busybox` | Makefile, README |
| `dosfstools` | Makefile |
| `i2c-tools-2013-12-15` | Makefile, README |
| `i2c-tools-3.1.2` | Makefile, README |
| `iperf` | README |
| `iperf3` | README.md |
| `iperf3_test` | Makefile |
| `mmc-utils` | Makefile |
| `ookla_speedtest` | Makefile |
| `pciutils-3.5.0` | Makefile, README.Windows |
| `strace` | README-sunos4 |
| `strace-4.5.20` | README-sunos4 |
| `strace-4.8` | README-linux-ptrace |
| `tools` | directory present |
| `util-linux` | README.licensing |

