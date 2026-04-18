from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator

import httpx

logger = logging.getLogger("starlearn.llm")

from config import settings

_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


async def call_llm_async(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
) -> str:
    client = await get_http_client()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.xunfei_api_key}",
    }
    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }

    # Try xunfei first
    try:
        response = await client.post(settings.xunfei_api_url, headers=headers, json=payload)
        if response.status_code == 200:
            body = response.json()
            return body["choices"][0]["message"]["content"]
        # If not 200, try minimax fallback below
    except (httpx.TimeoutException, httpx.RequestError):
        # Try minimax fallback
        pass

    # Fallback to MiniMax
    fallback_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.minimax_api_key}",
    }
    fallback_payload = {
        "model": settings.minimax_model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }

    try:
        response = await client.post(
            f"{settings.minimax_api_url}/chat/completions",
            headers=fallback_headers,
            json=fallback_payload,
        )
    except httpx.TimeoutException:
        raise RuntimeError("大模型接口请求超时，请稍后重试")
    except httpx.RequestError as e:
        raise RuntimeError(f"无法连接大模型接口: {str(e)}")

    if response.status_code != 200:
        snippet = (response.text or "")[:800]
        raise RuntimeError(f"大模型接口返回 HTTP {response.status_code}。响应摘要: {snippet}")

    try:
        body = response.json()
    except ValueError:
        raise RuntimeError("大模型接口返回非 JSON，请检查服务地址与鉴权")

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        brief = json.dumps(body, ensure_ascii=False)[:600]
        raise RuntimeError(f"大模型响应格式异常，片段: {brief}")


async def call_llm_stream(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
) -> AsyncGenerator[str, None]:
    client = await get_http_client()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.xunfei_api_key}",
    }
    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "stream": True,
    }

    fallback_used = False
    xunfei_yielded_content = False
    try:
        async with client.stream("POST", settings.xunfei_api_url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                snippet = body.decode("utf-8", errors="replace")[:800]
                raise RuntimeError(f"大模型接口返回 HTTP {response.status_code}。响应摘要: {snippet}")

            async for line in response.aiter_lines():
                if not line or not line.strip():
                    continue

                if line.startswith("data: "):
                    data_str = line[6:].strip()
                elif line.startswith("data:"):
                    data_str = line[5:].strip()
                else:
                    data_str = line.strip()

                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    # 尝试多种响应格式兼容讯飞和OpenAI
                    content = None
                    # OpenAI格式: delta.content
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta:
                        content = delta.get("content")
                    # 讯飞格式: text字段
                    if not content:
                        choices = chunk.get("choices", [{}])
                        if choices:
                            first_choice = choices[0]
                            # 讯飞流式格式
                            content = first_choice.get("text")
                            # 标准OpenAI格式
                            if not content:
                                content = first_choice.get("message", {}).get("content")
                    # 讯飞非流式格式(可能在流式中出现)
                    if not content:
                        content = chunk.get("result") or chunk.get("text") or chunk.get("content")
                    if content:
                        xunfei_yielded_content = True
                        yield content
                except json.JSONDecodeError:
                    continue
                except (KeyError, IndexError, TypeError):
                    continue

    except (httpx.TimeoutException, httpx.RequestError, RuntimeError):
        fallback_used = True

    # 如果讯飞没有返回任何内容，尝试 minimax fallback
    if not xunfei_yielded_content:
        fallback_used = True

    # Fallback to MiniMax if xunfei failed
    if fallback_used:
        fallback_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.minimax_api_key}",
        }
        fallback_payload = {
            "model": settings.minimax_model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "stream": True,
        }

        try:
            async with client.stream("POST", f"{settings.minimax_api_url}/chat/completions", headers=fallback_headers, json=fallback_payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    snippet = body.decode("utf-8", errors="replace")[:800]
                    yield f"\n\n[系统提示: MiniMax接口也返回 HTTP {response.status_code}。响应摘要: {snippet}]"
                    return

                async for line in response.aiter_lines():
                    if not line or not line.strip():
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                    else:
                        data_str = line.strip()

                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
                    except (KeyError, IndexError, TypeError):
                        continue

        except httpx.TimeoutException:
            yield "\n\n[系统提示: 大模型响应超时，请稍后重试]"
        except httpx.RequestError as e:
            yield f"\n\n[系统提示: 网络连接异常 - {str(e)}]"
        except RuntimeError as e:
            yield f"\n\n[系统提示: {str(e)}]"


async def call_llm_stream_with_log(
    system_prompt: str,
    user_prompt: str,
    agent_name: str = "generator",
    temperature: float = 0.3,
) -> AsyncGenerator[dict, None]:
    yield {"type": "log", "message": f"[{agent_name}] 正在调用大模型生成内容..."}

    full_text = ""
    chunk_count = 0
    start_time = time.time()

    try:
        async for chunk in call_llm_stream(system_prompt, user_prompt, temperature):
            full_text += chunk
            chunk_count += 1
            yield {"type": "content_chunk", "content": chunk}

            if chunk_count % 20 == 0:
                elapsed = int((time.time() - start_time) * 1000)
                yield {"type": "log", "message": f"[{agent_name}] 已生成 {len(full_text)} 字 ({elapsed}ms)"}

    except Exception as e:
        yield {"type": "log", "message": f"[{agent_name}] 生成异常: {str(e)}"}
        if not full_text:
            yield {"type": "text", "content": f"内容生成失败: {str(e)}"}

    elapsed = int((time.time() - start_time) * 1000)
    yield {"type": "log", "message": f"[{agent_name}] 生成完毕 | 共 {len(full_text)} 字 | 耗时 {elapsed}ms"}
    yield {"type": "done", "full_text": full_text, "agent_name": agent_name, "elapsed_ms": elapsed}
