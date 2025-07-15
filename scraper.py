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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_article_urls(page_url):
    """获取单个页面上所有文章的链接"""
    urls = []
    try:
        response = requests.get(page_url, headers=HEADERS)
        response.raise_for_status()  # 如果请求失败则抛出异常
        soup = BeautifulSoup(response.content, 'html.parser')

        # 查找所有文章的链接
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
        # 增加抓取间隔，避免对服务器造成太大压力
        time.sleep(2) 

        try:
            response = requests.get(current_url, headers=HEADERS)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 获取当前页的文章链接
            page_urls = get_article_urls(current_url)
            if not page_urls:
                print("No articles found on this page, stopping.")
                break

            all_urls.extend(page_urls)

            # 查找'下一页'按钮的链接
            next_page_link = soup.select_one('a.next.page-numbers')
            if next_page_link and next_page_link.has_attr('href'):
                current_url = next_page_link['href']
                page_num += 1
            else:
                print("No more pages found. Reached the last page.")
                current_url = None # 到达最后一页，结束循环

        except requests.exceptions.RequestException as e:
            print(f"Error on page {page_num}: {e}")
            break

    # 网站文章是按时间倒序排列的，为了阅读顺序，我们将链接反转
    return list(reversed(all_urls))

def get_article_content(article_url):
    """获取单篇文章的标题和正文内容"""
    print(f"Fetching article: {article_url}")
    try:
        response = requests.get(article_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 提取文章标题
        title_tag = soup.select_one('h1.entry-title')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        # 提取文章内容
        content_div = soup.select_one('div.entry-content')

        # 移除内容中的非文章部分，如脚本、样式、分享按钮等
        if content_div:
            for element_to_remove in content_div.select('script, style, .sharedaddy, .jp-relatedposts'):
                element_to_remove.decompose()

        # 过滤掉视频内容(iframe)
        if content_div and content_div.find('iframe'):
             print(f"Skipping video article: {title}")
             return None, None

        # 获取纯文本和基本格式
        content_html = str(content_div) if content_div else ""

        return title, content_html
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article content from {article_url}: {e}")
        return None, None

def create_epub(articles):
    """根据文章内容创建EPUB文件"""
    book = epub.EpubBook()

    # 设置电子书的元数据
    book.set_identifier('id123456')
    book.set_title('精选长文 - chentianyuzhou.com')
    book.set_language('zh')
    book.add_author('chentianyuzhou.com')

    chapters = []
    table_of_contents = []

    # 创建EPUB章节
    for i, article in enumerate(articles):
        title = article['title']
        content_html = article['content']

        # 清理文件名中不允许的字符
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        file_name = f'chap_{i+1}_{safe_title}.xhtml'

        # 创建章节对象
        chapter = epub.EpubHtml(title=title, file_name=file_name, lang='zh')
        chapter.content = f'<h1>{title}</h1>{content_html}'
        book.add_item(chapter)
        chapters.append(chapter)
        table_of_contents.append(epub.Link(file_name, title, f'chap_{i+1}'))
        print(f"Added to EPUB: {title}")

    # 设置电子书的目录
    book.toc = tuple(table_of_contents)

    # 添加导航文件
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 定义书籍的阅读顺序
    book.spine = ['nav'] + chapters

    # 保存EPUB文件
    epub.write_epub('Selected_Articles.epub', book, {})
    print("\nEPUB file 'Selected_Articles.epub' created successfully!")


if __name__ == '__main__':
    # 1. 获取所有文章链接
    all_article_urls = get_all_urls()

    if not all_article_urls:
        print("No article URLs found. Exiting.")
    else:
        print(f"\nFound {len(all_article_urls)} articles in total. Fetching content...")

        # 2. 爬取每篇文章的内容
        articles_data = []
        for url in all_article_urls:
            # 抓取间隔
            time.sleep(3) 
            title, content = get_article_content(url)
            if title and content:
                articles_data.append({'title': title, 'content': content})

        # 3. 创建EPUB
        if articles_data:
            create_epub(articles_data)
        else:
            print("No valid articles to create an EPUB.")
