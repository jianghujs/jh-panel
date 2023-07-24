#!/bin/bash

# Prompt the user for the username
read -p "请输入在xrdp远程连接时需要自动登出的用户: " username

# Create the auto_logout_user.sh script
echo "#!/bin/bash

# Check if a user is logged in
if who | grep -q \"^$username\"; then
    # If a user is logged in, log them out
    pkill -KILL -u $username
fi" | sudo tee /etc/xrdp/auto_logout_$username.sh > /dev/null

echo "配置登陆脚本成功!"

# Make the script executable
sudo chmod +x /etc/xrdp/auto_logout_$username.sh

# Check if startwm.sh already contains the line
if ! sudo grep -q "auto_logout_$username.sh" /etc/xrdp/startwm.sh; then
    # If not, add the script to startwm.sh
    sudo sed -i "1i\\/etc/xrdp/auto_logout_$username.sh" /etc/xrdp/startwm.sh
fi
echo "配置完成！"
