#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WritingAgent - 文章撰写Agent

功能：
- 读取热点标题文件
- 使用AI API撰写1000字左右的文章
- 输出包含题目、作者、内容的文档
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests


class WritingAgent:
    """文章撰写Agent"""
    
    # ECNU API配置
    API_KEY = "sk-bddadfd452fe4055bb8c18abbdd29a71"
    API_URL = "https://chat.ecnu.edu.cn/open/api/v1/chat/completions"
    
    def __init__(self, output_dir: str = "./data/articles"):
        """
        初始化WritingAgent
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def read_hot_topics(self, filepath: str) -> tuple:
        """
        读取热点标题文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            (新闻类型, 标题列表)
        """
        print(f"[WritingAgent] 读取热点文件: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析新闻类型
        category_match = re.search(r'新闻类型:\s*(.+)', content)
        category = category_match.group(1) if category_match else '综合'
        
        # 解析标题列表
        titles = []
        for line in content.split('\n'):
            # 匹配 "数字. 标题" 格式
            match = re.match(r'^\d+\.\s*(.+)', line.strip())
            if match:
                titles.append(match.group(1))
        
        print(f"[WritingAgent] 读取到 {len(titles)} 个标题")
        return category, titles
    
    def generate_title_from_topics(self, titles: list, category: str) -> str:
        """
        使用AI根据热点标题生成一个新的原创标题
        
        Args:
            titles: 标题列表（10个热点标题）
            category: 新闻类型
            
        Returns:
            AI生成的新标题
        """
        print(f"[WritingAgent] 正在使用AI生成标题...")
        
        # 构建prompt
        titles_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])
        
        prompt = f"""你是一个专业的新闻编辑。请根据以下{category}类别的10个热点标题，创作一个吸引人的新标题。

参考标题：
{titles_text}

要求：
1. 新标题必须与参考标题相关，但要有独特角度
2. 标题要吸引人点击，适合微信公众号
3. 标题长度在15-30字之间
4. 不要直接复制参考标题，要创作一个全新的标题
5. 只输出标题文字，不要包含序号、引号或其他内容

请创作一个新标题："""

        # 调用API
        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "你是一个专业的新闻编辑，擅长创作吸引人的标题。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 100
        }
        
        try:
            response = requests.post(self.API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            generated_title = result['choices'][0]['message']['content'].strip()
            
            # 清理标题（移除可能的引号、序号等）
            generated_title = generated_title.strip('"\'""').strip()
            # 如果包含换行，只取第一行
            if '\n' in generated_title:
                generated_title = generated_title.split('\n')[0].strip()
            
            # 验证标题长度
            if len(generated_title) < 5:
                raise ValueError(f"生成的标题太短: {generated_title}")
            
            print(f"[WritingAgent] AI生成标题: {generated_title}")
            return generated_title
            
        except Exception as e:
            print(f"[WritingAgent] AI生成标题失败: {e}，使用备选方案")
            # 备选方案：从原标题中选择一个
            return self._select_best_topic_fallback(titles, category)
    
    def _select_best_topic_fallback(self, titles: list, category: str) -> str:
        """
        备选方案：从原标题中选择最适合的一个（API失败时使用）
        """
        # 优先选择包含关键词的标题
        keywords = {
            '科技': ['AI', '人工智能', '科技', '技术', '创新', '数字'],
            '财经': ['经济', '市场', '投资', '金融', '产业', '发展'],
            '娱乐': ['电影', '综艺', '明星', '音乐', '文化'],
            '体育': ['比赛', '赛事', '冠军', '运动员', '联赛'],
            '社会': ['民生', '教育', '医疗', '就业', '环保'],
            '国际': ['全球', '国际', '外交', '贸易', '合作']
        }
        
        category_keywords = keywords.get(category, [])
        
        # 按关键词匹配度排序
        scored_titles = []
        for title in titles:
            score = 0
            for kw in category_keywords:
                if kw in title:
                    score += 1
            # 长度适中的标题得分更高
            if 15 <= len(title) <= 40:
                score += 0.5
            scored_titles.append((score, title))
        
        # 返回得分最高的
        scored_titles.sort(key=lambda x: x[0], reverse=True)
        selected = scored_titles[0][1] if scored_titles else titles[0]
        
        print(f"[WritingAgent] 选定标题（备选）: {selected}")
        return selected
    
    def generate_article(self, title: str, author: str, category: str) -> str:
        """
        使用AI API生成文章
        
        Args:
            title: 文章标题
            author: 作者名
            category: 新闻类型
            
        Returns:
            文章内容
        """
        print(f"[WritingAgent] 正在生成文章...")
        
        # 构建prompt
        prompt = f"""你是一个专业的公众号文章写手。请根据以下标题撰写一篇公众号文章。

标题：{title}
作者：{author}
类型：{category}

要求：
1. 文章字数约1000字
2. 语言流畅，逻辑清晰
3. 适合微信公众号风格
4. 包含引人入胜的开头
5. 有深度的分析和观点
6. 结尾有总结或启发
7. 不要包含任何违禁内容

请直接输出文章正文内容（不需要包含标题和作者信息）："""

        # 调用API
        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "你是一个专业的公众号文章写手，擅长撰写深度、有洞察力的文章。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(self.API_URL, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            content = result['choices'][0]['message']['content']
            # 清理可能的markdown标记
            content = content.strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('markdown'):
                    content = content[8:]
            content = content.strip()
            
            print(f"[WritingAgent] 文章生成完成，字数: {len(content)}")
            return content
            
        except Exception as e:
            print(f"[WritingAgent] API调用失败: {e}")
            # 返回默认内容
            return self._generate_default_content(title, category)
    
    def _generate_default_content(self, title: str, category: str) -> str:
        """生成默认内容（API失败时使用）"""
        return f"""关于"{title}"的深度分析

近日，{title}引发了社会各界的广泛关注。这一现象不仅反映了当前社会发展的趋势，也为我们提供了深入思考的契机。

首先，从宏观角度来看，这一话题与我们的生活息息相关。随着社会的不断进步和发展，类似的现象将会越来越多地出现在我们的视野中。如何正确认识和理解这些变化，成为了我们每个人都需要面对的问题。

其次，从微观层面分析，这一现象背后有着复杂的成因。技术的进步、政策的调整、市场的变化等多重因素共同作用，才形成了今天我们所看到的局面。理解这些深层次的原因，有助于我们更好地把握未来的发展方向。

再者，这一现象也给我们带来了诸多启示。在面对快速变化的环境时，保持开放的心态、积极学习新知识、不断提升自己的能力，成为了适应时代发展的必然要求。

展望未来，我们有理由相信，随着各方的共同努力，相关问题将得到妥善解决。同时，这也将为行业的健康发展奠定坚实的基础。

总之，{title}不仅是一个值得关注的热点话题，更是一个值得我们深入思考的社会现象。希望通过本文的分析，能够为读者提供一些有价值的参考和启示。

（本文仅代表作者本人观点，仅供参考）"""
    
    def save_article(self, title: str, author: str, content: str, category: str) -> str:
        """
        保存文章到文件
        
        Args:
            title: 标题
            author: 作者
            content: 内容
            category: 类型
            
        Returns:
            文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r'[^\w\u4e00-\u9fa5]+', '_', title)[:20]
        filename = f"article_{category}_{timestamp}_{safe_title}.txt"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"标题：{title}\n")
            f.write(f"作者：{author}\n")
            f.write(f"类型：{category}\n")
            f.write(f"字数：{len(content)}\n")
            f.write(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            f.write(content)
        
        print(f"[WritingAgent] 文章已保存: {filepath}")
        return str(filepath)
    
    def run(self, hot_topics_file: str, author: str) -> str:
        """
        运行WritingAgent
        
        Args:
            hot_topics_file: 热点标题文件路径
            author: 作者名
            
        Returns:
            输出文件路径
        """
        print(f"\n{'='*50}")
        print("WritingAgent - 文章撰写")
        print(f"{'='*50}")
        
        # 读取热点
        category, titles = self.read_hot_topics(hot_topics_file)
        
        if not titles:
            raise ValueError("没有读取到任何标题")
        
        # 使用AI生成新标题
        selected_title = self.generate_title_from_topics(titles, category)
        
        # 生成文章
        content = self.generate_article(selected_title, author, category)
        
        # 保存文章
        filepath = self.save_article(selected_title, author, content, category)
        
        print(f"[WritingAgent] 完成！文章已生成")
        return filepath


if __name__ == '__main__':
    # 测试
    agent = WritingAgent()
    
    import sys
    if len(sys.argv) >= 3:
        hot_file = sys.argv[1]
        author = sys.argv[2]
    else:
        hot_file = input("热点文件路径: ").strip()
        author = input("作者名: ").strip()
    
    agent.run(hot_file, author)
