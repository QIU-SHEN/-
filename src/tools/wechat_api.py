#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat_api - 微信公众号 API 工具模块
封装微信公众号所有常用接口
"""

import logging
import json
import time
from typing import Dict, List, Optional
from datetime import datetime


class WeChatAPI:
    """
    📤 微信公众号 API 工具
    
    封装接口:
    - Access Token 管理
    - 素材管理（图片、图文）
    - 消息发布（群发、草稿）
    - 用户管理
    - 数据分析
    """
    
    API_BASE = "https://api.weixin.qq.com/cgi-bin"
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 公众号配置
        self.app_id = self.config.get('app_id')
        self.app_secret = self.config.get('app_secret')
        self.token = self.config.get('token')  # 用于消息加解密
        self.encoding_aes_key = self.config.get('encoding_aes_key')
        
        # Token 管理
        self._access_token = None
        self._token_expires_at = 0
        
        self.logger.info("📤 WeChatAPI 已初始化")
    
    def _get_access_token(self) -> str:
        """获取 Access Token（带缓存）"""
        # 检查缓存
        if self._access_token and time.time() < self._token_expires_at - 300:
            return self._access_token
        
        # 重新获取
        return self._refresh_access_token()
    
    def _refresh_access_token(self) -> str:
        """刷新 Access Token"""
        self.logger.info("刷新 Access Token...")
        
        if not self.app_id or not self.app_secret:
            raise ValueError("AppID 或 AppSecret 未配置")
        
        try:
            import requests
            
            url = f"{self.API_BASE}/token"
            params = {
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'access_token' in data:
                self._access_token = data['access_token']
                expires_in = data.get('expires_in', 7200)
                self._token_expires_at = time.time() + expires_in
                
                self.logger.info(f"Token 刷新成功，有效期 {expires_in} 秒")
                return self._access_token
            else:
                error_msg = f"获取 Token 失败: {data.get('errmsg', 'Unknown error')}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.error(f"刷新 Token 失败: {e}")
            raise
    
    # ==================== 素材管理 ====================
    
    def upload_image(self, image_path: str, is_permanent: bool = True) -> str:
        """
        上传图片素材
        
        Args:
            image_path: 图片本地路径
            is_permanent: 是否永久素材
            
        Returns:
            media_id
        """
        self.logger.info(f"上传图片: {image_path}")
        
        try:
            import requests
            
            token = self._get_access_token()
            
            if is_permanent:
                url = f"{self.API_BASE}/material/add_material"
                params = {"access_token": token, "type": "image"}
            else:
                url = f"{self.API_BASE}/media/upload"
                params = {"access_token": token, "type": "image"}
            
            with open(image_path, 'rb') as f:
                files = {'media': f}
                response = requests.post(url, params=params, files=files, timeout=60)
            
            response.raise_for_status()
            data = response.json()
            
            if 'media_id' in data or 'url' in data:
                media_id = data.get('media_id') or data.get('url')
                self.logger.info(f"图片上传成功: {media_id[:20]}...")
                return media_id
            else:
                raise Exception(f"上传失败: {data.get('errmsg')}")
                
        except Exception as e:
            self.logger.error(f"图片上传失败: {e}")
            raise
    
    def upload_news(self, articles: List[Dict]) -> str:
        """
        上传图文消息素材
        
        Args:
            articles: 图文列表，每个图文包含:
                - title: 标题
                - thumb_media_id: 封面图 media_id
                - author: 作者
                - digest: 摘要
                - content: 内容（HTML）
                - content_source_url: 原文链接
                
        Returns:
            media_id
        """
        self.logger.info(f"上传图文素材: {len(articles)} 篇")
        
        try:
            import requests
            
            token = self._get_access_token()
            url = f"{self.API_BASE}/material/add_news"
            params = {"access_token": token}
            
            data = {"articles": articles}
            
            response = requests.post(
                url, 
                params=params, 
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if 'media_id' in result:
                self.logger.info(f"图文上传成功: {result['media_id'][:20]}...")
                return result['media_id']
            else:
                raise Exception(f"上传失败: {result.get('errmsg')}")
                
        except Exception as e:
            self.logger.error(f"图文上传失败: {e}")
            raise
    
    # ==================== 消息发布 ====================
    
    def publish_article(self, media_id: str) -> Dict:
        """
        发布文章（群发）
        
        Args:
            media_id: 图文素材 ID
            
        Returns:
            发布结果
        """
        self.logger.info(f"发布文章: {media_id[:20]}...")
        
        try:
            import requests
            
            token = self._get_access_token()
            url = f"{self.API_BASE}/message/mass/sendall"
            params = {"access_token": token}
            
            data = {
                "filter": {"is_to_all": True},
                "mpnews": {"media_id": media_id},
                "msgtype": "mpnews",
                "send_ignore_reprint": 0
            }
            
            response = requests.post(url, params=params, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('errcode') == 0:
                self.logger.info(f"发布成功: msg_id={result.get('msg_id')}")
                return {
                    'success': True,
                    'msg_id': result.get('msg_id'),
                    'msg_data_id': result.get('msg_data_id'),
                    'published_at': datetime.now().isoformat()
                }
            else:
                raise Exception(f"发布失败: {result.get('errmsg')}")
                
        except Exception as e:
            self.logger.error(f"发布失败: {e}")
            raise
    
    def save_draft(self, articles: List[Dict]) -> str:
        """
        保存草稿
        
        Args:
            articles: 图文列表
            
        Returns:
            media_id
        """
        self.logger.info("保存草稿...")
        
        # 草稿就是不上传的永久素材
        return self.upload_news(articles)
    
    def preview_article(self, media_id: str, openid: str) -> bool:
        """
        预览文章（发送给指定用户）
        
        Args:
            media_id: 素材 ID
            openid: 用户 OpenID
            
        Returns:
            是否成功
        """
        self.logger.info(f"发送预览给: {openid[:10]}...")
        
        try:
            import requests
            
            token = self._get_access_token()
            url = f"{self.API_BASE}/message/mass/preview"
            params = {"access_token": token}
            
            data = {
                "touser": openid,
                "mpnews": {"media_id": media_id},
                "msgtype": "mpnews"
            }
            
            response = requests.post(url, params=params, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('errcode') == 0:
                self.logger.info("预览发送成功")
                return True
            else:
                self.logger.error(f"预览发送失败: {result.get('errmsg')}")
                return False
                
        except Exception as e:
            self.logger.error(f"预览发送失败: {e}")
            return False
    
    def delete_material(self, media_id: str) -> bool:
        """删除素材"""
        self.logger.info(f"删除素材: {media_id[:20]}...")
        
        try:
            import requests
            
            token = self._get_access_token()
            url = f"{self.API_BASE}/material/del_material"
            params = {"access_token": token}
            
            data = {"media_id": media_id}
            
            response = requests.post(url, params=params, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get('errcode') == 0
            
        except Exception as e:
            self.logger.error(f"删除素材失败: {e}")
            return False
    
    # ==================== 数据分析 ====================
    
    def get_article_data(self, msgid: str, msg_data_id: str = None) -> Dict:
        """
        获取文章数据（阅读、分享等）
        
        注意: 这个数据有延迟，通常第二天才能获取
        """
        self.logger.info(f"获取文章数据: {msgid}")
        
        # 这里需要使用公众号后台的统计接口
        # 或者通过 datacube 接口获取汇总数据
        
        try:
            token = self._get_access_token()
            
            # 获取用户阅读数据
            # 注意: 微信不提供单篇文章的详细数据接口
            # 需要通过其他方式获取
            
            return {
                'msgid': msgid,
                'read_count': 0,  # 需要通过其他方式获取
                'share_count': 0,
                'note': '单篇文章数据需要通过公众号后台获取'
            }
            
        except Exception as e:
            self.logger.error(f"获取数据失败: {e}")
            return {}
    
    def get_user_summary(self, begin_date: str, end_date: str) -> Dict:
        """
        获取用户增减数据
        
        Args:
            begin_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        """
        return self._get_datacube_data(
            "datacube/getusersummary",
            begin_date,
            end_date
        )
    
    def get_article_summary(self, begin_date: str, end_date: str) -> Dict:
        """
        获取图文群发每日数据
        
        Args:
            begin_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        """
        return self._get_datacube_data(
            "datacube/getarticlesummary",
            begin_date,
            end_date
        )
    
    def get_article_total(self, begin_date: str, end_date: str) -> Dict:
        """
        获取图文群发总数据
        
        Args:
            begin_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        """
        return self._get_datacube_data(
            "datacube/getarticletotal",
            begin_date,
            end_date
        )
    
    def _get_datacube_data(self, api: str, begin_date: str, end_date: str) -> Dict:
        """通用数据接口调用"""
        try:
            import requests
            
            token = self._get_access_token()
            url = f"{self.API_BASE}/{api}"
            params = {"access_token": token}
            
            data = {
                "begin_date": begin_date,
                "end_date": end_date
            }
            
            response = requests.post(url, params=params, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if 'list' in result:
                return {'success': True, 'data': result['list']}
            else:
                return {'success': False, 'error': result.get('errmsg')}
                
        except Exception as e:
            self.logger.error(f"获取数据失败: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== 用户管理 ====================
    
    def get_user_list(self, next_openid: str = None) -> Dict:
        """获取关注者列表"""
        try:
            import requests
            
            token = self._get_access_token()
            url = f"{self.API_BASE}/user/get"
            params = {
                "access_token": token,
                "next_openid": next_openid or ""
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"获取用户列表失败: {e}")
            return {}
    
    def get_user_info(self, openid: str) -> Dict:
        """获取用户基本信息"""
        try:
            import requests
            
            token = self._get_access_token()
            url = f"{self.API_BASE}/user/info"
            params = {
                "access_token": token,
                "openid": openid,
                "lang": "zh_CN"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"获取用户信息失败: {e}")
            return {}


# 便捷函数
def create_api(config: dict = None) -> WeChatAPI:
    """创建 API 实例"""
    return WeChatAPI(config)
