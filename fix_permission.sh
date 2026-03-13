#!/bin/bash
# 检查并修复权限问题

echo "========== 权限诊断 =========="

echo "[1] 检查 /root/dist 权限:"
ls -ld /root/dist/
echo ""

echo "[2] 检查 index.html 权限:"
ls -la /root/dist/index.html
echo ""

echo "[3] 测试 www-data 用户访问:"
sudo -u www-data ls /root/dist/ 2>&1 || echo "❌ www-data 无法访问"
echo ""

echo "[4] 修复权限..."
# 给Nginx用户读取权限
chmod 755 /root/dist
chmod 644 /root/dist/index.html
chmod -R 755 /root/dist/assets 2>/dev/null || true
echo "✅ 权限已修复"
echo ""

echo "[5] 再次测试 www-data 访问:"
sudo -u www-data ls /root/dist/ 2>&1
echo ""

echo "========== 重启Nginx =========="
sudo pkill nginx && sudo nginx
echo "Nginx已重启"
