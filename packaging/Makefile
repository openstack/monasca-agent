# Builds the agent distributions using fpm.


#============
# Constants
#============

BUILD=../build/package
SRC=../
ROOT=root
BUILD_NUMBER ?= 0

VERSION=`PYTHONPATH=$(SRC) python -c "from monasca_agent.common.config import get_version; print get_version()"`

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
	cp -r $(SRC)/monasca_agent $(ROOT)/
	cp -r $(SRC)/conf.d $(ROOT)/
	cp -r $(SRC)/LICENSE* $(ROOT)/
	cp -r $(SRC)/agent.yaml.template $(ROOT)/
	find $(ROOT) -name "*.pyc" -exec rm {} \;


# Layout all of the files common to both versions of the Agent in
# the build directory.
install_full: source
	mkdir -p $(BUILD)
	mkdir -p $(BUILD)/usr/monasca/agent
	mkdir -p $(BUILD)/etc/monasca/agent
	mkdir -p $(BUILD)/etc/monasca/agent/conf.d
	mkdir -p $(BUILD)/usr/bin
	mkdir -p $(BUILD)/var/log/monasca/agent
	mkdir -p $(BUILD)/usr/share/monasca/agent
	# Install the source to usr/share
	cp -r $(ROOT)/* $(BUILD)/usr/share/monasca/agent
	# Install the common executables.
	ln -sf ../share/monasca/agent/monasca_agent/statsd/daemon.py $(BUILD)/usr/bin/monasca-statsd
	ln -sf ../share/monasca/agent/monasca_agent/forwarder/daemon.py $(BUILD)/usr/bin/monasca-forwarder
	ln -sf ../share/monasca/agent/monasca_agent/collector/daemon.py $(BUILD)/usr/bin/monasca-collector
	chmod 755 $(BUILD)/usr/bin/monasca-statsd
	chmod 755 $(BUILD)/usr/bin/monasca-forwarder
	chmod 755 $(BUILD)/usr/bin/monasca-collector

# =====================
# DEBIAN
# =====================

install_deb: install_full
	mkdir -p $(BUILD)/etc/init.d
	cp monasca-agent-deb/monasca-agent.init $(BUILD)/etc/init.d/monasca-agent
	chmod 755 $(BUILD)/etc/init.d/monasca-agent
	# Install supervisor config.
	cp monasca-agent-deb/supervisor.conf $(BUILD)/etc/monasca/agent/supervisor.conf


# Make the monasca agent debian package that includes supervisor, the forwarder
# etc.
monasca_agent_deb: clean install_deb
	FPM_EDITOR="echo 'Replaces: monasca-agent (<= $(VERSION)), monasca-agent, monasca-agent-base (<= $(VERSION)), monasca-agent-lib' >>" \
$(FPM_BUILD) -t deb \
-n monasca-agent \
-d "python (>= 2.6)" \
-d "python-tornado (>= 2.3)" \
-d "supervisor (>= 3.0)" \
-d "adduser" \
-d "sysstat" \
-d "python-pycurl" \
-d "python-requests (>= 0.8.2)" \
-d "python-httplib2" \
-d "python-ntplib" \
-d "python-yaml" \
-d "python-monascaclient" \
--post-install monasca-agent-deb/postinst \
--post-uninstall monasca-agent-deb/postrm \
--pre-uninstall  monasca-agent-deb/prerm \
.

#===================
# JENKINS TARGETS
#===================

deb:
	mkdir -p ../artifacts
	make monasca_agent_deb
	cp *.deb ../artifacts

installdeb:
	dpkg -i --force-confdef --force-confnew `ls -t ../artifacts/monasca-agent_*.deb | head -1`

deb_repo:
	rm Packages.gz
	sudo dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz

tmp:
	cp ../artifacts/*.deb /tmp/shared || true

all: clean deb
