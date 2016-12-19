#! /bin/bash

TESTIP=192.168.31.1                           
                                               
ping -c4 ${TESTIP} > /dev/null               
                                               
if [ $? != 0 ]                               
then                                         
    logger -t $0 "WiFi seems down, restarting"
    ifdown --force wlan0                     
    sleep 5
    ifup wlan0                               
else                                        
    logger -t $0 "WiFi seems up."           
fi
