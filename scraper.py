import os
import re
import time
import requests
from bs4 import BeautifulSoup
from ebooklib import epub

# 目标网站的基础 URL 和起始页面
BASE_URL = "https://chentianyuzhou.com"
START_URL = "https://chentianyuzhou.com/category/%e7%b2%be%e9%80%89%e9%95%bf%e6%96%87/"

# 设置请求头，模拟浏览器访问
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
}

def get_article_urls(page_url):
    """获取单个页面上所有文章的链接"""
    urls = []
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_links = soup.select('h2.entry-title a')
        for link in article_links:
            urls.append(link['href'])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article list from {page_url}: {e}")
    return urls

def get_all_urls():
    """获取'精选长文'分类下所有页面的所有文章链接"""
    all_urls = []
    current_url = START_URL
    page_num = 1
    
    while current_url:
        print(f"Scraping page {page_num}: {current_url}")
        time.sleep(2) 
        
        try:
            response = requests.get(current_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            page_urls = get_article_urls(current_url)
            if not page_urls:
                print("No articles found on this page, stopping.")
                break
            
            all_urls.extend(page_urls)
            
            next_page_link = soup.select_one('a.next.page-numbers')
            if next_page_link and next_page_link.has_attr('href'):
                current_url = next_page_link['href']
                page_num += 1
            else:
                print("No more pages found. Reached the last page.")
                current_url = None
                
        except requests.exceptions.RequestException as e:
            print(f"Error on page {page_num}: {e}")
            break
            
    return list(reversed(all_urls))

def get_article_content(article_url):
    """获取单篇文章的标题和正文内容 (使用更精细的提取逻辑)"""
    print(f"Fetching article: {article_url}")
    try:
        response = requests.get(article_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        title_tag = soup.select_one('h1.entry-title')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        content_div = soup.select_one('div.entry-content')
        
        if not content_div:
            print(f"Warning: Could not find content div for article: {title}")
            return title, "<p>未能抓取到正文内容。</p>"

        # 移除不需要的元素
        for element_to_remove in content_div.select('script, style, .sharedaddy, .jp-relatedposts, .wp-block-spacer, .wp-block-embed, .wp-block-buttons'):
            element_to_remove.decompose()
        
        # 过滤掉视频文章
        if content_div.find('iframe'):
             print(f"Skipping video article: {title}")
             return None, None
        
        # 精细化提取内容：只选择我们需要的标签
        # 这可以确保只保留文章段落、标题、列表、图片等核心内容
        content_tags = content_div.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol', 'li', 'figure', 'pre'])
        
        if not content_tags:
            print(f"Warning: Content div for '{title}' was found but no content tags (p, h2, etc.) were inside.")
            return title, "<p>未能抓取到正文内容。</p>"
        
        # 将所有找到的标签拼接成最终的 HTML 内容
        content_html = ''.join(str(tag) for tag in content_tags)
        
        return title, content_html

    except requests.exceptions.RequestException as e:
        print(f"Error fetching article content from {article_url}: {e}")
        return "Fetch Error", f"<p>抓取文章时出错: {e}</p>"

def create_epub(articles):
    """根据文章内容创建EPUB文件"""
    book = epub.EpubBook()
    
    book.set_identifier('id123456')
    book.set_title('精选长文 - chentianyuzhou.com')
    book.set_language('zh')
    book.add_author('chentianyuzhou.com')

    chapters = []
    for i, article in enumerate(articles):
        title = article['title']
        content_html = article['content']
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        file_name = f'chap_{i+1}_{safe_title[:50]}.xhtml' # 限制文件名长度
        
        chapter = epub.EpubHtml(title=title, file_name=file_name, lang='zh')
        chapter.content = f'<h1>{title}</h1>{content_html}'
        book.add_item(chapter)
        chapters.append(chapter)
        print(f"Added to EPUB: {title}")

    book.toc = [(epub.Link(c.file_name, c.title, f'chap_{i}'), ()) for i, c in enumerate(chapters)]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters
    epub.write_epub('Selected_Articles.epub', book, {})
    print(f"\nEPUB file 'Selected_Articles.epub' created with {len(articles)} articles.")

def create_placeholder_epub():
    """当未找到文章时，创建一个占位符EPUB"""
    book = epub.EpubBook()
    book.set_identifier('placeholder_id')
    book.set_title('精选长文 - 未找到文章')
    book.set_language('zh')
    book.add_author('Scraper Bot')
    chapter = epub.EpubHtml(title='执行报告', file_name='report.xhtml', lang='zh')

