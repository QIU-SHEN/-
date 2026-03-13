#!/bin/bash
# 诊断502错误

echo "========== 502错误诊断 =========="
echo ""

echo "[1] 检查Nginx是否运行:"
ps aux | grep nginx | head -5
echo ""

echo "[2] 检查6006端口监听:"
ss -tlnp | grep 6006
echo ""

echo "[3] 检查Nginx配置:"
cat /etc/nginx/sites-available/vue-app-8443
echo ""

echo "[4] 测试本地访问:"
curl -v http://localhost:6006/ 2>&1 | head -20
echo ""

echo "[5] 检查Nginx错误日志:"
tail -5 /var/log/nginx/error.log
echo ""

echo "========== 诊断完成 =========="
