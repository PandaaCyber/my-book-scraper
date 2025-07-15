import os
import re
import time
import requests
import traceback
from bs4 import BeautifulSoup
from ebooklib import epub

# 目标网站的基础 URL 和起始页面
BASE_URL = "https://chentianyuzhou.com"
START_URL = "https://chentianyuzhou.com/category/%e7%b2%be%e9%80%89%e9%95%bf%e6%96%87/"

# 设置请求头，模拟浏览器访问
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
}

def get_article_urls(page_url):
    """获取单个页面上所有文章的链接"""
    urls = []
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_links = soup.select('h2.entry-title a')
        for link in article_links:
            urls.append(link['href'])
    except requests.exceptions.RequestException as e:
        print(f"    - Error fetching article list from {page_url}: {e}", flush=True)
    return urls

def get_all_urls():
    """获取'精选长文'分类下所有页面的所有文章链接"""
    all_urls = []
    current_url = START_URL
    page_num = 1
    
    while current_url:
        print(f"  - Scraping page {page_num}: {current_url}", flush=True)
        time.sleep(3) # 增加延迟，表现得更像人类
        
        try:
            page_urls = get_article_urls(current_url)
            if not page_urls:
                print("    - No articles found on this page, stopping.", flush=True)
                break
            
            all_urls.extend(page_urls)
            
            # 重新请求页面以查找下一页链接，以防万一
            response = requests.get(current_url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            next_page_link = soup.select_one('a.next.page-numbers')

            if next_page_link and next_page_link.has_attr('href'):
                current_url = next_page_link['href']
                page_num += 1
            else:
                print("    - No more pages found. Reached the last page.", flush=True)
                current_url = None
                
        except requests.exceptions.RequestException as e:
            print(f"    - Error on page {page_num}, stopping crawl: {e}", flush=True)
            break
            
    return list(reversed(all_urls))

def get_article_content(article_url):
    """获取单篇文章的标题和正文内容"""
    try:
        response = requests.get(article_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        title_tag = soup.select_one('h1.entry-title')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        content_div = soup.select_one('div.entry-content')
        
        if not content_div:
            return title, "<p>未能抓取到正文内容。</p>"

        for element_to_remove in content_div.select('script, style, .sharedaddy, .jp-relatedposts, .wp-block-spacer, .wp-block-embed, .wp-block-buttons'):
            element_to_remove.decompose()
        
        if content_div.find('iframe'):
             return None, None
        
        content_tags = content_div.find_all(['p', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol', 'li', 'figure', 'pre'])
        
        if not content_tags:
            return title, "<p>未能抓取到正文内容。</p>"
        
        content_html = ''.join(str(tag) for tag in content_tags)
        return title, content_html

    except requests.exceptions.RequestException as e:
        print(f"    - Error fetching content for {article_url}: {e}", flush=True)
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
        file_name = f'chap_{i+1}_{safe_title[:50]}.xhtml'
        
        chapter = epub.EpubHtml(title=title, file_name=file_name, lang='zh')
        chapter.content = f'<h1>{title}</h1>{content_html}'
        book.add_item(chapter)
        chapters.append(chapter)

    book.toc = [(epub.Link(c.file_name, c.title, f'chap_{i}'), ()) for i, c in enumerate(chapters)]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters
    epub.write_epub('Selected_Articles.epub', book, {})
    print(f"--- EPUB file created with {len(articles)} articles.", flush=True)

def create_placeholder_epub(error_report=None):
    """当未找到文章或发生错误时，创建一个占位符EPUB"""
    book = epub.EpubBook()
    book.set_identifier('placeholder_id')
    book.set_language('zh')
    book.add_author('Scraper Bot')

    if error_report:
        book.set_title('爬虫发生错误 - Error Report')
        chapter_title = '错误报告'
        chapter_content = f"<h1>执行时发生错误</h1><p>爬虫在运行时遇到意外错误，未能完成任务。</p><h2>错误详情:</h2><pre>{error_report}</pre>"
    else:
        book.set_title('精选长文 - 未找到文章')
        chapter_title = '执行报告'
        chapter_content = "<h1>未找到新文章</h1><p>本次运行未能抓取到任何有效的非视频文章。</p>"
        
    chapter = epub.EpubHtml(title=chapter_title, file_name='report.xhtml', lang='zh')
    chapter.content = chapter_content
    book.add_item(chapter)
    book.toc = (epub.Link('report.xhtml', chapter_title, 'report'),)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', chapter]
    epub.write_epub('Selected_Articles.epub', book, {})
    print("--- Placeholder/Error EPUB created.", flush=True)


if __name__ == '__main__':
    print("--- SCRAPER SCRIPT STARTED ---", flush=True)
    try:
        print("Step 1: Getting all article URLs...", flush=True)
        all_article_urls = get_all_urls()
        print(f"Step 1 finished. Found {len(all_article_urls)} total URLs.", flush=True)
        
        articles_data = []
        if all_article_urls:
            print(f"Step 2: Fetching content for {len(all_article_urls)} articles...", flush=True)
            for i, url in enumerate(all_article_urls):
                print(f"  - Processing article {i+1}/{len(all_article_urls)}: {url}", flush=True)
                title, content = get_article_content(url)
                if title and content and "未能抓取到" not in content and "Fetch Error" not in title:
                    articles_data.append({'title': title, 'content': content})
            print("Step 2 finished.", flush=True)

        print("Step 3: Preparing to create EPUB file...", flush=True)
        if articles_data:
            print(f"Creating main EPUB with {len(articles_data)} articles.", flush=True)
            create_epub(articles_data)
        else:
            print("No valid articles found. Creating placeholder EPUB.", flush=True)
            create_placeholder_epub()
        
        print("--- SCRIPT FINISHED SUCCESSFULLY ---", flush=True)

    except Exception as e:
        print("--- AN UNEXPECTED ERROR OCCURRED ---", flush=True)
        error_details = traceback.format_exc()
        print(error_details, flush=True)
        print("\nAttempting to create a placeholder EPUB with the error report...", flush=True)
        create_placeholder_epub(error_report=error_details)
