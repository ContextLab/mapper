#!/usr/bin/env python3
"""
OpenAI Batch API utility functions.

This module handles:
- Batch request creation with prompt caching
- Batch submission and monitoring
- Result retrieval and parsing
- GPT-5-nano specific configurations
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI


def create_batch_request(
    requests: List[Dict[str, Any]],
    model: str = "gpt-5-nano",
    temperature: float = 0.7,
    max_tokens: int = 500,
    response_format: Optional[Dict] = None,
    system_prompt: Optional[str] = None
) -> List[str]:
    """
    Create batch request in JSONL format for OpenAI Batch API.

    Args:
        requests: List of request dicts with 'custom_id' and 'user_prompt' keys
        model: OpenAI model to use (default: gpt-5-nano)
        temperature: Sampling temperature (default: 0.7)
        max_tokens: Maximum tokens in response (default: 500)
        response_format: Optional JSON schema for structured outputs
        system_prompt: Optional system prompt (will be cached if provided)

    Returns:
        List of JSONL formatted request strings

    Example:
        >>> requests = [
        ...     {'custom_id': 'req-1', 'user_prompt': 'What is ATP?'},
        ...     {'custom_id': 'req-2', 'user_prompt': 'What is DNA?'}
        ... ]
        >>> jsonl_lines = create_batch_request(requests, system_prompt="You are a biology expert.")
    """
    jsonl_lines = []

    for req in requests:
        messages = []

        # Add system prompt if provided (for caching)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # Add user prompt
        messages.append({
            "role": "user",
            "content": req['user_prompt']
        })

        # Build request body
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add response format if provided
        if response_format:
            body["response_format"] = response_format

        # Create batch request in OpenAI format
        batch_request = {
            "custom_id": req['custom_id'],
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body
        }

        jsonl_lines.append(json.dumps(batch_request))

    return jsonl_lines


def submit_batch(
    client: OpenAI,
    jsonl_lines: List[str],
    description: str = "Knowledge map batch"
) -> str:
    """
    Submit batch request to OpenAI Batch API.

    Args:
        client: OpenAI client
        jsonl_lines: List of JSONL formatted requests
        description: Batch description for tracking

    Returns:
        str: Batch ID for monitoring
    """
    # Write JSONL to temporary file
    batch_file = Path(f'/tmp/batch_request_{int(time.time())}.jsonl')
    with open(batch_file, 'w') as f:
        f.write('\n'.join(jsonl_lines))

    # Upload file
    print(f"Uploading batch file ({len(jsonl_lines)} requests)...")
    with open(batch_file, 'rb') as f:
        file_response = client.files.create(
            file=f,
            purpose='batch'
        )

    # Submit batch
    print(f"Submitting batch (ID: {file_response.id})...")
    batch_response = client.batches.create(
        input_file_id=file_response.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"description": description}
    )

    print(f"✓ Batch submitted: {batch_response.id}")
    print(f"  Status: {batch_response.status}")

    # Clean up temp file
    batch_file.unlink()

    return batch_response.id


def wait_for_batch(
    client: OpenAI,
    batch_id: str,
    poll_interval: int = 60,
    timeout: Optional[int] = 3600
) -> Dict[str, Any]:
    """
    Wait for batch to complete, polling status periodically.

    Args:
        client: OpenAI client
        batch_id: Batch ID to monitor
        poll_interval: Seconds between status checks (default: 60)
        timeout: Maximum seconds to wait (default: 3600 = 1 hour), None for no timeout

    Returns:
        Dict containing batch status and metadata

    Raises:
        TimeoutError: If batch doesn't complete within timeout
        RuntimeError: If batch fails
    """
    start_time = time.time()

    print(f"Waiting for batch {batch_id} to complete...")
    if timeout is None:
        print(f"Polling every {poll_interval}s (no timeout)")
    else:
        print(f"Polling every {poll_interval}s (timeout: {timeout}s)")
    print()

    while True:
        # Check timeout (if set)
        elapsed = time.time() - start_time
        if timeout is not None and elapsed > timeout:
            raise TimeoutError(
                f"Batch {batch_id} did not complete within {timeout}s"
            )

        # Get batch status
        batch = client.batches.retrieve(batch_id)

        status = batch.status
        print(f"Status: {status} (elapsed: {int(elapsed)}s)")

        if status == "completed":
            print(f"✓ Batch completed!")
            print(f"  Total requests: {batch.request_counts.total}")
            print(f"  Successful: {batch.request_counts.completed}")
            print(f"  Failed: {batch.request_counts.failed}")
            return {
                'batch_id': batch_id,
                'status': status,
                'output_file_id': batch.output_file_id,
                'request_counts': {
                    'total': batch.request_counts.total,
                    'completed': batch.request_counts.completed,
                    'failed': batch.request_counts.failed
                }
            }

        elif status == "failed":
            raise RuntimeError(
                f"Batch {batch_id} failed: {batch.errors}"
            )

        elif status in ["validating", "in_progress", "finalizing"]:
            # Still processing, wait and check again
            time.sleep(poll_interval)

        else:
            raise RuntimeError(
                f"Unexpected batch status: {status}"
            )


def download_batch_results(
    client: OpenAI,
    output_file_id: str,
    save_path: Optional[Path] = None
) -> List[str]:
    """
    Download batch results from OpenAI.

    Args:
        client: OpenAI client
        output_file_id: Output file ID from completed batch
        save_path: Optional path to save results (default: /tmp/batch_results_<timestamp>.jsonl)

    Returns:
        List of JSONL result lines
    """
    print(f"Downloading batch results (file: {output_file_id})...")

    # Download file content
    file_response = client.files.content(output_file_id)
    content = file_response.read()

    # Save to file if requested
    if save_path:
        with open(save_path, 'wb') as f:
            f.write(content)
        print(f"  ✓ Saved to {save_path}")

    # Parse JSONL lines
    lines = content.decode('utf-8').strip().split('\n')
    print(f"  ✓ Downloaded {len(lines)} results")

    return lines


def parse_batch_results(
    jsonl_lines: List[str],
    extract_json: bool = False
) -> Dict[str, Any]:
    """
    Parse batch results from JSONL format.

    Args:
        jsonl_lines: List of JSONL result lines
        extract_json: If True, parse JSON from response content (for structured outputs)

    Returns:
        Dict mapping custom_id to response content

    Example:
        >>> results = parse_batch_results(jsonl_lines, extract_json=True)
        >>> results['req-1']
        {'suitable': True, 'concepts': ['ATP', 'energy'], 'reasoning': '...'}
    """
    results = {}
    errors = {}

    for line in jsonl_lines:
        data = json.loads(line)
        custom_id = data['custom_id']

        # Check for errors
        if data.get('error'):
            errors[custom_id] = data['error']
            continue

        # Extract response
        response = data['response']
        if response['status_code'] != 200:
            errors[custom_id] = f"HTTP {response['status_code']}"
            continue

        # Get message content
        content = response['body']['choices'][0]['message']['content']

        # Parse JSON if requested (with retry logic)
        if extract_json:
            max_retries = 3
            parsed_content = None

            for attempt in range(max_retries):
                try:
                    parsed_content = json.loads(content)
                    break  # Success
                except json.JSONDecodeError as e:
                    if attempt < max_retries - 1:
                        # Retry - content might have formatting issues
                        # Try stripping whitespace and removing markdown code blocks
                        content = content.strip()
                        if content.startswith('```json'):
                            content = content[7:]
                        if content.startswith('```'):
                            content = content[3:]
                        if content.endswith('```'):
                            content = content[:-3]
                        content = content.strip()
                    else:
                        # Final attempt failed - skip this result
                        errors[custom_id] = f"JSON parse error after {max_retries} attempts: {e}"
                        break

            if parsed_content is not None:
                results[custom_id] = parsed_content
            # If still None after retries, the error was already logged
        else:
            results[custom_id] = content

    print(f"Parsed {len(results)} successful results, {len(errors)} errors")

    if errors:
        print(f"Errors:")
        for custom_id, error in list(errors.items())[:5]:
            print(f"  {custom_id}: {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")

    return results


def batch_with_cache(
    client: OpenAI,
    requests: List[Dict[str, Any]],
    system_prompt: str,
    description: str,
    model: str = "gpt-5-nano",
    temperature: float = 0.7,
    max_tokens: int = 500,
    response_format: Optional[Dict] = None,
    poll_interval: int = 60,
    timeout: Optional[int] = 3600
) -> Dict[str, Any]:
    """
    Complete batch workflow with prompt caching.

    This is a convenience function that:
    1. Creates batch request with cached system prompt
    2. Submits batch
    3. Waits for completion
    4. Downloads and parses results

    Args:
        client: OpenAI client
        requests: List of request dicts with 'custom_id' and 'user_prompt'
        system_prompt: System prompt (will be cached across requests)
        description: Batch description for tracking
        model: OpenAI model (default: gpt-5-nano)
        temperature: Sampling temperature
        max_tokens: Max tokens in response
        response_format: Optional JSON schema for structured outputs
        poll_interval: Status check interval in seconds
        timeout: Maximum wait time in seconds

    Returns:
        Dict mapping custom_id to response content
    """
    print(f"Starting batch workflow: {description}")
    print(f"  Requests: {len(requests)}")
    print(f"  Model: {model}")
    print(f"  System prompt: {len(system_prompt)} chars")
    print()

    # Step 1: Create batch request
    jsonl_lines = create_batch_request(
        requests=requests,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
        system_prompt=system_prompt
    )

    # Step 2: Submit batch
    batch_id = submit_batch(client, jsonl_lines, description)

    # Step 3: Wait for completion
    batch_info = wait_for_batch(client, batch_id, poll_interval, timeout)

    # Step 4: Download results
    result_lines = download_batch_results(client, batch_info['output_file_id'])

    # Step 5: Parse results
    extract_json = response_format is not None
    results = parse_batch_results(result_lines, extract_json=extract_json)

    print()
    print(f"✓ Batch workflow complete: {description}")
    print(f"  Results: {len(results)}/{len(requests)}")
    print()

    return results
