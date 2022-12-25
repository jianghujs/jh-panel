#!/bin/bash

# 参考: https://docs.docker.com/engine/install/debian/
apt-get update
apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release -y

mkdir -p /etc/apt/keyrings
rm -rf /etc/apt/keyrings/docker.gpg
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null


apt-get update  

chmod a+r /etc/apt/keyrings/docker.gpg
apt-get update

export docker_version=20.10.6
version=$(apt-cache madison docker-ce | grep ${docker_version} | awk '{print $3}')
apt-get install docker-ce=${version} -y --allow-downgrades

# docker-compose
if [ -x "$(command -v docker-compose)" ]; then
  echo "Docker-compose had been installed"
else
  echo "Installing docker-compose..."
  cp -r ./docker-compose /usr/local/bin/
  chmod +x /usr/local/bin/docker-compose
  docker-compose -v
fi