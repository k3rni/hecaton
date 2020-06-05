export BINDIR=$(HOME)/.local/bin
export LIBDIR=$(HOME)/.local/lib/hecaton
SERVICEDIR=$(HOME)/.config/systemd/user

all: 
	make -C inputplug/
	@echo "Now run 'make install' to install systemd unit files and dependencies"

install:
	mkdir -p $(BINDIR) $(LIBDIR) $(SERVICEDIR)
	install inputplug/inputplug $(BINDIR)
	install hecaton.py $(LIBDIR)
	envsubst < hecaton.service > $(SERVICEDIR)/hecaton.service
	systemctl --user daemon-reload
	@echo "To start the service, run 'systemctl --user start hecaton'"
	@echo "To enable it to always start with your session, run 'systemctl --user enable hecaton'"





