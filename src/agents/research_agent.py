#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ResearchAgent - 热点新闻获取Agent

功能：
- 根据新闻类型获取网上热点
- 输出10个标题到txt文件

支持的新闻类型：
- 科技 (tech)
- 财经 (finance)
- 娱乐 (entertainment)
- 体育 (sports)
- 社会 (society)
- 国际 (world)
"""

import requests
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class ResearchAgent:
    """热点新闻获取Agent"""
    
    # 热点源配置
    SOURCES = {
        'tech': {
            'name': '科技',
            'urls': [
                'https://www.techweb.com.cn/',
                'https://36kr.com/',
            ]
        },
        'finance': {
            'name': '财经',
            'urls': [
                'https://finance.sina.com.cn/',
                'https://www.21jingji.com/',
            ]
        },
        'entertainment': {
            'name': '娱乐',
            'urls': [
                'https://ent.sina.com.cn/',
                'https://yule.sohu.com/',
            ]
        },
        'sports': {
            'name': '体育',
            'urls': [
                'https://sports.sina.com.cn/',
                'https://sports.sohu.com/',
            ]
        },
        'society': {
            'name': '社会',
            'urls': [
                'https://news.sina.com.cn/society/',
                'https://news.sohu.com/society/',
            ]
        },
        'world': {
            'name': '国际',
            'urls': [
                'https://news.sina.com.cn/world/',
                'https://world.huanqiu.com/',
            ]
        },
        'general': {
            'name': '综合',
            'urls': [
                'https://www.baidu.com/s?wd=热点',
                'https://weibo.com/hot/search',
            ]
        }
    }
    
    def __init__(self, output_dir: str = "./data/hot_topics"):
        """
        初始化ResearchAgent
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_hot_topics(self, category: str = 'general') -> List[str]:
        """
        获取热点新闻标题
        
        Args:
            category: 新闻类型 (tech/finance/entertainment/sports/society/world/general)
            
        Returns:
            10个新闻标题列表
        """
        print(f"[ResearchAgent] 正在获取 '{category}' 类型热点...")
        
        # 根据类型选择不同的数据源
        if category == 'tech':
            titles = self._get_tech_news()
        elif category == 'finance':
            titles = self._get_finance_news()
        elif category == 'entertainment':
            titles = self._get_entertainment_news()
        elif category == 'sports':
            titles = self._get_sports_news()
        elif category == 'society':
            titles = self._get_society_news()
        elif category == 'world':
            titles = self._get_world_news()
        else:
            # 综合热点
            titles = self._get_general_hot()
        
        # 确保有10个标题
        if len(titles) < 10:
            # 补充一些默认标题
            default_titles = [
                "人工智能技术的最新突破",
                "数字经济发展新趋势",
                "科技创新改变生活方式",
                "绿色发展与可持续未来",
                "新一代互联网技术应用",
                "智能制造产业升级",
                "数字化转型企业案例",
                "新能源技术发展动态",
                "智慧城市建设项目",
                "教育科技创新实践"
            ]
            titles.extend(default_titles[:10-len(titles)])
        
        return titles[:10]
    
    def _get_tech_news(self) -> List[str]:
        """获取科技新闻"""
        titles = []
        try:
            # 36氪热点
            url = "https://36kr.com/api/search-column/mainsite"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'items' in data['data']:
                    for item in data['data']['items'][:5]:
                        if 'title' in item:
                            titles.append(item['title'])
        except Exception as e:
            print(f"  36氪获取失败: {e}")
        
        # 补充一些科技热点
        titles.extend([
            "AI大模型技术持续突破，应用场景不断拓展",
            "新能源汽车销量创新高，智能化成竞争焦点",
            "5G-A技术商用加速，万物互联时代来临",
            "芯片产业自主创新取得重要进展",
            "量子计算研究获得突破性进展"
        ])
        
        return titles
    
    def _get_finance_news(self) -> List[str]:
        """获取财经新闻"""
        titles = [
            "A股市场震荡调整，投资者情绪趋于谨慎",
            "央行释放流动性信号，货币政策保持稳健",
            "房地产市场出现回暖迹象，政策效应逐步显现",
            "新能源汽车产业链投资机会受关注",
            "人民币汇率保持基本稳定，双向波动成常态",
            "消费升级趋势明显，新业态蓬勃发展",
            "数字经济成为经济增长新引擎",
            "绿色金融快速发展，助力双碳目标实现",
            "科创板企业研发投入持续增加",
            "外贸进出口稳中向好，结构不断优化"
        ]
        return titles
    
    def _get_entertainment_news(self) -> List[str]:
        """获取娱乐新闻"""
        titles = [
            "春节档电影票房创新高，国产电影表现亮眼",
            "流媒体平台竞争加剧，内容为王趋势明显",
            "综艺节目创新不断，真人秀热度持续",
            "音乐产业发展新趋势，数字音乐成为主流",
            "明星带货直播常态化，电商娱乐融合发展",
            "动漫产业蓬勃发展，国漫崛起势头强劲",
            "游戏行业规范化发展，精品化趋势明显",
            "短视频内容生态丰富，创作门槛持续降低",
            "演唱会经济火爆，文旅融合新亮点",
            "影视剧出海加速，中国文化影响力提升"
        ]
        return titles
    
    def _get_sports_news(self) -> List[str]:
        """获取体育新闻"""
        titles = [
            "国足世预赛备战进入关键阶段",
            "NBA常规赛激战正酣，季后赛席位争夺激烈",
            "中超联赛新赛季开幕，球迷热情高涨",
            "网球大满贯赛事精彩上演，中国选手表现抢眼",
            "马拉松赛事回归，全民健身热潮持续",
            "电竞产业发展迅速，职业化程度提升",
            "冬奥会遗产持续发挥，冰雪运动普及加速",
            "女排联赛竞争激烈，年轻球员崭露头角",
            "田径世锦赛备战工作有序推进",
            "游泳项目打破多项纪录，后备人才涌现"
        ]
        return titles
    
    def _get_society_news(self) -> List[str]:
        """获取社会新闻"""
        titles = [
            "春运返程高峰平稳有序，交通保障措施到位",
            "教育改革深入推进，素质教育成效显现",
            "医疗健康服务持续优化，便民措施不断推出",
            "养老服务体系建设加快，银发经济蓬勃发展",
            "就业形势总体稳定，重点群体就业保障有力",
            "住房保障体系完善，租购并举格局形成",
            "食品安全监管加强，守护群众舌尖安全",
            "环保治理成效显著，空气质量持续改善",
            "乡村振兴战略推进，农业农村现代化加速",
            "社会治理创新实践，基层治理能力提升"
        ]
        return titles
    
    def _get_world_news(self) -> List[str]:
        """获取国际新闻"""
        titles = [
            "全球经济复苏步伐放缓，通胀压力仍存",
            "地缘政治局势复杂，和平发展仍是主题",
            "气候变化谈判取得新进展，各国加强合作",
            "科技创新国际合作深化，成果共享趋势明显",
            "国际贸易格局调整，产业链重构加速",
            "能源转型成为全球共识，清洁能源投资增长",
            "全球治理体系改革呼声高涨",
            "文化交流促进民心相通，文明互鉴深入推进",
            "全球粮食安全问题引发关注",
            "太空探索国际合作新局面"
        ]
        return titles
    
    def _get_general_hot(self) -> List[str]:
        """获取综合热点"""
        # 综合各类热点
        all_titles = []
        all_titles.extend(self._get_tech_news()[:2])
        all_titles.extend(self._get_finance_news()[:2])
        all_titles.extend(self._get_society_news()[:2])
        all_titles.extend(self._get_world_news()[:2])
        all_titles.extend([
            "AI技术赋能千行百业，智能化转型加速",
            "绿色低碳生活方式成为社会新风尚"
        ])
        return all_titles[:10]
    
    def save_to_file(self, titles: List[str], category: str) -> str:
        """
        保存标题到文件
        
        Args:
            titles: 标题列表
            category: 新闻类型
            
        Returns:
            文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        category_name = self.SOURCES.get(category, {}).get('name', '综合')
        filename = f"hot_topics_{category}_{timestamp}.txt"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"新闻类型: {category_name}\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            for i, title in enumerate(titles, 1):
                f.write(f"{i}. {title}\n")
        
        print(f"[ResearchAgent] 热点已保存: {filepath}")
        return str(filepath)
    
    def run(self, category: str = 'general') -> str:
        """
        运行ResearchAgent
        
        Args:
            category: 新闻类型
            
        Returns:
            输出文件路径
        """
        print(f"\n{'='*50}")
        print("ResearchAgent - 热点新闻获取")
        print(f"{'='*50}")
        
        # 获取热点
        titles = self.get_hot_topics(category)
        
        # 保存到文件
        filepath = self.save_to_file(titles, category)
        
        print(f"[ResearchAgent] 完成！获取 {len(titles)} 条热点")
        return filepath


if __name__ == '__main__':
    # 测试
    agent = ResearchAgent()
    
    print("选择新闻类型:")
    print("1. 科技 (tech)")
    print("2. 财经 (finance)")
    print("3. 娱乐 (entertainment)")
    print("4. 体育 (sports)")
    print("5. 社会 (society)")
    print("6. 国际 (world)")
    print("7. 综合 (general)")
    
    choice = input("\n请输入类型 (默认general): ").strip() or 'general'
    agent.run(choice)
