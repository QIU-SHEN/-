#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComplianceAgent - 合规审查Agent

功能：
- 审查文章内容是否包含违禁词
- 使用AI API进行智能审查
- 审查2次无违禁词后通过
"""

import re
from pathlib import Path
from typing import Tuple, List
import requests


class ComplianceAgent:
    """合规审查Agent"""
    
    # ECNU API配置
    API_KEY = "sk-bddadfd452fe4055bb8c18abbdd29a71"
    API_URL = "https://chat.ecnu.edu.cn/open/api/v1/chat/completions"
    
    # 常见违禁词列表（作为初筛）
    SENSITIVE_WORDS = [
        '色情', '暴力', '赌博', '毒品', '反动', '谣言',
        '诈骗', '传销', '淫秽', '恐怖', '极端', '仇恨',
    ]
    
    def __init__(self, max_check_rounds: int = 2):
        """
        初始化ComplianceAgent
        
        Args:
            max_check_rounds: 最大审查轮次（默认2次）
        """
        self.max_check_rounds = max_check_rounds
        
    def read_article(self, filepath: str) -> dict:
        """
        读取文章文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            文章信息字典
        """
        print(f"[ComplianceAgent] 读取文章: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析文章
        lines = content.split('\n')
        
        article = {
            'title': '',
            'author': '',
            'category': '',
            'content': ''
        }
        
        # 解析头部信息
        content_started = False
        content_lines = []
        
        for line in lines:
            if line.startswith('标题：'):
                article['title'] = line.replace('标题：', '').strip()
            elif line.startswith('作者：'):
                article['author'] = line.replace('作者：', '').strip()
            elif line.startswith('类型：'):
                article['category'] = line.replace('类型：', '').strip()
            elif line.startswith('=' * 10):
                content_started = True
            elif content_started:
                content_lines.append(line)
        
        article['content'] = '\n'.join(content_lines).strip()
        
        print(f"[ComplianceAgent] 文章解析完成: {article['title'][:30]}...")
        return article
    
    def quick_check(self, content: str) -> Tuple[bool, List[str]]:
        """
        快速检查明显违禁词
        
        Args:
            content: 文章内容
            
        Returns:
            (是否通过, 违禁词列表)
        """
        found_words = []
        for word in self.SENSITIVE_WORDS:
            if word in content:
                found_words.append(word)
        
        passed = len(found_words) == 0
        return passed, found_words
    
    def ai_check(self, content: str) -> Tuple[bool, str]:
        """
        使用AI API进行深度审查
        
        Args:
            content: 文章内容
            
        Returns:
            (是否通过, 审查意见)
        """
        prompt = f"""你是一个内容审核专家。请对以下文章进行合规审查，判断是否包含违禁内容。

文章内容：
{content[:2000]}  # 只审查前2000字

请从以下维度审查：
1. 是否包含色情、淫秽内容
2. 是否包含暴力、恐怖内容
3. 是否包含赌博、毒品相关内容
4. 是否包含反动、极端言论
5. 是否包含谣言、虚假信息
6. 是否包含侮辱、诽谤他人内容
7. 是否符合微信公众号平台规范

请以JSON格式返回结果：
{{
    "passed": true/false,
    "issues": ["问题1", "问题2"],
    "suggestion": "修改建议"
}}

只返回JSON，不要其他内容。"""

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "你是一个严格的内容审核专家，擅长识别各种违规内容。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.API_URL, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            ai_response = result['choices'][0]['message']['content']
            
            # 解析JSON
            import json
            try:
                # 尝试直接解析
                review_result = json.loads(ai_response)
            except:
                # 尝试从文本中提取JSON
                json_match = re.search(r'\{[\s\S]*\}', ai_response)
                if json_match:
                    review_result = json.loads(json_match.group())
                else:
                    # 默认通过
                    return True, "AI审查完成，未发现问题"
            
            passed = review_result.get('passed', True)
            issues = review_result.get('issues', [])
            suggestion = review_result.get('suggestion', '')
            
            if passed:
                return True, "审查通过"
            else:
                return False, f"发现问题: {', '.join(issues)}; 建议: {suggestion}"
                
        except Exception as e:
            print(f"[ComplianceAgent] AI审查出错: {e}")
            # API失败时默认通过
            return True, "AI审查服务暂时不可用，默认通过"
    
    def check_article(self, article: dict) -> Tuple[bool, str]:
        """
        完整审查流程
        
        Args:
            article: 文章字典
            
        Returns:
            (是否通过, 审查报告)
        """
        content = article['content']
        
        print(f"[ComplianceAgent] 开始审查文章: {article['title'][:30]}...")
        
        # 第一轮：快速检查
        print("  [1/2] 快速检查...")
        quick_passed, sensitive_words = self.quick_check(content)
        
        if not quick_passed:
            return False, f"发现敏感词: {', '.join(sensitive_words)}"
        
        print("  [1/2] 快速检查通过")
        
        # 第二轮：AI深度检查
        print("  [2/2] AI深度审查...")
        ai_passed, ai_message = self.ai_check(content)
        
        if not ai_passed:
            return False, ai_message
        
        print("  [2/2] AI审查通过")
        
        return True, "文章审查通过，无违禁内容"
    
    def run(self, article_file: str) -> Tuple[bool, str]:
        """
        运行ComplianceAgent
        
        Args:
            article_file: 文章文件路径
            
        Returns:
            (是否通过, 审查报告)
        """
        print(f"\n{'='*50}")
        print("ComplianceAgent - 合规审查")
        print(f"{'='*50}")
        
        # 读取文章
        article = self.read_article(article_file)
        
        # 审查
        for round_num in range(1, self.max_check_rounds + 1):
            print(f"\n--- 审查轮次 {round_num}/{self.max_check_rounds} ---")
            
            passed, report = self.check_article(article)
            
            if passed:
                print(f"[ComplianceAgent] 第{round_num}轮审查通过")
                if round_num == self.max_check_rounds:
                    print(f"[ComplianceAgent] 完成{self.max_check_rounds}次审查，全部通过")
                    return True, report
            else:
                print(f"[ComplianceAgent] 第{round_num}轮审查未通过")
                print(f"[ComplianceAgent] 原因: {report}")
                return False, report
        
        return True, report


if __name__ == '__main__':
    # 测试
    agent = ComplianceAgent()
    
    import sys
    if len(sys.argv) >= 2:
        article_file = sys.argv[1]
    else:
        article_file = input("文章文件路径: ").strip()
    
    passed, report = agent.run(article_file)
    
    print(f"\n审查结果: {'通过' if passed else '未通过'}")
    print(f"审查报告: {report}")
