from http.server import BaseHTTPRequestHandler
import json
import requests
from bs4 import BeautifulSoup


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        try:
            target_url = "https://alist.crystelf.top"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(target_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            data = {
                "title": self.get_title(soup),
                "articles": self.get_articles(soup),
                "status": "success",
                "url": target_url
            }

        except Exception as e:
            data = {
                "status": "error",
                "message": f"爬取失败: {str(e)}"
            }

        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def get_title(self, soup):
        title_tag = soup.find('title')
        return title_tag.text.strip() if title_tag else "未找到标题"

    def get_articles(self, soup):
        articles = []
        article_elements = soup.select('h1, h2, h3, a')[:10]  # 简单的选择器

        for elem in article_elements:
            try:
                title = elem.text.strip()[:50]  # 只取前50个字
                if title:  # 只添加非空标题
                    articles.append({"title": title})
            except:
                continue

        return articles