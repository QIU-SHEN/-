#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat AI Publisher 打包脚本
生成单文件可执行程序（安全版本，不包含登录状态）
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def clean_old_builds():
    """清理旧的构建文件"""
    print("[1/4] 清理旧构建...")
    for dirname in ['build', 'dist']:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
            print(f"  ✓ 删除 {dirname}/")


def clean_login_state():
    """清理登录状态文件（重要安全措施）"""
    print("[2/4] 清理登录状态...")
    login_state = Path('data/rpa_state/wechat_login_state.json')
    if login_state.exists():
        login_state.unlink()
        print("  ⚠️ 已删除登录状态文件（安全）")
    else:
        print("  ✓ 无登录状态需要清理")


def build_executable():
    """使用 PyInstaller 构建可执行文件"""
    print("[3/4] 正在打包...")
    print("  这可能需要几分钟时间，请耐心等待...\n")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        'gui_app.py',
        '--onefile',
        '--windowed',
        '--name', 'WeChatAI_Publisher',
        '--add-data', 'config;config',
        '--add-data', 'src;src',
        '--hidden-import', 'webview',
        '--hidden-import', 'webview.platforms.winforms',
        '--hidden-import', 'yaml',
        '--hidden-import', 'requests',
        '--hidden-import', 'playwright',
        '--hidden-import', 'src.agents.research_agent',
        '--hidden-import', 'src.agents.writing_agent',
        '--hidden-import', 'src.agents.compliance_agent',
        '--hidden-import', 'src.agents.publish_agent',
        '--hidden-import', 'src.tools.rpa_tool',
        '--hidden-import', 'src.tools.wechat_api',
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'numpy',
        '--exclude-module', 'pandas',
        '--exclude-module', 'tkinter',
        '--clean',
    ]
    
    try:
        subprocess.check_call(cmd)
        print("\n  ✓ 打包成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ 打包失败: {e}")
        return False


def create_portable_version():
    """创建便携版目录结构"""
    print("[4/4] 创建便携版...")
    
    portable_dir = Path('dist/WeChatAI_Publisher_Portable')
    portable_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制主程序
    shutil.copy('dist/WeChatAI_Publisher.exe', portable_dir)
    print("  ✓ 复制主程序")
    
    # 复制配置文件
    shutil.copytree('config', portable_dir / 'config', dirs_exist_ok=True)
    print("  ✓ 复制配置文件")
    
    # 创建空的数据目录
    (portable_dir / 'data' / 'rpa_state').mkdir(parents=True, exist_ok=True)
    (portable_dir / 'data' / 'hot_topics').mkdir(parents=True, exist_ok=True)
    (portable_dir / 'data' / 'articles').mkdir(parents=True, exist_ok=True)
    print("  ✓ 创建数据目录")
    
    # 创建启动脚本
    with open(portable_dir / '启动.bat', 'w', encoding='utf-8') as f:
        f.write('''@echo off
chcp 65001 >nul
echo.
echo ===========================================
echo   WeChat AI Publisher
echo ===========================================
echo.
echo 首次使用需要扫码登录微信公众号
echo.
pause
echo 正在启动...
start WeChatAI_Publisher.exe
''')
    print("  ✓ 创建启动脚本")
    
    # 创建使用说明
    with open(portable_dir / '使用说明.txt', 'w', encoding='utf-8') as f:
        f.write('''WeChat AI Publisher 使用说明
============================================

【安全提示】
本程序打包时不包含任何登录信息
首次使用需要您自己扫码登录
登录状态仅保存在本机 data/rpa_state/ 目录

【使用步骤】
1. 双击 "启动.bat" 或直接运行 "WeChatAI_Publisher.exe"
2. 首次使用需扫码登录微信公众号平台
3. 选择新闻类型 -> 输入作者 -> 点击"一键发布"
4. 等待自动化流程完成（约2-3分钟）

【注意事项】
- 请勿将登录后的程序或 data/rpa_state/ 目录发给他人
- 如需分发，请先执行 "python build.py" 重新打包
- 程序需要 Edge 浏览器环境
- 需要网络连接用于获取热点和AI生成内容

【文件说明】
- WeChatAI_Publisher.exe: 主程序
- config/: 配置文件目录
- data/articles/: 生成的文章保存位置
- data/hot_topics/: 热点标题缓存
- data/rpa_state/: 登录状态（首次使用后生成）

============================================
''')
    print("  ✓ 创建使用说明")
    
    return portable_dir


def print_summary(portable_dir):
    """打印打包完成信息"""
    exe_size = Path('dist/WeChatAI_Publisher.exe').stat().st_size / (1024*1024)
    
    print("\n" + "="*50)
    print("打包完成！")
    print("="*50)
    print(f"\n单文件版本: dist/WeChatAI_Publisher.exe ({exe_size:.1f} MB)")
    print(f"便携版目录: {portable_dir}/")
    print("\n安全提示:")
    print("  ✓ 已自动清理登录状态")
    print("  ✓ 首次使用需要扫码登录")
    print("  ✓ 登录凭证仅保存在本机")
    print("\n使用方式:")
    print(f"  1. 进入 {portable_dir} 目录")
    print("  2. 双击 启动.bat 或直接运行 WeChatAI_Publisher.exe")
    print("  3. 首次需扫码登录，之后自动保持登录")
    print("\n" + "="*50)


def main():
    """主函数"""
    print("="*50)
    print("WeChat AI Publisher 打包工具")
    print("="*50 + "\n")
    
    # 检查必要文件
    if not Path('gui_app.py').exists():
        print("错误: 未找到 gui_app.py，请确保在正确目录运行")
        return False
    
    if not Path('config').exists():
        print("错误: 未找到 config 目录")
        return False
    
    # 执行打包流程
    clean_old_builds()
    clean_login_state()
    
    if not build_executable():
        return False
    
    portable_dir = create_portable_version()
    print_summary(portable_dir)
    
    return True


if __name__ == '__main__':
    success = main()
    input("\n按回车键退出...")
    sys.exit(0 if success else 1)
