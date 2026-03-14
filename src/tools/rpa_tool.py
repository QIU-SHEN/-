#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rpa_tool - 浏览器自动化工具模块
模拟人工操作公众号后台进行文章发布
支持 Playwright 和 Selenium 两种方式
"""

import logging
import time
import random
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

# 导入详细日志模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger, reset_logger


class WeChatRPA:
    """
    🤖 微信公众号 RPA 工具
    
    功能:
    - 自动登录公众号后台（扫码/保存登录态）
    - 新建图文消息
    - 自动填写标题、作者、正文
    - 上传封面图片
    - 保存草稿或发布
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 详细操作日志
        self.detail_logger = get_logger("RPA_Detail", "./logs")
        self.detail_logger.step("WeChatRPA 初始化")
        
        # 配置
        self.headless = self.config.get('headless', False)  # 是否无头模式
        self.slow_mo = self.config.get('slow_mo', 500)  # 操作延迟（毫秒）- 增加延迟防检测
        self.timeout = self.config.get('timeout', 30000)  # 超时时间
        
        # 登录状态保存路径
        self.state_dir = Path(self.config.get('state_dir', './data/rpa_state'))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / 'wechat_login_state.json'
        
        # 浏览器实例
        self.browser = None
        self.context = None
        self.page = None
        
        self.detail_logger.debug(f"配置: headless={self.headless}, slow_mo={self.slow_mo}, timeout={self.timeout}")
        self.detail_logger.debug(f"状态目录: {self.state_dir}")
        self.logger.info("🤖 WeChatRPA 已初始化")
    
    def _random_delay(self, min_seconds=1, max_seconds=3):
        """随机延迟，模拟人工操作"""
        delay = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"随机延迟 {delay:.1f} 秒...")
        time.sleep(delay)
    
    def _human_like_delay(self):
        """类人操作延迟 - 用于关键操作"""
        # 模拟人类的思考和操作时间
        delay = random.uniform(0.5, 2.0)
        time.sleep(delay)
    
    def _smooth_move_to(self, target_x: int, target_y: int, duration: float = 0.5):
        """
        平滑移动鼠标到目标位置，模拟人类手部的自然移动轨迹
        
        Args:
            target_x: 目标 X 坐标
            target_y: 目标 Y 坐标  
            duration: 移动持续时间（秒）
        """
        try:
            # 获取当前鼠标位置
            current_pos = self.page.evaluate("() => { return { x: window.mouseX || 0, y: window.mouseY || 0 }; }")
            start_x = current_pos.get('x', 0)
            start_y = current_pos.get('y', 0)
            
            # 如果获取失败，使用页面中心附近
            if start_x == 0 and start_y == 0:
                viewport = self.page.viewport_size
                start_x = viewport['width'] // 2
                start_y = viewport['height'] // 2
            
            # 添加随机偏移（模拟手部不精确性）
            offset_x = random.randint(-20, 20)
            offset_y = random.randint(-10, 10)
            final_x = target_x + offset_x
            final_y = target_y + offset_y
            
            # 计算贝塞尔曲线控制点（模拟自然曲线）
            mid_x = (start_x + final_x) / 2 + random.randint(-100, 100)
            mid_y = (start_y + final_y) / 2 + random.randint(-50, 50)
            
            # 分段移动，每段都有轻微随机偏移
            steps = int(duration * 60)  # 60fps
            for i in range(steps):
                t = i / steps
                # 二次贝塞尔曲线
                x = (1-t)**2 * start_x + 2*(1-t)*t * mid_x + t**2 * final_x
                y = (1-t)**2 * start_y + 2*(1-t)*t * mid_y + t**2 * final_y
                
                # 添加微小抖动（模拟手部颤抖）
                jitter_x = random.randint(-2, 2)
                jitter_y = random.randint(-1, 1)
                
                self.page.mouse.move(x + jitter_x, y + jitter_y)
                time.sleep(duration / steps)
                
        except Exception as e:
            self.logger.debug(f"平滑移动失败，使用直接移动: {e}")
            # 失败时直接移动
            self.page.mouse.move(target_x, target_y)
    
    def _human_like_click(self, element):
        """
        类人点击操作 - 包含平滑移动和随机停顿
        
        Args:
            element: 要点击的元素
        """
        try:
            # 获取元素位置
            box = element.bounding_box()
            if not box:
                # 如果无法获取位置，直接点击
                element.click()
                return
            
            # 计算元素中心点（带随机偏移，不是每次都点正中心）
            center_x = box['x'] + box['width'] / 2 + random.randint(-10, 10)
            center_y = box['y'] + box['height'] / 2 + random.randint(-5, 5)
            
            # 平滑移动鼠标到元素
            self.logger.debug(f"平滑移动鼠标到 ({center_x:.0f}, {center_y:.0f})")
            self._smooth_move_to(int(center_x), int(center_y), duration=random.uniform(0.3, 0.8))
            
            # 停顿一下（模拟人类确认位置）
            time.sleep(random.uniform(0.1, 0.3))
            
            # 执行点击
            element.click()
            
        except Exception as e:
            self.logger.debug(f"类人点击失败，使用普通点击: {e}")
            element.click()
    
    def _find_system_browser(self) -> str:
        """查找系统已安装的浏览器 - 优先使用 Edge"""
        import shutil
        import winreg
        from pathlib import Path
        
        # 优先检测 Edge（Windows 默认浏览器）
        edge_paths = [
            # 系统级 Edge
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            # 用户级 Edge
            Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ]
        
        for path in edge_paths:
            path_str = str(path) if isinstance(path, Path) else path
            if Path(path_str).exists():
                self.logger.info(f"找到 Edge 浏览器: {path_str}")
                return path_str
        
        # 尝试从注册表获取 Edge 路径
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe") as key:
                edge_path, _ = winreg.QueryValueEx(key, None)
                if edge_path and Path(edge_path).exists():
                    self.logger.info(f"从注册表找到 Edge: {edge_path}")
                    return edge_path
        except:
            pass
        
        # 备选：Chrome
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
        
        for path in chrome_paths:
            path_str = str(path) if isinstance(path, Path) else path
            if Path(path_str).exists():
                self.logger.info(f"找到 Chrome 浏览器: {path_str}")
                return path_str
        
        # 最后尝试环境变量
        for browser in ['msedge', 'chrome', 'google-chrome']:
            path = shutil.which(browser)
            if path:
                self.logger.info(f"从环境变量找到浏览器: {path}")
                return path
        
        return None
    
    def _init_browser(self, use_saved_state: bool = True):
        """初始化浏览器"""
        try:
            from playwright.sync_api import sync_playwright
            
            self.p = sync_playwright().start()
            
            # 查找浏览器
            browser_path = self._find_system_browser()
            
            # 构建启动参数
            launch_options = {
                'headless': self.headless,
                'slow_mo': self.slow_mo
            }
            
            # 如果找到系统浏览器，使用它
            if browser_path:
                launch_options['executable_path'] = browser_path
                self.logger.info(f"使用系统浏览器: {browser_path}")
            else:
                self.logger.info("使用 Playwright 自带 Chromium")
            
            # 启动浏览器
            self.browser = self.p.chromium.launch(**launch_options)
            
            # 创建上下文（尝试加载保存的登录状态）
            if use_saved_state and self.state_file.exists():
                self.logger.info("加载保存的登录状态...")
                self.context = self.browser.new_context(
                    storage_state=str(self.state_file)
                )
            else:
                self.context = self.browser.new_context()
            
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.timeout)
            
            # 注入鼠标位置追踪脚本
            self.page.evaluate("""
                document.addEventListener('mousemove', (e) => {
                    window.mouseX = e.clientX;
                    window.mouseY = e.clientY;
                });
            """)
            
            self.logger.info("浏览器初始化完成")
            
        except ImportError:
            self.logger.error("请先安装 Playwright: pip install playwright")
            raise
    
    def login(self, save_state: bool = True) -> bool:
        """
        登录公众号后台
        
        Args:
            save_state: 是否保存登录状态
            
        Returns:
            是否登录成功
        """
        self._init_browser(use_saved_state=True)
        
        try:
            # 访问公众号后台
            self.logger.info("访问公众号后台...")
            self.page.goto("https://mp.weixin.qq.com/")
            
            # 检查是否已经登录
            if self._is_logged_in():
                self.logger.info("已处于登录状态")
                return True
            
            # 需要重新登录
            self.logger.info("需要扫码登录，请使用微信扫描二维码...")
            
            # 等待扫码完成（页面跳转到后台首页）
            try:
                # 循环检测登录状态，同时检测各种登录按钮
                max_wait = 120  # 最多等待120秒
                clicked_relogin = False
                
                for i in range(max_wait):
                    # 检查是否已登录成功
                    if self._is_logged_in():
                        self.logger.info("✅ 登录成功！")
                        break
                    
                    current_url = self.page.url
                    self.logger.debug(f"当前页面: {current_url[:50]}...")
                    
                    # 检查是否有"重新登录"按钮
                    if not clicked_relogin:
                        try:
                            # 检测"重新登录"按钮
                            relogin_btn = self.page.locator('text=重新登录').first
                            if relogin_btn.is_visible(timeout=500):
                                self.logger.info("[检测到] '重新登录'按钮，准备点击...")
                                relogin_btn.click()
                                self.logger.info("[已点击] '重新登录'按钮")
                                clicked_relogin = True
                                time.sleep(3)  # 等待页面跳转
                                continue
                        except Exception as e:
                            self.logger.debug(f"检测'重新登录'按钮失败: {e}")
                        
                        # 检测"登录"按钮（可能是简单的"登录"两个字）
                        try:
                            # 方法1：通过文字内容
                            login_text_btn = self.page.locator('text=登录 >> visible=true').first
                            if login_text_btn.is_visible(timeout=500):
                                self.logger.info("[检测到] '登录'文字按钮，准备点击...")
                                login_text_btn.click()
                                self.logger.info("[已点击] '登录'文字按钮")
                                clicked_relogin = True
                                time.sleep(3)
                                continue
                        except Exception as e:
                            self.logger.debug(f"检测'登录'文字按钮失败: {e}")
                        
                        # 方法2：通过class检测登录按钮
                        try:
                            login_class_btn = self.page.locator('.btn_login:visible, .login_btn:visible, [class*="login"]:visible').first
                            if login_class_btn.is_visible(timeout=500):
                                btn_text = login_class_btn.inner_text() if login_class_btn.is_visible() else "未知"
                                self.logger.info(f"[检测到] 登录按钮(class)，文字: '{btn_text}'，准备点击...")
                                login_class_btn.click()
                                self.logger.info("[已点击] 登录按钮(class)")
                                clicked_relogin = True
                                time.sleep(3)
                                continue
                        except Exception as e:
                            self.logger.debug(f"检测登录按钮(class)失败: {e}")
                        
                        # 方法3：检测绿色/蓝色的登录按钮
                        try:
                            color_btns = self.page.locator('button:has-text("登录"), a:has-text("登录"), .btn:has-text("登录"), .weui-btn:has-text("登录")').all()
                            for btn in color_btns:
                                if btn.is_visible():
                                    btn_text = btn.inner_text()[:20]
                                    self.logger.info(f"[检测到] 登录按钮(文字匹配)，文字: '{btn_text}'，准备点击...")
                                    btn.click()
                                    self.logger.info("[已点击] 登录按钮(文字匹配)")
                                    clicked_relogin = True
                                    time.sleep(3)
                                    break
                            if clicked_relogin:
                                continue
                        except Exception as e:
                            self.logger.debug(f"检测登录按钮(文字匹配)失败: {e}")
                    
                    time.sleep(1)
                    
                    # 每10秒输出一次提示
                    if i % 10 == 0 and i > 0:
                        self.logger.info(f"等待登录中... {i}秒")
                        if not clicked_relogin:
                            self.logger.info("提示：如果看到登录按钮，程序会自动点击")
                            # 截图保存，方便调试
                            try:
                                screenshot_path = f"./data/rpa_state/login_wait_{i}.png"
                                self.page.screenshot(path=screenshot_path)
                                self.logger.debug(f"已保存截图: {screenshot_path}")
                            except:
                                pass
                else:
                    # 超时
                    if not self._is_logged_in():
                        self.logger.error("登录超时，请检查是否已完成扫码")
                        return False
                
                # 保存登录状态
                if save_state:
                    self.context.storage_state(path=str(self.state_file))
                    self.logger.info(f"登录状态已保存到: {self.state_file}")
                
                return True
                
            except Exception as e:
                self.logger.error(f"登录超时: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            return False
    
    def _is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            # 检查页面 URL
            current_url = self.page.url
            if "cgi-bin/home" in current_url:
                self.logger.debug("检测到已登录（URL包含home）")
                return True
            if "cgi-bin/appmsg" in current_url:
                self.logger.debug("检测到已登录（URL包含appmsg）")
                return True
            
            # 检查是否有登录后才会出现的元素
            # 方法1：检查左侧菜单
            if self.page.locator(".weui-desktop-layout__sidebar").count() > 0:
                self.logger.debug("检测到已登录（有侧边栏）")
                return True
            
            # 方法2：检查账号信息
            if self.page.locator(".weui-desktop-account__nickname").count() > 0:
                self.logger.debug("检测到已登录（有账号信息）")
                return True
            
            # 方法3：检查首页特有的元素
            if self.page.locator("text=新的创作").count() > 0:
                self.logger.debug("检测到已登录（有新的创作按钮）")
                return True
                
        except Exception as e:
            self.logger.debug(f"检查登录状态时出错: {e}")
        
        return False
    
    def create_article(self, article: Dict) -> Dict:
        """
        创建新文章
        
        Args:
            article: 文章数据
                - title: 标题
                - content: 正文（HTML 或纯文本）
                - author: 作者
                - cover_image: 封面图片路径（可选）
                
        Returns:
            创建结果
        """
        if not self._is_logged_in():
            if not self.login():
                return {'success': False, 'error': '未登录'}
        
        try:
            # 1. 进入新建图文页面
            self._goto_create_page()
            self._random_delay(1, 2)  # 页面进入后停顿
            
            # 检查登录状态
            if not self._check_and_restore_login():
                return {'success': False, 'error': '登录状态异常'}
            
            # 2. 等待编辑器加载
            self._wait_for_editor()
            self._random_delay(0.5, 1)  # 编辑器加载后停顿
            
            # 检查登录状态
            if not self._check_and_restore_login():
                return {'success': False, 'error': '登录状态异常'}
            
            # 3. 填写标题
            title = article.get('title', '')
            self.logger.info(f"准备填写标题，长度: {len(title)}, 内容: {title[:50]}...")
            if not title:
                self.logger.error("❌ 标题为空！")
                return {'success': False, 'error': '文章标题不能为空'}
            self._fill_title(title)
            self._random_delay(1, 2)  # 标题填写后停顿
            
            # 检查登录状态
            if not self._check_and_restore_login():
                return {'success': False, 'error': '登录状态异常'}
            
            # 4. 填写作者
            author = article.get('author', '')
            self.logger.info(f"准备填写作者: {author}")
            if not author:
                author = 'AI小编'  # 使用默认作者
                self.logger.info(f"作者为空，使用默认值: {author}")
            self._fill_author(author)
            self._random_delay(0.5, 1)  # 作者填写后停顿
            
            # 检查登录状态
            if not self._check_and_restore_login():
                return {'success': False, 'error': '登录状态异常'}
            
            # 5. 填写正文
            self._fill_content(article.get('content', ''))
            self._random_delay(1, 2)  # 正文填写后停顿
            
            # 最终检查登录状态
            if not self._check_and_restore_login():
                return {'success': False, 'error': '登录状态异常'}
            
            # 6. 上传封面图或使用AI配图
            use_ai_cover = article.get('use_ai_cover', True)  # 默认使用AI配图
            manual_ai_cover = article.get('manual_ai_cover', False)  # 手动模式
            
            if use_ai_cover and article.get('title'):
                self.logger.info("使用AI配图...")
                try:
                    self._upload_cover_ai(article['title'], manual_mode=manual_ai_cover)
                except Exception as e:
                    self.logger.error(f"AI配图失败: {e}")
                    if manual_ai_cover:
                        self.logger.info("请手动完成封面设置")
                        input("请手动设置封面，完成后按回车继续...")
                    else:
                        self.logger.warning("AI配图失败，但继续发布流程")
            elif article.get('cover_image'):
                self.logger.info("使用本地图片作为封面...")
                self._upload_cover(article['cover_image'])
            else:
                self.logger.info("未配置封面，跳过")
            
            self.logger.info("✅ 文章内容填写完成")
            
            return {
                'success': True,
                'status': 'draft_created',
                'message': '文章已创建，可以选择保存或发布'
            }
            
        except Exception as e:
            self.logger.error(f"创建文章失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _goto_create_page(self):
        """
        通过点击菜单进入新建图文页面（完全模拟人工操作）
        流程：首页 -> 直接点击"文章" -> 进入编辑页面
        """
        self.logger.info("通过菜单导航进入编辑页面...")
        
        # 步骤1：确保在首页
        if not self._ensure_at_home():
            raise Exception("无法进入公众号首页")
        
        # 步骤2：直接点击"文章"
        if not self._click_article():
            raise Exception("无法点击'文章'")
        
        # 步骤2.5：等待页面加载
        self.logger.info("等待页面加载...")
        time.sleep(3)  # 等待页面加载
        
        # 优先检查当前页面是否已经是编辑页面（检测"发表"按钮）
        if self._is_in_editor():
            self.logger.info("编辑器已在当前页面打开（检测到发表按钮）")
        else:
            # 尝试切换到新标签页（如果编辑器在新标签页打开）
            self.logger.info("检查是否有新标签页...")
            if not self._switch_to_new_page(timeout=5):
                self.logger.warning("未检测到新标签页，继续检查当前页面...")
                if not self._is_in_editor():
                    self.logger.warning("当前页面不是编辑器，可能加载较慢或点击未生效")
        
        # 步骤3：处理可能出现的重新登录弹窗
        if not self._handle_relogin_if_needed():
            raise Exception("无法处理登录验证")
        
        # 步骤4：验证是否成功进入编辑页面
        if not self._verify_in_editor():
            raise Exception("未能成功进入编辑页面")
        
        self.logger.info("✅ 成功通过菜单导航进入编辑页面")
    
    def _ensure_at_home(self) -> bool:
        """确保当前在公众号首页"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            current_url = self.page.url
            
            # 已经在首页
            if "cgi-bin/home" in current_url:
                self.logger.info("已在公众号首页")
                self._random_delay(2, 3)  # 模拟浏览首页
                return True
            
            # 在编辑页面，需要返回首页重新进入（避免直接URL访问）
            if self._is_in_editor():
                self.logger.info("在编辑页面，返回首页重新通过菜单进入...")
                # 点击左侧首页图标或返回按钮
                try:
                    home_btn = self.page.locator('.weui-desktop-layout__sidebar a[href*="home"], .icon_home').first
                    if home_btn.is_visible(timeout=3000):
                        self._human_like_click(home_btn)
                        time.sleep(3)
                        continue
                except:
                    pass
                # 如果找不到返回按钮，访问首页
                self.page.goto("https://mp.weixin.qq.com/cgi-bin/home")
                self.page.wait_for_load_state('networkidle')
                time.sleep(3)
                continue
            
            # 在登录页，需要登录
            if "loginpage" in current_url or not self._is_logged_in():
                self.logger.info("需要登录...")
                if not self._perform_login():
                    return False
                continue
            
            # 其他情况，访问首页
            self.logger.info(f"当前在 {current_url}，访问首页...")
            self.page.goto("https://mp.weixin.qq.com/cgi-bin/home")
            self.page.wait_for_load_state('networkidle')
            time.sleep(3)
        
        return "cgi-bin/home" in self.page.url
    
    def _click_article(self) -> bool:
        """直接点击'文章'选项进入编辑页面"""
        self.logger.info("点击'文章'...")
        self.detail_logger.step("开始点击'文章'按钮")
        self.detail_logger.page_state(url=self.page.url)
        
        # 多种可能的选择器（按优先级排序）
        selectors = [
            # 精确匹配"新的创作"区域的文章按钮
            '.new-creation__menu-item:has(.new-creation__menu-title:has-text("文章"))',
            '.new-creation__menu-item .new-creation__menu-title:has-text("文章")',
            'div.new-creation__menu-item:has-text("文章")',
            '.new-creation__menu-list .new-creation__menu-item:has-text("文章")',
            '[class*="new-creation"]:has-text("文章")',
            'text=文章',
            'a:has-text("文章")',
            'button:has-text("文章")',
            '.article',
            '.menu-item:has-text("文章")',
            'li:has-text("文章")',
            '[class*="article"]',
            '[title="文章"]',
            '.sidebar a:has-text("文章")',
            '.weui-desktop-layout__sidebar a:has-text("文章")',
        ]
        
        self.detail_logger.debug(f"准备尝试 {len(selectors)} 个选择器")
        
        for idx, selector in enumerate(selectors, 1):
            try:
                self.detail_logger.debug(f"[{idx}/{len(selectors)}] 尝试选择器: {selector}")
                btn = self.page.locator(selector).first
                
                if btn.is_visible(timeout=5000):
                    btn_text = btn.inner_text()[:20]
                    self.detail_logger.selector(selector, found=True, timeout=5.0)
                    self.logger.info(f"找到'文章'按钮: {selector} (文字: '{btn_text}')")
                    self.detail_logger.action("查找按钮", "文章按钮", f"选择器: {selector}, 文字: {btn_text}")
                    
                    # 对于新的创作区域的选择器，使用 JavaScript 点击更可靠
                    if 'new-creation' in selector:
                        self.detail_logger.action("点击", "文章按钮", "使用JavaScript点击")
                        self.logger.info("使用 JavaScript 点击新的创作区域文章按钮...")
                        clicked = self.page.evaluate("""
                            () => {
                                const items = document.querySelectorAll('.new-creation__menu-item');
                                for (let item of items) {
                                    const title = item.querySelector('.new-creation__menu-title');
                                    if (title && title.textContent.includes('文章')) {
                                        item.click();
                                        return 'clicked new-creation menu item';
                                    }
                                }
                                return null;
                            }
                        """)
                        if clicked:
                            self.detail_logger.success(f"JavaScript 点击成功: {clicked}")
                            self.logger.info(f"JavaScript 点击成功: {clicked}")
                        else:
                            self.detail_logger.warning("JavaScript 点击失败，回退到普通点击")
                            self._human_like_click(btn)
                    else:
                        self.detail_logger.action("点击", "文章按钮", "使用普通点击")
                        self._human_like_click(btn)
                    
                    self.detail_logger.success("已点击'文章'按钮")
                    self.logger.info("已点击'文章'，等待页面加载...")
                    time.sleep(4)  # 等待编辑页面加载
                    return True
                else:
                    self.detail_logger.selector(selector, found=False, timeout=5.0)
            except Exception as e:
                self.detail_logger.error(f"选择器 {selector} 失败", exception=e)
                self.logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        
        # 最后的备选：直接尝试 JavaScript 查找并点击
        try:
            self.logger.info("尝试 JavaScript 直接查找文章按钮...")
            js_clicked = self.page.evaluate("""
                () => {
                    // 方法1: 查找新的创作区域
                    const items = document.querySelectorAll('.new-creation__menu-item');
                    for (let item of items) {
                        const title = item.querySelector('.new-creation__menu-title');
                        if (title && title.textContent.trim() === '文章') {
                            item.click();
                            return 'new-creation article clicked';
                        }
                    }
                    
                    // 方法2: 查找所有包含"文章"的元素
                    const allElements = document.querySelectorAll('*');
                    for (let el of allElements) {
                        if (el.children.length === 0 && el.textContent.trim() === '文章') {
                            // 找到文本节点，尝试点击其父元素
                            let parent = el.parentElement;
                            for (let i = 0; i < 3; i++) {  // 向上查找3层
                                if (parent && parent.click) {
                                    parent.click();
                                    return 'clicked by text search: ' + parent.className;
                                }
                                parent = parent?.parentElement;
                            }
                        }
                    }
                    return null;
                }
            """)
            if js_clicked:
                self.detail_logger.success(f"JavaScript 备选点击成功: {js_clicked}")
                self.logger.info(f"JavaScript 备选点击成功: {js_clicked}")
                time.sleep(4)
                return True
            else:
                self.detail_logger.error("JavaScript 备选方案也未找到按钮")
        except Exception as e:
            self.detail_logger.error("JavaScript 备选点击失败", exception=e)
            self.logger.debug(f"JavaScript 备选点击失败: {e}")
        
        # 如果没找到，截图保存用于调试
        self.detail_logger.step("保存失败截图")
        try:
            screenshot_path = "./data/rpa_state/cant_find_article.png"
            self.page.screenshot(path=screenshot_path)
            self.detail_logger.screenshot(screenshot_path, "无法找到文章按钮")
            self.logger.info(f"已保存截图: {screenshot_path}")
        except Exception as e:
            self.detail_logger.error("截图保存失败", exception=e)
        
        self.detail_logger.error("点击文章按钮失败：所有方法都尝试过了")
        return False
    
    def _switch_to_new_page(self, timeout: int = 10) -> bool:
        """切换到新打开的标签页，或检查当前页面是否已是编辑页面"""
        try:
            # 首先检查当前页面是否已经是编辑页面（通过检测发表按钮）
            if self._is_in_editor():
                self.logger.info("当前页面已是编辑页面")
                return True
            
            # 等待新页面打开
            for i in range(timeout):
                contexts = self.browser.contexts
                if contexts:
                    pages = contexts[0].pages
                    if len(pages) > 1:
                        # 倒序遍历，优先选择最后打开的编辑页面
                        for p in reversed(pages):
                            # 临时切换到该页面检测
                            old_page = self.page
                            self.page = p
                            if self._is_in_editor():
                                self.logger.info(f"切换到编辑标签页")
                                self.page.bring_to_front()
                                return True
                            self.page = old_page
                        
                        # 如果没有找到编辑页面，切换到最新的
                        new_page = pages[-1]
                        self.logger.info(f"切换到新标签页")
                        self.page = new_page
                        self.page.bring_to_front()
                        # 再次检查是否是编辑页面
                        if self._is_in_editor():
                            return True
                time.sleep(1)
            
            # 最后再次检查当前页面
            if self._is_in_editor():
                self.logger.info("当前页面已是编辑页面（最终检查）")
                return True
                
            return False
        except Exception as e:
            self.logger.warning(f"切换标签页失败: {e}")
            return False
    
    def _handle_relogin_if_needed(self) -> bool:
        """处理可能出现的重新登录验证"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            # 首先尝试切换到新标签页（编辑器可能在新标签页打开）
            self._switch_to_new_page(timeout=3)
            
            # 检查是否出现重新登录界面
            if not self._has_relogin_button():
                # 没有出现重新登录，检查是否在编辑页面（通过检测发表按钮）
                if self._is_in_editor():
                    return True
                # 可能被重定向到首页
                if "cgi-bin/home" in self.page.url:
                    self.logger.info("检测到仍在首页，重新尝试点击'文章'...")
                    if self._click_article():
                        # 再次尝试切换标签页
                        time.sleep(3)
                        self._switch_to_new_page(timeout=5)
                        continue
                return False
            
            # 出现重新登录，自动点击
            self.logger.info(f"出现重新登录验证（尝试 {attempt+1}/{max_attempts}）...")
            if self._click_relogin_button():
                self.logger.info("已点击登录按钮，等待跳转...")
                # 等待跳转到编辑页面
                for i in range(15):  # 最多等待15秒
                    time.sleep(1)
                    # 检查是否需要切换标签页
                    self._switch_to_new_page(timeout=1)
                    if self._is_in_editor() and not self._has_relogin_button():
                        self.logger.info("成功进入编辑页面")
                        return True
                    # 如果在首页，重新点击菜单
                    if "cgi-bin/home" in self.page.url:
                        self.logger.info("在首页，重新点击菜单...")
                        break
            else:
                self.logger.warning("未找到登录按钮")
                return False
        
        return self._is_in_editor()
    
    def _is_in_editor(self) -> bool:
        """检测当前是否在编辑页面（通过检测发表按钮或标题输入框）"""
        try:
            # 检测发表按钮（编辑器页面的特征元素）
            publish_btn = self.page.locator('button.mass_send').first
            if publish_btn.is_visible(timeout=3000):
                self.logger.info("检测到发表按钮，当前在编辑页面")
                return True
            
            # 备用检测：检测新编辑器的标题输入框（ProseMirror）
            title_input = self.page.locator('.ProseMirror[contenteditable="true"][data-placeholder*="标题"]').first
            if title_input.is_visible(timeout=2000):
                self.logger.info("检测到标题输入框(ProseMirror)，当前在编辑页面")
                return True
            
            # 再备用：检测旧版标题输入框
            title_input_old = self.page.locator('#title').first
            if title_input_old.is_visible(timeout=1000):
                self.logger.info("检测到标题输入框(旧版)，当前在编辑页面")
                return True
                
            return False
        except:
            return False
    
    def _verify_in_editor(self) -> bool:
        """验证是否成功进入编辑页面"""
        # 优先检测发表按钮或标题输入框
        if self._is_in_editor():
            self._random_delay(2, 3)
            return True
        
        # 备用：等待编辑页面元素加载
        try:
            # 尝试新编辑器
            self.page.wait_for_selector('.ProseMirror[contenteditable="true"]', state='visible', timeout=15000)
            self.logger.info("编辑页面加载完成(ProseMirror)")
            self._random_delay(2, 3)
            return True
        except:
            # 尝试旧编辑器
            try:
                self.page.wait_for_selector("#title", state='visible', timeout=5000)
                self.logger.info("编辑页面加载完成(旧版)")
                self._random_delay(2, 3)
                return True
            except:
                self.logger.error(f"编辑页面验证失败，当前URL: {self.page.url}")
                return False
    
    def _perform_login(self) -> bool:
        """执行登录流程"""
        self.logger.info("执行登录...")
        return self.login(save_state=True)
    
    def _check_and_restore_login(self) -> bool:
        """
        检查登录状态，如果出现重新登录界面则自动处理
        
        Returns:
            True - 登录状态正常或已成功恢复
            False - 无法恢复登录状态
        """
        # 检查是否需要重新登录
        if self._has_relogin_button():
            self.logger.info("检测到需要重新登录，自动处理中...")
            
            # 尝试点击登录按钮
            if self._click_relogin_button():
                self.logger.info("已点击登录按钮，等待恢复...")
                
                # 等待恢复（最多10秒）
                for i in range(10):
                    time.sleep(1)
                    
                    # 检查是否恢复
                    if not self._has_relogin_button():
                        # 检查是否在编辑页面（通过检测发表按钮）
                        if self._is_in_editor():
                            self.logger.info("登录状态已恢复")
                            # 更新登录状态
                            try:
                                self.context.storage_state(path=str(self.state_file))
                                self.logger.debug("已更新登录状态文件")
                            except:
                                pass
                            return True
                        # 如果被重定向到首页，尝试重新进入编辑页面
                        elif "cgi-bin/home" in self.page.url:
                            self.logger.info("在首页，尝试重新进入编辑页面...")
                            self._goto_create_page()
                            return True
                
                self.logger.error("点击登录后未能恢复")
                return False
            else:
                self.logger.error("无法点击登录按钮")
                return False
        
        # 检查是否还在编辑页面
        if "appmsg_edit" not in self.page.url and "cgi-bin/home" not in self.page.url:
            self.logger.warning(f"当前不在预期页面: {self.page.url}")
            # 尝试返回编辑页面
            if "appmsg_edit" in self.page.url:
                return True
            self._goto_create_page()
        
        return True
    
    def _has_relogin_button(self) -> bool:
        """检查是否有重新登录/登录按钮"""
        try:
            # 检测各种可能的登录按钮
            selectors = [
                'text=重新登录',
                'text=登录',
                '.btn_login',
                'button:has-text("登录")',
                'a:has-text("登录")'
            ]
            
            for selector in selectors:
                try:
                    if self.page.locator(selector).first.is_visible(timeout=1000):
                        return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def _click_relogin_button(self) -> bool:
        """点击重新登录/登录按钮"""
        selectors = [
            ('text=重新登录', '重新登录'),
            ('text=登录', '登录'),
            ('.btn_login', '登录按钮(class)'),
            ('button:has-text("登录")', '登录按钮'),
            ('a:has-text("登录")', '登录链接'),
        ]
        
        for selector, name in selectors:
            try:
                btn = self.page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn_text = btn.inner_text()[:20] if btn.is_visible() else ""
                    self.logger.info(f"[点击] {name} 按钮 (文字: '{btn_text}')")
                    self._human_like_click(btn)
                    return True
            except:
                continue
        
        return False
    
    def _wait_for_editor(self):
        """等待编辑器加载完成（支持新版和旧版编辑器）"""
        self.logger.debug("等待编辑器加载...")
        
        # 等待标题输入框出现（最多等待 30 秒），同时检查是否出现重新登录
        start_time = time.time()
        while time.time() - start_time < 30:
            # 检查是否出现重新登录界面
            if self._has_relogin_button():
                self.logger.info("等待编辑器时出现重新登录界面，自动处理...")
                if self._click_relogin_button():
                    self.logger.info("已点击登录，继续等待...")
                    time.sleep(3)
                    continue
                else:
                    raise Exception("无法自动处理重新登录")
            
            # 检查新版编辑器是否已加载（ProseMirror）
            try:
                if self.page.locator('.ProseMirror[contenteditable="true"][data-placeholder*="标题"]').is_visible(timeout=1000):
                    self.logger.debug("新版编辑器(ProseMirror)已加载")
                    break
            except:
                pass
            
            # 检查旧版编辑器是否已加载
            try:
                if self.page.locator("#title").is_visible(timeout=1000):
                    self.logger.debug("旧版编辑器已加载")
                    break
            except:
                pass
            
            time.sleep(1)
        else:
            # 超时
            self.logger.error("等待编辑器超时")
            self.logger.info(f"当前页面 URL: {self.page.url}")
            # 截图保存供调试
            try:
                screenshot_path = "./data/rpa_state/error_screenshot.png"
                self.page.screenshot(path=screenshot_path)
                self.logger.info(f"已保存截图: {screenshot_path}")
            except:
                pass
            raise Exception("等待编辑器加载超时")
        
        # 额外等待编辑器初始化（增加随机延迟）
        self._random_delay(2, 4)
    
    def _fill_title(self, title: str):
        """填写标题 - 支持新版ProseMirror编辑器"""
        self.logger.info(f"填写标题: {title[:30]}...")
        self.detail_logger.step("开始填写标题")
        self.detail_logger.debug(f"标题内容长度: {len(title)}")
        
        # 首先尝试新版编辑器（ProseMirror）
        try:
            selector = '.ProseMirror[contenteditable="true"][data-placeholder*="标题"]'
            self.detail_logger.action("查找标题输入框", selector, "ProseMirror编辑器")
            
            title_input = self.page.locator(selector).first
            title_input.wait_for(state='visible', timeout=5000)
            
            self.detail_logger.selector(selector, found=True, timeout=5.0)
            self.detail_logger.action("点击", "标题输入框", "聚焦")
            
            # 点击聚焦
            title_input.click()
            self._random_delay(0.3, 0.5)
            
            # 全选并填写
            self.detail_logger.action("键盘操作", "标题输入框", "Control+a 全选")
            title_input.press('Control+a')
            self._random_delay(0.2, 0.3)
            
            self.detail_logger.action("填写", "标题输入框", f"内容: {title[:50]}...")
            title_input.fill(title)
            
            self.detail_logger.success("标题填写成功(ProseMirror)")
            self.logger.info(f"✅ 标题填写成功(ProseMirror)")
            self._random_delay(0.5, 1)
            return
            
        except Exception as e:
            self.detail_logger.warning(f"新版标题填写失败: {e}")
            self.logger.debug(f"新版标题填写失败: {e}，尝试旧版")
        
        # 回退到旧版编辑器
        self.detail_logger.step("尝试旧版标题输入框")
        try:
            selector = "#title"
            self.detail_logger.action("查找标题输入框", selector, "旧版编辑器")
            
            title_input = self.page.locator(selector)
            title_input.wait_for(state='visible', timeout=5000)
            
            self.detail_logger.selector(selector, found=True, timeout=5.0)
            self.detail_logger.action("填写", "标题输入框(旧版)", f"内容: {title[:50]}...")
            
            title_input.fill(title)
            
            self.detail_logger.success("标题填写成功(旧版)")
            self.logger.info(f"✅ 标题填写成功(旧版)")
            self._random_delay(0.5, 1)
            
        except Exception as e:
            self.detail_logger.error("填写标题失败", exception=e)
            self.logger.error(f"❌ 填写标题失败: {e}")
            raise
    
    def _fill_author(self, author: str):
        """填写作者 - 使用input#author"""
        self.logger.info(f"填写作者: {author}")
        self.detail_logger.step("开始填写作者")
        
        try:
            selector = "input#author"
            self.detail_logger.action("查找作者输入框", selector)
            
            # 等待并确保作者输入框可见
            author_input = self.page.locator(selector)
            author_input.wait_for(state='visible', timeout=10000)
            
            self.detail_logger.selector(selector, found=True, timeout=10.0)
            self.detail_logger.action("点击", "作者输入框", "聚焦")
            
            # 点击聚焦
            author_input.click()
            self._random_delay(0.3, 0.5)
            
            # 全选并填写
            self.detail_logger.action("键盘操作", "作者输入框", "Control+a 全选")
            author_input.press('Control+a')
            self._random_delay(0.2, 0.3)
            
            self.detail_logger.action("填写", "作者输入框", f"内容: {author}")
            author_input.fill(author)
            
            self.detail_logger.success("作者填写成功")
            self.logger.info(f"✅ 作者填写成功")
            self._random_delay(0.3, 0.5)
            
        except Exception as e:
            self.detail_logger.error("填写作者失败", exception=e)
            self.logger.error(f"❌ 填写作者失败: {e}")
            raise
    
    def _fill_content(self, content: str):
        """
        填写正文内容 - 支持新版ProseMirror编辑器
        """
        self.logger.info("填写正文内容...")
        self.detail_logger.step("开始填写正文")
        self.detail_logger.debug(f"正文长度: {len(content)} 字符")
        
        # 优先尝试新版编辑器（ProseMirror）
        try:
            self.detail_logger.action("尝试", "正文编辑器", "ProseMirror方式")
            self._fill_content_prosemirror(content)
            return
        except Exception as e:
            self.detail_logger.warning(f"ProseMirror填写失败: {e}")
            self.logger.debug(f"ProseMirror填写失败: {e}，尝试其他方式")
        
        # 判断是否为 HTML 内容
        is_html = '<' in content and '>' in content
        
        if is_html:
            self.detail_logger.action("尝试", "正文编辑器", "HTML方式")
            self._fill_html_content(content)
        else:
            self.detail_logger.action("尝试", "正文编辑器", "纯文本方式")
            self._fill_text_content_with_focus(content)
    
    def _fill_content_prosemirror(self, content: str):
        """使用新版ProseMirror编辑器填写正文"""
        self.logger.info("使用ProseMirror编辑器填写正文...")
        self.detail_logger.step("查找ProseMirror正文编辑器")
        
        # 精确匹配正文编辑器（带占位文字"从这里开始写正文"）
        editor_selectors = [
            'div.ProseMirror[contenteditable="true"]:has(.editor_content_placeholder:has-text("从这里开始写正文"))',
            'div.ProseMirror[contenteditable="true"][translate="no"]',
            'section .ProseMirror[contenteditable="true"]',
            'div.ProseMirror[contenteditable="true"]:not([data-placeholder*="标题"])'
        ]
        
        self.detail_logger.debug(f"准备尝试 {len(editor_selectors)} 个选择器")
        
        for idx, selector in enumerate(editor_selectors, 1):
            try:
                self.detail_logger.debug(f"[{idx}/{len(editor_selectors)}] 尝试选择器: {selector}")
                editor = self.page.locator(selector).first
                editor.wait_for(state='visible', timeout=5000)
                
                self.detail_logger.selector(selector, found=True, timeout=5.0)
                self.detail_logger.action("点击", "正文编辑器", f"选择器: {selector}")
                
                # 点击聚焦
                editor.click()
                self._random_delay(0.5, 1)
                
                # 全选
                self.detail_logger.action("键盘操作", "正文编辑器", "Control+a 全选")
                editor.press('Control+a')
                self._random_delay(0.3, 0.5)
                
                # 填写内容
                self.detail_logger.action("填写", "正文编辑器", f"内容长度: {len(content)}")
                editor.fill(content)
                
                self.detail_logger.success("正文填写成功(ProseMirror)")
                self.logger.info(f"✅ 正文填写成功(ProseMirror)")
                self._random_delay(1, 2)
                return
                
            except Exception as e:
                self.detail_logger.selector(selector, found=False, timeout=5.0)
                self.detail_logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        
        # 最后的备选：使用JavaScript直接查找并填写
        self.detail_logger.step("尝试JavaScript直接填写正文")
        try:
            self.logger.info("尝试JavaScript直接填写正文...")
            self.detail_logger.action("JavaScript填写", "正文编辑器", "查找占位符")
            
            result = self.page.evaluate(f"""
                () => {{
                    const placeholders = document.querySelectorAll('.editor_content_placeholder');
                    for (let ph of placeholders) {{
                        if (ph.textContent.includes('从这里开始写正文')) {{
                            let editor = ph.closest('div.ProseMirror[contenteditable="true"]');
                            if (editor) {{
                                editor.focus();
                                editor.innerHTML = '<section><span>{content}</span></section>';
                                return 'javascript fill success';
                            }}
                        }}
                    }}
                    return null;
                }}
            """.replace('{content}', content.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '<br>')))
            
            if result:
                self.detail_logger.success("正文填写成功(JavaScript)")
                self.logger.info("✅ 正文填写成功(JavaScript)")
            else:
                self.detail_logger.error("JavaScript填写返回null，未找到编辑器")
                
            self._random_delay(1, 2)
            return
            
        except Exception as e:
            self.detail_logger.error("JavaScript填写失败", exception=e)
            self.logger.error(f"JavaScript填写也失败: {e}")
        
        raise Exception("未找到ProseMirror正文编辑器")
    
    def _fill_text_content(self, content: str):
        """填写纯文本内容"""
        try:
            import pyperclip
            
            # 等待编辑器加载
            self._wait_for_editor_iframe()
            
            # 找到编辑器
            editor = self._find_editor()
            if not editor:
                raise Exception("无法找到编辑器")
            
            # 复制粘贴
            pyperclip.copy(content)
            editor.press('Control+a')
            self._random_delay(0.2, 0.3)
            editor.press('Control+v')
            self._random_delay(0.5, 1)
            
            self.logger.info("正文填写完成")
            
        except Exception as e:
            self.logger.warning(f"粘贴失败: {e}")
            self._fill_content_by_js(content)
    
    def _fill_text_content_with_focus(self, content: str):
        """
        填写纯文本内容 - 使用JavaScript直接设置（最可靠）
        """
        self.logger.info("填写正文内容...")
        
        try:
            # 优先使用JavaScript直接设置编辑器内容
            result = self._set_editor_html(content.replace('\n', '<br>').replace('\n\n', '</p><p>'))
            
            if result:
                self.logger.info(f"✅ 正文填写成功: {result}")
                self._random_delay(1, 2)
                return
            else:
                self.logger.warning("JavaScript设置失败，尝试备用方法...")
                
        except Exception as e:
            self.logger.warning(f"JavaScript方式失败: {e}")
        
        # 备用：使用iframe方式
        try:
            self._fill_content_via_iframe(content)
        except Exception as e:
            self.logger.error(f"iframe方式也失败: {e}")
            # 最后尝试pyperclip
            self._fill_content_via_clipboard(content)
    
    def _fill_content_via_iframe(self, content: str):
        """通过iframe填写内容"""
        self.logger.info("通过iframe填写正文...")
        
        # 转换内容为HTML
        html_content = content.replace('\n\n', '</p><p>').replace('\n', '<br>')
        html_content = f'<p>{html_content}</p>'
        
        # 找到iframe并设置内容
        iframe_selectors = [
            'iframe#ueditor_0',
            '.edui-editor-iframeholder iframe',
            'iframe[src*="ueditor"]'
        ]
        
        for selector in iframe_selectors:
            try:
                # 等待iframe加载
                self.page.wait_for_selector(selector, timeout=5000)
                
                # 使用frame_locator
                iframe = self.page.frame_locator(selector)
                editor = iframe.locator('body')
                
                # 点击聚焦
                editor.click()
                self._random_delay(0.5, 1)
                
                # 清空并填写
                editor.press('Control+a')
                self._random_delay(0.3, 0.5)
                
                # 使用fill直接填写
                editor.fill(content)
                
                self.logger.info("✅ iframe方式填写成功")
                self._random_delay(1, 2)
                return
                
            except Exception as e:
                self.logger.debug(f"iframe选择器 {selector} 失败: {e}")
                continue
        
        raise Exception("所有iframe选择器都失败")
    
    def _fill_content_via_clipboard(self, content: str):
        """通过剪贴板填写内容（最后备选）"""
        try:
            import pyperclip
            
            self.logger.info("使用剪贴板方式填写...")
            pyperclip.copy(content)
            
            # 点击编辑器区域
            editor_area = self.page.locator('#ueditor_0, .edui-editor-iframeholder, .edui-editor').first
            if editor_area:
                editor_area.click()
                self._random_delay(0.5, 1)
                
                # 粘贴
                self.page.keyboard.press('Control+a')
                self._random_delay(0.3, 0.5)
                self.page.keyboard.press('Control+v')
                self._random_delay(0.5, 1)
                
                self.logger.info("✅ 剪贴板方式填写成功")
            else:
                raise Exception("未找到编辑器区域")
                
        except Exception as e:
            self.logger.error(f"剪贴板方式失败: {e}")
            # 最后的最后尝试
            self._fill_content_by_js(content)
    
    def _fill_html_content(self, html_content: str):
        """
        填写 HTML 内容
        
        直接操作 ueditor 设置 HTML，保留完整格式
        """
        try:
            # 使用 JavaScript 设置 HTML 内容
            result = self._set_editor_html(html_content)
            
            if result:
                self.logger.info(f"HTML 内容设置成功: {result}")
                # 稍微等待编辑器渲染
                self._random_delay(1, 2)
            else:
                raise Exception("设置 HTML 失败")
                
        except Exception as e:
            self.logger.error(f"设置 HTML 内容失败: {e}")
            # 回退到纯文本
            self.logger.info("回退到纯文本模式...")
            text = self._html_to_text(html_content)
            self._fill_content_by_js(text)
    
    def _insert_ai_image_to_content(self, title: str):
        """
        在正文中插入AI配图
        
        流程：
        1. 点击编辑器上方的"图片"按钮
        2. 点击"AI配图"
        3. 输入标题生成图片
        4. 选择图片并插入正文
        
        Args:
            title: 用于生成AI图片的标题
        """
        self.logger.info("在正文中插入AI配图...")
        
        try:
            import pyperclip
            
            # 步骤1: 点击编辑器上方的"图片"按钮
            self.logger.info("步骤1: 点击图片按钮...")
            
            # 尝试多种选择器找到图片按钮
            image_btn_selectors = [
                '.edui-for-image',
                '.edui-button-image',
                'button[title*="图片"]',
                'button[data-type="image"]',
                '.edui-toolbar .edui-btn-image',
            ]
            
            image_btn = None
            for selector in image_btn_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=3000):
                        image_btn = btn
                        self.logger.info(f"找到图片按钮: {selector}")
                        break
                except:
                    continue
            
            if not image_btn:
                raise Exception("未找到图片按钮")
            
            image_btn.click()
            self._random_delay(1, 2)
            
            # 步骤2: 点击"AI配图"选项
            self.logger.info("步骤2: 点击AI配图...")
            
            # 使用JavaScript查找并点击AI配图
            clicked = self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('*');
                    for (let el of elements) {
                        if (el.textContent && el.textContent.trim() === 'AI配图') {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                el.click();
                                return 'clicked: ' + el.tagName;
                            }
                        }
                    }
                    return null;
                }
            """)
            
            if not clicked:
                # 回退到普通选择器
                ai_btn = self.page.locator('text=AI配图').first
                if ai_btn.is_visible(timeout=3000):
                    ai_btn.click()
                    clicked = 'fallback'
                else:
                    raise Exception("未找到AI配图按钮")
            
            self.logger.info(f"点击AI配图成功: {clicked}")
            self._random_delay(2, 3)
            
            # 步骤3: 粘贴标题到输入框
            self.logger.info("步骤3: 输入标题...")
            
            # 找到标题输入框
            title_input_selectors = [
                'input[placeholder*="标题"]',
                'textarea[placeholder*="标题"]',
                '.ai-cover-input',
                'input[type="text"]',
            ]
            
            title_input = None
            for selector in title_input_selectors:
                try:
                    inp = self.page.locator(selector).first
                    if inp.is_visible(timeout=3000):
                        title_input = inp
                        break
                except:
                    continue
            
            if not title_input:
                raise Exception("未找到标题输入框")
            
            # 粘贴标题
            pyperclip.copy(title)
            title_input.click()
            self._random_delay(0.3, 0.5)
            title_input.press('Control+a')
            self._random_delay(0.2, 0.3)
            title_input.press('Control+v')
            self._random_delay(0.5, 1)
            
            # 步骤4: 点击"开始创作"
            self.logger.info("步骤4: 点击开始创作...")
            
            start_btn = self.page.locator('text=开始创作').first
            if not start_btn or not start_btn.is_visible(timeout=3000):
                # 尝试其他文本
                start_btn = self.page.locator('text=生成, text=创作').first
            
            if not start_btn:
                raise Exception("未找到开始创作按钮")
            
            start_btn.click()
            self.logger.info("等待AI生成图片（约10-15秒）...")
            self._random_delay(10, 15)
            
            # 步骤5: 选择图片并插入
            self.logger.info("步骤5: 选择图片并插入...")
            
            # 找到生成的图片并点击
            image_selectors = [
                '.ai-generated-image',
                '.generated-image',
                '[class*="result"] img',
                '.ai-image-item',
            ]
            
            generated_image = None
            for selector in image_selectors:
                try:
                    img = self.page.locator(selector).first
                    if img.is_visible(timeout=5000):
                        generated_image = img
                        break
                except:
                    continue
            
            if not generated_image:
                raise Exception("未找到生成的图片")
            
            # Hover并点击使用
            generated_image.hover()
            self._random_delay(0.5, 1)
            
            # 点击使用/插入按钮
            use_btn = self.page.locator('text=使用, text=插入, text=确定').first
            if use_btn and use_btn.is_visible(timeout=3000):
                use_btn.click()
            else:
                # 直接点击图片本身
                generated_image.click()
            
            self._random_delay(2, 3)
            
            self.logger.info("✅ AI配图已插入正文")
            
        except Exception as e:
            self.logger.error(f"插入AI配图失败: {e}")
            raise
    
    def _paste_image_to_content(self, image_path: str):
        """
        复制图片并粘贴到正文 - Windows上使用win32clipboard
        
        Args:
            image_path: 图片文件路径
        """
        self.logger.info(f"复制图片并粘贴到正文: {image_path}")
        
        try:
            from PIL import Image
            import io
            
            # 检查图片文件
            if not Path(image_path).exists():
                raise Exception(f"图片文件不存在: {image_path}")
            
            # 方法1: Windows上使用win32clipboard
            try:
                import win32clipboard
                import win32con
                
                # 打开图片并转换为BMP格式（Windows剪贴板格式）
                img = Image.open(image_path)
                
                # 转换为BMP格式并移除BMP头部
                output = io.BytesIO()
                img.convert('RGB').save(output, 'BMP')
                data = output.getvalue()[14:]  # 移除BMP头部
                output.close()
                
                # 复制到剪贴板
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_DIB, data)
                win32clipboard.CloseClipboard()
                
                self.logger.info("图片已复制到Windows剪贴板")
                
                # 聚焦编辑器
                iframe = self.page.frame_locator(".edui-editor-iframeholder iframe")
                editor = iframe.locator("body")
                editor.click()
                self._random_delay(0.5, 1)
                
                # 粘贴图片
                editor.press('Control+v')
                self._random_delay(2, 3)
                
                self.logger.info("图片已粘贴到正文")
                
            except ImportError:
                self.logger.warning("win32clipboard未安装，使用文件上传方式")
                self._insert_image_via_upload(image_path)
            except Exception as clipboard_error:
                self.logger.warning(f"剪贴板方式失败: {clipboard_error}，使用文件上传方式")
                self._insert_image_via_upload(image_path)
                
        except Exception as e:
            self.logger.error(f"粘贴图片失败: {e}")
            raise
    
    def _insert_image_via_upload(self, image_path: str):
        """
        通过编辑器的图片上传功能插入图片
        
        流程:
        1. 点击编辑器图片按钮
        2. 选择本地上传
        3. 选择文件
        """
        self.logger.info("通过上传方式插入图片...")
        
        try:
            # 步骤1: 点击编辑器图片按钮
            self.logger.info("点击图片按钮...")
            
            image_btn_selectors = [
                '.edui-for-image',
                '.edui-button-image',
                'button[title*="图片"]',
                'button[data-type="image"]',
            ]
            
            image_btn = None
            for selector in image_btn_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=3000):
                        image_btn = btn
                        break
                except:
                    continue
            
            if not image_btn:
                raise Exception("未找到图片按钮")
            
            image_btn.click()
            self._random_delay(1, 2)
            
            # 步骤2: 点击本地上传
            self.logger.info("点击本地上传...")
            
            upload_btn = self.page.locator('text=本地上传').first
            if not upload_btn or not upload_btn.is_visible(timeout=3000):
                raise Exception("未找到本地上传按钮")
            
            upload_btn.click()
            self._random_delay(1, 2)
            
            # 步骤3: 选择文件
            self.logger.info("选择图片文件...")
            
            file_input = self.page.locator("input[type='file']").first
            file_input.set_input_files(image_path)
            
            # 等待上传完成
            self.page.wait_for_selector("text=上传成功", timeout=30000)
            self._random_delay(1, 2)
            
            self.logger.info("图片已插入正文")
            
        except Exception as e:
            self.logger.error(f"上传图片失败: {e}")
            raise
    
    def _wait_for_editor_iframe(self):
        """等待编辑器 iframe 加载"""
        selectors = [
            "iframe#ueditor_0",
            ".edui-editor-iframeholder iframe",
            "iframe[src*='ueditor']",
        ]
        
        for selector in selectors:
            try:
                self.page.wait_for_selector(selector, timeout=5000)
                return selector
            except:
                continue
        
        raise Exception("编辑器 iframe 未找到")
    
    def _find_editor(self):
        """查找编辑器元素"""
        selectors = [
            "iframe#ueditor_0",
            ".edui-editor-iframeholder iframe",
            "iframe[src*='ueditor']",
        ]
        
        for selector in selectors:
            try:
                iframe = self.page.frame_locator(selector)
                editor = iframe.locator("body")
                if editor.is_visible(timeout=2000):
                    return editor
            except:
                continue
        
        return None
    
    def _set_editor_html(self, html: str) -> str:
        """
        使用 JavaScript 设置编辑器 HTML
        
        Returns:
            操作结果描述
        """
        # 转义 HTML 中的特殊字符
        escaped_html = html.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        
        js_code = f"""
            (function() {{
                const htmlContent = '{escaped_html}';
                
                // 方法1：使用 ueditor API
                if (typeof UE !== 'undefined' && UE.instants) {{
                    for (let key in UE.instants) {{
                        let editor = UE.instants[key];
                        if (editor && editor.setContent) {{
                            editor.setContent(htmlContent, false);  // false = 追加模式改为替换
                            return 'ueditor-api';
                        }}
                    }}
                }}
                
                // 方法2：直接操作 iframe body
                const iframe = document.querySelector('#ueditor_0') || 
                               document.querySelector('.edui-editor-iframeholder iframe');
                if (iframe && iframe.contentDocument && iframe.contentDocument.body) {{
                    iframe.contentDocument.body.innerHTML = htmlContent;
                    return 'iframe-body';
                }}
                
                // 方法3：遍历所有 iframe
                const iframes = document.querySelectorAll('iframe');
                for (let i = 0; i < iframes.length; i++) {{
                    try {{
                        const doc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                        if (doc && doc.body && doc.body.getAttribute('contenteditable') === 'true') {{
                            doc.body.innerHTML = htmlContent;
                            return 'editable-iframe-' + i;
                        }}
                    }} catch(e) {{}}
                }}
                
                return null;
            }})()
        """
        
        return self.page.evaluate(js_code)
    
    def _html_to_text(self, html: str) -> str:
        """简单 HTML 转文本"""
        import re
        
        # 替换常见标签
        text = html
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<h[1-6][^>]*>', '\n## ', text, flags=re.IGNORECASE)
        text = re.sub(r'</h[1-6]>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '\n- ', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)
        
        # 移除所有其他标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 解码 HTML 实体
        import html
        text = html.unescape(text)
        
        return text.strip()
    
    def _fill_html_content(self, html_content: str):
        """填写 HTML 内容（需要特殊处理）"""
        # 公众号编辑器支持粘贴 HTML
        # 可以将 HTML 复制到剪贴板然后粘贴
        
        try:
            import pyperclip
            
            # 复制 HTML 到剪贴板
            pyperclip.copy(html_content)
            
            # 聚焦编辑器
            iframe = self.page.frame_locator(".edui-editor-iframeholder iframe")
            editor = iframe.locator("body")
            editor.click()
            
            # 粘贴
            editor.press('Control+v')
            
        except ImportError:
            self.logger.warning("pyperclip 未安装，使用备用方法")
            # 直接填写纯文本
            text = html_content.replace('<p>', '').replace('</p>', '\n\n')
            text = text.replace('<h2>', '## ').replace('</h2>', '\n\n')
            
            iframe = self.page.frame_locator(".edui-editor-iframeholder iframe")
            editor = iframe.locator("body")
            editor.fill(text)
    
    def _fill_content_by_js(self, content: str):
        """使用 JavaScript 填写内容（备用方法）"""
        self.logger.info("使用 JavaScript 填写正文...")
        
        # 处理 HTML 或纯文本
        if '<' in content and '>' in content:
            html_content = content
        else:
            # 纯文本转换为 HTML
            paragraphs = content.split('\n\n')
            html_paras = []
            for para in paragraphs:
                if para.strip().startswith('##'):
                    html_paras.append(f'<h2>{para.lstrip("# ")}</h2>')
                else:
                    html_paras.append(f'<p>{para}</p>')
            html_content = '\n'.join(html_paras)
        
        # 尝试多种方式设置编辑器内容
        js_code = """
            (content) => {
                // 尝试找到 ueditor 实例
                if (typeof UE !== 'undefined' && UE.instants) {
                    for (let key in UE.instants) {
                        let editor = UE.instants[key];
                        if (editor && editor.setContent) {
                            editor.setContent(content);
                            return 'ueditor setContent success';
                        }
                    }
                }
                
                // 尝试直接操作 iframe
                let iframe = document.querySelector('#ueditor_0') || 
                            document.querySelector('.edui-editor-iframeholder iframe');
                if (iframe && iframe.contentDocument) {
                    iframe.contentDocument.body.innerHTML = content;
                    return 'iframe direct set success';
                }
                
                // 最后尝试：查找任何包含 editor 的 iframe
                let iframes = document.querySelectorAll('iframe');
                for (let i = 0; i < iframes.length; i++) {
                    try {
                        if (iframes[i].contentDocument && 
                            iframes[i].contentDocument.body) {
                            iframes[i].contentDocument.body.innerHTML = content;
                            return 'fallback iframe set success';
                        }
                    } catch(e) {}
                }
                
                return 'failed to find editor';
            }
        """
        
        try:
            result = self.page.evaluate(js_code, html_content)
            self.logger.info(f"JavaScript 填写结果: {result}")
        except Exception as e:
            self.logger.error(f"JavaScript 填写失败: {e}")
            raise
    
    def _upload_cover(self, image_path: str):
        """上传封面图片"""
        self.logger.info(f"上传封面: {image_path}")
        
        try:
            # 点击 "从图片库选择" 或 "本地上传"
            upload_btn = self.page.locator("text=本地上传").first
            upload_btn.click()
            
            # 等待文件选择对话框
            time.sleep(1)
            
            # 选择文件
            file_input = self.page.locator("input[type='file']")
            file_input.set_input_files(image_path)
            
            # 等待上传完成
            self.page.wait_for_selector("text=上传成功", timeout=30000)
            
            self.logger.info("封面上传成功")
            
        except Exception as e:
            self.logger.error(f"封面上传失败: {e}")
    
    def _upload_cover_ai(self, title: str, manual_mode: bool = False):
        """
        使用AI配图生成封面 - 根据用户提供的精确HTML结构
        
        HTML结构（封面区域）:
        - Hover: <div class="select-cover__btn js_cover_btn_area select-cover__mask">拖拽或选择封面</div>
        - 菜单: <div class="pop-opr__group pop-opr__group-select-cover" id="js_cover_null">
        - AI配图: <a class="pop-opr__button js_aiImage">AI 配图</a>
        
        HTML结构（AI配图对话框）:
        - 输入框: <textarea id="ai-image-prompt" class="chat_textarea">
        - 开始创作: <button class="weui-desktop-btn weui-desktop-btn_primary">开始创作</button>
        - 使用: <div class="ai-image-finetuning-btn">使用</div>
        - 确认: <button class="weui-desktop-btn weui-desktop-btn_primary">确认</button>
        
        Args:
            title: 文章标题，用于AI生成配图
            manual_mode: 是否手动模式
        """
        self.logger.info("使用AI配图生成封面...")
        self.detail_logger.step("开始AI配图生成封面")
        
        try:
            # 步骤1: hover封面区域
            self.detail_logger.step("Hover封面区域")
            self.logger.info("步骤1: hover封面区域...")
            
            cover_selector = '.select-cover__btn.js_cover_btn_area'
            cover_area = self.page.locator(cover_selector).first
            
            try:
                if not cover_area.is_visible(timeout=5000):
                    self.detail_logger.selector(cover_selector, found=False, timeout=5.0)
                    raise Exception(f"未找到封面区域({cover_selector})")
            except Exception as e:
                self.detail_logger.selector(cover_selector, found=False, timeout=5.0, error=str(e))
                raise Exception(f"封面区域不可见: {e}")
            
            self.detail_logger.selector(cover_selector, found=True, timeout=5.0)
            self.detail_logger.action("Hover", "封面区域")
            cover_area.hover()
            self._random_delay(1, 2)
            self.detail_logger.success("已hover封面区域")
            self.logger.info("已hover封面区域")
            
            # 截图查看菜单是否弹出
            try:
                self.page.screenshot(path="./data/rpa_state/ai_cover_step1_menu.png")
            except:
                pass
            
            # 步骤2: 点击AI配图按钮
            self.detail_logger.step("点击AI配图按钮")
            self.logger.info("步骤2: 点击AI配图(.js_aiImage)...")
            
            # 等待菜单弹出 - 使用JavaScript检查
            self.detail_logger.debug("等待菜单弹出...")
            menu_visible = self.page.evaluate("""
                () => {
                    const menu = document.querySelector('.pop-opr__group');
                    if (menu) {
                        const style = window.getComputedStyle(menu);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    }
                    return false;
                }
            """)
            
            if menu_visible:
                self.detail_logger.success("菜单已弹出 (display: block)")
            else:
                self.detail_logger.warning("菜单未显示，等待后再次检查...")
                self._random_delay(2, 3)
                # 再次hover确保菜单显示
                cover_area.hover()
                self._random_delay(1, 2)
            
            # 直接使用JavaScript点击AI配图按钮（最可靠）
            self.detail_logger.action("JavaScript点击", "AI配图按钮", "在菜单中查找AI配图链接")
            
            clicked = self.page.evaluate("""
                () => {
                    // 方法1: 精确选择器
                    let btn = document.querySelector('a.pop-opr__button.js_aiImage');
                    if (btn) {
                        btn.click();
                        return 'method1: a.pop-opr__button.js_aiImage';
                    }
                    
                    // 方法2: 在菜单容器内找
                    const menu = document.querySelector('.pop-opr__group');
                    if (menu) {
                        btn = menu.querySelector('a.js_aiImage');
                        if (btn) {
                            btn.click();
                            return 'method2: menu.querySelector(a.js_aiImage)';
                        }
                    }
                    
                    // 方法3: 在#js_cover_null内找
                    const coverNull = document.getElementById('js_cover_null');
                    if (coverNull) {
                        btn = coverNull.querySelector('a.js_aiImage');
                        if (btn) {
                            btn.click();
                            return 'method3: #js_cover_null a.js_aiImage';
                        }
                    }
                    
                    // 方法4: 遍历所有li找包含"AI 配图"文本的a标签
                    const allLinks = document.querySelectorAll('.pop-opr__item a');
                    for (let a of allLinks) {
                        if (a.textContent.includes('AI') && a.textContent.includes('配图')) {
                            a.click();
                            return 'method4: text match - ' + a.textContent.trim();
                        }
                    }
                    
                    // 方法5: 最后的fallback，找所有a标签
                    const links = document.querySelectorAll('a');
                    for (let a of links) {
                        const text = a.textContent.trim();
                        if (text === 'AI 配图' || text.includes('AI') && text.includes('配图')) {
                            a.click();
                            return 'method5: fallback - ' + text;
                        }
                    }
                    
                    return null;
                }
            """)
            
            if clicked:
                self.detail_logger.success(f"点击AI配图成功 ({clicked})")
                self.logger.info(f"点击AI配图成功 ({clicked})")
            else:
                self.detail_logger.error("JavaScript点击AI配图失败，尝试Playwright备用方案")
                
                # 备用：使用Playwright尝试
                try:
                    ai_btn = self.page.locator('#js_cover_null a.js_aiImage').first
                    ai_btn.wait_for(state='visible', timeout=3000)
                    ai_btn.click()
                    self.detail_logger.success("Playwright点击AI配图成功")
                except Exception as pe:
                    self.detail_logger.error(f"Playwright备用方案也失败: {pe}")
                    raise Exception("未找到AI配图按钮，所有方法均失败")
            
            self._random_delay(2, 3)
            
            # 截图查看对话框
            try:
                self.page.screenshot(path="./data/rpa_state/ai_cover_step2_dialog.png")
            except:
                pass
            
            # 步骤3: 在textarea中输入标题
            self.detail_logger.step("输入标题到AI配图")
            self.logger.info("步骤3: 输入标题到AI配图...")
            
            prompt_selector = 'textarea#ai-image-prompt'
            title_input = self.page.locator(prompt_selector).first
            
            try:
                title_input.wait_for(state='visible', timeout=5000)
                self.detail_logger.selector(prompt_selector, found=True, timeout=5.0)
                self.detail_logger.action("点击", "AI配图输入框")
                title_input.click()
                
                self.detail_logger.action("填写", "AI配图输入框", f"标题: {title[:30]}...")
                title_input.fill(title)
                
                self.detail_logger.success(f"已输入标题: {title[:30]}...")
                self.logger.info(f"已输入标题: {title[:30]}...")
            except Exception as e:
                self.detail_logger.error(f"输入标题失败", exception=e)
                raise Exception(f"输入标题失败: {e}")
            
            self._random_delay(1, 2)
            
            # 步骤4: 点击开始创作
            self.detail_logger.step("点击开始创作")
            self.logger.info("步骤4: 点击开始创作...")
            
            # 记录点击前的图片数量（避免选到旧图片）
            initial_count = self.page.evaluate("""
                () => document.querySelectorAll('.ai-image-item-wrp img').length
            """)
            self.detail_logger.info(f"点击开始创作前已有 {initial_count} 张图片")
            
            self.detail_logger.action("JavaScript点击", "开始创作按钮", "查找包含'开始创作'文本的按钮")
            start_clicked = self.page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('button.weui-desktop-btn_primary');
                    for (let btn of buttons) {
                        if (btn.textContent.includes('开始创作')) {
                            btn.click();
                            return 'clicked';
                        }
                    }
                    return null;
                }
            """)
            
            if start_clicked:
                self.detail_logger.success("点击开始创作成功")
                self.logger.info("点击开始创作成功")
            else:
                self.detail_logger.error("未找到开始创作按钮")
                raise Exception("未找到开始创作按钮")
            
            # 等待AI生成图片 - 循环检测直到图片数量增加
            self.detail_logger.step("等待AI生成新图片")
            self.logger.info("等待AI生成新图片...")
            
            max_wait_time = 60  # 最多等待60秒
            check_interval = 2   # 每2秒检查一次
            elapsed = 0
            images_found = initial_count
            
            while elapsed < max_wait_time:
                self._random_delay(check_interval, check_interval + 1)
                elapsed += check_interval
                
                # 检查当前图片数量
                result = self.page.evaluate("""
                    () => {
                        const images = document.querySelectorAll('.ai-image-item-wrp img');
                        return {
                            count: images.length,
                            lastSrc: images.length > 0 ? images[images.length - 1].src : null
                        };
                    }
                """)
                
                current_count = result.get('count', 0)
                self.detail_logger.debug(f"等待AI新图片... {elapsed}s / {max_wait_time}s, 当前 {current_count} 张 (之前 {initial_count} 张)")
                
                # 等待图片数量增加（新的图片生成）
                if current_count > initial_count:
                    images_found = current_count
                    new_images = current_count - initial_count
                    self.detail_logger.success(f"AI新图片已生成，新增 {new_images} 张，共 {current_count} 张，用时 {elapsed} 秒")
                    self.logger.info(f"AI新图片已生成，新增 {new_images} 张，共 {current_count} 张，用时 {elapsed} 秒")
                    break
            
            if images_found == initial_count:
                self.detail_logger.error(f"等待 {max_wait_time} 秒后仍未生成新图片（始终 {initial_count} 张）")
                raise Exception(f"AI图片生成超时（{max_wait_time}秒）")
            
            # 截图查看生成的图片
            try:
                self.page.screenshot(path="./data/rpa_state/ai_cover_step3_generated.png")
            except:
                pass
            
            # 步骤5: 点击最新生成的图片（最后一张）
            self.detail_logger.step("选择最新生成的图片")
            self.logger.info("步骤5: 选择最新生成的图片...")
            
            self.detail_logger.action("JavaScript点击", "最新图片", f"第 {images_found} 张图片")
            img_clicked = self.page.evaluate("""
                () => {
                    const images = document.querySelectorAll('.ai-image-item-wrp img');
                    if (images.length > 0) {
                        images[images.length - 1].click();
                        return 'clicked last of ' + images.length;
                    }
                    return null;
                }
            """)
            
            if img_clicked:
                self.detail_logger.success(f"已点击最新图片 ({img_clicked})")
                self.logger.info(f"已点击最新图片 ({img_clicked})")
            else:
                self.detail_logger.warning("点击图片失败，继续尝试点击使用按钮")
            
            self._random_delay(1, 2)
            
            # 点击使用按钮 - 循环等待直到按钮可用
            self.detail_logger.step("点击使用按钮")
            self.logger.info("点击使用按钮...")
            
            use_clicked = False
            for attempt in range(5):  # 最多尝试5次
                self.detail_logger.action("JavaScript点击", "使用按钮", f"第 {attempt + 1} 次尝试")
                
                result = self.page.evaluate("""
                    () => {
                        const buttons = document.querySelectorAll('button.weui-desktop-btn_default');
                        for (let btn of buttons) {
                            if (btn.textContent.includes('使用')) {
                                // 检查按钮是否可点击
                                if (!btn.disabled && btn.offsetParent !== null) {
                                    btn.click();
                                    return { clicked: true, text: btn.textContent.trim() };
                                } else {
                                    return { clicked: false, reason: 'button disabled or hidden' };
                                }
                            }
                        }
                        return { clicked: false, reason: 'button not found' };
                    }
                """)
                
                if result.get('clicked'):
                    self.detail_logger.success(f"点击使用成功 ({result.get('text')})")
                    self.logger.info("点击使用成功")
                    use_clicked = True
                    break
                else:
                    self.detail_logger.warning(f"使用按钮不可用: {result.get('reason')}, 等待后重试...")
                    self._random_delay(2, 3)
            
            if not use_clicked:
                self.detail_logger.error("未找到使用按钮，多次尝试失败")
                raise Exception("未找到使用按钮(button.weui-desktop-btn_default)")
            
            self._random_delay(2, 3)
            
            # 步骤6: 点击确认 - 循环等待直到按钮出现
            self.detail_logger.step("点击确认按钮")
            self.logger.info("步骤6: 点击确认...")
            
            confirm_clicked = False
            confirm_method = None
            
            for attempt in range(10):  # 最多尝试10次，等待对话框弹出
                self.detail_logger.debug(f"查找确认按钮... 第 {attempt + 1} 次尝试")
                
                result = self.page.evaluate("""
                    () => {
                        // 方法1: 精确匹配"确认"或"确定"
                        const buttons = document.querySelectorAll('button.weui-desktop-btn_primary');
                        for (let btn of buttons) {
                            const text = btn.textContent.trim();
                            if (text === '确认' || text === '确定') {
                                btn.click();
                                return { clicked: true, method: 'method1: ' + text };
                            }
                        }
                        // 方法2: 包含文本
                        for (let btn of buttons) {
                            const text = btn.textContent.trim();
                            if (text.includes('确认') || text.includes('确定')) {
                                btn.click();
                                return { clicked: true, method: 'method2: ' + text };
                            }
                        }
                        // 方法3: 最后的fallback
                        const allButtons = document.querySelectorAll('button[type="button"].weui-desktop-btn_primary');
                        if (allButtons.length > 0) {
                            allButtons[allButtons.length - 1].click();
                            return { clicked: true, method: 'method3: last button' };
                        }
                        return { clicked: false, method: null };
                    }
                """)
                
                if result.get('clicked'):
                    confirm_clicked = True
                    confirm_method = result.get('method')
                    break
                else:
                    self._random_delay(1, 2)
            
            if confirm_clicked:
                self.detail_logger.success(f"点击确认成功 ({confirm_method})")
                self.logger.info(f"点击确认成功 ({confirm_method})")
            else:
                self.detail_logger.error("未找到确认按钮，多次尝试均失败")
                # 截图调试
                try:
                    self.page.screenshot(path="./data/rpa_state/ai_cover_step6_confirm.png")
                except:
                    pass
                raise Exception("未找到确认按钮")
            
            self._random_delay(2, 3)
            self.detail_logger.success("AI配图完成")
            self.logger.info("✅ AI配图完成")
            
        except Exception as e:
            self.detail_logger.error(f"AI配图失败", exception=e)
            self.logger.error(f"AI配图失败: {e}")
            try:
                self.page.screenshot(path="./data/rpa_state/ai_cover_error.png")
            except:
                pass
            if manual_mode:
                input("请手动完成AI配图，完成后按回车继续...")
            else:
                raise
    
    def save_draft(self) -> Dict:
        """保存草稿 - 简化版，直接点击保存按钮"""
        self.logger.info("保存草稿...")
        
        try:
            # 滚动到页面底部（保存按钮在底部）
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self._random_delay(1, 2)
            
            # 点击"保存为草稿"按钮
            save_btn_selectors = [
                'text=保存为草稿',
                '#js_save_btn',
                'button:has-text("保存")',
                '.js_save_btn',
            ]
            
            save_btn = None
            for selector in save_btn_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=3000):
                        save_btn = btn
                        self.logger.info(f"找到保存按钮: {selector}")
                        break
                except:
                    continue
            
            if not save_btn:
                raise Exception("未找到保存按钮")
            
            # 直接点击（不需要类人点击，简单直接）
            save_btn.click()
            self.logger.info("已点击保存为草稿")
            
            # 等待保存成功提示
            try:
                self.page.wait_for_selector("text=保存成功", timeout=10000)
                self.logger.info("✅ 草稿保存成功")
            except:
                # 有些版本可能没有明确提示，等待2秒假设成功
                self._random_delay(2, 3)
                self.logger.info("✅ 草稿已保存（假设成功）")
            
            return {'success': True, 'status': 'saved'}
            
        except Exception as e:
            self.logger.error(f"保存草稿失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish(self, confirm: bool = False) -> Dict:
        """
        发布文章 - 完整发表流程
        
        流程:
        1. 点击发表按钮 (button.mass_send)
        2. 点击确认发表 (button.weui-desktop-btn_primary:has-text("发表"))
        3. 点击继续发表 (button.weui-desktop-btn_primary:has-text("继续发表"))
        4. 等待用户扫描二维码
        5. 等待发布成功
        
        Args:
            confirm: 是否确认发布（会有二次确认弹窗）
            
        Returns:
            发布结果
        """
        self.logger.info("发布文章...")
        self.detail_logger.step("开始发布文章")
        
        try:
            # 步骤1: 点击发表按钮
            self.detail_logger.step("点击发表按钮")
            self.logger.info("步骤1: 点击发表按钮...")
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self._random_delay(1, 2)
            
            self.detail_logger.action("JavaScript点击", "发表按钮", "button.mass_send")
            publish_clicked = self.page.evaluate("""
                () => {
                    const btn = document.querySelector('button.mass_send');
                    if (btn) {
                        btn.click();
                        return 'clicked';
                    }
                    return null;
                }
            """)
            
            if not publish_clicked:
                self.detail_logger.error("未找到发表按钮(button.mass_send)")
                raise Exception("未找到发表按钮(button.mass_send)")
            
            self.detail_logger.success("已点击发表按钮")
            self.logger.info("已点击发表按钮")
            
            self._random_delay(2, 3)
            
            # 步骤2: 点击确认发表（循环等待按钮出现）
            self.detail_logger.step("点击确认发表")
            self.logger.info("步骤2: 点击确认发表...")
            
            self.detail_logger.info("等待确认发表按钮出现...")
            confirm1_clicked = False
            for attempt in range(10):  # 最多等待10秒
                self._random_delay(0.5, 1)
                
                confirm1_clicked = self.page.evaluate("""
                    () => {
                        const buttons = document.querySelectorAll('button.weui-desktop-btn_primary');
                        for (let btn of buttons) {
                            const text = btn.textContent.trim();
                            if (text === '发表' || text === '确定' || text === '确认') {
                                btn.click();
                                return 'clicked: ' + text;
                            }
                        }
                        return null;
                    }
                """)
                
                if confirm1_clicked:
                    self.detail_logger.success(f"已点击确认发表 ({confirm1_clicked})")
                    self.logger.info("已点击确认发表")
                    break
                else:
                    self.detail_logger.debug(f"等待确认按钮... {attempt+1}/10")
            
            if not confirm1_clicked:
                self.detail_logger.error("未找到确认发表按钮")
                raise Exception("未找到确认发表按钮")
            
            self._random_delay(2, 3)
            
            # 步骤3: 点击继续发表（循环等待按钮出现）
            self.detail_logger.step("点击继续发表")
            self.logger.info("步骤3: 点击继续发表...")
            
            self.detail_logger.info("等待继续发表按钮出现...")
            confirm2_clicked = False
            for attempt in range(10):  # 最多等待10秒
                self._random_delay(0.5, 1)
                
                confirm2_clicked = self.page.evaluate("""
                    () => {
                        const buttons = document.querySelectorAll('button.weui-desktop-btn_primary');
                        for (let btn of buttons) {
                            if (btn.textContent.includes('继续发表')) {
                                btn.click();
                                return 'clicked';
                            }
                        }
                        return null;
                    }
                """)
                
                if confirm2_clicked:
                    self.detail_logger.success("已点击继续发表")
                    self.logger.info("已点击继续发表")
                    break
                else:
                    self.detail_logger.debug(f"等待继续发表按钮... {attempt+1}/10")
            
            if not confirm2_clicked:
                self.detail_logger.error("未找到继续发表按钮")
                raise Exception("未找到继续发表按钮")
            
            # 点击成功，继续下一步
            
            # 步骤4: 等待用户扫描二维码
            self.detail_logger.step("等待用户扫描二维码")
            self.logger.info("步骤4: 请扫描二维码...")
            self.logger.info("请使用手机微信扫描屏幕上的二维码")
            
            # 循环等待扫码完成 - 检测首页元素或URL跳转
            self.detail_logger.info("等待用户扫码，最多60秒...")
            self.logger.info("等待60秒扫描二维码...")
            
            qr_wait_time = 60
            qr_elapsed = 0
            qr_scanned = False
            
            while qr_elapsed < qr_wait_time:
                time.sleep(2)
                qr_elapsed += 2
                
                # 每10秒输出一次倒计时
                if qr_elapsed % 10 == 0:
                    remaining = qr_wait_time - qr_elapsed
                    self.detail_logger.info(f"等待扫码中... 还剩 {remaining} 秒")
                    self.logger.info(f"等待扫码中... 还剩 {remaining} 秒")
                
                # 检测是否已经扫码完成 - 方法1: 检测URL跳转（最稳定）
                try:
                    current_url = self.page.url
                    if "cgi-bin/home" in current_url:
                        self.detail_logger.success("扫码完成，检测到首页URL")
                        self.logger.info("扫码完成，已跳转到首页")
                        qr_scanned = True
                        break
                except Exception as url_error:
                    self.detail_logger.debug(f"检测URL时出错: {url_error}")
                    continue
                
                # 检测方法2: 首页特有元素（捕获页面导航异常）
                try:
                    on_homepage = self.page.evaluate("""
                        () => {
                            try {
                                const articleBtn = document.querySelector('.new-creation__menu-item');
                                if (articleBtn) {
                                    const title = articleBtn.querySelector('.new-creation__menu-title');
                                    if (title && title.textContent.includes('文章')) {
                                        return 'homepage_element';
                                    }
                                }
                            } catch (e) {
                                return null;
                            }
                            return null;
                        }
                    """)
                    
                    if on_homepage:
                        self.detail_logger.success(f"扫码完成，检测到首页元素 ({on_homepage})")
                        self.logger.info("扫码完成，已回到首页")
                        qr_scanned = True
                        break
                except Exception as eval_error:
                    # 页面可能正在跳转，等待后重试
                    self.detail_logger.debug(f"检测首页元素时出错（可能正在跳转）: {eval_error}")
                    time.sleep(1)
                    continue
            
            if not qr_scanned:
                self.detail_logger.warning(f"{qr_wait_time}秒倒计时结束，未检测到返回首页")
                self.logger.warning("等待扫码时间结束，未检测到返回首页")
            
            # 步骤5: 等待发布成功（检测首页元素、URL跳转或成功提示）
            self.detail_logger.step("等待发布成功")
            self.logger.info("步骤5: 等待发布完成...")
            
            try:
                # 检测发布成功
                for i in range(60):  # 最多等待60秒
                    time.sleep(1)
                    
                    # 检测方法1: URL跳转（最稳定，不会受页面导航影响）
                    try:
                        if "cgi-bin/home" in self.page.url:
                            self.detail_logger.success("检测到跳转到首页，发表成功")
                            self.logger.info("检测到跳转到首页，发表成功")
                            return {'success': True, 'status': 'published'}
                    except:
                        pass
                    
                    # 检测方法2: 首页特有元素（捕获导航异常）
                    try:
                        on_homepage = self.page.evaluate("""
                            () => {
                                try {
                                    const articleBtn = document.querySelector('.new-creation__menu-item');
                                    if (articleBtn) {
                                        const title = articleBtn.querySelector('.new-creation__menu-title');
                                        if (title && title.textContent.includes('文章')) {
                                            return 'homepage';
                                        }
                                    }
                                } catch (e) {
                                    return null;
                                }
                                return null;
                            }
                        """)
                        
                        if on_homepage:
                            self.detail_logger.success("检测到首页元素，发表成功")
                            self.logger.info("检测到首页元素，发表成功")
                            return {'success': True, 'status': 'published'}
                    except Exception as eval_error:
                        # 页面可能正在跳转，跳过本次检测
                        self.detail_logger.debug(f"检测首页元素时出错（可能正在跳转）: {eval_error}")
                        continue
                    
                    # 检测方法3: 成功提示文字
                    try:
                        page_text = self.page.content()
                        if '群发成功' in page_text or '发表成功' in page_text or '发布成功' in page_text:
                            self.detail_logger.success("检测到成功提示")
                            self.logger.info("检测到成功提示")
                            return {'success': True, 'status': 'published'}
                    except:
                        pass
                
                self.detail_logger.warning("未检测到明确的成功提示，但流程已完成")
                self.logger.warning("未检测到明确的成功提示，但流程已完成")
                return {'success': True, 'status': 'unknown'}
                
            except Exception as e:
                self.detail_logger.error(f"等待成功提示时出错", exception=e)
                self.logger.warning(f"等待成功提示时出错: {e}")
                # 最后检查是否在首页（捕获导航异常）
                try:
                    on_homepage = self.page.evaluate("""
                        () => {
                            try {
                                return document.querySelector('.new-creation__menu-item') !== null;
                            } catch (e) {
                                return false;
                            }
                        }
                    """)
                    if on_homepage or "cgi-bin/home" in self.page.url:
                        return {'success': True, 'status': 'published'}
                except:
                    pass
                return {'success': False, 'error': str(e)}
            
        except Exception as e:
            self.detail_logger.error(f"发布失败", exception=e)
            self.logger.error(f"发布失败: {e}")
            try:
                self.page.screenshot(path="./data/rpa_state/publish_error.png")
            except:
                pass
            return {'success': False, 'error': str(e)}
    
    def preview(self, wechat_id: str) -> bool:
        """
        发送预览到指定微信号
        
        Args:
            wechat_id: 接收预览的微信号
            
        Returns:
            是否成功
        """
        self.logger.info(f"发送预览给: {wechat_id}")
        
        try:
            # 点击预览按钮
            preview_btn = self.page.locator("#js_preview_btn")
            preview_btn.click()
            
            time.sleep(1)
            
            # 填写微信号
            input_box = self.page.locator(".js_preview_wx_input")
            input_box.fill(wechat_id)
            
            # 发送
            send_btn = self.page.locator("text=发送").first
            send_btn.click()
            
            self.logger.info("预览已发送")
            return True
            
        except Exception as e:
            self.logger.error(f"预览发送失败: {e}")
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'p'):
            self.p.stop()
        
        self.logger.info("浏览器已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def publish_article(article: Dict, headless: bool = False) -> Dict:
    """
    便捷发布函数
    
    示例:
        result = publish_article({
            'title': '文章标题',
            'content': '正文内容...',
            'author': '小编',
            'cover_image': '/path/to/image.jpg'
        })
    """
    rpa = WeChatRPA({'headless': headless})
    
    try:
        # 登录
        if not rpa.login():
            return {'success': False, 'error': '登录失败'}
        
        # 创建文章
        result = rpa.create_article(article)
        
        if result['success']:
            # 保存草稿
            rpa.save_draft()
        
        return result
        
    finally:
        rpa.close()
