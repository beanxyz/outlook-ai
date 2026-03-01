"""Prompt templates for AI email processing."""

from typing import Dict


PROMPTS: Dict[str, str] = {
    "summarize": """你是一个邮件助手。请用中文简洁总结以下邮件的关键信息。
包括：1) 发件人和主题 2) 核心内容 3) 是否需要回复或采取行动 4) 如有截止日期请标注

发件人：{sender}
日期：{date}
主题：{subject}
正文：
{body}

请用2-3句话总结：""",

    "batch_summarize": """你是一个邮件助手。请用中文总结以下多封邮件的整体内容。
按优先级分组，给出今日/近期邮件的整体概览。

邮件列表：
{emails_content}

请给出整体概览，包括：1) 重要邮件数量 2) 需要关注的事项 3) 需要采取的行动""",

    "classify": """Classify this email. Respond with ONLY valid JSON, no other text.

Categories: important, work, personal, subscription, promotion, spam, bill, notification

Email:
From: {sender}
Subject: {subject}
Body: {body_preview}

Output ONLY this JSON format:
{{"category": "category_name", "priority": "high|medium|low", "reason": "one sentence reason"}}

Respond with JSON only:""",

    "draft_reply": """你是邮件助手。根据以下邮件和用户意图，草拟一封回复。
语气要自然得体，长度适中。

原始邮件：
发件人：{sender}
主题：{subject}
正文：{body}

用户回复意图：{intent}

请草拟回复（只写正文，不需要称呼和落款）：""",

    "extract_actions": """从以下邮件中提取所有需要采取行动的事项。
只输出 JSON 数组，不要其他内容。

{emails_content}

输出格式：[{{"task": "...", "deadline": "...", "from_email_subject": "...", "priority": "high/medium/low"}}]""",

    "translate": """请将以下邮件翻译成{target_lang}。

发件人：{sender}
主题：{subject}
正文：
{body}

请翻译以上内容：""",

    "smart_search": """你是一个邮件搜索助手。判断以下邮件是否与用户查询相关。

用户查询：{query}

邮件信息：
发件人：{sender}
主题：{subject}
正文前300字：{body_preview}

请判断这封邮件是否与查询相关，并给出简要理由。
输出格式：{{"relevant": true/false, "reason": "简要理由"}}""",
}


def get_prompt(prompt_name: str, **kwargs) -> str:
    """Get a prompt template and fill in the variables.
    
    Args:
        prompt_name: Name of the prompt template
        **kwargs: Variables to fill in the template
        
    Returns:
        Filled prompt string
    """
    if prompt_name not in PROMPTS:
        raise ValueError(f"Unknown prompt: {prompt_name}")
    
    template = PROMPTS[prompt_name]
    return template.format(**kwargs)


def truncate_body(body: str, max_length: int = 2000) -> str:
    """Truncate email body to max length while preserving context.
    
    Args:
        body: Email body text
        max_length: Maximum length to truncate to
        
    Returns:
        Truncated body text
    """
    if len(body) <= max_length:
        return body
    
    # Keep the first part and some context from the end
    head_length = max_length - 500
    return body[:head_length] + "\n\n...[内容截断]...\n\n" + body[-500:]
