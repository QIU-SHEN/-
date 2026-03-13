#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志模块 - 详细记录RPA操作步骤
使用ASCII字符避免Windows控制台编码问题
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class RPALogger:
    """RPA专用日志记录器"""
    
    def __init__(self, name: str = "RPA", log_dir: str = "./logs"):
        """
        初始化日志记录器
        
        Args:
            name: 日志名称
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成日志文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"rpa_run_{timestamp}.log"
        
        # 创建日志记录器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 清除已有处理器
        self.logger.handlers = []
        
        # 文件处理器（详细日志，使用UTF-8编码）
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器（简洁输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        self.step_count = 0
        
    def step(self, message: str):
        """记录操作步骤"""
        self.step_count += 1
        self.logger.info(f"[步骤 {self.step_count}] {message}")
        
    def action(self, action_type: str, target: str, details: str = ""):
        """
        记录用户操作
        
        Args:
            action_type: 操作类型（点击、填写、检测等）
            target: 操作目标
            details: 详细信息
        """
        msg = f"[操作] {action_type} | 目标: {target}"
        if details:
            msg += f" | 详情: {details}"
        self.logger.info(msg)
        
    def success(self, message: str):
        """记录成功操作 - 使用ASCII字符[OK]替代Unicode"""
        self.logger.info(f"[OK] {message}")
        
    def error(self, message: str, exception: Exception = None):
        """
        记录错误 - 使用ASCII字符[FAIL]替代Unicode
        
        Args:
            message: 错误描述
            exception: 异常对象
        """
        if exception:
            import traceback
            error_detail = f"{message}\n异常类型: {type(exception).__name__}\n"
            error_detail += f"异常信息: {str(exception)}\n"
            error_detail += f"堆栈跟踪:\n{traceback.format_exc()}"
            self.logger.error(f"[FAIL] {error_detail}")
        else:
            self.logger.error(f"[FAIL] {message}")
            
    def warning(self, message: str):
        """记录警告 - 使用ASCII字符[WARN]替代Unicode"""
        self.logger.warning(f"[WARN] {message}")
        
    def debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(f"[DEBUG] {message}")
        
    def info(self, message: str):
        """记录一般信息"""
        self.logger.info(f"[INFO] {message}")
        
    def selector(self, selector: str, found: bool, timeout: float = None):
        """
        记录选择器查找结果 - 使用ASCII字符[OK]/[FAIL]替代Unicode
        
        Args:
            selector: CSS选择器
            found: 是否找到
            timeout: 超时时间
        """
        status = "找到" if found else "未找到"
        msg = f"[选择器] {selector} -> {status}"
        if timeout:
            msg += f" (超时: {timeout}s)"
        if found:
            self.logger.info(f"[OK] {msg}")
        else:
            self.logger.error(f"[FAIL] {msg}")
            
    def page_state(self, url: str = None, title: str = None):
        """记录页面状态"""
        msg = "[页面状态]"
        if url:
            msg += f" URL: {url}"
        if title:
            msg += f" 标题: {title}"
        self.logger.info(msg)
        
    def timing(self, action: str, elapsed: float):
        """记录操作耗时"""
        self.logger.info(f"[耗时] {action} 用时 {elapsed:.2f}s")
        
    def screenshot(self, path: str, reason: str = ""):
        """记录截图"""
        msg = f"[截图] 已保存: {path}"
        if reason:
            msg += f" (原因: {reason})"
        self.logger.info(msg)
        
    def summary(self, success: bool, total_steps: int = None):
        """记录执行摘要"""
        total = total_steps or self.step_count
        if success:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"[完成] 执行成功，共 {total} 个步骤")
            self.logger.info(f"[日志] 详细日志: {self.log_file}")
            self.logger.info(f"{'='*50}")
        else:
            self.logger.error(f"\n{'='*50}")
            self.logger.error(f"[终止] 执行失败，共完成 {total} 个步骤")
            self.logger.error(f"[日志] 详细日志: {self.log_file}")
            self.logger.error(f"{'='*50}")


# 全局日志实例
_rpa_logger = None

def get_logger(name: str = "RPA", log_dir: str = "./logs") -> RPALogger:
    """获取日志记录器实例"""
    global _rpa_logger
    if _rpa_logger is None:
        _rpa_logger = RPALogger(name, log_dir)
    return _rpa_logger


def reset_logger():
    """重置日志记录器（用于新的运行）"""
    global _rpa_logger
    _rpa_logger = None
