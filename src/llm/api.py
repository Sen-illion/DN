# -*- coding: utf-8 -*-
"""LLM ????? JSON ???"""
import json
import os
import random
import re
import time
from typing import Dict

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from server.provider_control import log_provider_event, provider_request_slot, set_provider_backoff
from src.config import AI_API_CONFIG


@retry(
    stop=stop_after_attempt(15),
    wait=wait_exponential(multiplier=1, min=5, max=30),
    retry=(
        retry_if_exception_type(requests.exceptions.ConnectionError)
        | retry_if_exception_type(requests.exceptions.Timeout)
    ),
    reraise=True,
)
def call_ai_api(request_body: Dict) -> Dict:
    """?? AI API ?????????????????"""
    api_key = AI_API_CONFIG.get("api_key", "")
    base_url = AI_API_CONFIG.get("base_url", "")

    if not api_key:
        raise ValueError("API????????.env?????Camera_Analyst_API_KEY")
    if not base_url:
        raise ValueError("API??URL??????.env?????Camera_Analyst_BASE_URL")

    headers = {
        "Authorization": f"Bearer {api_key}" ,
        "Content-Type": "application/json; charset=utf-8" ,
    }

    connect_timeout = 30
    read_timeout = request_body.get("timeout")
    if read_timeout is not None and isinstance(read_timeout, (int, float)) and read_timeout > 0:
        read_timeout = int(read_timeout)
    else:
        read_timeout = AI_API_CONFIG.get("read_timeout", 180)
    timeout = (connect_timeout, read_timeout)

    if request_body.get("stream"):
        request_body = dict(request_body)
        request_body.pop("stream", None)
        print("?? Stream ?????????????")

    max_429_retries = max(1, int(os.getenv("LLM_429_MAX_RETRIES", "3")))
    base_wait = max(1.0, float(os.getenv("LLM_429_BASE_WAIT_SECONDS", "8")))
    request_type = request_body.get("request_type", "chat_completion")
    message_count = len(request_body.get("messages", []) or [])

    try:
        for attempt in range(max_429_retries):
            response = None
            with provider_request_slot(
                "llm",
                "yunwu",
                request_type,
                attempt=attempt + 1,
                message_count=message_count,
            ) as slot:
                request_started_at = time.time()
                print(f"?? ??API??... (????{connect_timeout}??????{read_timeout}??????{slot['queue_wait_ms']}ms)")
                response = requests.post(
                    url=f"{base_url}/chat/completions" ,
                    headers=headers,
                    json=request_body,
                    timeout=timeout,
                )
                latency_ms = int((time.time() - request_started_at) * 1000)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        wait_seconds = float(retry_after) if retry_after else 0.0
                    except (TypeError, ValueError):
                        wait_seconds = 0.0
                    if wait_seconds <= 0:
                        wait_seconds = min(60.0, base_wait * (2 ** attempt) + random.random())
                    set_provider_backoff(
                        "llm",
                        "yunwu",
                        wait_seconds,
                        reason="http_429",
                        request_type=request_type,
                        attempt=attempt + 1,
                    )
                    log_provider_event(
                        "llm",
                        "yunwu",
                        request_type,
                        "rate_limited",
                        attempt=attempt + 1,
                        retry_after=retry_after,
                        latency_ms=latency_ms,
                        queue_wait_ms=slot["queue_wait_ms"],
                        wait_seconds=round(wait_seconds, 2),
                    )
                    if attempt < max_429_retries - 1:
                        print(f"?? LLM ???? 429??? {wait_seconds:.1f} ?????{attempt + 1}/{max_429_retries}?")
                        continue

                response.raise_for_status()
                log_provider_event(
                    "llm",
                    "yunwu",
                    request_type,
                    "success",
                    attempt=attempt + 1,
                    latency_ms=latency_ms,
                    queue_wait_ms=slot["queue_wait_ms"],
                )
                print("? API????")
                return response.json()
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 0
        log_provider_event(
            "llm",
            "yunwu",
            request_type,
            "http_error",
            status_code=status_code,
            error=str(e)[:200],
        )
        if status_code in [401, 403]:
            print(f"? API?????HTTP {status_code}?????API???????")
            print("   ??API???")
            print(f"   - API??URL: {base_url}")
            print(f"   - API??: {'???' if api_key else '???'} (??: {len(api_key) if api_key else 0})")
            print(f"   - ??URL: {base_url}/chat/completions")
            print("   ??????.env????Camera_Analyst_API_KEY????")
            print("   ??????API??URL?Camera_Analyst_BASE_URL????????????URL???https://api.example.com/v1")
            if base_url and not base_url.startswith(("http://", "https://")):
                print("   ?? ???API??URL???????????http://?https://??")
            error_msg = (
                f"API?????HTTP {status_code}??????1) .env????Camera_Analyst_API_KEY???? "
                "2) API??????? 3) Camera_Analyst_BASE_URL????????????URL?"
            )
            raise ValueError(error_msg) from e
        print(f"?? API?????HTTP?? {status_code}???????{str(e)[:100]}")
        raise
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        log_provider_event(
            "llm",
            "yunwu",
            request_type,
            "transport_error",
            error=str(e)[:200],
        )
        print(f"?? API???????/??????????{str(e)[:100]}")
        print(f"   ?????? 1) ?????? {base_url}  2) ??????(HTTP_PROXY/HTTPS_PROXY)  3) ??????? 443")
        raise
    except Exception as e:
        log_provider_event(
            "llm",
            "yunwu",
            request_type,
            "unexpected_error",
            error=str(e)[:200],
        )
        print(f"?? API???????????{str(e)[:100]}")
        raise


def extract_and_validate_json(raw_text: str) -> str:
    """
    ????????JSON????????
    ?????AI??????????????????????
    """
    if not raw_text:
        return ""

    first_brace = raw_text.find('{')
    first_bracket = raw_text.find('[')
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
    elif first_bracket != -1:
        start_idx = first_bracket
    else:
        return ""

    cleaned_text = raw_text[start_idx:]

    if cleaned_text.startswith('{'):
        brace_count = 1
        end_idx = 1
        for i, char in enumerate(cleaned_text[1:], start=1):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
    else:
        bracket_count = 1
        end_idx = 1
        for i, char in enumerate(cleaned_text[1:], start=1):
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break

    json_str = cleaned_text[:end_idx]
    json_str = json_str.strip()
    json_str = json_str.replace("...", "")
    while json_str and json_str[-1] in [",", ";", ".", " ", "\n", "\t", '"', "'"]:
        json_str = json_str[:-1]
    json_str = json_str.replace("?", ":").replace("?", ",").replace("\u201c", '"').replace("\u201d", '"')
    json_str = re.sub(r'(?<=[{,\s])\s*([a-zA-Z0-9_\u4e00-\u9fa5]+)\s*:', r' "\1":', json_str)
    json_str = json_str.replace("'", '"')
    json_str = json_str.replace("True", "true").replace("False", "false").replace("None", "null")
    json_str = re.sub(r'\\"', '"', json_str)
    json_str = json_str.replace("\n", "\\n").replace("\t", "\\t")

    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        simple_json = json_str.replace(' ', '').replace('\n', '').replace('\t', '')
        try:
            json.loads(simple_json)
            return simple_json
        except json.JSONDecodeError:
            return json_str
    return json_str
