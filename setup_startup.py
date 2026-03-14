#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置开机自启动 - 最简单的方法
"""

import os
import sys
from pathlib import Path
import shutil


def setup_startup():
    """设置开机自启动"""
    # 获取程序路径
    if getattr(sys, 'frozen', False):
        # 打包后的 exe
        exe_path = sys.executable
    else:
        # 开发环境 - 使用打包后的版本
        exe_path = Path(__file__).parent / "dist" / "WeChatAI_Publisher_Portable" / "WeChatAI_Publisher.exe"
        if not exe_path.exists():
            print("错误: 未找到打包后的程序")
            print(f"请先运行: python build.py")
            input("\n按回车退出...")
            return False
    
    # Windows 启动文件夹路径
    startup_folder = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    
    # 快捷方式名称
    shortcut_name = "WeChatAI_Publisher.lnk"
    shortcut_path = startup_folder / shortcut_name
    
    try:
        # 创建快捷方式（使用 PowerShell）
        import subprocess
        ps_command = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.WorkingDirectory = "{Path(exe_path).parent}"
$Shortcut.IconLocation = "{exe_path},0"
$Shortcut.Save()
'''
        subprocess.run(["powershell", "-Command", ps_command], check=True)
        
        print("=" * 50)
        print("开机自启动设置成功！")
        print("=" * 50)
        print(f"\n程序路径: {exe_path}")
        print(f"快捷方式: {shortcut_path}")
        print("\n说明:")
        print("- 下次开机时会自动启动程序")
        print("- 如需取消，删除上述快捷方式即可")
        print("- 或在 任务管理器 > 启动 中禁用")
        print("\n" + "=" * 50)
        return True
        
    except Exception as e:
        print(f"设置失败: {e}")
        return False


def remove_startup():
    """取消开机自启动"""
    startup_folder = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_folder / "WeChatAI_Publisher.lnk"
    
    if shortcut_path.exists():
        shortcut_path.unlink()
        print("已取消开机自启动")
        return True
    else:
        print("未找到开机启动项")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("WeChat AI Publisher - 开机自启动设置")
    print("=" * 50)
    print("\n1. 设置开机自启动")
    print("2. 取消开机自启动")
    print("3. 退出")
    print()
    
    choice = input("请选择 (1-3): ").strip()
    
    if choice == "1":
        setup_startup()
    elif choice == "2":
        remove_startup()
    else:
        print("已退出")
    
    input("\n按回车键退出...")


if __name__ == '__main__':
    main()
