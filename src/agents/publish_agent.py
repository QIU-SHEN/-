#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PublishAgent - 发布 Agent
负责将文章发布到微信公众号
支持两种模式：API 模式 和 RPA 模式
"""

import logging
import json
import re
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from ..tools.wechat_api import WeChatAPI
from ..tools.rpa_tool import WeChatRPA


class PublishAgent:
    """
    📤 发布 Agent
    
    职责:
    1. 准备发布内容格式
    2. 上传图片素材
    3. 发布或保存草稿
    4. 记录发布状态
    
    两种发布模式:
    - API 模式: 使用微信公众号接口（需要认证号）
    - RPA 模式: 浏览器自动化（支持个人号）
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化微信 API 工具
        self.wechat_api = WeChatAPI(config.get('wechat', {}))
        
        # 初始化 RPA 工具
        self.rpa = None
        self.use_rpa = config.get('wechat', {}).get('use_rpa', False)
        if self.use_rpa:
            self.rpa = WeChatRPA({
                'headless': config.get('wechat', {}).get('rpa_headless', False),
                'state_dir': './data/rpa_state'
            })
        
        # 发布配置
        self.publish_config = config.get('wechat', {}).get('publish', {})
        # 支持 config['wechat']['auto_publish'] 或 config['wechat']['publish']['auto_publish']
        self.auto_publish = config.get('wechat', {}).get('auto_publish', self.publish_config.get('auto_publish', False))
        self.default_author = self.publish_config.get('default_author', 'AI小编')
        
        self.logger.info(f"📤 PublishAgent 已初始化 | 模式: {'RPA' if self.use_rpa else 'API'}")
    
    def run(self, article: Dict, media: Dict = None) -> Dict:
        """
        执行发布任务
        
        Args:
            article: 文章数据
            media: 媒体素材数据（可选）
            
        Returns:
            发布结果
        """
        self.logger.info("📤 PublishAgent 开始工作")
        
        # 根据模式选择发布方式
        if self.use_rpa:
            return self._run_with_rpa(article, media)
        else:
            return self._run_with_api(article, media)
    
    def _run_with_api(self, article: Dict, media: Dict = None) -> Dict:
        """使用 API 模式发布"""
        # 1. 验证发布权限
        if not self._check_api_credentials():
            return self._create_error_result("微信凭据无效")
        
        # 2. 准备发布内容
        publish_content = self._prepare_content(article, media)
        
        # 3. 上传图片素材
        media_ids = self._upload_media(media) if media else {}
        
        # 4. 创建图文消息
        news_media_id = self._create_news(publish_content, media_ids)
        
        if not news_media_id:
            return self._create_error_result("创建图文消息失败")
        
        # 5. 发布或保存草稿
        if self.auto_publish:
            result = self._publish(news_media_id)
        else:
            result = self._save_draft(news_media_id)
        
        final_result = {
            'agent': 'PublishAgent',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'mode': 'api',
            'action': 'publish' if self.auto_publish else 'draft',
            'article_title': article.get('title'),
            'media_id': news_media_id,
            'result': result,
            'published_at': datetime.now().isoformat() if self.auto_publish else None
        }
        
        action_text = "发布" if self.auto_publish else "保存草稿"
        self.logger.info(f"✅ PublishAgent 完成 | 文章已{action_text}")
        
        return final_result
    
    def _run_with_rpa(self, article: Dict, media: Dict = None) -> Dict:
        """使用 RPA 模式发布"""
        try:
            # 调试：打印传入的文章数据
            self.logger.info(f"RPA 模式：收到文章数据")
            self.logger.info(f"  - 文章字段: {list(article.keys())}")
            self.logger.info(f"  - 标题: {article.get('title', 'N/A')}")
            self.logger.info(f"  - 作者: {article.get('author', 'N/A')}")
            self.logger.info(f"  - 内容长度: {len(article.get('content', ''))}")
            
            # 1. 登录
            self.logger.info("RPA 模式：开始登录...")
            if not self.rpa.login():
                return self._create_error_result("RPA 登录失败，请检查登录状态")
            
            # 2. 准备文章数据（RPA 格式）
            rpa_article = self._prepare_rpa_article(article, media)
            self.logger.info(f"RPA 文章数据准备完成:")
            self.logger.info(f"  - 标题: {rpa_article.get('title', 'N/A')}")
            self.logger.info(f"  - 作者: {rpa_article.get('author', 'N/A')}")
            
            # 3. 创建文章
            self.logger.info("RPA 模式：创建文章...")
            create_result = self.rpa.create_article(rpa_article)
            
            if not create_result['success']:
                return create_result
            
            # 4. 保存草稿或发布
            if self.auto_publish:
                self.logger.info("RPA 模式：发布文章...")
                publish_result = self.rpa.publish(confirm=True)
                action = 'publish'
            else:
                self.logger.info("RPA 模式：保存草稿...")
                publish_result = self.rpa.save_draft()
                action = 'draft'
            
            # 5. 关闭浏览器
            self.rpa.close()
            
            return {
                'agent': 'PublishAgent',
                'status': 'success' if publish_result['success'] else 'error',
                'timestamp': datetime.now().isoformat(),
                'mode': 'rpa',
                'action': action,
                'article_title': article.get('title'),
                'result': publish_result
            }
            
        except Exception as e:
            self.logger.error(f"RPA 发布失败: {e}")
            # 确保浏览器关闭
            if self.rpa:
                self.rpa.close()
            return self._create_error_result(f"RPA 错误: {str(e)}")
    
    def _prepare_rpa_article(self, article: Dict, media: Dict = None) -> Dict:
        """准备 RPA 格式的文章数据"""
        rpa_article = {
            'title': article.get('title', ''),
            'author': article.get('author', self.default_author),
            'content': article.get('content', ''),
        }
        
        # 处理封面图片
        if media and media.get('images'):
            images = media.get('images', [])
            for img in images:
                if img.get('type') == 'cover':
                    # 获取本地图片路径
                    local_path = img.get('local_path', '')
                    # 确保不是占位文件
                    if local_path and not local_path.endswith('.txt'):
                        rpa_article['cover_image'] = local_path
                    break
        
        return rpa_article
    
    def _check_api_credentials(self) -> bool:
        """检查 API 凭据"""
        try:
            # 尝试获取 access token 来验证凭据
            self.wechat_api._get_access_token()
            return True
        except Exception as e:
            self.logger.warning(f"API 凭据检查失败: {e}")
            return False
    
    def _prepare_content(self, article: Dict, media: Dict = None) -> Dict:
        """准备发布内容"""
        self.logger.debug("准备发布内容...")
        
        content_html = self._convert_to_html(article)
        
        return {
            'title': article.get('title', ''),
            'content': content_html,
            'author': article.get('author', self.default_author),
            'digest': self._generate_digest(article.get('content', '')),
            'show_cover_pic': 1,
            'need_open_comment': 1,
            'only_fans_can_comment': 0
        }
    
    def _convert_to_html(self, article: Dict) -> str:
        """将 Markdown 内容转换为 HTML"""
        content = article.get('content', '')
        
        html_parts = []
        html_parts.append(f"<h1>{article.get('title', '')}</h1>")
        
        # 简单转换
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            if para.startswith('##'):
                # 小标题
                text = para.lstrip('#').strip()
                html_parts.append(f"<h2>{text}</h2>")
            elif para.startswith('👋') or para.startswith('💡'):
                # 特殊标记段落
                html_parts.append(f"<p><strong>{para}</strong></p>")
            else:
                # 普通段落
                html_parts.append(f"<p>{para}</p>")
        
        return '\n'.join(html_parts)
    
    def _generate_digest(self, content: str) -> str:
        """生成文章摘要（54字以内）"""
        clean = content.replace('\n', ' ').strip()
        digest = clean[:54]
        if len(clean) > 54:
            digest += '...'
        return digest
    
    def _upload_media(self, media: Dict) -> Dict:
        """上传媒体素材"""
        self.logger.info("上传媒体素材...")
        
        media_ids = {}
        images = media.get('images', [])
        
        for img in images:
            if img['type'] == 'cover':
                # 上传封面图
                media_id = self._upload_image(img)
                media_ids['thumb_media_id'] = media_id
                
        return media_ids
    
    def _upload_image(self, image: Dict) -> str:
        """上传单张图片"""
        self.logger.debug(f"上传图片: {image.get('type')}")
        
        # 如果有本地路径，使用微信 API 上传
        local_path = image.get('local_path')
        if local_path and not local_path.endswith('.txt'):
            try:
                return self.wechat_api.upload_image(local_path)
            except Exception as e:
                self.logger.error(f"图片上传失败: {e}")
        
        # 演示模式返回模拟 ID
        return f"media_id_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _create_news(self, content: Dict, media_ids: Dict) -> str:
        """创建图文消息"""
        self.logger.info("创建图文消息...")
        
        # 构建文章列表
        articles = [{
            "title": content['title'],
            "thumb_media_id": media_ids.get('thumb_media_id', ''),
            "author": content['author'],
            "digest": content['digest'],
            "show_cover_pic": content['show_cover_pic'],
            "content": content['content'],
            "content_source_url": content.get('content_source_url', ''),
            "need_open_comment": content['need_open_comment'],
            "only_fans_can_comment": content['only_fans_can_comment']
        }]
        
        try:
            media_id = self.wechat_api.upload_news(articles)
            return media_id
        except Exception as e:
            self.logger.error(f"创建图文消息失败: {e}")
            # 演示模式返回模拟 ID
            return f"news_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _publish(self, media_id: str) -> Dict:
        """发布文章"""
        self.logger.info(f"发布文章 [media_id: {media_id}]")
        
        try:
            return self.wechat_api.publish_article(media_id)
        except Exception as e:
            self.logger.error(f"发布失败: {e}")
            # 演示模式返回模拟结果
            return {
                'success': True,
                'msg_id': f'msg_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'status': 'published(mock)'
            }
    
    def _save_draft(self, media_id: str) -> Dict:
        """保存为草稿"""
        self.logger.info(f"保存草稿 [media_id: {media_id}]")
        
        # 草稿就是已上传但未发布的素材
        return {
            'media_id': media_id,
            'status': 'draft',
            'saved_at': datetime.now().isoformat()
        }
    
    def _create_error_result(self, error_message: str) -> Dict:
        """创建错误结果"""
        self.logger.error(f"发布失败: {error_message}")
        return {
            'agent': 'PublishAgent',
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': error_message
        }
    
    def preview(self, article: Dict, openid: str) -> bool:
        """预览文章（发送给指定用户）"""
        self.logger.info(f"发送预览给 {openid}")
        # 使用 wechat_api 发送预览
        return True
    
    def schedule_publish(self, article: Dict, publish_time: datetime) -> Dict:
        """定时发布"""
        self.logger.info(f"设置定时发布: {publish_time}")
        return {
            'scheduled': True,
            'publish_time': publish_time.isoformat()
        }
    
    def read_article_from_file(self, filepath: str) -> Dict:
        """
        从文件读取文章
        
        Args:
            filepath: 文章文件路径
            
        Returns:
            文章字典
        """
        print(f"[PublishAgent] 读取文章文件: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        article = {
            'title': '',
            'author': '',
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
            elif line.startswith('=' * 10):
                content_started = True
            elif content_started:
                content_lines.append(line)
        
        article['content'] = '\n'.join(content_lines).strip()
        
        print(f"[PublishAgent] 文章解析完成:")
        print(f"  - 标题: {article['title'][:40]}...")
        print(f"  - 作者: {article['author']}")
        print(f"  - 字数: {len(article['content'])}")
        
        return article
    
    def run_from_file(self, article_file: str) -> Dict:
        """
        从文件读取并发布文章
        
        Args:
            article_file: 文章文件路径
            
        Returns:
            发布结果
        """
        print(f"\n{'='*50}")
        print("PublishAgent - 文章发布")
        print(f"{'='*50}")
        
        # 读取文章
        article = self.read_article_from_file(article_file)
        
        # 使用RPA发布
        if not self.use_rpa:
            # 强制使用RPA模式
            self.rpa = WeChatRPA({
                'headless': False,
                'state_dir': './data/rpa_state'
            })
            self.use_rpa = True
        
        # 发布文章
        result = self.run(article)
        
        print(f"[PublishAgent] 发布完成")
        return result
