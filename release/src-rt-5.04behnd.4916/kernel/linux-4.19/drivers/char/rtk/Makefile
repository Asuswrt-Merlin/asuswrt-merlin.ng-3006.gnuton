obj-m += rtl8367s.o
rtl8367s-objs += rtl8367s_preb.o

RTL8367S_PREB := $(obj)/rtl8367s.$(ARCH).o
ifeq ($(wildcard $(RTL8367S_PREB)),)
RTL8367S_PREB := $(obj)/rtl8367s.arm.o
endif

$(obj)/rtl8367s_preb.o:
	cp $(RTL8367S_PREB) $(obj)/rtl8367s_preb.o
