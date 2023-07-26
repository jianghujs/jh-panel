# nfs-util

# 安装卸载nfs-util

apt-get install nfs-kernel-server

apt-get remove nfs-kernel-server
apt-get remove nfs-common


# NFS使用教程：https://blog.csdn.net/tdw2011/article/details/130082434

# 共享
echo "/root/test_share 192.168.3.60(rw,sync,no_root_squash,insecure)" >> /etc/exports
/etc/init.d/nfs-kernel-server  restart


# 查看共享资源
showmount -e 192.168.3.63

# 挂载
mount -t nfs 192.168.3.63:/root/test_share /root/test_share_client

# 查看容量
df -h

# 开机自动挂载
echo "192.168.3.63:/root/test_share /root/test_share_client nfs defaults 0 0" >> /etc/fstab