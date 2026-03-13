#!/bin/bash
# Vue部署一键修复脚本

echo "========== Vue部署修复 =========="

# 1. 检查Nginx配置是否存在
if [ ! -f /etc/nginx/sites-available/vue-app-8443 ]; then
    echo "创建Nginx配置..."
    cat > /etc/nginx/sites-available/vue-app-8443 << 'EOF'
server {
    listen 8443 ssl;
    server_name _;
    ssl_certificate /etc/nginx/ssl.crt;
    ssl_certificate_key /etc/nginx/ssl.key;
    root /root/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF
fi

# 2. 启用配置
ln -sf /etc/nginx/sites-available/vue-app-8443 /etc/nginx/sites-enabled/

# 3. 测试配置
echo "测试Nginx配置..."
nginx -t

if [ $? -ne 0 ]; then
    echo "❌ 配置测试失败"
    exit 1
fi

# 4. 重启Nginx
echo "重启Nginx..."
pkill nginx 2>/dev/null
sleep 1
nginx

# 5. 验证
echo "验证部署..."
sleep 2
curl -s http://localhost:8443/ | head -10

echo ""
echo "========== 修复完成 =========="
echo "请访问: https://uu622404-cr6v-4f1cecfa.bjb2.seetacloud.com:8443"
