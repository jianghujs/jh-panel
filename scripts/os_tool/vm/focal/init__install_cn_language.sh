# 安装中文环境
sed -i -e "s/# en_US.UTF-8.*/en_US.UTF-8 UTF-8/" /etc/locale.gen
sed -i -e "s/# zh_CN.UTF-8.*/zh_CN.UTF-8 UTF-8/" /etc/locale.gen
sed -i -e "s/# zh_CN.GBK.*/zh_CN.GBK GBK/" /etc/locale.gen
sed -i -e "s/# zh_CN.GB2312.*/zh_CN.GB2312 GB2312/" /etc/locale.gen
apt install -y locales ttf-wqy-microhei
dpkg-reconfigure --frontend=noninteractive locales 