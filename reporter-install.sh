#!/bin/bash
set -e

if [ "$(id -u)" != "0" ]; then
	echo "Please run script as root"
	exit 1
fi

SERVICE_NAME=reporter

REPORTER_DB=/var/${SERVICE_NAME}
SRC_DIR=/usr/src/${SERVICE_NAME}
REPORTER_LOG_DIR=/var/log/${SERVICE_NAME}
SYSTEMD_DIR=/etc/systemd/system/

INSTALLER_DIR=/tmp/${SERVICE_NAME}

REPORTER_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/reporter.py
VALIDATOR_REPORTER_SERVICE_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/${SERVICE_NAME}.service
EXIT_STAKE_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/exit.py
ENTER_STAKE_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/enter.py
RE_STAKE_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/restake.py
RESET_EMERGENCY_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/reset_emergency.py
CONSTANTS_DESCRIPTOR=https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/constants.json

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
	echo "creating ${SRC_DIR}"
	mkdir -m 777 "${SRC_DIR}"
fi

if [ -d ${REPORTER_DB} ]; then
	echo "${REPORTER_DB} exists"
else
	echo "creating ${REPORTER_DB}"
	mkdir -m 777 "${REPORTER_DB}"
fi

if [ -d ${REPORTER_LOG_DIR} ]; then
	echo "${REPORTER_LOG_DIR} exists"
else
	echo "creating ${REPORTER_LOG_DIR}"
	mkdir -m 777 "${REPORTER_LOG_DIR}"
fi

echo "Downloading ${SERVICE_NAME}.service ..."
wget "${VALIDATOR_REPORTER_SERVICE_DESCRIPTOR}"

echo "Downloading reporter script ..."
wget "${REPORTER_DESCRIPTOR}"

echo "Downloading exit script ..."
wget "${EXIT_STAKE_DESCRIPTOR}"

echo "Downloading enter script ..."
wget "${ENTER_STAKE_DESCRIPTOR}"

echo "Downloading re-enter script ..."
wget "${RE_STAKE_DESCRIPTOR}"

echo "Downloading reset_emergency script ..."
wget "${RESET_EMERGENCY_DESCRIPTOR}"

echo "Downloading constants script ..."
wget "${CONSTANTS_DESCRIPTOR}"

echo "adding ${SERVICE_NAME}.service to systemd"
cp ${SERVICE_NAME}.service ${SYSTEMD_DIR}

echo "adding reporter script to ${SRC_DIR}"
cp 'reporter.py' ${SRC_DIR}

echo "adding exit script to ${SRC_DIR}"
cp 'exit.py' ${SRC_DIR}

echo "adding enter script to ${SRC_DIR}"
cp 'enter.py' ${SRC_DIR}

echo "adding reset_emergency script to ${SRC_DIR}"
cp 'reset_emergency.py' ${SRC_DIR}

echo "adding constants script to ${REPORTER_DB}"
cp 'constants.json' ${REPORTER_DB}

echo "restarting ${SERVICE_NAME}.service"
sudo systemctl daemon-reload
sudo systemctl restart ${SERVICE_NAME}.service

echo "owning directories for git purposes 'git config --global --add safe.directory /usr/src/ton'"
echo "owning directories for git purposes 'git config --global --add safe.directory /usr/src/mytonctrl'"
git config --global --add safe.directory /usr/src/ton
git config --global --add safe.directory /usr/src/mytonctrl

echo "enable ${SERVICE_NAME}.service on every boot"
sudo systemctl enable ${SERVICE_NAME}.service

echo "all done"
