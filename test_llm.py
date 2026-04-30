# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 直接测试 LLM API 调用
from dotenv import load_dotenv
from project_paths import path_in_project
load_dotenv(path_in_project(".env"))

import openai

api_key = os.environ.get("Camera_Analyst_API_KEY", "")
base_url = os.environ.get("Camera_Analyst_BASE_URL", "")
model = os.environ.get("Camera_Analyst_MODEL", "")

print(f"API Key: {api_key[:20]}...")
print(f"Base URL: {base_url}")
print(f"Model: {model}")

client = openai.OpenAI(api_key=api_key, base_url=base_url)

print("\n发送测试请求...")
start = time.time()
try:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "说 hello"}],
        max_tokens=50,
        timeout=60
    )
    elapsed = time.time() - start
    print(f"成功! 耗时: {elapsed:.1f}秒")
    print(f"回复: {resp.choices[0].message.content}")
except Exception as e:
    elapsed = time.time() - start
    print(f"失败! 耗时: {elapsed:.1f}秒")
    print(f"错误: {e}")
