#!/usr/bin/env python3
"""
API utility functions for OpenAI integration.

This module handles:
- Secure API key loading from .credentials/openai.key
- OpenAI client creation
- Common API patterns
"""

import os
from pathlib import Path
from openai import OpenAI


def load_openai_key():
    """
    Load OpenAI API key from .credentials/openai.key

    Returns:
        str: OpenAI API key

    Raises:
        FileNotFoundError: If .credentials/openai.key doesn't exist
        ValueError: If key file is empty
    """
    key_path = Path('.credentials/openai.key')

    if not key_path.exists():
        raise FileNotFoundError(
            f"OpenAI API key not found at {key_path}\n"
            "Please create .credentials/openai.key with your API key"
        )

    with open(key_path, 'r') as f:
        api_key = f.read().strip()

    if not api_key:
        raise ValueError(f"OpenAI API key file {key_path} is empty")

    if not api_key.startswith('sk-'):
        raise ValueError(
            f"Invalid OpenAI API key format in {key_path}\n"
            "Expected key to start with 'sk-'"
        )

    return api_key


def create_openai_client():
    """
    Create OpenAI client with API key from .credentials/openai.key

    Returns:
        OpenAI: Configured OpenAI client
    """
    api_key = load_openai_key()
    return OpenAI(api_key=api_key)


def count_tokens_estimate(text):
    """
    Estimate token count for text (rough approximation).

    For accurate counts, use tiktoken library:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-5-nano")
        return len(enc.encode(text))

    Args:
        text (str): Text to count tokens for

    Returns:
        int: Estimated token count (1 token ≈ 4 chars)
    """
    return len(text) // 4


def format_system_prompt(task, examples=None):
    """
    Format a system prompt for consistent caching.

    Args:
        task (str): Task description
        examples (list, optional): List of example strings

    Returns:
        str: Formatted system prompt
    """
    prompt = f"You are an expert assistant helping with: {task}\n\n"

    if examples:
        prompt += "Examples:\n\n"
        for i, example in enumerate(examples, 1):
            prompt += f"Example {i}:\n{example}\n\n"

    prompt += "Provide accurate, high-quality responses following the examples above."

    return prompt
