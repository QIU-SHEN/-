#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号自动发布系统 - 一键直达版

输入类型+作者 → 自动完成: 获取热点 → 写文章 → 审查 → 直接发布

使用方法:
    python auto_publish.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.research_agent import ResearchAgent
from src.agents.writing_agent import WritingAgent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.publish_agent import PublishAgent


def show_banner():
    """显示标题"""
    print("\n" + "="*60)
    print("  微信公众号自动发布系统")
    print("  输入后自动完成: 热点→写作→审查→发布")
    print("="*60)


def get_inputs():
    """获取用户输入"""
    category_map = {
        '1': 'tech', '2': 'finance', '3': 'entertainment',
        '4': 'sports', '5': 'society', '6': 'world', '7': 'general',
    }
    
    print("\n新闻类型: 1.科技 2.财经 3.娱乐 4.体育 5.社会 6.国际 7.综合")
    choice = input("选择编号(默认7): ").strip() or '7'
    category = category_map.get(choice, 'general')
    
    author = input("作者名(默认AI小编): ").strip() or "AI小编"
    
    print(f"\n  类型: {category} | 作者: {author}")
    confirm = input("  按回车开始，输入n取消: ").strip().lower()
    
    return None if confirm == 'n' else (category, author)


def run_pipeline(category: str, author: str):
    """运行完整流程"""
    print("\n" + "="*60)
    print(" 开始自动流程 ")
    print("="*60)
    
    # 步骤1: 获取热点
    print("\n[1/4] 获取热点新闻...")
    try:
        hot_file = ResearchAgent().run(category)
        print(f"  ✓ 已生成: {Path(hot_file).name}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False
    
    # 步骤2: 撰写文章
    print("\n[2/4] AI撰写文章...")
    try:
        article_file = WritingAgent().run(hot_file, author)
        print(f"  ✓ 已生成: {Path(article_file).name}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False
    
    # 步骤3: 合规审查
    print("\n[3/4] 合规审查...")
    try:
        passed, report = ComplianceAgent(max_check_rounds=2).run(article_file)
        status = "✓ 通过" if passed else "✗ 未通过"
        print(f"  {status}: {report[:50]}...")
        if not passed:
            print("  停止发布")
            return False
    except Exception as e:
        print(f"  ! 审查异常: {e}")
    
    # 步骤4: 直接发布
    print("\n[4/4] 直接发布文章...")
    print("  正在打开浏览器...")
    
    try:
        import yaml
        config_file = Path("./config/config.yaml")
        config = yaml.safe_load(open(config_file, 'r', encoding='utf-8')) if config_file.exists() else {'wechat': {'use_rpa': True}}
        
        # 强制直接发布模式
        config['wechat']['auto_publish'] = True
        
        result = PublishAgent(config).run_from_file(article_file)
        
        if result.get('status') == 'success':
            print("\n  ✓✓✓ 发布成功! ✓✓✓")
            return True
        else:
            print(f"\n  ✗ 发布失败: {result.get('error', '未知错误')}")
            return False
    except Exception as e:
        print(f"  ✗ 发布出错: {e}")
        return False


def main():
    show_banner()
    
    inputs = get_inputs()
    if not inputs:
        print("\n已取消")
        return 0
    
    category, author = inputs
    success = run_pipeline(category, author)
    
    print("\n" + "="*60)
    print(" 完成!" if success else " 未完成")
    print("="*60 + "\n")
    
    return 0 if success else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
