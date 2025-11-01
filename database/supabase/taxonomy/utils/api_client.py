"""
API Client Utility
Provides a robust HTTP client for OpenAI API calls with retry logic and session pooling.
"""

import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class AnalysisResult:
    """Data class for API analysis results"""
    status: str  # "success" or "api_error"
    question_id: str
    input_data: Dict
    response: Optional[str] = None
    error_details: Optional[str] = None
    processing_time: Optional[float] = None


class APIClient:
    """
    Robust API client with automatic retry and connection pooling.

    Features:
    - Automatic retry on transient failures (429, 500, 502, 503, 504)
    - Exponential backoff strategy
    - Connection pooling for improved performance
    - Support for both Chat Completions and Responses APIs

    Args:
        api_url: Base API URL (e.g., "https://api.openai.com/v1/")
        api_key: OpenAI API key
        model_name: Model identifier (e.g., "gpt-4o-mini")
        use_responses_api: Whether to use Responses API instead of Chat Completions
        retry_total: Total number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        pool_connections: Number of connection pool connections
        pool_maxsize: Maximum pool size
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model_name: str,
        use_responses_api: bool = False,
        retry_total: int = 5,
        backoff_factor: float = 1.5,
        pool_connections: int = 20,
        pool_maxsize: int = 100
    ):
        # Normalize URL
        self.base_url = api_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.use_responses_api = use_responses_api

        # Choose endpoint based on API type
        if self.use_responses_api:
            self.endpoint = f"{self.base_url}/responses"
        else:
            self.endpoint = f"{self.base_url}/chat/completions"

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=retry_total,
            backoff_factor=backoff_factor,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )

        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # Set headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

    def call_api(self, messages: List[Dict], timeout: int = 120) -> Dict:
        """
        Make an API call with the configured model.

        Args:
            messages: List of message dictionaries with "role" and "content"
            timeout: Request timeout in seconds

        Returns:
            Dictionary with either:
            - {"status": "success", "content": "<response_text>"}
            - {"status": "error", "error": "<error_message>"}
        """
        # Prepare request payload
        if self.use_responses_api:
            # Responses API payload (simplified)
            data = {
                "model": self.model_name,
                "input": [{"role": "user", "content": messages[-1]["content"]}]
            }
        else:
            # Chat Completions API payload
            data = {
                "model": self.model_name,
                "messages": messages,
                "stream": False
            }

        try:
            # Make the API call
            response = self.session.post(
                url=self.endpoint,
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()

            # Extract content based on API type
            if self.use_responses_api:
                # Responses API format
                content = result.get("output_text", "")
            else:
                # Chat Completions format
                content = result["choices"][0]["message"]["content"]

            return {"status": "success", "content": content}

        except requests.exceptions.RequestException as e:
            # Capture server error details if available
            error_message = str(e)
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_message += f" | server: {e.response.text}"
            except Exception:
                pass

            return {"status": "error", "error": error_message}

    def close(self):
        """Close the session and release resources."""
        self.session.close()
