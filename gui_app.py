#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat AI Publisher - GUI 版本 (微信风格)
"""

import sys
import json
import threading
import webview
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.research_agent import ResearchAgent
from src.agents.writing_agent import WritingAgent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.publish_agent import PublishAgent


class Api:
    """后端 API"""
    
    def __init__(self):
        self.current_article_file: Optional[str] = None
        self.current_hot_file: Optional[str] = None
        self.is_running: bool = False
        
    def log(self, message: str, type_: str = "info"):
        """添加日志"""
        if hasattr(self, 'window'):
            try:
                self.window.evaluate_js(f"addLog('{self._escape(message)}', '{type_}')")
            except:
                pass
    
    def _escape(self, s: str) -> str:
        """转义字符串用于 JS"""
        return s.replace("'", "\\'").replace("\n", "\\n")
    
    def get_categories(self) -> list:
        """获取新闻类型"""
        return [
            {"id": "tech", "name": "科技", "icon": "💻"},
            {"id": "finance", "name": "财经", "icon": "💰"},
            {"id": "entertainment", "name": "娱乐", "icon": "🎬"},
            {"id": "sports", "name": "体育", "icon": "⚽"},
            {"id": "society", "name": "社会", "icon": "🏘️"},
            {"id": "world", "name": "国际", "icon": "🌍"},
            {"id": "general", "name": "综合", "icon": "📰"},
        ]
    
    def start_publish(self, category: str, author: str) -> Dict:
        """开始发布"""
        if self.is_running:
            return {"success": False, "error": "已有任务在运行"}
        
        self.is_running = True
        
        thread = threading.Thread(target=self._run_pipeline, args=(category, author))
        thread.daemon = True
        thread.start()
        
        return {"success": True}
    
    def _run_pipeline(self, category: str, author: str):
        """运行流程"""
        try:
            self._update_step(1, "running")
            self.log("正在获取热点新闻...")
            
            try:
                research_agent = ResearchAgent()
                self.current_hot_file = research_agent.run(category)
                self.log("[OK] 热点获取完成")
                self._update_step(1, "completed")
            except Exception as e:
                self.log(f"[FAIL] 获取热点失败: {e}", "error")
                self._update_step(1, "error")
                self.is_running = False
                return
            
            self._update_step(2, "running")
            self.log("AI正在撰写文章...")
            
            try:
                writing_agent = WritingAgent()
                self.current_article_file = writing_agent.run(self.current_hot_file, author)
                self.log("[OK] 文章撰写完成")
                self._update_step(2, "completed")
            except Exception as e:
                self.log(f"[FAIL] 撰写失败: {e}", "error")
                self._update_step(2, "error")
                self.is_running = False
                return
            
            self._update_step(3, "running")
            self.log("正在进行合规审查...")
            
            max_rewrite_attempts = 2  # 最多重写2次
            rewrite_count = 0
            
            while rewrite_count < max_rewrite_attempts:
                try:
                    compliance_agent = ComplianceAgent(max_check_rounds=2)
                    passed, report = compliance_agent.run(self.current_article_file)
                    
                    if passed:
                        self.log("[OK] 审查通过")
                        self._update_step(3, "completed")
                        break
                    else:
                        rewrite_count += 1
                        if rewrite_count >= max_rewrite_attempts:
                            self.log(f"[FAIL] 审查未通过，已达最大重写次数({max_rewrite_attempts})", "error")
                            self.log(f"[FAIL] 未通过原因: {report}", "error")
                            self._update_step(3, "error")
                            self.is_running = False
                            return
                        
                        self.log(f"[WARN] 审查未通过(第{rewrite_count}次)，原因: {report}", "warning")
                        self.log(f"[WARN] 正在根据反馈重写文章...")
                        
                        # 读取当前文章并重写
                        try:
                            with open(self.current_article_file, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                            
                            # 解析文章信息
                            title = lines[0].replace('标题：', '').strip()
                            author = lines[1].replace('作者：', '').strip()
                            category = lines[2].replace('类型：', '').strip()
                            content = ''.join(lines[6:]).strip()
                            
                            # 调用重写
                            writing_agent = WritingAgent()
                            new_content = writing_agent.rewrite_article(
                                title=title,
                                author=author,
                                category=category,
                                content=content,
                                feedback=report
                            )
                            
                            # 保存重写后的文章
                            with open(self.current_article_file, 'w', encoding='utf-8') as f:
                                f.write(f"标题：{title}\n")
                                f.write(f"作者：{author}\n")
                                f.write(f"类型：{category}\n")
                                f.write(f"字数：{len(new_content)}\n")
                                f.write(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                f.write("=" * 50 + "\n\n")
                                f.write(new_content)
                            
                            self.log(f"[OK] 文章已重写，重新审查...")
                            
                        except Exception as rewrite_error:
                            self.log(f"[FAIL] 重写失败: {rewrite_error}", "error")
                            self._update_step(3, "error")
                            self.is_running = False
                            return
                        
                except Exception as e:
                    self.log(f"! 审查异常: {e}", "warning")
                    self._update_step(3, "completed")
                    break
            
            self._update_step(4, "running")
            self.log("正在发布文章...")
            self.log("请扫码确认")
            
            try:
                import yaml
                config_file = Path("./config/config.yaml")
                config = yaml.safe_load(open(config_file, 'r', encoding='utf-8')) if config_file.exists() else {'wechat': {'use_rpa': True}}
                config['wechat']['auto_publish'] = True
                
                publish_agent = PublishAgent(config)
                result = publish_agent.run_from_file(self.current_article_file)
                
                if result.get('status') == 'success':
                    self.log("[OK] [OK] [OK] 发布成功!")
                    self._update_step(4, "completed")
                else:
                    self.log(f"[FAIL] 发布失败", "error")
                    self._update_step(4, "error")
            except Exception as e:
                self.log(f"[FAIL] 发布出错: {e}", "error")
                self._update_step(4, "error")
            
            self.is_running = False
            
        except Exception as e:
            self.log(f"流程异常: {e}", "error")
            self.is_running = False
    
    def _update_step(self, step: int, state: str):
        """更新步骤状态"""
        if hasattr(self, 'window'):
            try:
                self.window.evaluate_js(f"updateStep({step}, '{state}')")
            except:
                pass
    
    def is_task_running(self) -> bool:
        return self.is_running
    
    def check_browser(self) -> Dict:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                browser.close()
            return {"installed": True}
        except:
            return {"installed": False}
    
    def install_browser(self) -> Dict:
        try:
            import subprocess
            self.log("正在下载浏览器...")
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            self.log("浏览器安装完成")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_startup_status(self) -> Dict:
        """获取开机自启动状态"""
        try:
            from src.utils.startup_manager import StartupManager
            manager = StartupManager()
            enabled = manager.is_enabled()
            return {"success": True, "enabled": enabled}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def toggle_startup(self, enabled: bool) -> Dict:
        """设置开机自启动"""
        try:
            from src.utils.startup_manager import StartupManager
            manager = StartupManager()
            result = manager.toggle(enabled)
            if result:
                status = "启用" if enabled else "禁用"
                self.log(f"[设置] 开机自启动已{status}")
                return {"success": True, "enabled": enabled}
            else:
                return {"success": False, "error": "设置失败"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_scheduler_config(self) -> Dict:
        """获取定时任务配置"""
        try:
            from src.utils.scheduler import get_scheduler
            scheduler = get_scheduler()
            config = scheduler.get_config()
            return {"success": True, "config": config}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_scheduler_config(self, config: Dict) -> Dict:
        """更新定时任务配置"""
        try:
            from src.utils.scheduler import get_scheduler
            scheduler = get_scheduler()
            
            # 更新配置
            scheduler.update_config(**config)
            
            # 如果启用了任何定时任务，确保调度器在运行
            if config.get('analytics_enabled') or config.get('publish_enabled'):
                if not scheduler.running:
                    self._setup_scheduler_callbacks(scheduler)
                    scheduler.start()
                    self.log("[Scheduler] 定时任务调度器已启动")
            
            self.log("[设置] 定时任务配置已更新")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _setup_scheduler_callbacks(self, scheduler):
        """设置定时任务回调"""
        # 注册数据分析回调
        def analytics_callback():
            self.log("[Scheduler] 执行定时数据分析...")
            try:
                from src.agents.analytics_agent import AnalyticsAgent
                agent = AnalyticsAgent()
                report = agent.run()
                self.log(f"[Scheduler] [OK] 数据分析完成，昨日阅读: {report.yesterday.read_count}")
            except Exception as e:
                self.log(f"[Scheduler] [FAIL] 数据分析失败: {e}", "error")
        
        # 注册自动发布回调
        def publish_callback():
            self.log("[Scheduler] 执行定时发布...")
            # 在新线程中执行发布流程，避免阻塞调度器
            thread = threading.Thread(target=self._scheduled_publish, daemon=True)
            thread.start()
        
        scheduler.register_callback('analytics', analytics_callback)
        scheduler.register_callback('publish', publish_callback)
    
    def _scheduled_publish(self):
        """定时发布任务"""
        try:
            from src.utils.scheduler import get_scheduler
            config = get_scheduler().get_config()
            category = config.get('publish_category', 'tech')
            author = config.get('publish_author', 'AI小编')
            
            self.log(f"[Scheduler] 开始自动发布流程: {category}")
            
            # 获取热点
            from src.agents.research_agent import ResearchAgent
            research = ResearchAgent()
            hot_file = research.run(category)
            
            # 写作
            from src.agents.writing_agent import WritingAgent
            writer = WritingAgent()
            article_file = writer.run(hot_file, author)
            
            # 审查
            from src.agents.compliance_agent import ComplianceAgent
            compliance = ComplianceAgent(max_check_rounds=2)
            passed, report = compliance.run(article_file)
            
            if not passed:
                self.log(f"[Scheduler] [FAIL] 审查未通过: {report}", "error")
                return
            
            # 发布
            import yaml
            cfg_file = Path("./config/config.yaml")
            cfg = yaml.safe_load(open(cfg_file, 'r', encoding='utf-8')) if cfg_file.exists() else {'wechat': {'use_rpa': True}}
            cfg['wechat']['auto_publish'] = True
            
            from src.agents.publish_agent import PublishAgent
            publish = PublishAgent(cfg)
            result = publish.run_from_file(article_file)
            
            if result.get('status') == 'success':
                self.log("[Scheduler] [OK] [OK] [OK] 定时发布成功!")
            else:
                self.log(f"[Scheduler] [FAIL] 发布失败", "error")
                
        except Exception as e:
            self.log(f"[Scheduler] [FAIL] 定时发布异常: {e}", "error")
    
    def run_analytics(self) -> Dict:
        """运行数据分析"""
        if self.is_running:
            return {"success": False, "error": "已有任务在运行"}
        
        self.is_running = True
        self.log("[Analytics] 开始数据分析...")
        self.log("[Analytics] 将打开浏览器，请扫码登录")
        
        def analytics_task():
            try:
                from src.agents.analytics_agent import AnalyticsAgent
                
                agent = AnalyticsAgent()
                report = agent.run()
                
                self.log(f"[Analytics] [OK] 数据获取成功")
                self.log(f"[Analytics] 昨日阅读: {report.yesterday.read_count}")
                self.log(f"[Analytics] 昨日点赞: {report.yesterday.like_count}")
                self.log(f"[Analytics] 昨日分享: {report.yesterday.share_count}")
                self.log(f"[Analytics] 建议发布时间: {report.best_publish_time}")
                self.log(f"[Analytics] 优化建议已保存，下次创作将自动应用")
                
            except Exception as e:
                self.log(f"[Analytics] [FAIL] 分析失败: {e}", "error")
            finally:
                self.is_running = False
                # 通知前端重置状态
                if hasattr(self, 'window'):
                    try:
                        self.window.evaluate_js("analyticsCompleted()")
                    except:
                        pass
        
        threading.Thread(target=analytics_task, daemon=True).start()
        return {"success": True}


def create_html() -> str:
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=400, initial-scale=1.0">
    <title>WeChat AI Publisher</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #ededed;
            width: 400px;
            min-height: 100vh;
            margin: 0 auto;
        }
        
        .container {
            background: #f5f5f5;
            min-height: 100vh;
            padding-bottom: 20px;
        }
        
        /* 顶部标题栏 - 微信绿 */
        .header {
            background: #07c160;
            color: white;
            padding: 15px 20px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header h1 {
            font-size: 18px;
            font-weight: 500;
        }
        
        .header p {
            font-size: 12px;
            opacity: 0.9;
            margin-top: 4px;
        }
        
        .header-settings {
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            cursor: pointer;
            font-size: 20px;
            opacity: 0.9;
            transition: opacity 0.2s;
        }
        
        .header-settings:hover {
            opacity: 1;
        }
        
        /* 设置弹窗 */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s;
        }
        
        .modal-overlay.active {
            opacity: 1;
            visibility: visible;
        }
        
        .modal {
            background: white;
            border-radius: 12px;
            width: 320px;
            max-width: 90%;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            transform: scale(0.9);
            transition: transform 0.3s;
        }
        
        .modal-overlay.active .modal {
            transform: scale(1);
        }
        
        .modal-header {
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-header h3 {
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }
        
        .modal-close {
            font-size: 24px;
            cursor: pointer;
            color: #999;
            line-height: 1;
        }
        
        .modal-close:hover {
            color: #333;
        }
        
        .modal-body {
            padding: 10px 20px;
        }
        
        /* 开关样式 */
        .switch-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .switch-item:last-child {
            border-bottom: none;
        }
        
        .switch-info {
            flex: 1;
        }
        
        .switch-label {
            font-size: 14px;
            color: #333;
            display: block;
        }
        
        .switch-desc {
            font-size: 12px;
            color: #999;
            margin-top: 4px;
            display: block;
        }
        
        .switch {
            position: relative;
            width: 50px;
            height: 28px;
            flex-shrink: 0;
            margin-left: 10px;
        }
        
        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: .3s;
            border-radius: 28px;
        }
        
        .slider:before {
            position: absolute;
            content: "";
            height: 22px;
            width: 22px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }
        
        input:checked + .slider {
            background-color: #07c160;
        }
        
        input:checked + .slider:before {
            transform: translateX(22px);
        }
        
        /* 内容区 */
        .content {
            padding: 15px;
        }
        
        /* 卡片样式 */
        .card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        .card-title {
            font-size: 14px;
            color: #333;
            font-weight: 500;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        /* 步骤指示器 */
        .steps {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
        }
        
        .step {
            display: flex;
            flex-direction: column;
            align-items: center;
            flex: 1;
            position: relative;
        }
        
        .step:not(:last-child)::after {
            content: '';
            position: absolute;
            top: 10px;
            right: -50%;
            width: 100%;
            height: 2px;
            background: #e0e0e0;
            z-index: 0;
        }
        
        .step.completed:not(:last-child)::after {
            background: #07c160;
        }
        
        .step-dot {
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: #e0e0e0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            color: #999;
            position: relative;
            z-index: 1;
            transition: all 0.3s;
        }
        
        .step.active .step-dot {
            background: #07c160;
            color: white;
            animation: pulse 1.5s infinite;
        }
        
        .step.completed .step-dot {
            background: #07c160;
            color: white;
        }
        
        .step.error .step-dot {
            background: #fa5151;
            color: white;
        }
        
        .step-label {
            font-size: 11px;
            color: #999;
            margin-top: 5px;
        }
        
        .step.active .step-label,
        .step.completed .step-label {
            color: #07c160;
        }
        
        .step.error .step-label {
            color: #fa5151;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        /* 类型选择 - 网格 */
        .type-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
        }
        
        .type-item {
            background: #f7f7f7;
            border: 2px solid transparent;
            border-radius: 8px;
            padding: 12px 5px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .type-item:hover {
            background: #e8f5e9;
        }
        
        .type-item.selected {
            border-color: #07c160;
            background: #e8f5e9;
        }
        
        .type-icon {
            font-size: 24px;
            margin-bottom: 4px;
        }
        
        .type-name {
            font-size: 12px;
            color: #666;
        }
        
        .type-item.selected .type-name {
            color: #07c160;
            font-weight: 500;
        }
        
        /* 输入框 */
        .input-group {
            margin-top: 5px;
        }
        
        .input-group label {
            display: block;
            font-size: 12px;
            color: #999;
            margin-bottom: 6px;
        }
        
        .input-group input {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            background: #fafafa;
            transition: border-color 0.2s;
        }
        
        .input-group input:focus {
            outline: none;
            border-color: #07c160;
            background: white;
        }
        
        /* 按钮 */
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: #07c160;
            color: white;
        }
        
        .btn-primary:hover:not(:disabled) {
            background: #06ad56;
        }
        
        .btn-primary:disabled {
            background: #9edfb8;
            cursor: not-allowed;
        }
        
        .btn-secondary {
            background: #f2f2f2;
            color: #333;
        }
        
        /* 日志区 */
        .log-container {
            background: #1e1e1e;
            border-radius: 6px;
            padding: 12px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            line-height: 1.5;
        }
        
        .log-entry {
            margin-bottom: 3px;
            color: #ddd;
        }
        
        .log-time {
            color: #666;
            margin-right: 6px;
        }
        
        .log-success { color: #4CAF50; }
        .log-error { color: #fa5151; }
        .log-warning { color: #ffc107; }
        
        /* 提示卡片 */
        .tip-card {
            background: #fffbe6;
            border: 1px solid #ffe58f;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 12px;
        }
        
        .tip-card h4 {
            color: #d48806;
            font-size: 13px;
            margin-bottom: 5px;
        }
        
        .tip-card p {
            color: #d48806;
            font-size: 12px;
        }
        
        /* 隐藏 */
        .hidden {
            display: none !important;
        }
        
        /* 加载动画 */
        .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>WeChat AI Publisher</h1>
            <p>自动获取热点 · AI写作 · 一键发布</p>
            <div class="header-settings" onclick="openSettings()" title="设置">⚙️</div>
        </div>
        
        <!-- 设置弹窗 -->
        <div class="modal-overlay" id="settingsModal">
            <div class="modal">
                <div class="modal-header">
                    <h3>设置</h3>
                    <span class="modal-close" onclick="closeSettings()">&times;</span>
                </div>
                <div class="modal-body">
                    <!-- 开机自启动 -->
                    <div class="switch-item">
                        <div class="switch-info">
                            <span class="switch-label">开机自启动</span>
                            <span class="switch-desc">系统启动时自动运行本程序</span>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="startupSwitch" onchange="toggleStartup(this)">
                            <span class="slider"></span>
                        </label>
                    </div>
                    
                    <!-- 分隔线 -->
                    <div style="border-top: 1px solid #eee; margin: 15px 0;"></div>
                    
                    <!-- 定时数据分析 -->
                    <div class="switch-item">
                        <div class="switch-info">
                            <span class="switch-label">定时数据分析</span>
                            <span class="switch-desc">每天自动采集昨日数据</span>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="schedulerAnalyticsEnabled" onchange="toggleSchedulerAnalytics(this)">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="time-picker" id="analyticsTimePicker" style="margin-bottom: 15px; padding-left: 10px;">
                        <label style="font-size: 13px; color: #666; margin-right: 10px;">执行时间:</label>
                        <input type="time" id="analyticsTime" value="09:00" onchange="updateSchedulerConfig()" style="padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
                    </div>
                    
                    <!-- 定时自动发布 -->
                    <div class="switch-item">
                        <div class="switch-info">
                            <span class="switch-label">定时自动发布</span>
                            <span class="switch-desc">每天自动生成并发布文章</span>
                        </div>
                        <label class="switch">
                            <input type="checkbox" id="schedulerPublishEnabled" onchange="toggleSchedulerPublish(this)">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div id="publishConfig" style="padding-left: 10px; display: none;">
                        <div style="margin-bottom: 10px;">
                            <label style="font-size: 13px; color: #666; margin-right: 10px;">执行时间:</label>
                            <input type="time" id="publishTime" value="10:00" onchange="updateSchedulerConfig()" style="padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
                        </div>
                        <div style="margin-bottom: 10px;">
                            <label style="font-size: 13px; color: #666; margin-right: 10px;">文章类型:</label>
                            <select id="schedulerCategory" onchange="updateSchedulerConfig()" style="padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 120px;">
                                <option value="tech">科技</option>
                                <option value="finance">财经</option>
                                <option value="entertainment">娱乐</option>
                                <option value="sports">体育</option>
                                <option value="society">社会</option>
                                <option value="world">国际</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size: 13px; color: #666; margin-right: 10px;">作者名称:</label>
                            <input type="text" id="schedulerAuthor" value="AI小编" onchange="updateSchedulerConfig()" style="padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; width: 120px;">
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="content">
            <!-- 浏览器提示 -->
            <div class="tip-card hidden" id="browserTip">
                <h4>⚠️ 需要安装浏览器</h4>
                <p style="margin-bottom:10px">首次使用需下载浏览器(约100MB)</p>
                <button class="btn btn-primary" onclick="installBrowser()" id="installBtn">
                    立即安装
                </button>
            </div>
            
            <!-- 步骤 -->
            <div class="card">
                <div class="steps">
                    <div class="step" data-step="1">
                        <div class="step-dot">1</div>
                        <div class="step-label">热点</div>
                    </div>
                    <div class="step" data-step="2">
                        <div class="step-dot">2</div>
                        <div class="step-label">写作</div>
                    </div>
                    <div class="step" data-step="3">
                        <div class="step-dot">3</div>
                        <div class="step-label">审查</div>
                    </div>
                    <div class="step" data-step="4">
                        <div class="step-dot">4</div>
                        <div class="step-label">发布</div>
                    </div>
                </div>
            </div>
            
            <!-- 类型选择 -->
            <div class="card">
                <div class="card-title">📋 选择类型</div>
                <div class="type-grid" id="typeGrid">
                    <!-- JS 生成 -->
                </div>
            </div>
            
            <!-- 作者 -->
            <div class="card">
                <div class="input-group">
                    <label>作者名称</label>
                    <input type="text" id="author" placeholder="默认：AI小编" value="AI小编">
                </div>
            </div>
            
            <!-- 操作按钮 -->
            <div style="display: flex; gap: 10px;">
                <button class="btn btn-primary" id="startBtn" onclick="startPublish()" style="flex: 2;">
                    <span>🚀</span> 一键发布
                </button>
                <button class="btn" id="analyticsBtn" onclick="runAnalytics()" style="flex: 1; background: #07c160; color: white;">
                    <span>📊</span> 数据分析
                </button>
            </div>
            
            <!-- 日志 -->
            <div class="card" style="margin-top: 12px;">
                <div class="card-title">📋 运行日志</div>
                <div class="log-container" id="logBox">
                    <div class="log-entry">
                        <span class="log-time">--:--:--</span>
                        <span>等待开始...</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedType = 'general';
        let isRunning = false;
        
        // 初始化
        window.onload = async function() {
            renderTypes();
            await checkBrowser();
            // 延迟加载设置，确保pywebview已初始化
            setTimeout(async () => {
                await loadSettings();
            }, 500);
            addLog('程序就绪，请选择类型并点击发布', 'info');
        };
        
        // 渲染类型
        function renderTypes() {
            const types = [
                {id: 'tech', name: '科技', icon: '💻'},
                {id: 'finance', name: '财经', icon: '💰'},
                {id: 'entertainment', name: '娱乐', icon: '🎬'},
                {id: 'sports', name: '体育', icon: '⚽'},
                {id: 'society', name: '社会', icon: '🏘️'},
                {id: 'world', name: '国际', icon: '🌍'},
                {id: 'general', name: '综合', icon: '📰'},
                {id: 'auto', name: '自动', icon: '🤖'},
            ];
            
            const grid = document.getElementById('typeGrid');
            grid.innerHTML = types.map(t => `
                <div class="type-item ${t.id === 'general' ? 'selected' : ''}" 
                     data-id="${t.id}"
                     onclick="selectType('${t.id}')">
                    <div class="type-icon">${t.icon}</div>
                    <div class="type-name">${t.name}</div>
                </div>
            `).join('');
        }
        
        // 选择类型
        function selectType(id) {
            selectedType = id;
            document.querySelectorAll('.type-item').forEach(el => {
                el.classList.toggle('selected', el.dataset.id === id);
            });
        }
        
        // 检查浏览器
        async function checkBrowser() {
            try {
                const result = await window.pywebview.api.check_browser();
                if (!result.installed) {
                    document.getElementById('browserTip').classList.remove('hidden');
                }
            } catch(e) {}
        }
        
        // 安装浏览器
        async function installBrowser() {
            const btn = document.getElementById('installBtn');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div> 下载中...';
            
            try {
                const result = await window.pywebview.api.install_browser();
                if (result.success) {
                    document.getElementById('browserTip').classList.add('hidden');
                    addLog('浏览器安装完成', 'success');
                } else {
                    addLog('安装失败', 'error');
                }
            } catch(e) {
                addLog('安装出错', 'error');
            }
            
            btn.disabled = false;
            btn.innerHTML = '立即安装';
        }
        
        // 开始发布
        async function startPublish() {
            if (isRunning) return;
            
            const author = document.getElementById('author').value.trim() || 'AI小编';
            
            try {
                const result = await window.pywebview.api.start_publish(selectedType, author);
                if (result.success) {
                    isRunning = true;
                    resetSteps();
                    updateBtnState();
                    addLog('开始发布流程...', 'info');
                }
            } catch(e) {
                addLog('启动失败', 'error');
            }
        }
        
        // 更新按钮状态
        function updateBtnState() {
            const btn = document.getElementById('startBtn');
            const analyticsBtn = document.getElementById('analyticsBtn');
            if (isRunning) {
                btn.disabled = true;
                analyticsBtn.disabled = true;
                btn.innerHTML = '<div class="spinner"></div> 执行中...';
                analyticsBtn.innerHTML = '<div class="spinner"></div> 分析中...';
            } else {
                btn.disabled = false;
                analyticsBtn.disabled = false;
                btn.innerHTML = '<span>🚀</span> 一键发布';
                analyticsBtn.innerHTML = '<span>📊</span> 数据分析';
            }
        }
        
        // 分析完成回调（供Python调用）
        window.analyticsCompleted = function() {
            isRunning = false;
            updateBtnState();
            addLog('数据分析完成', 'info');
        };
        
        // 运行数据分析
        async function runAnalytics() {
            if (isRunning) return;
            isRunning = true;
            updateBtnState();
            addLog('启动数据分析...', 'info');
            
            try {
                const result = await pywebview.api.run_analytics();
                if (!result.success) {
                    addLog('启动失败: ' + result.error, 'error');
                    isRunning = false;
                    updateBtnState();
                }
                // 成功启动后等待回调，不在这里重置状态
            } catch(e) {
                addLog('启动失败', 'error');
                isRunning = false;
                updateBtnState();
            }
        }
        
        // 重置步骤
        function resetSteps() {
            document.querySelectorAll('.step').forEach(s => {
                s.className = 'step';
            });
        }
        
        // 更新步骤 (供Python调用)
        window.updateStep = function(step, state) {
            const el = document.querySelector(`.step[data-step="${step}"]`);
            if (el) {
                el.className = 'step ' + state;
            }
            if (step === 4 && (state === 'completed' || state === 'error')) {
                isRunning = false;
                updateBtnState();
            }
        };
        
        // 添加日志 (供Python调用)
        window.addLog = function(msg, type) {
            const box = document.getElementById('logBox');
            const time = new Date().toLocaleTimeString('zh-CN', {hour12:false});
            const div = document.createElement('div');
            div.className = 'log-entry' + (type ? ' log-' + type : '');
            div.innerHTML = `<span class="log-time">${time}</span>${escapeHtml(msg)}`;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        };
        
        // 设置相关函数
        async function openSettings() {
            document.getElementById('settingsModal').classList.add('active');
            // 打开时刷新状态
            await loadSettings();
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').classList.remove('active');
        }
        
        async function loadSettings() {
            try {
                console.log('正在加载设置...');
                
                // 加载开机自启动设置
                const startupResult = await pywebview.api.get_startup_status();
                console.log('开机启动设置返回:', startupResult);
                if (startupResult.success) {
                    document.getElementById('startupSwitch').checked = startupResult.enabled;
                }
                
                // 加载定时任务设置
                const schedulerResult = await pywebview.api.get_scheduler_config();
                console.log('定时任务设置返回:', schedulerResult);
                if (schedulerResult.success) {
                    const config = schedulerResult.config;
                    
                    // 数据分析设置
                    document.getElementById('schedulerAnalyticsEnabled').checked = config.analytics_enabled;
                    document.getElementById('analyticsTime').value = config.analytics_time;
                    document.getElementById('analyticsTimePicker').style.display = 
                        config.analytics_enabled ? 'block' : 'none';
                    
                    // 自动发布设置
                    document.getElementById('schedulerPublishEnabled').checked = config.publish_enabled;
                    document.getElementById('publishTime').value = config.publish_time;
                    document.getElementById('schedulerCategory').value = config.publish_category;
                    document.getElementById('schedulerAuthor').value = config.publish_author;
                    document.getElementById('publishConfig').style.display = 
                        config.publish_enabled ? 'block' : 'none';
                }
            } catch(e) {
                console.error('加载设置异常:', e);
            }
        }
        
        async function toggleStartup(checkbox) {
            const enabled = checkbox.checked;
            try {
                const result = await pywebview.api.toggle_startup(enabled);
                if (!result.success) {
                    checkbox.checked = !enabled;
                    addLog('设置失败: ' + result.error, 'error');
                } else {
                    addLog(enabled ? '[设置] 开机自启动已启用' : '[设置] 开机自启动已禁用');
                }
            } catch(e) {
                checkbox.checked = !enabled;
                addLog('设置失败', 'error');
            }
        }
        
        // 定时任务设置函数
        function toggleSchedulerAnalytics(checkbox) {
            document.getElementById('analyticsTimePicker').style.display = 
                checkbox.checked ? 'block' : 'none';
            updateSchedulerConfig();
            addLog(checkbox.checked ? '[设置] 定时数据分析已启用' : '[设置] 定时数据分析已禁用');
        }
        
        function toggleSchedulerPublish(checkbox) {
            document.getElementById('publishConfig').style.display = 
                checkbox.checked ? 'block' : 'none';
            updateSchedulerConfig();
            addLog(checkbox.checked ? '[设置] 定时自动发布已启用' : '[设置] 定时自动发布已禁用');
        }
        
        async function updateSchedulerConfig() {
            try {
                const config = {
                    analytics_enabled: document.getElementById('schedulerAnalyticsEnabled').checked,
                    analytics_time: document.getElementById('analyticsTime').value,
                    publish_enabled: document.getElementById('schedulerPublishEnabled').checked,
                    publish_time: document.getElementById('publishTime').value,
                    publish_category: document.getElementById('schedulerCategory').value,
                    publish_author: document.getElementById('schedulerAuthor').value
                };
                
                const result = await pywebview.api.update_scheduler_config(config);
                if (!result.success) {
                    addLog('定时任务设置保存失败: ' + result.error, 'error');
                }
            } catch(e) {
                console.error('保存定时任务配置失败:', e);
            }
        }
        
        // 点击弹窗外部关闭
        document.getElementById('settingsModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeSettings();
            }
        });
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>'''


def main():
    api = Api()
    
    # 初始化并启动定时任务调度器
    try:
        from src.utils.scheduler import get_scheduler
        scheduler = get_scheduler()
        api._setup_scheduler_callbacks(scheduler)
        
        # 如果配置了定时任务，自动启动调度器
        config = scheduler.get_config()
        if config.get('analytics_enabled') or config.get('publish_enabled'):
            scheduler.start()
            print(f"[Main] 定时任务调度器已启动")
            print(f"[Main] 数据分析: {'启用' if config.get('analytics_enabled') else '禁用'} {config.get('analytics_time', '09:00')}")
            print(f"[Main] 自动发布: {'启用' if config.get('publish_enabled') else '禁用'} {config.get('publish_time', '10:00')}")
    except Exception as e:
        print(f"[Main] 初始化调度器失败: {e}")
    
    window = webview.create_window(
        title='WeChat AI Publisher',
        html=create_html(),
        js_api=api,
        width=420,
        height=750,
        resizable=False,
        text_select=False,
    )
    
    api.window = window
    
    webview.start(debug=False, http_server=True)
    
    # 程序退出时停止调度器
    try:
        from src.utils.scheduler import stop_scheduler
        stop_scheduler()
        print("[Main] 定时任务调度器已停止")
    except:
        pass


if __name__ == '__main__':
    main()
