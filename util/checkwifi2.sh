#! /bin/bash

# google public DNS server
SERVER=8.8.8.8
                                               
ping -c4 ${SERVER} > /dev/null               
                                               
if [ $? != 0 ]                               
then                                         
    logger -t $0 "WiFi seems down, restarting"
    sudo reboot
fi
