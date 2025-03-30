#!/usr/bin/env python3
"""
Threads.net Scraper

This module provides functionality to scrape posts and replies from Threads.net accounts
and save them in various formats (PDF, JSON, TXT) while preserving images and metadata.
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Union

import requests
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ThreadsScraper:
    """A class to scrape posts and replies from Threads.net accounts."""

    def __init__(self, username: str, max_scrolls: int = 10):
        """
        Initialize the ThreadsScraper.

        Args:
            username: Threads.net username to scrape (without @ symbol)
            max_scrolls: Maximum number of page scrolls to perform
        """
        self.username = username
        self.base_url = f"https://www.threads.net/@{username}"
        self.replies_url = f"{self.base_url}/replies"
        self.posts: List[Dict] = []
        self.replies: List[Dict] = []
        self.max_scrolls = max_scrolls
        self.setup_driver()

    def setup_driver(self) -> None:
        """Set up the Selenium WebDriver with appropriate options."""
        chrome_options = Options()
        # Configure headless browser options
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Add realistic user agent and enable JavaScript
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        )
        chrome_options.add_argument("--enable-javascript")
        
        # Disable automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Try to find and use the system's Chrome/Chromium installation
            chromedriver_path = self._find_chromedriver()
            if not chromedriver_path:
                raise FileNotFoundError("Could not find chromedriver")
            
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Successfully initialized WebDriver")
            
        except Exception as e:
            print(f"Error setting up WebDriver: {str(e)}")
            self._print_troubleshooting_steps()
            sys.exit(1)

    def _find_chromedriver(self) -> Optional[str]:
        """
        Find the ChromeDriver executable in common system locations.

        Returns:
            Optional[str]: Path to ChromeDriver if found, None otherwise
        """
        chromedriver_paths = [
            "/usr/bin/chromedriver",
            "/usr/lib/chromium/chromedriver",
            "/usr/lib/chromium-browser/chromedriver",
            shutil.which("chromedriver")
        ]
        
        for path in chromedriver_paths:
            if path and os.path.exists(path):
                print(f"Found chromedriver at: {path}")
                return path
        return None

    def _print_troubleshooting_steps(self) -> None:
        """Print helpful troubleshooting steps for WebDriver setup issues."""
        print("\nTroubleshooting steps:")
        print("1. Make sure Chrome or Chromium is installed:")
        print("   - Run: which chromium-browser")
        print("2. Check if chromedriver is installed:")
        print("   - Run: which chromedriver")
        print("3. Set Chrome/Chromium path if needed:")
        print("   export CHROME_DRIVER_PATH=/usr/bin/chromium")

    def _wait_for_content(self, timeout: int = 30) -> bool:
        """
        Wait for content to load with multiple selectors and conditions.

        Args:
            timeout: Maximum time to wait for content in seconds

        Returns:
            bool: True if content was found, False otherwise
        """
        print("Waiting for content to load...")
        
        selectors = [
            "article",
            "div[role='article']",
            "div[data-pressable-container='true']",
            "div._aabd._aa8k._al3l",
            "div[style*='flex-direction: column']",
            "span[dir='auto']",
            "img:not([alt='Profile picture'])"
        ]
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                for selector in selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"Found content with selector: {selector}")
                        if len(self.driver.page_source) > 1000:
                            return True
                
                if self._is_blocked_page():
                    return False
                
                time.sleep(2)
            except Exception as e:
                print(f"Error while waiting for content: {str(e)}")
                time.sleep(2)
        
        return False

    def _is_blocked_page(self) -> bool:
        """
        Check if the current page is a login wall or blocking page.

        Returns:
            bool: True if blocked, False otherwise
        """
        current_url = self.driver.current_url
        return "login" in current_url.lower() or "blocked" in current_url.lower()

    def scrape_posts(self) -> None:
        """Scrape posts from the user's Threads account."""
        print(f"Scraping posts from {self.base_url}...")
        self.driver.get(self.base_url)
        
        # Add initial wait to let the page fully load
        time.sleep(5)
        
        # Execute JavaScript to scroll and trigger content load
        self._trigger_initial_load()
        
        if self._wait_for_content():
            self._scroll_and_extract(is_replies=False)
        else:
            print("Failed to load posts. The page might be protected or require authentication.")
        
    def scrape_replies(self) -> None:
        """Scrape replies from the user's Threads account."""
        print(f"Scraping replies from {self.replies_url}...")
        self.driver.get(self.replies_url)
        
        time.sleep(5)
        self._trigger_initial_load()
        
        if self._wait_for_content():
            self._scroll_and_extract(is_replies=True)
        else:
            print("Failed to load replies. The page might be protected or require authentication.")
    
    def _trigger_initial_load(self) -> None:
        """Execute JavaScript to trigger initial content load."""
        self.driver.execute_script("""
            window.scrollTo(0, 100);
            setTimeout(() => window.scrollTo(0, 0), 500);
        """)
    
    def _scroll_and_extract(self, is_replies: bool = False) -> None:
        """
        Scroll through the page and extract posts/replies.

        Args:
            is_replies: Whether to extract replies instead of posts
        """
        content_type = "replies" if is_replies else "posts"
        print(f"Loading {content_type} page...")
        
        # Save debug information
        self._save_debug_info(is_replies)
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        posts_count = 0
        scroll_attempts = 0
        max_scroll_attempts = self.max_scrolls * 2
        
        while scroll_attempts < max_scroll_attempts:
            articles = self._find_article_elements()
            
            for article in articles:
                try:
                    self._scroll_to_article(article)
                    post_data = self._extract_post_data(article)
                    
                    if self._should_save_post(post_data, is_replies):
                        self._save_post(post_data, is_replies)
                        posts_count += 1
                        print(f"Extracted {content_type[:-1]} #{posts_count}: "
                              f"{post_data.get('text', '')[:100]}...")
                        
                except Exception as e:
                    print(f"Error extracting post: {str(e)}")
            
            if not self._scroll_page(scroll_attempts, max_scroll_attempts, last_height):
                break
                
            scroll_attempts += 1
            
        print(f"Extracted {posts_count} {content_type}")
        
        if posts_count == 0:
            self._handle_no_content(is_replies)
    
    def _save_debug_info(self, is_replies: bool) -> None:
        """
        Save debug screenshots and page source.

        Args:
            is_replies: Whether this is for replies page
        """
        # Save screenshot
        screenshot_path = f"debug_{is_replies}_page.png"
        self.driver.save_screenshot(screenshot_path)
        print(f"Saved debug screenshot to {screenshot_path}")
        
        # Save page source
        with open(f"debug_{is_replies}_page.html", "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        print(f"Saved page source to debug_{is_replies}_page.html")
    
    def _find_article_elements(self) -> List:
        """
        Find article elements using multiple selectors.

        Returns:
            List: List of found article elements
        """
        selectors = [
            "article",
            "div[role='article']",
            "div[data-pressable-container='true']",
            "div._aabd._aa8k._al3l",
            "div[style*='flex-direction: column']"
        ]
        
        for selector in selectors:
            articles = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if articles:
                print(f"Found {len(articles)} items with selector: {selector}")
                return articles
        return []
    
    def _scroll_to_article(self, article) -> None:
        """
        Scroll article into view and wait for lazy loading.

        Args:
            article: The article element to scroll to
        """
        self.driver.execute_script("arguments[0].scrollIntoView(true);", article)
        time.sleep(1)
    
    def _should_save_post(self, post_data: Dict, is_replies: bool) -> bool:
        """
        Check if the post should be saved.

        Args:
            post_data: The extracted post data
            is_replies: Whether this is a reply

        Returns:
            bool: True if the post should be saved
        """
        if not (post_data.get('text') or post_data.get('images')):
            return False
            
        collection = self.replies if is_replies else self.posts
        
        # Check for duplicates
        for existing_post in collection:
            if (existing_post.get('text') == post_data.get('text') and
                existing_post.get('timestamp') == post_data.get('timestamp')):
                return False
        
        return True
    
    def _save_post(self, post_data: Dict, is_replies: bool) -> None:
        """
        Save the post to the appropriate collection.

        Args:
            post_data: The post data to save
            is_replies: Whether this is a reply
        """
        if is_replies:
            self.replies.append(post_data)
        else:
            self.posts.append(post_data)
    
    def _scroll_page(self, current_attempt: int, max_attempts: int, last_height: int) -> bool:
        """
        Scroll the page and check if we've reached the bottom.

        Args:
            current_attempt: Current scroll attempt number
            max_attempts: Maximum number of scroll attempts
            last_height: Last recorded page height

        Returns:
            bool: True if should continue scrolling, False if reached bottom
        """
        print(f"Scrolling... (attempt {current_attempt + 1}/{max_attempts})")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        new_height = self.driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # Try one more scroll with JavaScript
            self.driver.execute_script("""
                window.scrollTo(0, document.body.scrollHeight);
                setTimeout(() => window.scrollTo(0, document.body.scrollHeight + 100), 500);
            """)
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Reached the bottom of the page")
                return False
        return True
    
    def _handle_no_content(self, is_replies: bool) -> None:
        """
        Handle cases where no content was extracted.

        Args:
            is_replies: Whether this was for replies
        """
        print("Warning: No content was extracted. This might indicate:")
        print("1. The account might be private")
        print("2. The content might require authentication")
        print("3. The page structure might have changed")
        print("4. There might be anti-scraping measures in place")
        
        # Save final screenshot for debugging
        final_screenshot = f"final_{is_replies}_page.png"
        self.driver.save_screenshot(final_screenshot)
        print(f"Saved final state screenshot to {final_screenshot}")
    
    def _extract_post_data(self, article) -> Dict[str, Union[str, List[str]]]:
        """
        Extract data from a post article element.

        Args:
            article: The article element to extract data from

        Returns:
            Dict containing post data with keys:
                - text: Post text content
                - timestamp: Post timestamp
                - stats: List of engagement stats
                - images: List of image URLs
                - url: Post URL
        """
        post_data = {
            'text': self._extract_text(article),
            'timestamp': self._extract_timestamp(article),
            'stats': self._extract_stats(article),
            'images': self._extract_images(article),
            'url': self._extract_url(article)
        }
        return post_data

    def _extract_text(self, article) -> str:
        """Extract text content from article."""
        try:
            text_element = article.find_element(By.CSS_SELECTOR, "span[dir='auto']")
            return text_element.text
        except NoSuchElementException:
            return ""

    def _extract_timestamp(self, article) -> str:
        """Extract timestamp from article."""
        try:
            time_element = article.find_element(By.CSS_SELECTOR, "time")
            return time_element.get_attribute("datetime") or ""
        except NoSuchElementException:
            return ""

    def _extract_stats(self, article) -> List[str]:
        """Extract engagement stats from article."""
        try:
            stats = article.find_elements(By.CSS_SELECTOR, "span.x193iq5w")
            return [stat.text for stat in stats if stat.text]
        except NoSuchElementException:
            return []

    def _extract_images(self, article) -> List[str]:
        """
        Extract image URLs from article, excluding profile pictures.
        
        Returns:
            List[str]: List of image URLs
        """
        try:
            profile_indicators = [
                "profile_pic",
                "profile-pic",
                "avatar",
                "profile",
                "/p/",
                "_pp_",
                "profile_image"
            ]
            
            images = article.find_elements(By.CSS_SELECTOR, "img:not([alt='Profile picture'])")
            image_urls = []
            
            for img in images:
                src = img.get_attribute("src")
                alt = (img.get_attribute("alt") or "").lower()
                
                if not src:
                    continue
                
                # Skip profile pictures and small images
                if self._is_profile_picture(src, alt, profile_indicators):
                    print(f"Skipping profile image: {src}")
                    continue
                
                if self._is_small_image(img):
                    continue
                
                if src not in image_urls:
                    print(f"Adding post image: {src}")
                    image_urls.append(src)
            
            return image_urls
        except Exception as e:
            print(f"Error extracting images: {str(e)}")
            return []

    def _is_profile_picture(self, src: str, alt: str, indicators: List[str]) -> bool:
        """
        Check if an image is a profile picture.

        Args:
            src: Image source URL
            alt: Image alt text
            indicators: List of profile picture indicators

        Returns:
            bool: True if image is a profile picture
        """
        return (any(indicator in src.lower() for indicator in indicators) or
                any(indicator in alt for indicator in indicators) or
                "profile" in alt or
                alt == "avatar")

    def _is_small_image(self, img) -> bool:
        """
        Check if an image is too small (likely an icon or profile picture).

        Args:
            img: Image element to check

        Returns:
            bool: True if image is too small
        """
        try:
            width = int(img.get_attribute("width") or 0)
            height = int(img.get_attribute("height") or 0)
            if 0 < width < 50 or 0 < height < 50:
                print(f"Skipping small image: {img.get_attribute('src')} ({width}x{height})")
                return True
        except (ValueError, TypeError):
            pass
        return False

    def _extract_url(self, article) -> str:
        """Extract post URL from article."""
        try:
            link_element = article.find_element(By.CSS_SELECTOR, "a[href*='/t/']")
            return link_element.get_attribute("href") or ""
        except NoSuchElementException:
            return ""

    def download_image(self, url: str) -> Optional[BytesIO]:
        """
        Download an image from a URL.

        Args:
            url: Image URL to download

        Returns:
            Optional[BytesIO]: Image data if successful, None otherwise
        """
        try:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                return BytesIO(response.content)
        except Exception as e:
            print(f"Error downloading image {url}: {str(e)}")
        return None
    
    def generate_pdf(self, output_filename: str = "threads_posts.pdf") -> None:
        """
        Generate a PDF with the scraped posts and replies.

        Args:
            output_filename: Path to save the PDF file
        """
        print(f"Generating PDF: {output_filename}")
        os.makedirs(os.path.dirname(os.path.abspath(output_filename)), exist_ok=True)
        
        try:
            doc = self._create_pdf_document(output_filename)
            styles = self._create_pdf_styles()
            elements = self._create_pdf_elements(styles)
            
            self._build_pdf(doc, elements, output_filename)
        except Exception as e:
            print(f"Critical error in PDF generation: {str(e)}")
            self._save_as_json(output_filename)

    def _create_pdf_document(self, output_filename: str) -> SimpleDocTemplate:
        """Create the PDF document with proper settings."""
        return SimpleDocTemplate(
            output_filename,
            pagesize=letter,
            encoding='utf-8'
        )

    def _create_pdf_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom styles for the PDF document."""
        styles = getSampleStyleSheet()
        
        return {
            'title': ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.darkblue,
                spaceAfter=12
            ),
            'subtitle': ParagraphStyle(
                'Subtitle',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.darkblue,
                spaceAfter=10
            ),
            'timestamp': ParagraphStyle(
                'Timestamp',
                parent=styles['Italic'],
                fontSize=8,
                textColor=colors.gray
            ),
            'content': ParagraphStyle(
                'Content',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            )
        }

    def _create_pdf_elements(self, styles: Dict[str, ParagraphStyle]) -> List:
        """Create the content elements for the PDF."""
        elements = []
        
        # Add title
        elements.extend(self._create_title_elements(styles))
        
        # Add posts section
        if self.posts:
            elements.extend(self._create_posts_section(styles))
        
        # Add page break before replies if needed
        if self.posts and self.replies:
            elements.append(PageBreak())
        
        # Add replies section
        if self.replies:
            elements.extend(self._create_replies_section(styles))
        
        return elements

    def _create_title_elements(self, styles: Dict[str, ParagraphStyle]) -> List:
        """Create the title section elements."""
        return [
            Paragraph(f"Threads Posts and Replies for @{self.username}", styles['title']),
            Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                     styles['timestamp']),
            Spacer(1, 0.25*inch)
        ]

    def _create_posts_section(self, styles: Dict[str, ParagraphStyle]) -> List:
        """Create the posts section elements."""
        elements = [
            Paragraph("Posts", styles['subtitle']),
            Spacer(1, 0.1*inch)
        ]
        
        for i, post in enumerate(self.posts, 1):
            try:
                elements.extend(self._create_post_elements(post, i, styles))
                
                # Add page break after every 3 posts
                if i % 3 == 0 and i < len(self.posts):
                    elements.append(PageBreak())
            except Exception as e:
                print(f"Error processing post #{i}: {str(e)}")
        
        return elements

    def _create_replies_section(self, styles: Dict[str, ParagraphStyle]) -> List:
        """Create the replies section elements."""
        elements = [
            Paragraph("Replies", styles['subtitle']),
            Spacer(1, 0.1*inch)
        ]
        
        for i, reply in enumerate(self.replies, 1):
            try:
                elements.extend(self._create_post_elements(reply, i, styles, is_reply=True))
                
                # Add page break after every 3 replies
                if i % 3 == 0 and i < len(self.replies):
                    elements.append(PageBreak())
            except Exception as e:
                print(f"Error processing reply #{i}: {str(e)}")
        
        return elements

    def _create_post_elements(self, post: Dict, index: int, styles: Dict[str, ParagraphStyle], 
                            is_reply: bool = False) -> List:
        """Create elements for a single post or reply."""
        elements = []
        post_type = "Reply" if is_reply else "Post"
        
        # Add header with timestamp
        header = f"{post_type} #{index}"
        if post.get('timestamp'):
            try:
                dt = datetime.fromisoformat(post['timestamp'].replace('Z', '+00:00'))
                header += f" - {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            except:
                header += f" - {post['timestamp']}"
        
        elements.append(Paragraph(self._clean_text(header), styles['timestamp']))
        
        # Add post text
        if post.get('text'):
            elements.append(Paragraph(self._clean_text(post['text']), styles['content']))
        
        # Add stats
        if post.get('stats'):
            stats_text = " | ".join(post['stats'])
            elements.append(Paragraph(self._clean_text(stats_text), styles['timestamp']))
        
        # Add URL
        if post.get('url'):
            elements.append(Paragraph(f"URL: {post['url']}", styles['timestamp']))
        
        # Add images
        if post.get('images'):
            elements.extend(self._create_image_elements(post['images']))
        
        elements.append(Spacer(1, 0.2*inch))
        return elements

    def _create_image_elements(self, image_urls: List[str], max_images: int = 3) -> List:
        """Create elements for post images."""
        elements = []
        for img_url in image_urls[:max_images]:
            try:
                img_data = self.download_image(img_url)
                if img_data:
                    img = self._process_image(img_data)
                    if img:
                        elements.append(img)
                        elements.append(Spacer(1, 0.1*inch))
            except Exception as e:
                print(f"Error processing image: {str(e)}")
        return elements

    def _process_image(self, img_data: BytesIO) -> Optional[Image]:
        """Process and resize an image for PDF inclusion."""
        try:
            pil_img = PILImage.open(img_data)
            
            # Convert to RGB if needed
            if pil_img.mode == 'RGBA':
                rgb_img = PILImage.new('RGB', pil_img.size, (255, 255, 255))
                rgb_img.paste(pil_img, mask=pil_img.split()[3])
                pil_img = rgb_img
            
            # Save as JPEG
            img_buffer = BytesIO()
            pil_img.save(img_buffer, format='JPEG')
            img_buffer.seek(0)
            
            # Calculate dimensions
            width, height = pil_img.size
            max_width = 4 * inch
            max_height = 4 * inch
            
            # Scale image
            width_ratio = max_width / width if width > max_width else 1
            height_ratio = max_height / height if height > max_height else 1
            ratio = min(width_ratio, height_ratio)
            
            return Image(img_buffer, width=width * ratio, height=height * ratio)
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return None

    def _clean_text(self, text: str) -> str:
        """Clean text for PDF compatibility."""
        if not text:
            return ""
        
        if not isinstance(text, str):
            text = str(text)
        
        # Replace problematic characters
        text = text.replace('\u2028', ' ')  # Line separator
        text = text.replace('\u2029', ' ')  # Paragraph separator
        
        # Replace XML/HTML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#39;')
        
        # Remove control characters
        return ''.join(c if ord(c) >= 32 or c in '\n\r\t' else ' ' for c in text)

    def _build_pdf(self, doc: SimpleDocTemplate, elements: List, output_filename: str) -> None:
        """Build the PDF with error handling and fallbacks."""
        try:
            doc.build(elements)
            print(f"PDF generated successfully: {output_filename}")
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            self._try_fallback_formats(elements, output_filename)

    def _try_fallback_formats(self, elements: List, output_filename: str) -> None:
        """Try alternative output formats if PDF generation fails."""
        # Try text-only PDF
        try:
            print("Attempting to save without images...")
            elements_no_images = [el for el in elements if not isinstance(el, Image)]
            text_only_filename = output_filename.replace('.pdf', '_text_only.pdf')
            text_doc = SimpleDocTemplate(text_only_filename, pagesize=letter, encoding='utf-8')
            text_doc.build(elements_no_images)
            print(f"Text-only PDF generated successfully: {text_only_filename}")
            return
        except Exception as e2:
            print(f"Failed to generate text-only PDF: {str(e2)}")
        
        # Try plain text
        try:
            self._save_as_text(elements, output_filename)
            return
        except Exception as e3:
            print(f"Failed to save as text: {str(e3)}")
        
        # Final fallback - JSON
        self._save_as_json(output_filename)

    def _save_as_text(self, elements: List, output_filename: str) -> None:
        """Save content as plain text."""
        txt_filename = output_filename.replace('.pdf', '.txt')
        with open(txt_filename, 'w', encoding='utf-8') as f:
            for el in elements:
                if isinstance(el, Paragraph):
                    text = el.text
                    # Remove HTML entities
                    text = text.replace('&amp;', '&').replace('&lt;', '<')
                    text = text.replace('&gt;', '>').replace('&quot;', '"')
                    text = text.replace('&#39;', "'")
                    f.write(text + '\n\n')
        print(f"Content saved as text file: {txt_filename}")

    def _save_as_json(self, output_filename: str) -> None:
        """Save content as JSON."""
        try:
            json_filename = output_filename.replace('.pdf', '.json')
            data = {
                'username': self.username,
                'posts': self.posts,
                'replies': self.replies
            }
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"Data saved as JSON: {json_filename}")
        except Exception as e_json:
            print(f"Failed to save data as JSON: {str(e_json)}")

    def generate_markdown(self, output_filename: str = "threads_posts.md") -> None:
        """
        Generate a Markdown file with the scraped posts and replies.

        Args:
            output_filename: Path to save the Markdown file
        """
        print(f"Generating Markdown: {output_filename}")
        output_dir = os.path.dirname(os.path.abspath(output_filename))
        os.makedirs(output_dir, exist_ok=True)
        
        # Create images directory
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"# Threads Posts and Replies for @{self.username}\n\n")
                f.write(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                
                # Write posts
                if self.posts:
                    f.write("## Posts\n\n")
                    for i, post in enumerate(self.posts, 1):
                        self._write_post_markdown(f, post, i, is_reply=False, images_dir=images_dir)
                
                # Write replies
                if self.replies:
                    f.write("## Replies\n\n")
                    for i, reply in enumerate(self.replies, 1):
                        self._write_post_markdown(f, reply, i, is_reply=True, images_dir=images_dir)
                
            print(f"Markdown generated successfully: {output_filename}")
        except Exception as e:
            print(f"Error generating Markdown: {str(e)}")
            self._save_as_json(output_filename)
    
    def _write_post_markdown(self, file, post: Dict, index: int, is_reply: bool = False, images_dir: str = None) -> None:
        """Write a single post or reply to the markdown file."""
        post_type = "Reply" if is_reply else "Post"
        
        # Add header with timestamp
        file.write(f"### {post_type} #{index}")
        if post.get('timestamp'):
            try:
                dt = datetime.fromisoformat(post['timestamp'].replace('Z', '+00:00'))
                file.write(f" - {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            except:
                file.write(f" - {post['timestamp']}")
        file.write("\n\n")
        
        # Add post text (preserving emojis)
        if post.get('text'):
            # Ensure proper Unicode handling for emojis
            text = post['text'].encode('utf-8').decode('utf-8')
            file.write(f"{text}\n\n")
        
        # Add stats
        if post.get('stats'):
            stats_text = " | ".join(post['stats'])
            file.write(f"*{stats_text}*\n\n")
        
        # Add URL
        if post.get('url'):
            file.write(f"[View on Threads]({post['url']})\n\n")
        
        # Add images (excluding profile pictures)
        if post.get('images') and images_dir:
            for i, img_url in enumerate(post['images']):
                try:
                    # Download image with proper headers
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        'Referer': 'https://www.threads.net/',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                    }
                    
                    response = requests.get(img_url, headers=headers, stream=True, timeout=10)
                    if response.status_code == 200:
                        # Generate unique filename
                        ext = os.path.splitext(img_url)[1] or '.jpg'
                        img_filename = f"post_{index}_img_{i}{ext}"
                        img_path = os.path.join(images_dir, img_filename)
                        
                        # Save image
                        with open(img_path, 'wb') as img_file:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    img_file.write(chunk)
                        
                        # Use relative path in markdown
                        relative_path = os.path.join("images", img_filename)
                        file.write(f"![Thread Image]({relative_path})\n\n")
                    else:
                        print(f"Failed to download image {img_url}: HTTP {response.status_code}")
                        # Fallback to original URL if download fails
                        file.write(f"![Thread Image]({img_url})\n\n")
                except Exception as e:
                    print(f"Error processing image {img_url}: {str(e)}")
                    # Fallback to original URL if processing fails
                    file.write(f"![Thread Image]({img_url})\n\n")
        
        file.write("---\n\n")

    def close(self):
        """Close the WebDriver."""
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def run(self, output_filename="threads_posts.pdf"):
        """Run the complete scraping and PDF generation process."""
        try:
            self.scrape_posts()
            self.scrape_replies()
            
            # Determine output format from filename extension
            if output_filename.endswith('.md'):
                self.generate_markdown(output_filename)
            else:
                self.generate_pdf(output_filename)
        finally:
            self.close()


if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Scrape posts and replies from a Threads.net account and save to PDF.')
    parser.add_argument('--username', type=str, required=True,
                        help='Threads username to scrape (without the @ symbol)')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Directory to save the output files')
    parser.add_argument('--max-scrolls', type=int, default=10,
                        help='Maximum number of scrolls to perform (more scrolls = more posts)')
    parser.add_argument('--skip-replies', action='store_true',
                        help='Skip scraping replies')
    parser.add_argument('--skip-posts', action='store_true',
                        help='Skip scraping posts')
    parser.add_argument('--output-format', type=str, choices=['pdf', 'json', 'txt', 'md'], default='pdf',
                        help='Output format: pdf, json, txt, or md (markdown)')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Set file extension based on output format
    if args.output_format == 'json':
        extension = '.json'
    elif args.output_format == 'txt':
        extension = '.txt'
    elif args.output_format == 'md':
        extension = '.md'
    else:
        extension = '.pdf'
    
    output_filename = os.path.join(args.output_dir, f"{args.username}_threads_{timestamp}{extension}")
    
    # Run the scraper
    scraper = ThreadsScraper(args.username, max_scrolls=args.max_scrolls)
    
    try:
        if not args.skip_posts:
            scraper.scrape_posts()
        
        if not args.skip_replies:
            scraper.scrape_replies()
        
        # Generate output in the specified format
        if args.output_format == 'json':
            # Save as JSON
            data = {
                'username': args.username,
                'posts': scraper.posts,
                'replies': scraper.replies
            }
            
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"Data saved as JSON: {output_filename}")
        elif args.output_format == 'txt':
            # Save as plain text
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(f"Threads Posts and Replies for @{args.username}\n")
                f.write(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Write posts
                if scraper.posts:
                    f.write("=== POSTS ===\n\n")
                    for i, post in enumerate(scraper.posts, 1):
                        f.write(f"Post #{i}")
                        if post.get('timestamp'):
                            try:
                                dt = datetime.fromisoformat(post['timestamp'].replace('Z', '+00:00'))
                                formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                                f.write(f" - {formatted_date}")
                            except:
                                f.write(f" - {post['timestamp']}")
                        f.write("\n\n")
                        
                        if post.get('text'):
                            f.write(f"{post['text']}\n\n")
                        
                        if post.get('stats'):
                            f.write(f"{' | '.join(post['stats'])}\n\n")
                        
                        if post.get('url'):
                            f.write(f"URL: {post['url']}\n\n")
                        
                        if post.get('images'):
                            f.write(f"Images: {len(post['images'])}\n")
                            for img_url in post['images']:
                                f.write(f"  {img_url}\n")
                            f.write("\n")
                        
                        f.write("---\n\n")
                
                # Write replies
                if scraper.replies:
                    f.write("=== REPLIES ===\n\n")
                    for i, reply in enumerate(scraper.replies, 1):
                        f.write(f"Reply #{i}")
                        if reply.get('timestamp'):
                            try:
                                dt = datetime.fromisoformat(reply['timestamp'].replace('Z', '+00:00'))
                                formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                                f.write(f" - {formatted_date}")
                            except:
                                f.write(f" - {reply['timestamp']}")
                        f.write("\n\n")
                        
                        if reply.get('text'):
                            f.write(f"{reply['text']}\n\n")
                        
                        if reply.get('stats'):
                            f.write(f"{' | '.join(reply['stats'])}\n\n")
                        
                        if reply.get('url'):
                            f.write(f"URL: {reply['url']}\n\n")
                        
                        if reply.get('images'):
                            f.write(f"Images: {len(reply['images'])}\n")
                            for img_url in reply['images']:
                                f.write(f"  {img_url}\n")
                            f.write("\n")
                        
                        f.write("---\n\n")
            
            print(f"Data saved as text: {output_filename}")
        elif args.output_format == 'md':
            # Generate Markdown
            scraper.generate_markdown(output_filename)
        else:
            # Generate PDF (default)
            scraper.generate_pdf(output_filename)
    finally:
        scraper.close() 