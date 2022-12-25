#!/bin/bash

echo "uninstall Start"


# uninstall docker
apt-get purge docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-ce-rootless-extras -y
rm -rf /var/lib/docker
rm -rf /var/lib/containerd

# uninstall docker-compose
rm -rf /usr/local/bin/docker-compose


echo "Success"
