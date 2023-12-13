### move to home linux

# Check if the current user is 'ubuntu'
if [ "$(whoami)" = "ubuntu" ]; then
    echo "The current user is ubuntu."
    # Add commands to be executed if the user is ubuntu
else
    echo "The current user is not ubuntu."
    exit 1
fi

cd 
rm reporter-uninstall.sh
wget https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/reporter-uninstall.sh
chmod +x reporter-uninstall.sh
sudo ./reporter-uninstall.sh
echo 'uninstall reporter completed'
rm reporter-install.sh
wget https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/reporter-install.sh
chmod +x reporter-install.sh
./reporter-install.sh 

echo 'resotre exit.py'
mv /usr/src/reporter/_exit.py  /usr/src/reporter/exit.py

echo 'install and upgrader reporter completed , run systemctl status reporter'
