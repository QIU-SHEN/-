#!/bin/bash
# 诊断脚本 - 检查Vue部署问题

echo "========== Vue部署诊断 =========="
echo ""

echo "[1] 检查dist目录内容:"
ls -la /root/dist/
echo ""

echo "[2] 检查index.html是否存在:"
if [ -f /root/dist/index.html ]; then
    echo "✅ index.html 存在"
    head -5 /root/dist/index.html
else
    echo "❌ index.html 不存在"
fi
echo ""

echo "[3] 检查Nginx配置:"
cat /etc/nginx/sites-available/vue-app-8443
echo ""

echo "[4] 检查Nginx是否在运行:"
ps aux | grep nginx | grep -v grep
echo ""

echo "[5] 检查端口监听:"
ss -tlnp | grep 8443
echo ""

echo "[6] 检查Nginx错误日志:"
tail -10 /var/log/nginx/error.log 2>/dev/null || echo "无错误日志"
echo ""

echo "[7] 测试本地访问:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8443/
echo ""

echo "========== 诊断完成 =========="
