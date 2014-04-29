# Builds the agent distributions using fpm.


#============
# Constants
#============

BUILD=../build/package
SRC=../
ROOT=root
BUILD_NUMBER ?= 0

VERSION=`PYTHONPATH=$(SRC)/monagent python -c "from config import get_version; print get_version()"`

FPM_BUILD=fpm --epoch 1 -s dir -e -C $(BUILD) \
-a all -m "HP Cloud Monitoring <hpcs-mon@hp.com>" \
--url "http://www.hpcloud.com/" \
--description "`cat desc`"\
-v $(VERSION) \
--vendor "HP Cloud Monitoring" \
--iteration $(BUILD_NUMBER)


#=============
# COMMON
#=============

clean:
	rm -rf $(ROOT)
	rm -rf build
	rm -f *.deb

# Copy the code + static files we want to deploy to our
# root directory.
source:
	mkdir -p $(ROOT)
	cp -r $(SRC)/monagent/checks $(ROOT)/
	cp -r $(SRC)/monagent/dogstream $(ROOT)/
	cp -r $(SRC)/monagent/checks.d $(ROOT)/
	cp -r $(SRC)/conf.d $(ROOT)/
	cp -r $(SRC)/monagent/resources $(ROOT)/
	cp -r $(SRC)/monagent/api $(ROOT)/
	cp -r $(SRC)/monagent/*.py $(ROOT)/
	cp -r $(SRC)/LICENSE* $(ROOT)/
	cp -r $(SRC)/datadog.conf.example $(ROOT)/
	find $(ROOT) -name "*.pyc" -exec rm {} \;


# Layout all of the files common to both versions of the Agent in
# the build directory.
install_full: source
	mkdir -p $(BUILD)
	mkdir -p $(BUILD)/usr/share/mon/agent
	mkdir -p $(BUILD)/etc/mon-agent
	mkdir -p $(BUILD)/etc/mon-agent/conf.d
	mkdir -p $(BUILD)/usr/bin
	mkdir -p $(BUILD)/var/log/mon-agent
	# Install the source to usr/share
	cp -r $(ROOT)/*		 $(BUILD)/usr/share/mon/agent/
	# Install the common executables.
	ln -sf ../share/mon/agent/dogstatsd.py  $(BUILD)/usr/bin/dogstatsd
	ln -sf ../share/mon/agent/forwarder.py $(BUILD)/usr/bin/mon-forwarder
	ln -sf ../share/mon/agent/collector_daemon.py      $(BUILD)/usr/bin/mon-collector
	chmod 755 $(BUILD)/usr/bin/dogstatsd
	chmod 755 $(BUILD)/usr/bin/mon-forwarder
	chmod 755 $(BUILD)/var/log/mon-collector

# =====================
# DEBIAN
# =====================

install_deb: install_full
	mkdir -p $(BUILD)/etc/init.d
	cp mon-agent-deb/mon-agent.init $(BUILD)/etc/init.d/mon-agent
	chmod 755 $(BUILD)/etc/init.d/mon-agent
	# Install supervisor config.
	cp mon-agent-deb/supervisor.conf $(BUILD)/etc/mon-agent/supervisor.conf


# Make the mon agent debian package that includes supervisor, the forwarder
# etc.
mon_agent_deb: clean install_deb
	FPM_EDITOR="echo 'Replaces: mon-agent (<= $(VERSION)), mon-agent, mon-agent-base (<= $(VERSION)), mon-agent-lib' >>" \
$(FPM_BUILD) -t deb \
-n mon-agent \
-d "python (>= 2.6)" \
-d "python-tornado (>= 2.3)" \
-d "supervisor (>= 3.0)" \
-d "adduser" \
-d "sysstat" \
-d "python-pycurl" \
-d "python-requests (>= 0.8.2)" \
-d "python-psutil" \
-d "python-httplib2" \
-d "python-ntplib" \
-d "python-yaml" \
--post-install mon-agent-deb/postinst \
--post-uninstall mon-agent-deb/postrm \
--pre-uninstall  mon-agent-deb/prerm \
.


#===================
# JENKINS TARGETS
#===================

deb:
	mkdir -p ../artifacts
	make mon_agent_deb
	cp *.deb ../artifacts

installdeb:
	dpkg -i --force-confdef --force-confnew `ls -t ../artifacts/mon-agent_*.deb | head -1`

deb_repo:
	rm Packages.gz
	sudo dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz

tmp:
	cp ../artifacts/*.deb /tmp/shared || true

all: clean deb
