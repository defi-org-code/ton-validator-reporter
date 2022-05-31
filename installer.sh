#!/bin/bash
set -e

if [ "$(id -u)" != "0" ]; then
	echo "Please run script as root"
	exit 1
fi

REPORTER_DIR=/var/ton-validator-reporter
SRC_DIR=/usr/src/ton-validator-reporter
INSTALLER_DIR=/tmp/ton-validator-reporter

REPORTER_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/reporter.py
VALIDATOR_REPORTER_SERVICE_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/ton-validator-reporter.service
VALIDATOR_VC_SERVICE_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/ton-validator-version-control.service
VALIDATOR_VC_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/version_controller.py

if [ -d "${INSTALLER_DIR}" ]; then
	echo "removing ${INSTALLER_DIR}"
	rm -rf ${INSTALLER_DIR}
fi

echo "creating installation dir at ${INSTALLER_DIR}"
mkdir -m 777 ${INSTALLER_DIR}

cd ${INSTALLER_DIR}

if [ -d ${SRC_DIR} ]; then
	echo "${SRC_DIR} exists"
else
	mkdir -m 777 "${SRC_DIR}"
fi

if [ -d ${REPORTER_DIR} ]; then
	echo "${REPORTER_DIR} exists"
else
	mkdir -m 777 "${REPORTER_DIR}"
fi


echo "Downloading ton-validator-reporter.service ..."
wget "${VALIDATOR_REPORTER_SERVICE_DESCRIPTOR}"

echo "Downloading version controller service ..."
wget "${VALIDATOR_VC_SERVICE_DESCRIPTOR}"

echo "Downloading reporter app ..."
wget "${REPORTER_DESCRIPTOR}"

echo "Downloading version controller app..."
wget "${VALIDATOR_VC_DESCRIPTOR}"

echo "adding ton-validator-reporter.service to systemd"
cp 'ton-validator-reporter.service' '/etc/systemd/system/'
echo "adding ton-validator-version-control.service to systemd"
cp 'ton-validator-version-control.service' '/etc/systemd/system/'

cp 'reporter.py' ${SRC_DIR}
cp 'version_controller.py' ${SRC_DIR}

systemctl daemon-reload
echo "restarting ton-validator-reporter.service"
systemctl restart 'ton-validator-reporter.service'

echo "restarting ton-validator-version-control.service"
systemctl restart 'ton-validator-version-control.service'

echo "enable ton-validator-reporter.service on every boot"
sudo systemctl enable 'ton-validator-reporter.service'

echo "enable ton-validator-version-control.service on every boot"
sudo systemctl enable 'ton-validator-version-control.service'
