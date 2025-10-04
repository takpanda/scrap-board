"""
Unit tests for SpeakerDeckHandler.

Tests PDF URL extraction and download functionality using mocked HTTP responses.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import httpx

from app.services.speakerdeck_handler import SpeakerDeckHandler

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


class TestSpeakerDeckHandler:
    """Test suite for SpeakerDeckHandler"""
    
    @pytest.fixture
    def handler(self):
        """Create SpeakerDeckHandler instance for testing"""
        return SpeakerDeckHandler(timeout=10)
    
    # Test is_speakerdeck_url()
    
    def test_is_speakerdeck_url_valid(self, handler):
        """Test detection of valid SpeakerDeck URLs"""
        valid_urls = [
            "https://speakerdeck.com/username/presentation-title",
            "http://speakerdeck.com/user/slides",
            "https://www.speakerdeck.com/test/demo",
        ]
        
        for url in valid_urls:
            assert handler.is_speakerdeck_url(url) is True
    
    def test_is_speakerdeck_url_invalid(self, handler):
        """Test rejection of non-SpeakerDeck URLs"""
        invalid_urls = [
            "https://example.com/presentation",
            "https://slideshare.net/slides",
            "https://speakerdeck.org/fake",  # Different TLD
            "not-a-url",
            "",
        ]
        
        for url in invalid_urls:
            assert handler.is_speakerdeck_url(url) is False
    
    # Test get_pdf_url() with oEmbed success
    
    @patch('httpx.Client')
    def test_get_pdf_url_oembed_success(self, mock_client_class, handler):
        """Test PDF URL extraction via oEmbed API success"""
        # Mock oEmbed API response with PDF URL
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "url": "https://speakerd.s3.amazonaws.com/presentations/abc123/slides.pdf",
            "title": "Test Presentation"
        }
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        url = "https://speakerdeck.com/user/presentation"
        pdf_url = handler.get_pdf_url(url)
        
        assert pdf_url == "https://speakerd.s3.amazonaws.com/presentations/abc123/slides.pdf"
        mock_client.get.assert_called_once()
    
    # Test get_pdf_url() with oEmbed failure and HTML scraping success
    
    @patch('httpx.Client')
    def test_get_pdf_url_oembed_fail_html_success(self, mock_client_class, handler):
        """Test fallback to HTML scraping when oEmbed fails"""
        mock_client = Mock()
        
        # First call (oEmbed) fails
        oembed_response = Mock()
        oembed_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=Mock(status_code=404)
        )
        
        # Second call (HTML) succeeds with PDF link
        html_response = Mock()
        html_response.status_code = 200
        html_response.text = '''
            <html>
                <body>
                    <a href="https://speakerd.s3.amazonaws.com/presentations/xyz789/deck.pdf" 
                       class="download-link">Download PDF</a>
                </body>
            </html>
        '''
        html_response.raise_for_status = Mock()
        
        # Configure mock to return different responses
        mock_client.get.side_effect = [oembed_response, html_response]
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        url = "https://speakerdeck.com/user/presentation"
        pdf_url = handler.get_pdf_url(url)
        
        assert pdf_url == "https://speakerd.s3.amazonaws.com/presentations/xyz789/deck.pdf"
        assert mock_client.get.call_count == 2
    
    # Test get_pdf_url() complete failure
    
    @patch('httpx.Client')
    def test_get_pdf_url_complete_failure(self, mock_client_class, handler):
        """Test when both oEmbed and HTML scraping fail"""
        mock_client = Mock()
        
        # Both calls fail
        error_response = Mock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=Mock(status_code=404)
        )
        
        mock_client.get.return_value = error_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        url = "https://speakerdeck.com/user/presentation"
        pdf_url = handler.get_pdf_url(url)
        
        assert pdf_url is None
    
    # Test get_pdf_url() with non-SpeakerDeck URL
    
    def test_get_pdf_url_non_speakerdeck(self, handler):
        """Test rejection of non-SpeakerDeck URLs"""
        url = "https://example.com/presentation"
        pdf_url = handler.get_pdf_url(url)
        
        assert pdf_url is None
    
    # Test download_pdf() successful download
    
    @patch('httpx.Client')
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_pdf_success(self, mock_file, mock_mkdir, mock_client_class, handler):
        """Test successful PDF download"""
        # Mock streaming response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '1024'}
        mock_response.raise_for_status = Mock()
        mock_response.iter_bytes.return_value = [b'PDF content chunk 1', b'PDF content chunk 2']
        
        mock_client = Mock()
        mock_client.stream.return_value.__enter__ = Mock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = Mock(return_value=False)
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        pdf_url = "https://speakerd.s3.amazonaws.com/presentations/abc123/slides.pdf"
        document_id = "test-doc-123"
        
        result = handler.download_pdf(pdf_url, document_id, base_dir="test_data")
        
        assert result == "assets/pdfs/speakerdeck/test-doc-123.pdf"
        mock_mkdir.assert_called_once()
        mock_file.assert_called_once()
    
    # Test download_pdf() network error
    
    @patch('httpx.Client')
    @patch('pathlib.Path.mkdir')
    def test_download_pdf_network_error(self, mock_mkdir, mock_client_class, handler):
        """Test PDF download with network error"""
        mock_client = Mock()
        mock_client.stream.side_effect = httpx.RequestError("Network error")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        pdf_url = "https://speakerd.s3.amazonaws.com/presentations/abc123/slides.pdf"
        document_id = "test-doc-456"
        
        result = handler.download_pdf(pdf_url, document_id)
        
        assert result is None
    
    # Test download_pdf() file size limit exceeded
    
    @patch('httpx.Client')
    @patch('pathlib.Path.mkdir')
    def test_download_pdf_size_limit_exceeded(self, mock_mkdir, mock_client_class, handler):
        """Test PDF download with file size exceeding limit"""
        # Mock response with size exceeding limit
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(handler.MAX_FILE_SIZE + 1)}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.stream.return_value.__enter__ = Mock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = Mock(return_value=False)
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        pdf_url = "https://speakerd.s3.amazonaws.com/presentations/huge.pdf"
        document_id = "test-doc-789"
        
        result = handler.download_pdf(pdf_url, document_id)
        
        assert result is None
    
    # Test download_pdf() with size limit exceeded during streaming
    
    @patch('httpx.Client')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.unlink')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_download_pdf_size_exceeded_during_stream(
        self, mock_file, mock_exists, mock_unlink, mock_mkdir, mock_client_class, handler
    ):
        """Test PDF download aborted when accumulated size exceeds limit"""
        # Mock streaming response with large chunks
        chunk_size = handler.MAX_FILE_SIZE // 2 + 1
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}  # No content-length header
        mock_response.raise_for_status = Mock()
        # Simulate two large chunks that exceed limit
        mock_response.iter_bytes.return_value = [b'x' * chunk_size, b'x' * chunk_size]
        
        mock_client = Mock()
        mock_client.stream.return_value.__enter__ = Mock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = Mock(return_value=False)
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        pdf_url = "https://speakerd.s3.amazonaws.com/presentations/huge.pdf"
        document_id = "test-doc-stream"
        
        result = handler.download_pdf(pdf_url, document_id)
        
        assert result is None
        # Verify cleanup was attempted
        mock_unlink.assert_called_once()
    
    # Test HTML extraction edge cases
    
    def test_extract_pdf_from_html_meta_tag(self, handler):
        """Test PDF extraction from meta tags"""
        html = '''
            <html>
                <head>
                    <meta property="og:pdf" content="https://example.com/slides.pdf">
                </head>
            </html>
        '''
        
        pdf_url = handler._extract_pdf_from_html_content(html)
        assert pdf_url == "https://example.com/slides.pdf"
    
    def test_extract_pdf_from_html_data_attribute(self, handler):
        """Test PDF extraction from data attributes"""
        html = '''
            <html>
                <body>
                    <div data-pdf="/presentations/slides.pdf"></div>
                </body>
            </html>
        '''
        
        pdf_url = handler._extract_pdf_from_html_content(html)
        assert pdf_url == "https://speakerdeck.com/presentations/slides.pdf"
    
    def test_extract_pdf_from_html_script(self, handler):
        """Test PDF extraction from script tags"""
        html = '''
            <html>
                <body>
                    <script>
                        var pdfUrl = "https://speakerd.s3.amazonaws.com/abc.pdf";
                    </script>
                </body>
            </html>
        '''
        
        pdf_url = handler._extract_pdf_from_html_content(html)
        assert pdf_url == "https://speakerd.s3.amazonaws.com/abc.pdf"
    
    def test_extract_pdf_from_html_no_pdf(self, handler):
        """Test HTML without PDF links returns None"""
        html = '''
            <html>
                <body>
                    <p>No PDF here</p>
                </body>
            </html>
        '''
        
        pdf_url = handler._extract_pdf_from_html_content(html)
        assert pdf_url is None
