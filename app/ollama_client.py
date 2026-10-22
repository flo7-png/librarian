"""
Minimal local Ollama wrapper for summarization
"""
import os
import logging
import json
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_SUMMARIZE_MODEL", "phi4-mini:3.8b")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "5m")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # seconds


@dataclass
class OllamaResponse:
    """Response from Ollama"""
    success: bool
    text: str = ""
    error: str = ""
    model: str = ""
    eval_count: int = 0
    eval_duration: int = 0


class OllamaClient:
    """Minimal Ollama client for local summarization"""
    
    def __init__(
        self,
        host: str = None,
        model: str = None,
        keep_alive: str = None,
        num_ctx: int = None,
        timeout: int = None
    ):
        self.host = host or OLLAMA_HOST
        self.model = model or OLLAMA_MODEL
        self.keep_alive = keep_alive or OLLAMA_KEEP_ALIVE
        self.num_ctx = num_ctx or OLLAMA_NUM_CTX
        self.timeout = timeout or OLLAMA_TIMEOUT
        self.base_url = self.host.rstrip('/')
    
    def _make_request(self, endpoint: str, payload: Dict) -> Dict:
        """Make a request to Ollama API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")
    
    def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.3,
        top_p: float = 0.9,
        max_tokens: int = 512
    ) -> OllamaResponse:
        """
        Generate text using Ollama.
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Max tokens to generate (approximate)
        
        Returns:
            OllamaResponse
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": self.num_ctx,
                "num_predict": max_tokens,
            },
            "keep_alive": self.keep_alive,
        }
        
        if system:
            payload["system"] = system
        
        try:
            result = self._make_request("/api/generate", payload)
            
            return OllamaResponse(
                success=True,
                text=result.get("response", "").strip(),
                model=result.get("model", self.model),
                eval_count=result.get("eval_count", 0),
                eval_duration=result.get("eval_duration", 0),
            )
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return OllamaResponse(
                success=False,
                error=str(e),
                model=self.model,
            )
    
    def summarize(
        self,
        text: str,
        max_length: int = 200,
        focus: str = None
    ) -> OllamaResponse:
        """
        Summarize a document.
        
        Args:
            text: Document text to summarize
            max_length: Target summary length in words
            focus: Optional focus area (e.g., "technical details", "action items")
        
        Returns:
            OllamaResponse with summary text
        """
        # Truncate text if too long for context window
        # Rough estimate: 1 token ~ 4 chars, leave room for prompt + response
        max_chars = (self.num_ctx - 1000) * 4
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[TRUNCATED]"
            logger.warning(f"Text truncated to {max_chars} chars for summarization")
        
        system_prompt = (
            "You are a precise summarizer. Create a concise, accurate summary "
            "of the provided document. Focus on key facts, decisions, and actionable information. "
            "Do not add information not present in the source."
        )
        
        focus_instruction = f"\nFocus on: {focus}" if focus else ""
        
        prompt = (
            f"Summarize the following document in approximately {max_length} words.{focus_instruction}\n\n"
            f"Document:\n{text}\n\n"
            f"Summary:"
        )
        
        return self.generate(
            prompt=prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=max_length * 2,  # Rough word-to-token conversion
        )
    
    def extract_key_points(self, text: str, max_points: int = 5) -> OllamaResponse:
        """Extract key points from a document"""
        max_chars = (self.num_ctx - 1000) * 4
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[TRUNCATED]"
        
        prompt = (
            f"Extract the {max_points} most important key points from this document. "
            f"Return as a numbered list.\n\n"
            f"Document:\n{text}\n\n"
            f"Key Points:"
        )
        
        return self.generate(
            prompt=prompt,
            system="You extract key points from documents. Be concise and accurate.",
            temperature=0.2,
            max_tokens=200,
        )
    
    def check_health(self) -> bool:
        """Check if Ollama is reachable"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> list:
        """List available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                return [m["name"] for m in response.json().get("models", [])]
        except Exception:
            pass
        return []


# Convenience functions
_default_client = None

def get_client() -> OllamaClient:
    """Get or create default client"""
    global _default_client
    if _default_client is None:
        _default_client = OllamaClient()
    return _default_client


def summarize_text(text: str, **kwargs) -> OllamaResponse:
    """Quick summarization using default client"""
    return get_client().summarize(text, **kwargs)


def extract_key_points(text: str, **kwargs) -> OllamaResponse:
    """Quick key point extraction using default client"""
    return get_client().extract_key_points(text, **kwargs)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    client = OllamaClient()
    
    if not client.check_health():
        print("ERROR: Ollama not reachable at", OLLAMA_HOST)
        sys.exit(1)
    
    print(f"Ollama reachable. Models: {client.list_models()}")
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.ollama_client <text_file> [max_words]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    max_words = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    result = client.summarize(text, max_length=max_words)
    if result.success:
        print(f"\nSummary ({result.eval_count} tokens):")
        print(result.text)
    else:
        print(f"Error: {result.error}")