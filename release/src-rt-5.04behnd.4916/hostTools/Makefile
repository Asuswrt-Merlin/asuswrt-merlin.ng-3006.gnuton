
TOPDIR  := $(shell /bin/pwd)

default:

$(MAKECMDGOALS):
	-if [ -f prebuilt/$(BUILD_NAME)/mksquashfs ]; then cp prebuilt/$(BUILD_NAME)/mksquashfs ./mksquashfs; else cp prebuilt/mksquashfs ./mksquashfs; fi
	mkdir -p mtd-utils-2.0.2
	ln -sf mtd-utils-2.0.2 mtd-utils
	-if [ -f prebuilt/$(BUILD_NAME)/mkfs.ubifs ]; then cp prebuilt/$(BUILD_NAME)/mkfs.ubifs mtd-utils/; else cp prebuilt/mkfs.ubifs mtd-utils/; fi
	-if [ -f prebuilt/$(BUILD_NAME)/ubinize ]; then cp prebuilt/$(BUILD_NAME)/ubinize mtd-utils/; else cp prebuilt/ubinize mtd-utils/; fi
	mkdir -p local_install
	-cp prebuilt/$(BUILD_NAME)/lzop local_install/
	-cp prebuilt/make_ext4fs local_install/
	-if [ -f prebuilt/$(BUILD_NAME)/cmplzma ]; then cp prebuilt/$(BUILD_NAME)/cmplzma ./cmplzma; else cp prebuilt/cmplzma ./cmplzma; fi
	-cp prebuilt/lzmacmd ./lzmacmd
	mkdir -p prelink/src
	-cp prebuilt/execstack ./prelink/src/execstack
	-mkdir -p libelf/lib
	-cp prebuilt/libelf.so ./libelf/lib/libelf.so
	rm -f libelf/lib/libelf.so.0
	-(cd libelf/lib && ln -sf libelf.so libelf.so.0)


build_execstack: $(TOPDIR)/prelink/src/execstack


