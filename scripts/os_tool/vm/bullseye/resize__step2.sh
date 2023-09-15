echo "分区调整完成✅"
mkswap /dev/sda5
swapon /dev/sda5
echo "启用swap分区完成✅"

resize2fs /dev/sda1
echo "扩大/dev/sda1文件系统完成✅"


echo ""
echo "===========================扩容流程已完成✅=========================="
fdisk -l /dev/sda
echo "====================================================================="



