#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开机自启动管理器
"""

import os
import sys
import json
from pathlib import Path
import subprocess


class StartupManager:
    """开机自启动管理"""
    
    def __init__(self):
        self.startup_folder = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        self.shortcut_name = "WeChatAI_Publisher.lnk"
        self.config_file = Path("./config/settings.json")
        
    def is_enabled(self) -> bool:
        """检查是否已启用开机自启动"""
        shortcut_path = self.startup_folder / self.shortcut_name
        return shortcut_path.exists()
    
    def enable(self) -> bool:
        """启用开机自启动"""
        try:
            # 获取程序路径
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = Path(__file__).parent.parent.parent / "dist" / "WeChatAI_Publisher_Portable" / "WeChatAI_Publisher.exe"
                if not exe_path.exists():
                    print("[StartupManager] 未找到打包后的程序")
                    return False
            
            shortcut_path = self.startup_folder / self.shortcut_name
            
            # 创建快捷方式
            ps_command = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.WorkingDirectory = "{Path(exe_path).parent}"
$Shortcut.IconLocation = "{exe_path},0"
$Shortcut.Save()
'''
            subprocess.run(["powershell", "-Command", ps_command], check=True, capture_output=True)
            
            # 保存设置
            self._save_setting(True)
            
            print(f"[StartupManager] 已启用开机自启动")
            return True
            
        except Exception as e:
            print(f"[StartupManager] 启用失败: {e}")
            return False
    
    def disable(self) -> bool:
        """禁用开机自启动"""
        try:
            shortcut_path = self.startup_folder / self.shortcut_name
            if shortcut_path.exists():
                shortcut_path.unlink()
            
            # 保存设置
            self._save_setting(False)
            
            print(f"[StartupManager] 已禁用开机自启动")
            return True
            
        except Exception as e:
            print(f"[StartupManager] 禁用失败: {e}")
            return False
    
    def toggle(self, enabled: bool) -> bool:
        """切换开机自启动状态"""
        if enabled:
            return self.enable()
        else:
            return self.disable()
    
    def _save_setting(self, enabled: bool):
        """保存设置到配置文件"""
        try:
            settings = {}
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            settings['startup_enabled'] = enabled
            
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[StartupManager] 保存设置失败: {e}")
    
    def get_setting(self) -> bool:
        """从配置文件读取设置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('startup_enabled', False)
        except Exception as e:
            print(f"[StartupManager] 读取设置失败: {e}")
        return False


# 便捷函数
def is_startup_enabled() -> bool:
    """检查是否启用开机自启动"""
    return StartupManager().is_enabled()


def set_startup(enabled: bool) -> bool:
    """设置开机自启动状态"""
    return StartupManager().toggle(enabled)
