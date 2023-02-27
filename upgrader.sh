### move to home linux
cd 
systemctl status reporter
rm reporter-uninstall.sh
wget https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/reporter-uninstall.sh
chmod +x reporter-uninstall.sh
sudo ./reporter-uninstall.sh
systemctl status reporter
echo 'uninstall reporter completed'
rm reporter-install.sh
wget https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/reporter-install.sh
chmod +x reporter-install.sh
sudo ./reporter-install.sh
systemctl status reporter 

echo 'install and upgrader reporter completed'