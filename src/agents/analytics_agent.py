#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnalyticsAgent - 数据分析Agent
用于回收公众号作品数据并生成优化建议报告
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple


@dataclass
class DailyMetrics:
    """每日数据指标"""
    date: str              # 日期
    read_count: int        # 阅读数
    like_count: int        # 点赞数（喜欢/推荐）
    share_count: int       # 分享数
    comment_count: int     # 留言数
    collect_time: str      # 采集时间


@dataclass
class WeeklyMetrics:
    """7天汇总数据指标"""
    period: str            # 时间段描述，如"最近7天"
    read_count: int        # 阅读数
    like_count: int        # 点赞数
    share_count: int       # 分享数
    comment_count: int     # 留言数
    avg_read: float        # 平均阅读数
    avg_like: float        # 平均点赞数
    collect_time: str      # 采集时间


@dataclass
class AnalyticsReport:
    """分析报告"""
    report_date: str
    yesterday: DailyMetrics      # 昨日数据
    weekly: WeeklyMetrics        # 最近7天数据
    analysis: str                # AI分析结果
    suggestions: List[str]       # 优化建议
    keywords: List[str]          # 热点关键词
    best_publish_time: str       # 建议发布时间


class AnalyticsAgent:
    """数据分析Agent"""
    
    # API配置（复用writing_agent的配置）
    API_KEY = "sk-bddadfd452fe4055bb8c18abbdd29a71"
    API_URL = "https://chat.ecnu.edu.cn/open/api/v1/chat/completions"
    
    def __init__(self, output_dir: str = "./data/analytics"):
        """
        初始化AnalyticsAgent
        
        Args:
            output_dir: 数据输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据存储文件
        self.metrics_file = self.output_dir / "metrics_history.json"
        self.report_file = self.output_dir / "latest_report.json"
        
    def run(self, rpa_controller=None) -> AnalyticsReport:
        """
        执行完整的数据分析流程
        
        Args:
            rpa_controller: RPA控制器（如果为None则创建新的）
            
        Returns:
            AnalyticsReport: 分析报告
        """
        print("[AnalyticsAgent] 开始数据回收与分析...")
        
        # 1. 采集数据
        if rpa_controller is None:
            # 尝试两种导入方式（支持相对导入和绝对导入）
            try:
                from ..tools.rpa_tool import WeChatRPA
            except ImportError:
                from src.tools.rpa_tool import WeChatRPA
            config = {'browser': {'headless': False, 'slow_mo': 500}}
            rpa = WeChatRPA(config)
            # 登录并初始化浏览器
            rpa.login(save_state=True)
        else:
            rpa = rpa_controller
        
        try:
            # 2. 导航到数据分析页面并采集（昨日 + 7天）
            yesterday, weekly = self.collect_data(rpa)
            
            # 3. 保存原始数据
            self.save_metrics(yesterday, weekly)
            
            # 4. AI分析生成报告
            report = self.analyze_with_ai(yesterday, weekly)
            
            # 5. 保存报告
            self.save_report(report)
            
            print(f"[AnalyticsAgent] 分析完成，报告已保存: {self.report_file}")
            return report
            
        finally:
            if rpa_controller is None:
                rpa.close()
    
    def collect_data(self, rpa) -> Tuple[DailyMetrics, WeeklyMetrics]:
        """
        通过RPA采集数据（昨日 + 最近7天）
        
        Args:
            rpa: WeChatRPA实例
            
        Returns:
            Tuple[DailyMetrics, WeeklyMetrics]: 昨日数据和7天数据
        """
        print("[AnalyticsAgent] 正在采集数据...")
        
        # 1. 确保已登录（通过检查page和URL）
        if not rpa.page or "mp.weixin.qq.com" not in rpa.page.url:
            print("[AnalyticsAgent] 需要登录，等待扫码...")
            # 访问公众号后台
            rpa.page.goto("https://mp.weixin.qq.com/")
            time.sleep(3)  # 给页面加载时间
            
            # 循环检测登录状态
            for i in range(60):  # 最多等待60秒
                time.sleep(2)
                current_url = rpa.page.url
                if "cgi-bin/home" in current_url or "cgi-bin/appmsg" in current_url:
                    print("[AnalyticsAgent] 登录成功")
                    break
                print(f"[AnalyticsAgent] 等待登录... {i+1}/60")
            else:
                raise Exception("登录超时")
        
        # 2. 点击"数据分析"菜单
        print("[AnalyticsAgent] 点击数据分析菜单...")
        self._click_data_analysis_menu(rpa)
        
        # 3. 点击"内容分析"
        print("[AnalyticsAgent] 点击内容分析...")
        self._click_content_analysis(rpa)
        
        # 4. 等待页面加载并提取昨日数据
        print("[AnalyticsAgent] 提取昨日数据...")
        time.sleep(3)  # 等待页面数据加载
        
        yesterday = self._extract_yesterday_data(rpa)
        print(f"[AnalyticsAgent] 昨日数据: 阅读{yesterday.read_count}, 点赞{yesterday.like_count}")
        
        # 5. 点击"最近7天"并提取数据
        print("[AnalyticsAgent] 点击最近7天...")
        self._click_last_7_days(rpa)
        time.sleep(2)  # 等待数据刷新
        
        weekly = self._extract_weekly_data(rpa)
        print(f"[AnalyticsAgent] 7天数据: 阅读{weekly.read_count}, 平均{weekly.avg_read:.0f}")
        
        print("[AnalyticsAgent] 数据采集完成")
        return yesterday, weekly
    
    def _click_data_analysis_menu(self, rpa):
        """点击数据分析菜单"""
        # 尝试多种选择器找到数据分析菜单
        selectors = [
            'span[title="数据分析"]',
            '.weui-desktop-menu__name:has-text("数据分析")',
            '.weui-desktop-menu__link:has(.weui-desktop-menu__name:has-text("数据分析"))'
        ]
        
        for selector in selectors:
            try:
                menu = rpa.page.locator(selector).first
                menu.wait_for(state='visible', timeout=5000)
                menu.click()
                print(f"[AnalyticsAgent] 已点击数据分析菜单: {selector}")
                time.sleep(2)
                return
            except:
                continue
        
        # 尝试JavaScript点击
        clicked = rpa.page.evaluate("""
            () => {
                const menus = document.querySelectorAll('.weui-desktop-menu__name');
                for (let menu of menus) {
                    if (menu.textContent.includes('数据分析')) {
                        menu.closest('.weui-desktop-menu__link').click();
                        return true;
                    }
                }
                return false;
            }
        """)
        
        if clicked:
            print("[AnalyticsAgent] 已通过JavaScript点击数据分析菜单")
            time.sleep(2)
        else:
            raise Exception("未找到数据分析菜单")
    
    def _click_content_analysis(self, rpa):
        """点击内容分析子菜单"""
        # 尝试找到内容分析链接
        selectors = [
            'a[href*="appmsganalysis"]:has-text("内容分析")',
            '.weui-desktop-menu__link:has-text("内容分析")'
        ]
        
        for selector in selectors:
            try:
                link = rpa.page.locator(selector).first
                link.wait_for(state='visible', timeout=5000)
                link.click()
                print(f"[AnalyticsAgent] 已点击内容分析: {selector}")
                time.sleep(3)  # 等待页面加载
                return
            except:
                continue
        
        # 直接导航到URL
        rpa.page.goto("https://mp.weixin.qq.com/misc/appmsganalysis?action=report&type=daily_v2")
        print("[AnalyticsAgent] 已导航到内容分析页面")
        time.sleep(3)
    
    def _extract_yesterday_data(self, rpa) -> DailyMetrics:
        """提取昨日数据"""
        # 使用JavaScript提取数据
        data = rpa.page.evaluate("""
            () => {
                const result = {
                    read_count: 0,
                    like_count: 0,
                    share_count: 0,
                    comment_count: 0
                };
                
                // 获取所有数据项
                const items = document.querySelectorAll('.yesterday-all__item');
                
                items.forEach(item => {
                    const title = item.querySelector('.yesterday-all__title')?.textContent?.trim();
                    const count = item.querySelector('.yesterday-all__count')?.textContent?.trim();
                    
                    if (title && count) {
                        const num = parseInt(count.replace(/,/g, '')) || 0;
                        
                        if (title.includes('阅读')) {
                            result.read_count = num;
                        } else if (title.includes('喜欢') || title.includes('点赞') || title.includes('推荐')) {
                            // 根据SVG图标判断，或者包含特定文字
                            result.like_count = num;
                        } else if (title.includes('分享')) {
                            result.share_count = num;
                        } else if (title.includes('留言')) {
                            result.comment_count = num;
                        }
                    }
                });
                
                return result;
            }
        """)
        
        # 获取昨日日期
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        metrics = DailyMetrics(
            date=yesterday,
            read_count=data.get('read_count', 0),
            like_count=data.get('like_count', 0),
            share_count=data.get('share_count', 0),
            comment_count=data.get('comment_count', 0),
            collect_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return metrics
    
    def _click_last_7_days(self, rpa):
        """点击'最近7天'标签"""
        # 尝试多种选择器
        selectors = [
            'li.weui-desktop-tag:has-text("最近 7 天")',
            '.weui-desktop-tag:has-text("最近7天")',
            '.weui-desktop-tags li:has-text("7")'
        ]
        
        for selector in selectors:
            try:
                tag = rpa.page.locator(selector).first
                tag.wait_for(state='visible', timeout=3000)
                tag.click()
                print(f"[AnalyticsAgent] 已点击'最近7天': {selector}")
                return
            except:
                continue
        
        # 尝试JavaScript点击
        clicked = rpa.page.evaluate("""
            () => {
                const tags = document.querySelectorAll('.weui-desktop-tag');
                for (let tag of tags) {
                    if (tag.textContent.includes('7') || tag.textContent.includes('最近')) {
                        tag.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        
        if clicked:
            print("[AnalyticsAgent] 已通过JavaScript点击'最近7天'")
        else:
            print("[AnalyticsAgent] 警告: 未找到'最近7天'标签")
    
    def _extract_weekly_data(self, rpa) -> WeeklyMetrics:
        """提取7天汇总数据"""
        # 使用JavaScript提取数据（复用昨日数据的提取逻辑）
        data = rpa.page.evaluate("""
            () => {
                const result = {
                    read_count: 0,
                    like_count: 0,
                    share_count: 0,
                    comment_count: 0
                };
                
                // 获取所有数据项（同样的结构）
                const items = document.querySelectorAll('.yesterday-all__item');
                
                items.forEach(item => {
                    const title = item.querySelector('.yesterday-all__title')?.textContent?.trim();
                    const count = item.querySelector('.yesterday-all__count')?.textContent?.trim();
                    
                    if (title && count) {
                        const num = parseInt(count.replace(/,/g, '')) || 0;
                        
                        if (title.includes('阅读')) {
                            result.read_count = num;
                        } else if (title.includes('喜欢') || title.includes('点赞') || title.includes('推荐')) {
                            result.like_count = num;
                        } else if (title.includes('分享')) {
                            result.share_count = num;
                        } else if (title.includes('留言')) {
                            result.comment_count = num;
                        }
                    }
                });
                
                return result;
            }
        """)
        
        # 计算平均值
        read_count = data.get('read_count', 0)
        like_count = data.get('like_count', 0)
        
        metrics = WeeklyMetrics(
            period="最近7天",
            read_count=read_count,
            like_count=like_count,
            share_count=data.get('share_count', 0),
            comment_count=data.get('comment_count', 0),
            avg_read=round(read_count / 7, 1) if read_count > 0 else 0,
            avg_like=round(like_count / 7, 1) if like_count > 0 else 0,
            collect_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return metrics
    
    def save_metrics(self, yesterday: DailyMetrics, weekly: WeeklyMetrics):
        """保存数据到历史记录"""
        # 加载已有数据（兼容旧格式）
        history = {'daily': [], 'weekly': []}
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # 兼容旧格式（列表）和新格式（字典）
                if isinstance(loaded, list):
                    # 旧格式：只有daily数据
                    history['daily'] = loaded
                elif isinstance(loaded, dict):
                    history = loaded
        
        # 保存昨日数据
        daily_history = history.get('daily', [])
        for i, item in enumerate(daily_history):
            if item['date'] == yesterday.date:
                daily_history[i] = asdict(yesterday)
                break
        else:
            daily_history.append(asdict(yesterday))
        daily_history.sort(key=lambda x: x['date'])
        
        # 保存7天数据（按周）
        weekly_history = history.get('weekly', [])
        weekly_dict = asdict(weekly)
        weekly_dict['date'] = yesterday.date  # 记录采集日期
        weekly_history.append(weekly_dict)
        # 只保留最近30条周数据
        if len(weekly_history) > 30:
            weekly_history = weekly_history[-30:]
        
        history = {'daily': daily_history, 'weekly': weekly_history}
        
        # 保存
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        print(f"[AnalyticsAgent] 数据已保存: {self.metrics_file}")
    
    def analyze_with_ai(self, yesterday: DailyMetrics, weekly: WeeklyMetrics) -> AnalyticsReport:
        """
        使用AI分析数据并生成建议
        
        Args:
            yesterday: 昨日数据
            weekly: 最近7天数据
            
        Returns:
            AnalyticsReport: 分析报告
        """
        print("[AnalyticsAgent] AI正在分析数据...")
        
        # 获取历史数据进行对比
        history = self.get_history()
        
        # 构建prompt（包含昨日和7天数据）
        prompt = self._build_analysis_prompt(yesterday, weekly, history)
        
        # 调用AI API
        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "你是一个专业的公众号数据分析师，擅长通过数据分析提供内容优化建议。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(self.API_URL, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            analysis_text = result['choices'][0]['message']['content']
            
            # 解析AI返回的内容
            analysis, suggestions, keywords, best_time = self._parse_ai_response(analysis_text)
            
            report = AnalyticsReport(
                report_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                yesterday=yesterday,
                weekly=weekly,
                analysis=analysis,
                suggestions=suggestions,
                keywords=keywords,
                best_publish_time=best_time
            )
            
            return report
            
        except Exception as e:
            print(f"[AnalyticsAgent] AI分析失败: {e}")
            # 返回基础报告
            return AnalyticsReport(
                report_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                yesterday=yesterday,
                weekly=weekly,
                analysis="AI分析失败，使用基础数据",
                suggestions=["建议增加互动性内容", "尝试不同发布时间"],
                keywords=[],
                best_publish_time="09:00"
            )
    
    def _build_analysis_prompt(self, yesterday: DailyMetrics, weekly: WeeklyMetrics, history: List[Dict]) -> str:
        """构建AI分析prompt（包含昨日和7天数据）"""
        
        # 计算趋势（昨日 vs 7天平均）
        trend_info = ""
        if weekly.avg_read > 0:
            vs_weekly = (yesterday.read_count - weekly.avg_read) / weekly.avg_read * 100
            trend_info = f"""
相对7天平均变化：
- 阅读数: {vs_weekly:+.1f}%
- 7天平均阅读: {weekly.avg_read:.0f}
- 7天平均点赞: {weekly.avg_like:.0f}"""
        
        # 计算昨日互动率
        engagement_rate_yesterday = (yesterday.like_count + yesterday.share_count + yesterday.comment_count) / max(yesterday.read_count, 1) * 100
        
        # 计算7天互动率
        engagement_rate_weekly = (weekly.like_count + weekly.share_count + weekly.comment_count) / max(weekly.read_count * 7, 1) * 100
        
        prompt = f"""请分析以下公众号数据（昨日+最近7天），并提供优化建议：

【昨日数据】({yesterday.date})
- 阅读数: {yesterday.read_count}
- 点赞数: {yesterday.like_count}
- 分享数: {yesterday.share_count}
- 留言数: {yesterday.comment_count}
- 互动率: {engagement_rate_yesterday:.2f}%

【最近7天汇总数据】
- 总阅读数: {weekly.read_count}
- 总点赞数: {weekly.like_count}
- 总分享数: {weekly.share_count}
- 总留言数: {weekly.comment_count}
- 平均日阅读: {weekly.avg_read:.0f}
- 平均日点赞: {weekly.avg_like:.0f}
- 7天平均互动率: {engagement_rate_weekly:.2f}%
{trend_info}

【对比分析】
昨日相对7天平均表现：{'高于' if yesterday.read_count > weekly.avg_read else '低于'}平均水平

请提供以下分析（用特定格式输出）：

===分析摘要===
（用2-3句话总结昨日数据相对于7天平均的表现，指出亮点或问题）

===优化建议===
1. （基于数据的具体建议1）
2. （基于数据的具体建议2）
3. （基于数据的具体建议3）
4. （基于数据的具体建议4）
5. （基于数据的具体建议5）

===热点关键词===
（列出3-5个建议关注的热点关键词，用逗号分隔）

===最佳发布时间===
（建议的最佳发布时间，格式如：09:00）
"""
        return prompt
    
    def _calc_change(self, current: int, previous: int) -> float:
        """计算环比变化百分比"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return (current - previous) / previous * 100
    
    def _calc_avg_read(self, history: List[Dict]) -> int:
        """计算平均阅读数"""
        if not history:
            return 0
        return sum(item.get('read_count', 0) for item in history) // len(history)
    
    def _parse_ai_response(self, text: str) -> Tuple[str, List[str], List[str], str]:
        """解析AI返回的内容"""
        analysis = ""
        suggestions = []
        keywords = []
        best_time = "09:00"
        
        # 提取分析摘要
        if "===分析摘要===" in text:
            analysis_section = text.split("===分析摘要===")[1].split("===")[0]
            analysis = analysis_section.strip()
        
        # 提取优化建议
        if "===优化建议===" in text:
            suggestions_section = text.split("===优化建议===")[1].split("===")[0]
            for line in suggestions_section.strip().split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # 移除序号
                    suggestion = line.lstrip('0123456789.- ') 
                    if suggestion:
                        suggestions.append(suggestion)
        
        # 提取关键词
        if "===热点关键词===" in text:
            keywords_section = text.split("===热点关键词===")[1].split("===")[0]
            keywords_text = keywords_section.strip()
            keywords = [k.strip() for k in keywords_section.replace('，', ',').split(',') if k.strip()]
        
        # 提取最佳发布时间
        if "===最佳发布时间===" in text:
            time_section = text.split("===最佳发布时间===")[1].strip()
            # 提取时间格式如 09:00
            import re
            time_match = re.search(r'(\d{1,2}:\d{2})', time_section)
            if time_match:
                best_time = time_match.group(1)
        
        # 确保至少有默认建议
        if not suggestions:
            suggestions = [
                "建议增加互动性内容，如问答或投票",
                "尝试使用更具吸引力的标题",
                "优化文章发布时间",
                "增加图文并茂的内容",
                "关注读者留言，及时回复互动"
            ]
        
        return analysis, suggestions, keywords, best_time
    
    def save_report(self, report: AnalyticsReport):
        """保存分析报告"""
        report_data = {
            'report_date': report.report_date,
            'yesterday': asdict(report.yesterday),
            'weekly': asdict(report.weekly),
            'analysis': report.analysis,
            'suggestions': report.suggestions,
            'keywords': report.keywords,
            'best_publish_time': report.best_publish_time
        }
        
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    def get_history(self, days: int = 30) -> List[Dict]:
        """获取历史数据"""
        if not self.metrics_file.exists():
            return []
        
        with open(self.metrics_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 返回最近N天的日数据
        daily = data.get('daily', [])
        return daily[-days:] if len(daily) > days else daily
    
    def get_latest_report(self) -> Optional[AnalyticsReport]:
        """获取最新报告"""
        if not self.report_file.exists():
            return None
        
        with open(self.report_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        yesterday = DailyMetrics(**data['yesterday'])
        weekly = WeeklyMetrics(**data['weekly'])
        
        return AnalyticsReport(
            report_date=data['report_date'],
            yesterday=yesterday,
            weekly=weekly,
            analysis=data['analysis'],
            suggestions=data['suggestions'],
            keywords=data['keywords'],
            best_publish_time=data['best_publish_time']
        )
    
    def export_to_markdown(self, report: AnalyticsReport = None) -> str:
        """导出报告为Markdown格式（包含昨日和7天数据）"""
        if report is None:
            report = self.get_latest_report()
            if report is None:
                return "暂无报告"
        
        md = f"""# 微信公众号数据分析报告

生成时间: {report.report_date}

## 昨日数据概览 ({report.yesterday.date})

| 指标 | 数值 |
|------|------|
| 阅读数 | {report.yesterday.read_count} |
| 点赞数 | {report.yesterday.like_count} |
| 分享数 | {report.yesterday.share_count} |
| 留言数 | {report.yesterday.comment_count} |

## 最近7天数据汇总

| 指标 | 7天总计 | 日均 |
|------|---------|------|
| 阅读数 | {report.weekly.read_count} | {report.weekly.avg_read:.0f} |
| 点赞数 | {report.weekly.like_count} | {report.weekly.avg_like:.0f} |
| 分享数 | {report.weekly.share_count} | - |
| 留言数 | {report.weekly.comment_count} | - |

## 对比分析

昨日表现相对7天平均：{'**高于**' if report.yesterday.read_count > report.weekly.avg_read else '**低于**'}平均水平

## 分析摘要

{report.analysis}

## 优化建议

"""
        for i, suggestion in enumerate(report.suggestions, 1):
            md += f"{i}. {suggestion}\n"
        
        md += f"""
## 热点关键词推荐

{', '.join(report.keywords) if report.keywords else '暂无推荐'}

## 最佳发布时间建议

{report.best_publish_time}

---
*报告由 WeChat AI Publisher 自动生成*
"""
        
        return md


# 便捷函数
def collect_and_analyze(rpa_controller=None) -> AnalyticsReport:
    """
    便捷函数：执行数据采集和分析
    
    Args:
        rpa_controller: RPA控制器
        
    Returns:
        AnalyticsReport: 分析报告
    """
    agent = AnalyticsAgent()
    return agent.run(rpa_controller)


def get_optimization_hints() -> Dict:
    """
    获取优化提示（供research_agent和writing_agent使用）
    
    Returns:
        Dict: 包含建议关键词、最佳发布时间等
    """
    agent = AnalyticsAgent()
    report = agent.get_latest_report()
    
    if report is None:
        return {
            'has_report': False,
            'suggestions': ['建议关注当前热点话题'],
            'keywords': [],
            'best_publish_time': '09:00'
        }
    
    return {
        'has_report': True,
        'suggestions': report.suggestions,
        'keywords': report.keywords,
        'best_publish_time': report.best_publish_time,
        'latest_metrics': {
            'read_count': report.yesterday.read_count,
            'like_count': report.yesterday.like_count,
            'share_count': report.yesterday.share_count
        },
        'weekly_avg': {
            'read': report.weekly.avg_read,
            'like': report.weekly.avg_like
        }
    }
