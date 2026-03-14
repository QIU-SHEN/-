#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnalyticsAgent 独立运行脚本
用于手动触发数据分析和报告生成
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.analytics_agent import AnalyticsAgent, collect_and_analyze


def main():
    """主函数"""
    print("="*60)
    print("微信公众号数据分析工具")
    print("="*60)
    print()
    print("功能说明：")
    print("1. 自动登录微信公众号后台")
    print("2. 采集昨日阅读、点赞、分享、留言数据")
    print("3. AI分析数据并生成优化建议报告")
    print("4. 报告将用于优化后续文章创作")
    print()
    
    input("按回车键开始数据分析（将打开浏览器）...")
    
    try:
        # 执行数据分析
        report = collect_and_analyze()
        
        # 显示报告摘要
        print("\n" + "="*60)
        print("数据分析报告")
        print("="*60)
        print(f"\n分析日期: {report.metrics.date}")
        print(f"数据采集时间: {report.collect_time}")
        print()
        print("昨日数据概览:")
        print(f"  阅读数: {report.metrics.read_count}")
        print(f"  点赞数: {report.metrics.like_count}")
        print(f"  分享数: {report.metrics.share_count}")
        print(f"  留言数: {report.metrics.comment_count}")
        print()
        print("AI分析摘要:")
        print(report.analysis)
        print()
        print("优化建议:")
        for i, suggestion in enumerate(report.suggestions, 1):
            print(f"  {i}. {suggestion}")
        print()
        print(f"推荐关键词: {', '.join(report.keywords)}")
        print(f"建议发布时间: {report.best_publish_time}")
        print()
        print("="*60)
        print("报告已保存，下次创作文章时将自动应用这些优化建议")
        print("="*60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...")


if __name__ == '__main__':
    main()
