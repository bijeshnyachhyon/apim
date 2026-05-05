# T24 TCServer Connector - HTTP and TCP modes
import asyncio
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings

class T24Connector:
    """Connector for Temenos T24 TCServer via HTTP or TCP."""

    def __init__(self, host: str, port: int, username: str, password: str,
                 mode: str = "http", http_endpoint: str = "/BrowserWeb/servlet/BrowserServlet",
                 timeout: int = 30, max_retries: int = 3):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mode = mode
        self.http_endpoint = http_endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def send_ofs_http(self, ofs_message: str) -> str:
        """Send OFS message via HTTP POST to T24 BrowserServlet."""
        client = await self._get_client()
        url = f"http://{self.host}:{self.port}{self.http_endpoint}"
        data = {
            "OFS": ofs_message,
            "USER": self.username,
            "PASSWORD": self.password,
        }
        response = await client.post(url, data=data)
        response.raise_for_status()
        return self._extract_ofs_response(response.text)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionRefusedError, TimeoutError))
    )
    async def send_ofs_tcp(self, ofs_message: str) -> str:
        """Send OFS message via raw TCP socket to TCServer."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=self.timeout
        )
        try:
            # Send OFS message + newline
            writer.write((ofs_message + "\n").encode())
            await writer.drain()

            # Read response until EOF or timeout
            response_bytes = await asyncio.wait_for(
                reader.readuntil(b'\n'),
                timeout=self.timeout
            )
            return response_bytes.decode('utf-8', errors='replace').strip()
        finally:
            writer.close()
            await writer.wait_closed()

    async def send_ofs(self, ofs_message: str) -> str:
        """Send OFS message using configured mode."""
        start = datetime.now()
        try:
            if self.mode == "http":
                response = await self.send_ofs_http(ofs_message)
            else:
                response = await self.send_ofs_tcp(ofs_message)
            return response
        finally:
            elapsed = (datetime.now() - start).total_seconds() * 1000

    async def test_connection(self) -> bool:
        """Test T24 connection with a simple enquiry."""
        try:
            test_ofs = f"ENQ.CUSTOMER,CUSTOMER,0/{self.username}/{self.password},,@ID=TEST"
            await self.send_ofs(test_ofs)
            return True
        except Exception:
            return False

    def _extract_ofs_response(self, html_response: str) -> str:
        """Extract OFS response from HTML wrapper (BrowserServlet)."""
        # T24 BrowserServlet wraps OFS response in HTML <pre> tags
        import re
        pre_match = re.search(r'<pre>(.*?)</pre>', html_response, re.DOTALL)
        if pre_match:
            return pre_match.group(1).strip()
        # If no <pre> tag, return raw response
        return html_response.strip()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
