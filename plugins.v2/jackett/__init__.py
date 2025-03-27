from typing import Dict, Any, List, Optional, Tuple
from app.plugins import _PluginBase
from app.utils.http import RequestUtils
import json
import os
import time

class Jackett(_PluginBase):
    """
    Jackett 搜索器插件
    """
    # 插件名称
    plugin_name = "Jackett"
    # 插件描述
    plugin_desc = "支持 Jackett 搜索器，将Jackett索引器添加到内建搜索器中。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/Jackett/Jackett/master/src/Jackett.Common/Content/favicon.ico"
    # 插件版本
    plugin_version = "1.06"
    # 插件作者
    plugin_author = "jason"
    # 作者主页
    author_url = "https://github.com/xj-bear"
    # 插件配置项ID前缀
    plugin_config_prefix = "jackett_"
    # 加载顺序
    plugin_order = 21
    # 可使用的用户级别
    user_level = 2

    # 私有属性
    _enabled = False
    _host = None
    _api_key = None
    _password = None
    _indexers = None
    _added_indexers = []

    def init_plugin(self, config: dict = None) -> None:
        """
        插件初始化
        """
        print(f"【{self.plugin_name}】正在初始化插件...")
        if not config:
            print(f"【{self.plugin_name}】配置为空")
            return

        # 读取配置
        self._enabled = config.get("enabled", False)
        self._host = config.get("host")
        self._api_key = config.get("api_key")
        self._password = config.get("password")
        self._indexers = config.get("indexers", [])
        
        print(f"【{self.plugin_name}】插件初始化完成，状态: {self._enabled}")
        
        # 如果插件已启用且配置了API信息，则添加索引器
        if self._enabled and self._host and self._api_key:
            print(f"【{self.plugin_name}】尝试添加Jackett索引器...")
            self._add_jackett_indexers()

    def _add_jackett_indexers(self):
        """
        添加Jackett索引器到MoviePilot内建索引器
        """
        try:
            # 先清理之前添加的索引器
            self._remove_jackett_indexers()
            
            # 导入SitesHelper
            try:
                from app.helper.sites import SitesHelper
                print(f"【{self.plugin_name}】成功导入SitesHelper")
            except Exception as e:
                print(f"【{self.plugin_name}】导入SitesHelper失败: {str(e)}")
                return
            
            # 获取Jackett索引器列表
            indexers = self._fetch_jackett_indexers()
            if not indexers:
                print(f"【{self.plugin_name}】未获取到Jackett索引器")
                return
            
            print(f"【{self.plugin_name}】获取到{len(indexers)}个Jackett索引器")
            
            # 添加索引器到MoviePilot
            sites_helper = SitesHelper()
            
            # 先获取已有的索引器
            existing_indexers = sites_helper.get_indexers()
            
            for indexer in indexers:
                indexer_id = indexer.get("id")
                if not indexer_id:
                    continue
                    
                if self._indexers and indexer_id not in self._indexers:
                    print(f"【{self.plugin_name}】跳过未选择的索引器: {indexer.get('name')}")
                    continue
                
                domain = f"jackett_{indexer_id}"
                
                # 检查是否已存在
                if domain in existing_indexers:
                    print(f"【{self.plugin_name}】索引器已存在，跳过添加: {indexer.get('name')}")
                    self._added_indexers.append(domain)
                    continue
                    
                # 格式化为MoviePilot支持的格式
                mp_indexer = self._format_indexer(indexer)
                if not mp_indexer:
                    continue
                    
                # 添加到MoviePilot
                try:
                    sites_helper.add_indexer(domain=domain, indexer=mp_indexer)
                    self._added_indexers.append(domain)
                    print(f"【{self.plugin_name}】成功添加索引器: {indexer.get('name')} -> {domain}")
                except Exception as e:
                    print(f"【{self.plugin_name}】添加索引器失败: {indexer.get('name')} - {str(e)}")
            
            print(f"【{self.plugin_name}】共添加了{len(self._added_indexers)}个索引器")
            
        except Exception as e:
            print(f"【{self.plugin_name}】添加Jackett索引器异常: {str(e)}")
    
    def _remove_jackett_indexers(self):
        """
        移除之前添加的Jackett索引器
        """
        try:
            from app.helper.sites import SitesHelper
            sites_helper = SitesHelper()
            
            for domain in self._added_indexers:
                try:
                    sites_helper.remove_indexer(domain)
                    print(f"【{self.plugin_name}】移除索引器: {domain}")
                except:
                    pass
            
            self._added_indexers = []
        except Exception as e:
            print(f"【{self.plugin_name}】移除Jackett索引器异常: {str(e)}")
    
    def _fetch_jackett_indexers(self):
        """
        获取Jackett索引器列表
        """
        try:
            # 获取Cookie
            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
                "X-Api-Key": self._api_key,
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
            
            # 先尝试不使用密码连接
            indexer_query_url = f"{self._host}/api/v2.0/indexers?configured=true"
            print(f"【{self.plugin_name}】请求索引器: {indexer_query_url}")
            
            # 直接使用RequestUtils，不调用get_session
            response = RequestUtils(headers=headers).get_res(indexer_query_url)
            
            # 如果失败且有密码，尝试先获取cookie
            if (not response or response.status_code != 200) and self._password:
                print(f"【{self.plugin_name}】直接请求失败，尝试使用密码登录...")
                # 这里使用另一种方式获取cookie
                login_url = f"{self._host}/UI/Dashboard"
                login_data = {"password": self._password}
                auth_response = RequestUtils(headers=headers).post_res(url=login_url, data=login_data)
                
                if auth_response and auth_response.cookies:
                    cookies = auth_response.cookies.get_dict()
                    print(f"【{self.plugin_name}】获取到Cookie: {cookies}")
                    # 使用获取到的cookies再次请求
                    response = RequestUtils(headers=headers, cookies=cookies).get_res(indexer_query_url)
            
            if not response:
                print(f"【{self.plugin_name}】无法连接到Jackett服务器")
                return []
            
            if response.status_code != 200:
                print(f"【{self.plugin_name}】获取索引器失败: HTTP {response.status_code}")
                return []
            
            indexers = response.json()
            print(f"【{self.plugin_name}】成功获取到{len(indexers)}个索引器")
            return indexers
        except Exception as e:
            print(f"【{self.plugin_name}】获取Jackett索引器异常: {str(e)}")
            return []
    
    def _format_indexer(self, jackett_indexer):
        """
        将Jackett索引器格式化为MoviePilot索引器格式
        """
        try:
            indexer_id = jackett_indexer.get("id")
            indexer_name = jackett_indexer.get("name")
            indexer_type = jackett_indexer.get("type")
            
            # 使用原始路径作为domain，确保API请求能正确路由
            full_api_url = f"{self._host}/api/v2.0/indexers/{indexer_id}"
            
            # 基本配置
            mp_indexer = {
                "id": f"jackett_{indexer_id}",
                "name": f"[Jackett] {indexer_name}",
                "domain": full_api_url,
                "encoding": "UTF-8",
                "public": indexer_type == "public",
                "proxy": False,  # 设为False，因为Jackett已经是代理
                "result_num": 100,
                "timeout": 30,
                "level": 2
            }
            
            # 搜索配置
            mp_indexer["search"] = {
                "paths": [
                    {
                        "path": "/results/torznab/api",
                        "method": "get"
                    }
                ],
                "params": {
                    "apikey": self._api_key,
                    "t": "search",
                    "q": "{keyword}"
                }
            }
            
            # 种子解析配置 - 更加符合Jackett的XML格式
            mp_indexer["torrents"] = {
                "list": {
                    "selector": "item"
                },
                "fields": {
                    "id": {
                        "selector": "guid"
                    },
                    "title": {
                        "selector": "title"
                    },
                    "details": {
                        "selector": "comments"
                    },
                    "download": {
                        "selector": "link"
                    },
                    "size": {
                        "selector": "size"
                    },
                    "date_added": {
                        "selector": "pubDate"
                    },
                    "seeders": {
                        "selector": "seeders"
                    },
                    "leechers": {
                        "selector": "peers"
                    },
                    "grabs": {
                        "selector": "grabs"
                    },
                    "categories": {
                        "selector": "category",
                        "multiple": True
                    },
                    "downloadvolumefactor": {
                        "case": {
                            "*": 1
                        }
                    },
                    "uploadvolumefactor": {
                        "case": {
                            "*": 1
                        }
                    }
                }
            }
            
            print(f"【{self.plugin_name}】已格式化索引器: {indexer_name}")
            return mp_indexer
        except Exception as e:
            print(f"【{self.plugin_name}】格式化索引器失败: {str(e)}")
            return None
            

    def get_form(self) -> Tuple[List[dict], dict]:
        """
        获取配置表单
        """
        print(f"【{self.plugin_name}】正在加载配置表单...")
        
        # 简化表单结构
        return [
            {
                'component': 'VSwitch',
                'props': {
                    'model': 'enabled',
                    'label': '启用插件'
                }
            },
            {
                'component': 'VTextField',
                'props': {
                    'model': 'host',
                    'label': 'Jackett地址',
                    'placeholder': 'http://localhost:9117',
                    'hint': '请输入Jackett的完整地址，包括http或https前缀'
                }
            },
            {
                'component': 'VTextField',
                'props': {
                    'model': 'api_key',
                    'label': 'API Key',
                    'type': 'password',
                    'placeholder': 'Jackett管理界面右上角的API Key'
                }
            },
            {
                'component': 'VTextField',
                'props': {
                    'model': 'password',
                    'label': '管理密码',
                    'type': 'password',
                    'placeholder': 'Jackett管理界面配置的Admin password，如未配置可为空'
                }
            },
            {
                'component': 'VSelect',
                'props': {
                    'model': 'indexers',
                    'label': '索引器',
                    'multiple': True,
                    'chips': True,
                    'items': [],
                    'hint': '留空则使用全部索引器'
                },
                'events': [
                    {
                        'name': 'mounted',
                        'value': 'this.get_indexers'
                    }
                ]
            }
        ], {
            "enabled": False,
            "host": "",
            "api_key": "",
            "password": "",
            "indexers": []
        }

    def get_page(self) -> List[dict]:
        """
        获取页面
        """
        print(f"【{self.plugin_name}】正在加载插件页面...")
        return [
            {
                'component': 'VAlert',
                'props': {
                    'type': 'info',
                    'text': '此插件用于对接Jackett搜索器，将Jackett中配置的索引器添加到MoviePilot的内建索引中。需要先在Jackett中添加并配置好索引器，启用插件并保存配置后，即可在搜索中使用这些索引器。',
                    'class': 'mb-4'
                }
            },
            {
                'component': 'VBtn',
                'props': {
                    'color': 'primary',
                    'block': True,
                    'class': 'mb-4'
                },
                'text': '刷新索引器列表',
                'events': [
                    {
                        'name': 'click',
                        'value': 'this.get_indexers()'
                    }
                ]
            },
            {
                'component': 'VCard',
                'props': {
                    'class': 'mb-4'
                },
                'content': [
                    {
                        'component': 'VCardTitle',
                        'props': {
                            'class': 'primary--text'
                        },
                        'text': '索引器列表'
                    },
                    {
                        'component': 'VDataTable',
                        'props': {
                            'headers': [
                                {'text': 'ID', 'value': 'id'},
                                {'text': '索引器名称', 'value': 'name'},
                                {'text': '类型', 'value': 'type'}
                            ],
                            'items': [],
                            'loading': False,
                            'loadingText': '加载中...',
                            'noDataText': '暂无索引器',
                            'itemsPerPage': 10,
                            'class': 'indexer-table'
                        },
                        'events': [
                            {
                                'name': 'mounted',
                                'value': 'this.get_indexers().then(res => { if(res.code === 0) { this.items = res.data.map(item => ({ id: item.value, name: item.text, type: "Jackett" })); } })'
                            }
                        ]
                    }
                ]
            }
        ]

    def get_api(self) -> List[dict]:
        """
        获取API接口
        """
        print(f"【{self.plugin_name}】正在加载API接口...")
        return [
            {
                "path": "/jackett/indexers",
                "endpoint": self.get_indexers,
                "methods": ["GET"],
                "summary": "获取Jackett索引器列表",
                "description": "获取已配置的Jackett索引器列表"
            }
        ]

    def get_indexers(self):
        """
        获取索引器列表
        """
        print(f"【{self.plugin_name}】正在获取索引器列表...")
        if not self._host or not self._api_key:
            return {"code": 1, "message": "请先配置Jackett地址和API Key"}
        
        try:
            indexers = self._fetch_jackett_indexers()
            if not indexers:
                return {"code": 1, "message": "未获取到Jackett索引器"}
            
            formatted_indexers = []
            for indexer in indexers:
                formatted_indexers.append({
                    "value": indexer.get("id"),
                    "text": indexer.get("name")
                })
            
            return {"code": 0, "data": formatted_indexers}
        except Exception as e:
            return {"code": 1, "message": f"获取索引器异常: {str(e)}"}

    def get_state(self) -> bool:
        """
        获取插件状态
        """
        # 确保返回明确的布尔值
        state = bool(self._enabled and self._host and self._api_key)
        print(f"【{self.plugin_name}】get_state返回: {state}, enabled={self._enabled}, host={bool(self._host)}, api_key={bool(self._api_key)}")
        return state

    def stop_service(self) -> None:
        """
        停止插件服务
        """
        print(f"【{self.plugin_name}】停止插件服务...")
        self._remove_jackett_indexers()

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册定时服务
        """
        return [{
            "id": "jackett_update_indexers",
            "name": "更新Jackett索引器",
            "trigger": "interval",
            "func": self._add_jackett_indexers,
            "kwargs": {"hours": 12}
        }] 