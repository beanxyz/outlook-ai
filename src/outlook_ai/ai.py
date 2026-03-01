"""AI processing module using Ollama."""

import json
import logging
import re
from typing import List, Optional, Dict, Any

import requests

from outlook_ai.models import (
    Email,
    EmailCategory,
    EmailClassification,
    ActionItem,
    Priority,
)
from outlook_ai.prompts import get_prompt, truncate_body
from outlook_ai.utils import truncate_string


logger = logging.getLogger(__name__)


class OllamaEmailAI:
    """Local LLM email processing using Ollama."""
    
    def __init__(
        self,
        model: str = "qwen2.5:14b",
        base_url: str = "http://localhost:11434",
        timeout: int = 60,
    ):
        """Initialize Ollama client.
        
        Args:
            model: Ollama model name
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
    
    def _call_api(
        self,
        prompt: str,
        stream: bool = False,
        temperature: float = 0.7,
    ) -> str:
        """Call Ollama API.
        
        Args:
            prompt: Input prompt
            stream: Whether to stream response
            temperature: Sampling temperature
            
        Returns:
            Model response text
        """
        endpoint = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "temperature": temperature,
            "format": "json",  # Request JSON for structured outputs
        }
        
        try:
            response = self._session.post(
                endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            if stream:
                # Handle streaming response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            full_response += data.get("response", "")
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                return full_response
            else:
                # Handle non-streaming response
                data = response.json()
                return data.get("response", "")
                
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running."
            )
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Ollama API error: {e}")
    
    def _call_api_raw(
        self,
        prompt: str,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Call Ollama API without JSON format (for free-form text).
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            
        Returns:
            Full API response
        """
        endpoint = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
        }
        
        try:
            response = self._session.post(
                endpoint,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running."
            )
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Ollama API error: {e}")
    
    def summarize(self, email: Email) -> str:
        """Generate summary for a single email.
        
        Args:
            email: Email object
            
        Returns:
            Summary text
        """
        body = truncate_body(email.body_text, max_length=2000)
        
        prompt = get_prompt(
            "summarize",
            sender=email.sender,
            date=email.date.strftime("%Y-%m-%d %H:%M"),
            subject=email.subject,
            body=body,
        )
        
        try:
            response = self._call_api_raw(prompt, temperature=0.3)
            return response.get("response", "").strip()
        except Exception as e:
            logger.error(f"Failed to summarize email: {e}")
            return f"摘要生成失败: {e}"
    
    def batch_summarize(self, emails: List[Email], max_emails: int = 10) -> str:
        """Generate summary for multiple emails.
        
        Args:
            emails: List of Email objects
            max_emails: Maximum number of emails to process
            
        Returns:
            Batch summary text
        """
        # Format email list for the prompt
        emails_content = []
        # Truncate to 400 chars per email to fit in 4K context
        for i, email in enumerate(emails[:max_emails], 1):
            body_preview = truncate_string(email.body_text, 400)
            emails_content.append(
                f"""
--- 邮件 {i} ---
发件人: {email.sender}
主题: {email.subject}
日期: {email.date.strftime("%Y-%m-%d %H:%M")}
正文预览: {body_preview}
"""
            )
        
        prompt = get_prompt(
            "batch_summarize",
            emails_content="\n".join(emails_content),
        )
        
        try:
            response = self._call_api_raw(prompt, temperature=0.3)
            return response.get("response", "").strip()
        except Exception as e:
            logger.error(f"Failed to generate batch summary: {e}")
            return f"批量摘要生成失败: {e}"
    
    def _classify_by_rules(self, email: Email) -> EmailClassification:
        """Classify email using simple keyword rules (fast fallback)."""
        from outlook_ai.config import get_config
        
        config = get_config()
        sender = email.sender.lower()
        subject = email.subject.lower()
        body = email.body_text.lower()[:500]
        
        # Check for spam/promotion (use configurable keywords)
        if any(kw in sender or kw in subject for kw in config.spam_keywords):
            return EmailClassification(
                category=EmailCategory.SPAM,
                priority=Priority.LOW,
                reason="垃圾邮件/赌博推广",
            )
        
        # Check for bills (use configurable keywords)
        if any(kw in body for kw in config.bill_keywords):
            return EmailClassification(
                category=EmailCategory.BILL,
                priority=Priority.HIGH,
                reason="账单/付款通知",
            )
        
        # Check for work emails (use configurable keywords)
        if any(kw in sender for kw in config.work_keywords):
            return EmailClassification(
                category=EmailCategory.WORK,
                priority=Priority.MEDIUM,
                reason="LinkedIn招聘邮件",
            )
        
        # Check for notifications (use configurable keywords)
        if any(kw in sender for kw in config.notification_senders):
            return EmailClassification(
                category=EmailCategory.NOTIFICATION,
                priority=Priority.MEDIUM,
                reason="账户通知",
            )
        
        # Default
        return EmailClassification(
            category=EmailCategory.PERSONAL,
            priority=Priority.LOW,
            reason="个人邮件",
        )
    
    def classify(self, email: Email) -> EmailClassification:
        """Classify an email.
        
        Args:
            email: Email object
            
        Returns:
            EmailClassification object
        """
        # Use fast rule-based classification
        return self._classify_by_rules(email)
    
    def draft_reply(self, email: Email, intent: str = "") -> str:
        """Draft a reply to an email.
        
        Args:
            email: Email object
            intent: User's intent for the reply
            
        Returns:
            Draft reply text
        """
        body = truncate_body(email.body_text, max_length=2000)
        
        prompt = get_prompt(
            "draft_reply",
            sender=email.sender,
            subject=email.subject,
            body=body,
            intent=intent or "请帮我草拟一封合适的回复",
        )
        
        try:
            response = self._call_api_raw(prompt, temperature=0.7)
            return response.get("response", "").strip()
        except Exception as e:
            logger.error(f"Failed to draft reply: {e}")
            return f"回复草拟失败: {e}"
    
    def extract_action_items(self, emails: List[Email]) -> List[ActionItem]:
        """Extract action items from emails.
        
        Args:
            emails: List of Email objects
            
        Returns:
            List of ActionItem objects
        """
        # Format email list for the prompt
        emails_content = []
        for email in emails[:10]:  # Limit to 10 emails
            body_preview = truncate_string(email.body_text, 500)
            emails_content.append(
                f"""
--- 邮件 ---
发件人: {email.sender}
主题: {email.subject}
日期: {email.date.strftime("%Y-%m-%d")}
正文: {body_preview}
"""
            )
        
        prompt = get_prompt(
            "extract_actions",
            emails_content="\n".join(emails_content),
        )
        
        try:
            response = self._call_api(prompt, temperature=0.3)
            
            # Try to parse JSON array
            try:
                data = json.loads(response)
                if isinstance(data, list):
                    items = []
                    for item in data:
                        priority_str = item.get("priority", "medium")
                        priority = Priority(priority_str) if priority_str in ["high", "medium", "low"] else Priority.MEDIUM
                        
                        items.append(ActionItem(
                            task=item.get("task", ""),
                            deadline=item.get("deadline"),
                            from_email_subject=item.get("from_email_subject"),
                            priority=priority,
                        ))
                    return items
            except json.JSONDecodeError:
                # Try to extract JSON array from response
                json_match = re.search(r"\[.*\]", response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    if isinstance(data, list):
                        items = []
                        for item in data:
                            priority_str = item.get("priority", "medium")
                            priority = Priority(priority_str) if priority_str in ["high", "medium", "low"] else Priority.MEDIUM
                            
                            items.append(ActionItem(
                                task=item.get("task", ""),
                                deadline=item.get("deadline"),
                                from_email_subject=item.get("from_email_subject"),
                                priority=priority,
                            ))
                        return items
                
                logger.warning(f"Could not parse action items JSON: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to extract action items: {e}")
            return []
    
    def smart_search(
        self,
        query: str,
        emails: List[Email],
    ) -> List[Email]:
        """Semantic search for emails.
        
        Args:
            query: Search query
            emails: List of Email objects to search
            
        Returns:
            List of relevant Email objects
        """
        relevant_emails = []
        
        for email in emails:
            body_preview = truncate_string(email.body_text, 300)
            
            prompt = get_prompt(
                "smart_search",
                query=query,
                sender=email.sender,
                subject=email.subject,
                body_preview=body_preview,
            )
            
            try:
                response = self._call_api(prompt, temperature=0.3)
                
                # Try to parse JSON response
                try:
                    data = json.loads(response)
                    if data.get("relevant", False):
                        relevant_emails.append(email)
                except json.JSONDecodeError:
                    # Fallback: simple keyword matching
                    if query.lower() in email.subject.lower() or query.lower() in email.body_text.lower():
                        relevant_emails.append(email)
                        
            except Exception as e:
                logger.warning(f"Failed to check email relevance: {e}")
                # Fallback to simple matching
                if query.lower() in email.subject.lower() or query.lower() in email.body_text.lower():
                    relevant_emails.append(email)
        
        return relevant_emails
    
    def translate(self, email: Email, target_lang: str = "zh") -> str:
        """Translate email content.
        
        Args:
            email: Email object
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        lang_names = {
            "zh": "中文",
            "en": "English",
            "ja": "日本語",
            "ko": "한국어",
            "fr": "Français",
            "de": "Deutsch",
            "es": "Español",
        }
        
        target_lang_name = lang_names.get(target_lang, target_lang)
        body = truncate_body(email.body_text, max_length=2000)
        
        prompt = get_prompt(
            "translate",
            target_lang=target_lang_name,
            sender=email.sender,
            subject=email.subject,
            body=body,
        )
        
        try:
            response = self._call_api_raw(prompt, temperature=0.5)
            return response.get("response", "").strip()
        except Exception as e:
            logger.error(f"Failed to translate email: {e}")
            return f"翻译失败: {e}"
    
    def check_connection(self) -> bool:
        """Check if Ollama is accessible.
        
        Returns:
            True if connected
        """
        try:
            response = self._session.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[str]:
        """List available Ollama models.
        
        Returns:
            List of model names
        """
        try:
            response = self._session.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception:
            return []
