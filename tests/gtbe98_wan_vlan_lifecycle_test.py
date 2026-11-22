#!/usr/bin/env python3
"""Compile actual shared lifecycle hooks with mocked NVRAM/PHY/commands.

This verifies source control flow only; it does not exercise hardware.
Run from any directory: python3 tests/gtbe98_wan_vlan_lifecycle_test.py
"""
from pathlib import Path
import subprocess
import os
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def function(path, signature):
    s=(ROOT / path).read_text(); begin=s.index(signature); start=s.index('{',begin); depth=0
    for end in range(start,len(s)):
        depth += (s[end]=='{')-(s[end]=='}')
        if depth==0:
            return s[begin:end+1]
    raise AssertionError('Unclosed function')

code=r'''
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <assert.h>
#define GTBE98 1
#define WAN_UNIT_FIRST 0
static const char *dot1q="", *owned="0", *ready="0", *extwan="0", *active_extwan="0";
static const char *wan_name="vlan835";
static int calls, selected[8], board=1, legacy_status_calls, rtk_status=1, hnd_status=1;
const char *nvram_safe_get(const char *key) {
 if(!strcmp(key,"AllLED")) return "1";
 if(!strcmp(key,"wan_ifname")) return wan_name;
 if(!strcmp(key,"wan0_dot1q")) return dot1q;
 if(!strcmp(key,"gtbe98_wan_vlan_owned")) return owned;
 if(!strcmp(key,"gtbe98_wan_vlan_ready")) return ready;
 if(!strcmp(key,"wans_extwan")) return extwan;
 if(!strcmp(key,"gtbe98_wan_vlan_extwan")) return active_extwan;
 assert(0); return "";
}
int nvram_match(const char *key,const char *value) {return !strcmp(nvram_safe_get(key),value);}
int is_rtl8372_boardid(void) {return board;}
int rtk_get_phy_status(int port) {assert(port==1);return rtk_status;}
int hnd_get_phy_status(const char *port) {assert(!strcmp(port,"eth0"));return hnd_status;}
int wanport_status_brcm(int unit) {++legacy_status_calls;return 10+unit;}
int mock_eval(const char *cmd,const char *op,...) {
 va_list ap; const char *arg; assert(!strcmp(cmd,"rtkswitch"));
 va_start(ap,op);arg=va_arg(ap,const char *);va_end(ap);
 assert(calls<8);
 if(!strcmp(op,"12") || !strcmp(op,"13")){
  assert(arg); selected[calls++]=(!strcmp(op,"12") ? 1 : -1)*(arg[0]-'0');
 }
 else {assert(!strcmp(op,"5") || !strcmp(op,"6"));selected[calls++]=op[0]-'0';}
 return 0;
}
#define eval(...) mock_eval(__VA_ARGS__,NULL)
'''
for signature in ('static int rtkswitch_lan_power(int up)', 'int rtkswitch_LanPort_linkUp(void)', 'int rtkswitch_LanPort_linkDown(void)'):
    code += function('release/src/router/shared/sysdeps/broadcom/rtkswitch.c', signature) + '\n'
code+=function('release/src/router/shared/boardapi.c','int wanport_status(int wan_unit)')+'\n'
code+=r'''
#include <limits.h>
#define ERP_DBG(...) ((void)0)
#define ERP_WAKEUP 0
#define ERP_STANDBY 1
#define ERP_DEFAULT_COUNT 60
#define ERP_ZERO_STA_COUNT 6
#define MODEL_DSLAC68U 1
static int erp_status, erp_count=1, erp_standbys, erp_checks;
static unsigned int erp_zero_sta_cnt;
static int get_model(void) { return 0; }
static int gtbe98_vlan_requested(void) { return (*dot1q && strcmp(dot1q,"0")) || !strcmp(owned,"1"); }
static int ERP_CHECK_MODEL_LIST(void) { ++erp_checks; return 1; }
static int ERP_CHECK_TCODE_LIST(void) { return 1; }
static int nvram_get_int(const char *key) {
 if(!strcmp(key,"wans_extwan")) return !strcmp(extwan,"1");
 return strcmp(key,"Ate_power_on_off_enable") && strcmp(key,"etlan_led_reset");
}
static int erp_check_usb_stat(void) { return 0; }
static int erp_check_wl_stat(int model) { (void)model; return 0; }
static int erp_check_arp_stat(int model) { (void)model; return 0; }
static int erp_check_gphy_stat(int model) { (void)model; return 0; }
static int erp_check_dsl_stat(int model) { (void)model; return 0; }
static int erp_check_wl_auth_stat(void) { return 0; }
static void erp_standby_mode(int model) { (void)model; ++erp_standbys; }
static void erp_wakeup_mode(int model) { (void)model; }
static void doSystem(const char *cmd) { (void)cmd; }
'''
code+=function('release/src/router/rc/erp_monitor.c','static void ERP_CHECK_MODE()')+'\n'
# Compile the real upstream ioctl encoder and dispatcher. Synthetic switch
# tests alone would miss sending raw command numbers to the kernel.
shared = (ROOT / 'release/src/router/shared/shared.h').read_text()
encoder = shared.index('#define RTKSWITCH_IOC_MAGIC')
code += '#include <sys/ioctl.h>\n#include <fcntl.h>\n'
code += shared[encoder:shared.index('\n#endif', encoder)] + '\n'
code += r'''
static unsigned long sent_ioctl;
static unsigned int sent_argument;
static int switch_open(const char *path, int flags) { assert(!strcmp(path,"/dev/rtkswitch") && flags==O_RDONLY); return 42; }
static int switch_close(int fd) { assert(fd==42); return 0; }
static int switch_ioctl(int fd, unsigned long cmd, int *arg) { assert(fd==42); sent_ioctl=cmd; sent_argument=arg?*arg:0; return 0; }
#define RTKSWITCH_DEV "/dev/rtkswitch"
#define open switch_open
#define close switch_close
#define ioctl switch_ioctl
#define dbg(...) ((void)0)
#define usleep(n) ((void)(n))
#define f_write_string(a,b,c,d) ((void)(a),(void)(b),(void)(c),(void)(d))
#define rtkswitch_port_stat(a) ((void)(a),0)
#define rtkswitch_port_mactable(a) ((void)(a),0)
#define rtkswitch_testmode(a,b,c) ((void)(a),(void)(b),(void)(c),0)
#define rtkswitch_regop(a,b,c,d,e) ((void)(a),(void)(b),(void)(c),(void)(d),(void)(e),0)
'''
code+=function('release/src/router/shared/sysdeps/broadcom/rtkswitch.c','int rtkswitch_ioctl(int val, int val2, int val3, int val4, int val5)')+'\n'
code+='\n#undef open\n#undef close\n#undef ioctl\n'
code += r'''
enum { LED_LAN, LED_10G_WHITE };
enum { LED_OFF, LED_ON };
static int lstatus = -1, lstatus_extra = -1, allstatus, allstatus_extra;
static int link_bits, traffic_ports, led_state[2];
static void led_control(int led, int mode) { led_state[led] = mode; }
static int led_sched_off(void) { return 0; }
static int rand_seed_by_time(void) { return 0; }
static void nvram_set_int(const char *key, int value) { (void)key; (void)value; assert(0); }
static int GetPhyStatus(int verbose, void *list) { assert(!verbose && !list); return link_bits; }
static unsigned long get_etlan_count(void) { return 0; }
static unsigned long get_etlan_count_specific_if(const char *ifname) {
 if (!strcmp(ifname, "eth0")) traffic_ports |= 0x1;
 else { assert(!strcmp(ifname, "eth3")); traffic_ports |= 0x40; }
 return 0;
}
'''
watchdog = 'release/src/router/rc/watchdog.c'
# The firmware shares LAN6 accounting with models that use lan_num for RGB.
code += '#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wunused-but-set-variable"\n'
for signature in ('static int gtbe98_vlan_owned_extwan(', 'static int gtbe_lan_led_has_link(',
                  'void fake_etlan_led(void)', 'void fake_etlan_led_extra(void)'):
    code += function(watchdog, signature) + '\n'
code += '#pragma GCC diagnostic pop\n'
code += r'''
static void test_leds(void) {
 static const struct {
  const char *wan_name, *extwan, *dot1q, *owned, *active_extwan;
  int lan_bits, ten_g_bits;
 } cases[] = {
  { "eth0",     "0", "0", "0", "1", 0x3e, 0x40 },
  { "vlan4094", "1", "0", "0", "0", 0x3d, 0x41 },
  { "eth3",     "0", "0", "0", "0",    0, 0x40 },
  /* Tagged ownership outlives pending port changes and a saved disable. */
  { "vlan835",  "1", "1", "1", "0", 0x3e, 0x40 },
  { "vlan835",  "0", "1", "1", "1", 0x3d, 0x41 },
  { "eth3",     "0", "0", "1", "1", 0x3d, 0x41 },
 };
 unsigned int i;
 for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
  wan_name = cases[i].wan_name;
  extwan = cases[i].extwan;
  dot1q = cases[i].dot1q;
  owned = cases[i].owned;
  active_extwan = cases[i].active_extwan;
  for (link_bits = 0; link_bits <= 0x7f; ++link_bits) {
   int j, want_lan = !!(link_bits & cases[i].lan_bits);
   int ten_g = link_bits & cases[i].ten_g_bits;
   /* Upstream also lights LAN for the legacy WAN + LAN6 combination. */
   if (!strcmp(owned, "0") && cases[i].lan_bits &&
       link_bits == (0x40 | (!strcmp(extwan, "1") ? 0x2 : 0x1)))
    want_lan = 1;
   traffic_ports = 0;
   for (j = 0; j < 10; ++j) {
    fake_etlan_led();
    fake_etlan_led_extra();
   }
   assert(led_state[LED_LAN] == want_lan);
   assert(led_state[LED_10G_WHITE] == !!ten_g);
   assert(traffic_ports == ten_g);
  }
 }
 owned = "0";
 dot1q = "";
 extwan = "0";
 active_extwan = "0";
 wan_name = "vlan835";
}

#include <net/if.h>
static int parent_mtu, mtu_reads, mtu_writes, fail_read, fail_write;
static int mtu_ioctl(int fd, unsigned long op, struct ifreq *ifr) {
 assert(fd == 42 && !strcmp(ifr->ifr_name, "eth1"));
 if (op == SIOCGIFMTU) {
  ++mtu_reads;
  if (fail_read) return -1;
  ifr->ifr_mtu = parent_mtu;
 } else {
  assert(op == SIOCSIFMTU);
  ++mtu_writes;
  if (fail_write) return -1;
  parent_mtu = ifr->ifr_mtu;
 }
 return 0;
}
#define ioctl mtu_ioctl
#define strlcpy(dst,src,n) snprintf(dst,n,"%s",src)
'''
code += function('release/src/router/rc/wan.c', 'static int ensure_parent_mtu(') + '\n'
code += '#undef ioctl\n#undef strlcpy\n'
# Run the discovery list generator with stale AutoWAN candidates, as after an upgrade.
shutils = (ROOT / 'release/src/router/shared/shutils.h').read_text()
start = shutils.index('#define foreach(word, wordlist, next)')
code += shutils[start:shutils.index('\n#endif', start)] + '\n'
code += r'''
#define RTCONFIG_AUTO_WANPORT
#define is_router_mode() 1
#define re_mode() 0
#define is_auto_wanport_enabled() 0
#define _dprintf(...) ((void)0)
#define strlcpy(dst,src,n) snprintf(dst,n,"%s",src)
static int mesh_configured;
static char *mesh_lan = "eth0 eth1 bond0 wl0";
static int mesh_int(const char *key) {
 if (!strcmp(key,"x_Setting")) return mesh_configured;
 assert(!strcmp(key,"re_mode")); return 0;
}
static char *mesh_get(const char *key) {
 if (!strcmp(key,"wan0_ifname")) return "vlan835";
 if (!strcmp(key,"wans_cap")) return "wan lan";
 if (!strcmp(key,"eth_ifnames") || !strcmp(key,"autowan_ifnames")) return "eth0 vlan4094";
 if (!strcmp(key,"lan_ifnames")) return mesh_lan;
 assert(!strcmp(key,"autowan_detected_ifname")); return "";
}
#define nvram_safe_get mesh_get
#define nvram_get_int mesh_int
'''
for signature in ('static int amas_lldp_lan_only(', 'void gen_lldpd_if('):
    code += function('release/src/router/rc/services.c', signature) + '\n'
code += '#undef nvram_safe_get\n#undef nvram_get_int\n#undef strlcpy\n'
code+=r'''
int main(void) {
 unsigned int i, commands[]={10,11,12,13,36,37,38,39,380,3901,3951,3952,3953};
 char bind[256]={0};
 test_leds();
 gen_lldpd_if(bind); assert(!strcmp(bind,"vlan835,eth0,vlan4094"));
 dot1q="1"; gen_lldpd_if(bind); assert(!strcmp(bind,"eth0,eth1,bond0,wl0"));
 mesh_configured=1; gen_lldpd_if(bind); assert(!strcmp(bind,"eth0,eth1,bond0,wl0"));
 mesh_lan="eth1 eth2 eth3 wl0"; gen_lldpd_if(bind); assert(!strcmp(bind,"eth1,eth2,eth3,wl0"));
 dot1q="0"; owned="1"; gen_lldpd_if(bind); assert(!strcmp(bind,"eth1,eth2,eth3,wl0"));
 owned="0";
 parent_mtu=9000; assert(!ensure_parent_mtu(42,"eth1",1508) && !mtu_writes && parent_mtu==9000);
 parent_mtu=1500; assert(!ensure_parent_mtu(42,"eth1",1508) && mtu_writes==1 && parent_mtu==1508);
 assert(!ensure_parent_mtu(42,"eth1",1508) && mtu_writes==1);
 fail_read=1; assert(ensure_parent_mtu(42,"eth1",1510)<0 && mtu_writes==1);
 fail_read=0; fail_write=1; assert(ensure_parent_mtu(42,"eth1",1510)<0 && parent_mtu==1508 && mtu_reads==5);
 for(i=0;i<sizeof(commands)/sizeof(commands[0]);++i) {
  assert(!rtkswitch_ioctl(commands[i],0x28,0,0,0));
  assert(_IOC_TYPE(sent_ioctl)=='R' && _IOC_DIR(sent_ioctl)==_IOC_NONE);
  assert((_IOC_NR(sent_ioctl)|(_IOC_SIZE(sent_ioctl)<<8))==commands[i]);
  assert(sent_argument==0x28);
 }
 assert(rtkswitch_LanPort_linkUp()==0 && calls==1 && selected[0]==5);
 calls=0; assert(rtkswitch_LanPort_linkDown()==0 && calls==1 && selected[0]==6);
 dot1q="1"; extwan="1"; calls=0;
 assert(rtkswitch_LanPort_linkDown()==0 && calls==3);
 assert(selected[0]==-1 && selected[1]==-2 && selected[2]==-3);
 calls=0;
 assert(rtkswitch_LanPort_linkUp()==0 && calls==3);
 assert(selected[0]==1 && selected[1]==2 && selected[2]==3);
 dot1q="invalid"; calls=0; assert(rtkswitch_LanPort_linkUp()==0 && calls==3);
 dot1q="0";owned="1";extwan="0";active_extwan="1";calls=0;
 assert(rtkswitch_LanPort_linkUp()==0 && calls==3);
 calls=0; assert(rtkswitch_LanPort_linkDown()==0 && calls==3);
 assert(selected[0]==-1 && selected[1]==-2 && selected[2]==-3);
 assert(wanport_status(0)==0 && legacy_status_calls==0);
 ready="1";assert(wanport_status(0)==1);rtk_status=-1;assert(wanport_status(0)==0);
 active_extwan="0";assert(wanport_status(0)==1);hnd_status=-1;assert(wanport_status(0)==0);
 assert(wanport_status(1)==11 && legacy_status_calls==1);
 owned="0";assert(wanport_status(0)==10 && legacy_status_calls==2);
 dot1q="1";ERP_CHECK_MODE();assert(!erp_checks && !erp_standbys && erp_count==1);
 dot1q="invalid";ERP_CHECK_MODE();assert(!erp_checks && !erp_standbys);
 dot1q="0";owned="1";ERP_CHECK_MODE();assert(!erp_checks && !erp_standbys);
 owned="0";ERP_CHECK_MODE();assert(erp_checks==1 && erp_standbys==1);
 puts("GTBE98 lifecycle hook tests passed");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="gtbe98-lifecycle-") as work:
    source = Path(work) / "test.c"
    binary = Path(work) / "test"
    source.write_text(code)
    subprocess.run([os.environ.get("CC", "cc"), "-std=gnu99", "-Wall", "-Wextra", "-Werror",
                    str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
