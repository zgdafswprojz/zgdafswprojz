from http.server import BaseHTTPRequestHandler
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        try:
            # 从查询参数中获取URL
            query_params = self.parse_query()
            target_url = query_params.get('url', '').strip()

            if not target_url:
                raise ValueError("请提供URL参数")

            # 验证URL格式
            if not target_url.startswith(('http://', 'https://')):
                target_url = 'https://' + target_url

            # 发送请求
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(target_url, headers=headers, timeout=15)
            response.raise_for_status()

            # 解析内容
            soup = BeautifulSoup(response.text, 'lxml')

            data = {
                "status": "success",
                "url": target_url,
                "title": self.get_title(soup),
                "description": self.get_description(soup),
                "images": self.get_images(soup, target_url),
                "links": self.get_links(soup, target_url),
                "text_content": self.get_text_content(soup),
                "metadata": {
                    "status_code": response.status_code,
                    "content_type": response.headers.get('content-type', ''),
                    "encoding": response.encoding
                }
            }

        except Exception as e:
            data = {
                "status": "error",
                "message": f"爬取失败: {str(e)}",
                "url": target_url if 'target_url' in locals() else ''
            }

        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def parse_query(self):
        """解析查询参数"""
        query_params = {}
        if '?' in self.path:
            query_string = self.path.split('?', 1)[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value
        return query_params

    def get_title(self, soup):
        """获取页面标题"""
        title = soup.find('title')
        return title.text.strip() if title else "无标题"

    def get_description(self, soup):
        """获取页面描述"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()[:200]
        return "无描述"

    def get_images(self, soup, base_url):
        """获取图片列表"""
        images = []
        for img in soup.find_all('img', src=True)[:10]:  # 只取前10张
            src = img['src']
            # 处理相对路径
            if not src.startswith(('http://', 'https://')):
                src = urljoin(base_url, src)
            images.append({
                "src": src,
                "alt": img.get('alt', '')[:50]
            })
        return images

    def get_links(self, soup, base_url):
        """获取链接列表"""
        links = []
        for a in soup.find_all('a', href=True)[:15]:  # 只取前15个
            href = a['href']
            text = a.text.strip()
            # 过滤空链接和javascript链接
            if href and not href.startswith(('javascript:', 'mailto:', 'tel:')):
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(base_url, href)
                if text:  # 只添加有文本的链接
                    links.append({
                        "text": text[:50],
                        "url": href
                    })
        return links

    def get_text_content(self, soup):
        """获取主要文本内容"""
        # 移除脚本和样式
        for script in soup(["script", "style"]):
            script.decompose()

        # 获取文本并清理
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text[:500] + "..." if len(text) > 500 else text  # 限制长度