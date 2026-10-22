"""
Normalize Claude/Gemini chat export JSON to ordered turns
"""
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def normalize_chat_export(data: Any) -> Dict:
    """
    Detect and normalize chat export format.
    
    Supported formats:
    - Claude: list of {"type": "user"|"assistant", "message": {"content": ...}}
    - Generic: list of {"role": "user"|"assistant", "content": "..."}
    - Gemini: {"candidates": [{"content": {"parts": [{"text": ...}]}}]}
    - OpenAI/ChatGPT: {"messages": [...]}
    - Anthropic API: {"messages": [...], "system": ...}
    
    Returns:
        Dict with keys: turns (list of {role, text}), text (concatenated), 
        turn_count, format
    """
    turns = []
    format_detected = "unknown"
    
    # List formats first
    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        if isinstance(first, dict):
            if "type" in first and "message" in first:
                format_detected = "claude"
                turns = _normalize_claude(data)
            elif "role" in first and "content" in first:
                format_detected = "generic_list"
                turns = _normalize_generic_list(data)
    
    # Dict formats
    elif isinstance(data, dict):
        if "messages" in data and "system" in data:
            format_detected = "anthropic_api"
            turns = _normalize_anthropic_api(data)
        elif "messages" in data:
            format_detected = "openai"
            turns = _normalize_openai(data)
        elif "candidates" in data:
            format_detected = "gemini"
            turns = _normalize_gemini(data)
    
    if not turns:
        logger.warning(f"Unknown chat export format: {type(data)}")
        # Try to extract any text
        text = _extract_any_text(data)
        return {
            "turns": [],
            "text": text,
            "turn_count": 0,
            "format": "unknown",
        }
        return {
            "turns": [],
            "text": text,
            "turn_count": 0,
            "format": "unknown",
        }
    
    # Concatenate with role markers
    text_parts = []
    for turn in turns:
        role = turn["role"]
        content = turn["text"]
        if role == "user":
            text_parts.append(f"User: {content}")
        elif role == "assistant":
            text_parts.append(f"Assistant: {content}")
        else:
            text_parts.append(f"{role.capitalize()}: {content}")
    
    full_text = "\n\n".join(text_parts)
    
    return {
        "turns": turns,
        "text": full_text,
        "turn_count": len(turns),
        "format": format_detected,
    }


def _normalize_claude(data: List[Dict]) -> List[Dict]:
    """Normalize Claude export format"""
    turns = []
    
    for item in data:
        msg_type = item.get("type")
        message = item.get("message", {})
        
        # Skip tool_use and tool_result
        if msg_type in ("tool_use", "tool_result"):
            continue
        
        content = message.get("content", "")
        
        # Content can be string or list of blocks
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            content = "\n".join(text_parts)
        
        if not content:
            continue
        
        # Map type to role
        role = "user" if msg_type == "user" else "assistant"
        turns.append({"role": role, "text": content})
    
    return turns


def _normalize_gemini(data: Dict) -> List[Dict]:
    """Normalize Gemini export format"""
    turns = []
    
    candidates = data.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                text = part["text"]
                if text:
                    # Gemini doesn't always have clear role separation
                    # Assume alternating or infer from context
                    role = "assistant"  # Default
                    turns.append({"role": role, "text": text})
    
    return turns


def _normalize_openai(data: Dict) -> List[Dict]:
    """Normalize OpenAI/ChatGPT export format"""
    turns = []
    
    messages = data.get("messages", [])
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # Skip system messages and tool messages
        if role in ("system", "tool", "function"):
            continue
        
        if isinstance(content, list):
            # Handle content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            content = "\n".join(text_parts)
        
        if content:
            turns.append({"role": role, "text": content})
    
    return turns


def _normalize_anthropic_api(data: Dict) -> List[Dict]:
    """Normalize Anthropic API format (with system prompt)"""
    turns = []
    
    system = data.get("system", "")
    if system:
        turns.append({"role": "system", "text": system})
    
    messages = data.get("messages", [])
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            content = "\n".join(text_parts)
        
        if content:
            turns.append({"role": role, "text": content})
    
    return turns


def _normalize_generic_list(data: List[Dict]) -> List[Dict]:
    """Normalize generic list of {role, content}"""
    turns = []
    
    for item in data:
        role = item.get("role", "unknown")
        content = item.get("content", "")
        
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            content = "\n".join(text_parts)
        
        if content:
            turns.append({"role": role, "text": content})
    
    return turns


def _extract_any_text(data: Any) -> str:
    """Fallback: extract any text from unknown structure"""
    if isinstance(data, str):
        return data
    elif isinstance(data, dict):
        parts = []
        for v in data.values():
            parts.append(_extract_any_text(v))
        return "\n".join(parts)
    elif isinstance(data, list):
        parts = [_extract_any_text(item) for item in data]
        return "\n".join(parts)
    else:
        return str(data)


def save_normalized_json(
    data: Any,
    output_path: Path,
    source_path: Path = None
) -> Dict:
    """
    Normalize chat export and save to JSON file.
    
    Returns the normalized result dict.
    """
    result = normalize_chat_export(data)
    
    output = {
        "source_file": str(source_path) if source_path else None,
        "format": result["format"],
        "turn_count": result["turn_count"],
        "turns": result["turns"],
        "text": result["text"],
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.jsonnorm <json_file>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = normalize_chat_export(data)
    print(f"Format: {result['format']}")
    print(f"Turns: {result['turn_count']}")
    print(f"Text length: {len(result['text'])}")
    print(f"\nFirst 3 turns:")
    for turn in result['turns'][:3]:
        print(f"  {turn['role']}: {turn['text'][:100]}...")