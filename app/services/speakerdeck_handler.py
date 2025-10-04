"""
SpeakerDeck presentation handler for PDF extraction and download.

This module provides functionality to:
- Detect SpeakerDeck URLs
- Extract PDF URLs from SpeakerDeck presentations using oEmbed API
- Fall back to HTML scraping when oEmbed fails
- Download PDFs with streaming for large files
"""

import httpx
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class SpeakerDeckHandler:
    """Handle SpeakerDeck presentation PDF extraction and downloads"""
    
    # Constants
    SPEAKERDECK_DOMAIN = "speakerdeck.com"
    OEMBED_ENDPOINT = "https://speakerdeck.com/oembed.json"
    USER_AGENT = "Scrap-Board/1.0 (+https://github.com/takpanda/scrap-board)"
    TIMEOUT_SEC = 30
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    def __init__(self, timeout: int = TIMEOUT_SEC):
        """
        Initialize SpeakerDeckHandler.
        
        Args:
            timeout: HTTP request timeout in seconds (default: 30)
        """
        self.timeout = timeout
    
    def is_speakerdeck_url(self, url: str) -> bool:
        """
        Check if URL is from SpeakerDeck domain.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is from speakerdeck.com, False otherwise
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() == self.SPEAKERDECK_DOMAIN
        except Exception as e:
            logger.warning(f"Failed to parse URL {url}: {e}")
            return False
    
    def get_pdf_url(self, presentation_url: str) -> Optional[str]:
        """
        Extract PDF URL from SpeakerDeck presentation.
        
        Tries oEmbed API first, falls back to HTML scraping.
        
        Args:
            presentation_url: SpeakerDeck presentation URL
            
        Returns:
            PDF URL if found, None otherwise
        """
        if not self.is_speakerdeck_url(presentation_url):
            logger.warning(f"URL is not from SpeakerDeck: {presentation_url}")
            return None
        
        # Try oEmbed API first
        pdf_url = self._get_pdf_url_from_oembed(presentation_url)
        if pdf_url:
            logger.info(f"Found PDF URL via oEmbed: {pdf_url}")
            return pdf_url
        
        # Fall back to HTML scraping
        logger.info(f"oEmbed failed, trying HTML scraping for {presentation_url}")
        pdf_url = self._get_pdf_url_from_html(presentation_url)
        if pdf_url:
            logger.info(f"Found PDF URL via HTML scraping: {pdf_url}")
            return pdf_url
        
        logger.warning(f"Failed to extract PDF URL from {presentation_url}")
        return None
    
    def _get_pdf_url_from_oembed(self, presentation_url: str) -> Optional[str]:
        """
        Extract PDF URL using SpeakerDeck oEmbed API.
        
        Args:
            presentation_url: SpeakerDeck presentation URL
            
        Returns:
            PDF URL if found in oEmbed response, None otherwise
        """
        try:
            with httpx.Client(
                headers={"User-Agent": self.USER_AGENT},
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                response = client.get(
                    self.OEMBED_ENDPOINT,
                    params={"url": presentation_url}
                )
                response.raise_for_status()
                
                data = response.json()
                # oEmbed response may contain PDF URL in various fields
                # Check common locations
                for key in ['url', 'pdf_url', 'download_url']:
                    if key in data and data[key] and data[key].endswith('.pdf'):
                        return data[key]
                
                # Check if HTML contains PDF link
                if 'html' in data:
                    pdf_url = self._extract_pdf_from_html_content(data['html'])
                    if pdf_url:
                        return pdf_url
                
                return None
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"oEmbed API error for {presentation_url}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.warning(f"oEmbed API request failed for {presentation_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in oEmbed extraction: {e}")
            return None
    
    def _get_pdf_url_from_html(self, presentation_url: str) -> Optional[str]:
        """
        Extract PDF URL by scraping presentation HTML.
        
        Args:
            presentation_url: SpeakerDeck presentation URL
            
        Returns:
            PDF URL if found in HTML, None otherwise
        """
        try:
            with httpx.Client(
                headers={"User-Agent": self.USER_AGENT},
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                response = client.get(presentation_url)
                response.raise_for_status()
                
                return self._extract_pdf_from_html_content(response.text)
                
        except httpx.RequestError as e:
            logger.warning(f"Failed to fetch HTML for {presentation_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in HTML scraping: {e}")
            return None
    
    def _extract_pdf_from_html_content(self, html_content: str) -> Optional[str]:
        """
        Extract PDF URL from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            PDF URL if found, None otherwise
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Strategy 1: Look for download links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '.pdf' in href.lower():
                    # Convert relative URLs to absolute
                    if href.startswith('http'):
                        return href
                    # SpeakerDeck PDFs are typically on S3
                    if 'speakerd.s3.amazonaws.com' in href:
                        return href if href.startswith('http') else f"https:{href}"
            
            # Strategy 2: Look for meta tags
            for meta in soup.find_all('meta'):
                content = meta.get('content', '')
                if '.pdf' in content.lower():
                    if content.startswith('http') and '.pdf' in content:
                        return content
            
            # Strategy 3: Look for data attributes
            for elem in soup.find_all(attrs={'data-pdf': True}):
                pdf_url = elem['data-pdf']
                if pdf_url:
                    return pdf_url if pdf_url.startswith('http') else urljoin('https://speakerdeck.com', pdf_url)
            
            # Strategy 4: Look for PDF URLs in script tags or data
            for script in soup.find_all('script'):
                if script.string:
                    # Look for PDF URLs in JavaScript
                    pdf_matches = re.findall(r'https?://[^"\s]+\.pdf', script.string)
                    if pdf_matches:
                        return pdf_matches[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting PDF from HTML: {e}")
            return None
    
    def download_pdf(self, pdf_url: str, document_id: str, base_dir: str = "data") -> Optional[str]:
        """
        Download PDF file with streaming for large files.
        
        Args:
            pdf_url: URL of PDF to download
            document_id: Document ID for filename
            base_dir: Base directory for storage (default: "data")
            
        Returns:
            Relative path to downloaded PDF if successful, None otherwise
        """
        try:
            # Create directory structure
            pdf_dir = Path(base_dir) / "assets" / "pdfs" / "speakerdeck"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate file path
            pdf_filename = f"{document_id}.pdf"
            pdf_path = pdf_dir / pdf_filename
            relative_path = f"assets/pdfs/speakerdeck/{pdf_filename}"
            
            logger.info(f"Downloading PDF from {pdf_url} to {pdf_path}")
            
            # Download with streaming
            with httpx.Client(
                headers={"User-Agent": self.USER_AGENT},
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                with client.stream("GET", pdf_url) as response:
                    response.raise_for_status()
                    
                    # Check file size
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.MAX_FILE_SIZE:
                        logger.warning(f"PDF exceeds size limit: {content_length} bytes > {self.MAX_FILE_SIZE}")
                        return None
                    
                    # Stream to file
                    total_size = 0
                    with open(pdf_path, 'wb') as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            total_size += len(chunk)
                            
                            # Check accumulated size
                            if total_size > self.MAX_FILE_SIZE:
                                logger.warning(f"PDF exceeded size limit during download: {total_size} bytes")
                                pdf_path.unlink(missing_ok=True)  # Clean up partial file
                                return None
                            
                            f.write(chunk)
                    
                    logger.info(f"Successfully downloaded PDF ({total_size} bytes) to {relative_path}")
                    return relative_path
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading PDF from {pdf_url}: {e.response.status_code}")
            # Clean up partial file
            if pdf_path.exists():
                pdf_path.unlink(missing_ok=True)
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error downloading PDF from {pdf_url}: {e}")
            # Clean up partial file
            if pdf_path.exists():
                pdf_path.unlink(missing_ok=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading PDF: {e}")
            # Clean up partial file
            if pdf_path.exists():
                pdf_path.unlink(missing_ok=True)
            return None
