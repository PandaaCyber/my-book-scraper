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
            response = requests.get(current_url, headers=HEADERS)
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
    """获取单篇文章的标题和正文内容"""
    print(f"Fetching article: {article_url}")
    try:
        response = requests.get(article_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        title_tag = soup.select_one('h1.entry-title')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        content_div = soup.select_one('div.entry-content')
        
        if content_div:
            for element_to_remove in content_div.select('script, style, .sharedaddy, .jp-relatedposts'):
                element_to_remove.decompose()
        
        if content_div and content_div.find('iframe'):
             print(f"Skipping video article: {title}")
             return None, None
        
        content_html = str(content_div) if content_div else ""
        
        return title, content_html
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article content from {article_url}: {e}")
        return None, None

def create_epub(articles):
    """根据文章内容创建EPUB文件"""
    book = epub.EpubBook()
    
    book.set_identifier('id123456')
    book.set_title('精选长文 - chentianyuzhou.com')
    book.set_language('zh')
    book.add_author('chentianyuzhou.com')

    chapters = []
    table_of_contents = []

    for i, article in enumerate(articles):
        title = article['title']
        content_html = article['content']
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        file_name = f'chap_{i+1}_{safe_title}.xhtml'
        
        chapter = epub.EpubHtml(title=title, file_name=file_name, lang='zh')
        chapter.content = f'<h1>{title}</h1>{content_html}'
        book.add_item(chapter)
        chapters.append(chapter)
        table_of_contents.append(epub.Link(file_name, title, f'chap_{i+1}'))
        print(f"Added to EPUB: {title}")

    book.toc = tuple(table_of_contents)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters
    epub.write_epub('Selected_Articles.epub', book, {})
    print("\nEPUB file 'Selected_Articles.epub' created successfully!")

def create_placeholder_epub():
    """当未找到文章时，创建一个占位符EPUB"""
    book = epub.EpubBook()
    book.set_identifier('placeholder_id')
    book.set_title('精选长文 - 未找到文章')
    book.set_language('zh')
    book.add_author('Scraper Bot')

    chapter = epub.EpubHtml(title='执行报告', file_name='report.xhtml', lang='zh')
    chapter.content = """
    <h1>未找到新文章</h1>
    <p>本次运行未能抓取到任何有效的非视频文章。</p>
    <p>可能的原因包括：</p>
    <ul>
        <li>网站“精选长文”分类下当前没有文章。</li>
        <li>所有文章都被识别为视频内容而被跳过。</li>
        <li>网站结构发生变化，导致爬虫无法识别内容。</li>
    </ul>
    <p>此文件为自动生成的占位符，以确保自动化流程能够成功完成。</p>
    """
    book.add_item(chapter)

    book.toc = (epub.Link('report.xhtml', '执行报告', 'report'),)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', chapter]
    epub.write_epub('Selected_Articles.epub', book, {})
    print("\nNo articles found. A placeholder EPUB 'Selected_Articles.epub' was created.")


if __name__ == '__main__':
    all_article_urls = get_all_urls()
    
    articles_data = []
    if not all_article_urls:
        print("No article URLs found during crawl.")
    else:
        print(f"\nFound {len(all_article_urls)} article URLs. Fetching content...")
        for url in all_article_urls:
            time.sleep(2) 
            title, content = get_article_content(url)
            if title and content:
                articles_data.append({'title': title, 'content': content})

    if articles_data:
        print(f"Successfully fetched content for {len(articles_data)} articles.")
        create_epub(articles_data)
    else:
        print("No valid article content was fetched. Creating a placeholder EPUB.")
        create_placeholder_epub()
