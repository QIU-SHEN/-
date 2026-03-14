#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器 - 支持定时数据分析和自动发布
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self, config_file: str = "./config/scheduler.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.callbacks = {}
        
        # 默认配置
        self.config = {
            'analytics_enabled': False,
            'analytics_time': '09:00',  # 数据分析时间
            'publish_enabled': False,
            'publish_time': '10:00',    # 自动发布时间
            'publish_category': 'tech',
            'publish_author': 'AI小编',
            'last_run': {
                'analytics': None,
                'publish': None
            }
        }
        
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
            except Exception as e:
                print(f"[Scheduler] 加载配置失败: {e}")
    
    def _save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Scheduler] 保存配置失败: {e}")
    
    def register_callback(self, task_type: str, callback: Callable):
        """
        注册任务回调函数
        
        Args:
            task_type: 'analytics' 或 'publish'
            callback: 回调函数
        """
        self.callbacks[task_type] = callback
        print(f"[Scheduler] 注册回调: {task_type}")
    
    def start(self):
        """启动定时任务调度器"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[Scheduler] 定时任务调度器已启动")
    
    def stop(self):
        """停止定时任务调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[Scheduler] 定时任务调度器已停止")
    
    def _run_loop(self):
        """主循环 - 每分钟检查一次"""
        while self.running:
            try:
                current_time = datetime.now()
                current_time_str = current_time.strftime("%H:%M")
                current_date = current_time.strftime("%Y-%m-%d")
                
                # 检查数据分析任务
                if self.config['analytics_enabled']:
                    if current_time_str == self.config['analytics_time']:
                        # 检查今天是否已执行
                        last_run = self.config['last_run'].get('analytics')
                        if last_run != current_date:
                            self._execute_task('analytics')
                            self.config['last_run']['analytics'] = current_date
                            self._save_config()
                
                # 检查自动发布任务
                if self.config['publish_enabled']:
                    if current_time_str == self.config['publish_time']:
                        # 检查今天是否已执行
                        last_run = self.config['last_run'].get('publish')
                        if last_run != current_date:
                            self._execute_task('publish')
                            self.config['last_run']['publish'] = current_date
                            self._save_config()
                
                # 每分钟检查一次
                time.sleep(60)
                
            except Exception as e:
                print(f"[Scheduler] 调度异常: {e}")
                time.sleep(60)
    
    def _execute_task(self, task_type: str):
        """执行任务"""
        print(f"[Scheduler] 执行定时任务: {task_type} at {datetime.now()}")
        
        callback = self.callbacks.get(task_type)
        if callback:
            try:
                # 在后台线程中执行
                task_thread = threading.Thread(target=callback, daemon=True)
                task_thread.start()
                print(f"[Scheduler] 任务 {task_type} 已启动")
            except Exception as e:
                print(f"[Scheduler] 任务执行失败: {e}")
        else:
            print(f"[Scheduler] 未找到回调函数: {task_type}")
    
    def update_config(self, **kwargs):
        """
        更新配置
        
        Args:
            analytics_enabled: 是否启用定时分析
            analytics_time: 分析时间 (HH:MM)
            publish_enabled: 是否启用定时发布
            publish_time: 发布时间 (HH:MM)
            publish_category: 发布分类
            publish_author: 发布作者
        """
        self.config.update(kwargs)
        self._save_config()
        print(f"[Scheduler] 配置已更新: {kwargs}")
    
    def get_config(self) -> dict:
        """获取当前配置"""
        return self.config.copy()
    
    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self.running


# 全局调度器实例
_scheduler_instance = None


def get_scheduler() -> TaskScheduler:
    """获取调度器实例（单例）"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance


def start_scheduler():
    """启动调度器"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """停止调度器"""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None
