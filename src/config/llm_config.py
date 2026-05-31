import os
import random
import time
import openai
from dotenv import load_dotenv

load_dotenv()

# Per-call timeout (seconds). Caps single LLM call wall time so a hung gateway
# can't eat the whole 900s pipeline budget. Tunable via env.
_LLM_CALL_TIMEOUT = float(os.getenv("EBM_LLM_CALL_TIMEOUT", "90"))
_LLM_MAX_RETRIES = int(os.getenv("EBM_LLM_MAX_RETRIES", "3"))
# Long backoff for 429 rate-limit responses. Most gateways sliding-window over
# 60s+, so retrying after a few seconds just burns through the quota faster.
_LLM_RATE_LIMIT_BACKOFF = float(os.getenv("EBM_LLM_RATE_LIMIT_BACKOFF", "60"))
_LLM_RATE_LIMIT_MAX_RETRIES = int(os.getenv("EBM_LLM_RATE_LIMIT_MAX_RETRIES", "5"))

# Per-purpose client pool — each key gets its own openai.OpenAI instance with
# its own HTTP connection pool, preventing pipeline agents from blocking Judge/Scheduling.
_clients: dict[str, openai.OpenAI] = {}


def _get_client(purpose: str) -> openai.OpenAI:
    if purpose not in _clients:
        _clients[purpose] = openai.OpenAI(
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("LLM_API_KEY", ""),
            timeout=_LLM_CALL_TIMEOUT,
            max_retries=0,
        )
    return _clients[purpose]


# Transient errors worth retrying with exponential backoff. 5xx, connection
# drops, and read timeouts at the gateway layer are usually safe to retry; other
# 4xx (400 bad request, 401 auth) are not. 429 is retryable but uses a much
# longer dedicated backoff (see _call_with_retry).
_RETRYABLE_EXC = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)


def _retry_after_seconds(exc) -> float | None:
    """Pull a Retry-After value out of a RateLimitError, if the gateway supplied one."""
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    try:
        val = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
    except Exception:
        return None
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _call_with_retry(fn, label: str):
    last_exc = None
    rate_limit_attempts = 0
    for attempt in range(_LLM_MAX_RETRIES):
        try:
            return fn()
        except openai.RateLimitError as exc:
            last_exc = exc
            if rate_limit_attempts >= _LLM_RATE_LIMIT_MAX_RETRIES - 1:
                break
            rate_limit_attempts += 1
            # Sliding-window quotas reset over tens of seconds; short backoff just
            # consumes more quota slots. Respect Retry-After when present, else
            # use a long fixed backoff with light jitter.
            hinted = _retry_after_seconds(exc)
            backoff = hinted if hinted is not None else (_LLM_RATE_LIMIT_BACKOFF + random.uniform(0, 10))
            print(f"[LLM-RETRY] {label} rate-limited (429) attempt {rate_limit_attempts}/{_LLM_RATE_LIMIT_MAX_RETRIES}. Backing off {backoff:.1f}s")
            time.sleep(backoff)
        except _RETRYABLE_EXC as exc:
            last_exc = exc
            if attempt == _LLM_MAX_RETRIES - 1:
                break
            backoff = (2 ** attempt) + random.uniform(0, 0.5)
            print(f"[LLM-RETRY] {label} attempt {attempt + 1}/{_LLM_MAX_RETRIES} failed: {type(exc).__name__}: {exc}. Backing off {backoff:.1f}s")
            time.sleep(backoff)
    raise last_exc


class _LLMResponse:
    """Minimal response wrapper with .content attribute."""
    def __init__(self, content: str, usage=None, ttft=None, elapsed=None):
        self.content = content
        self.usage = usage
        self.ttft = ttft
        self.elapsed = elapsed


# Aggregate cache-hit telemetry across the session so we can confirm whether
# the upstream gateway supports OpenAI-style automatic prompt caching.
_cache_stats = {"calls": 0, "prompt_tokens": 0, "cached_tokens": 0}

# Per-purpose TTFT samples for streaming-mode runs.
_ttft_samples: dict[str, list[dict]] = {}


def get_cache_stats() -> dict:
    """Return a snapshot of per-session prompt-cache telemetry."""
    return dict(_cache_stats)


def get_ttft_samples() -> dict:
    """Return all TTFT samples grouped by purpose."""
    return {k: list(v) for k, v in _ttft_samples.items()}


class _LLMClient:
    """Thin wrapper around openai.OpenAI that mimics langchain's .invoke() interface.

    By default uses non-streaming (server returns a complete response). Streaming
    mode is available via env `EBM_STREAM_TTFT=1` for TTFT measurement, but it
    was observed that the huatuogpt.cn gateway can inject a literal string
    "[Error: Stream interrupted: NetworkError]" into a chunk when its upstream
    connection drops, which silently corrupts the response content. Production
    runs therefore stay on non-streaming."""

    def __init__(self, purpose: str, model: str, temperature: float):
        self._purpose = purpose
        self._model = model
        self._temperature = temperature

    def invoke(self, prompt) -> _LLMResponse:
        # Some Anthropic-compatible gateways (e.g. hk.oarel.com) reject role="system"
        # in the messages array — they expect the Anthropic Messages API shape where
        # `system` is a top-level parameter. Setting EBM_FOLD_SYSTEM_INTO_USER=1
        # concatenates system content into the first user message instead. Default ON
        # because it works on both gateway styles (the OpenAI ones treat the extra
        # prefix as ordinary user text and still hit prefix cache on the static part).
        fold_system = os.getenv("EBM_FOLD_SYSTEM_INTO_USER", "1") != "0"

        if isinstance(prompt, dict) and "system" in prompt and "user" in prompt:
            if fold_system:
                messages = [
                    {"role": "user", "content": f"{prompt['system']}\n\n{prompt['user']}"},
                ]
            else:
                # System+user split: maximizes prefix caching on the static portion.
                messages = [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ]
        elif isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            role_map = {"human": "user", "ai": "assistant", "system": "system"}
            converted = [
                {"role": role_map.get(getattr(m, "type", "user"), "user"), "content": m.content}
                for m in prompt
            ]
            if fold_system and converted and converted[0]["role"] == "system":
                sys_content = converted[0]["content"]
                rest = converted[1:]
                if rest and rest[0]["role"] == "user":
                    rest[0] = {"role": "user", "content": f"{sys_content}\n\n{rest[0]['content']}"}
                    messages = rest
                else:
                    messages = [{"role": "user", "content": sys_content}] + rest
            else:
                messages = converted
        else:
            messages = [{"role": "user", "content": str(prompt)}]

        if os.getenv("EBM_STREAM_TTFT") == "1":
            return self._invoke_streaming(messages)
        return self._invoke_blocking(messages)

    def _invoke_blocking(self, messages) -> _LLMResponse:
        t0 = time.time()
        resp = _call_with_retry(
            lambda: _get_client(self._purpose).chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                seed=42,
            ),
            label=f"{self._purpose}/blocking",
        )
        elapsed = time.time() - t0
        usage = getattr(resp, "usage", None)
        self._record_telemetry(usage, ttft=None, elapsed=elapsed)
        return _LLMResponse(
            resp.choices[0].message.content, usage=usage, ttft=None, elapsed=elapsed
        )

    def stream_reasoning(self, prompt, prefix: str = "") -> _LLMResponse:
        """Stream the LLM response, printing only the Reasoning section live.

        The LLM output format is:
            **JSON:** ```json {...} ```
            ---
            ### Reasoning: ...

        This method scans for a reasoning marker and streams that section to
        stdout in real time.  The full response (JSON + Reasoning) is returned
        in _LLMResponse.content so callers can parse JSON from it as usual.
        """
        fold_system = os.getenv("EBM_FOLD_SYSTEM_INTO_USER", "1") != "0"
        if isinstance(prompt, dict) and "system" in prompt and "user" in prompt:
            if fold_system:
                messages = [{"role": "user", "content": prompt["system"] + "\n\n" + prompt["user"]}]
            else:
                messages = [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ]
        elif isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = [{"role": "user", "content": str(prompt)}]

        t0 = time.time()
        ttft = None
        chunks: list[str] = []
        usage = None
        state = "SCAN"
        scan_buf = ""
        printed_prefix = False
        MARKERS = ("### Reasoning:", "**Reasoning:**", "---\n\n### Reasoning")
        # When printing Reasoning that comes BEFORE the JSON block, stop when we
        # hit the JSON fence so we don't dump the raw JSON to the console.
        JSON_FENCE = "**JSON:**"

        stream = _get_client(self._purpose).chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
            seed=42,
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta if chunk.choices[0] else None
                if delta is not None and getattr(delta, "content", None):
                    token = delta.content
                    if ttft is None:
                        ttft = time.time() - t0
                    chunks.append(token)
                    if state == "SCAN":
                        scan_buf += token
                        for marker in MARKERS:
                            if marker in scan_buf:
                                state = "PRINT"
                                after = scan_buf.split(marker, 1)[1]
                                if prefix and not printed_prefix:
                                    print(prefix, end="", flush=True)
                                    printed_prefix = True
                                if after:
                                    print(after, end="", flush=True)
                                scan_buf = ""
                                break
                        else:
                            if len(scan_buf) > 200:
                                scan_buf = scan_buf[-100:]
                    elif state == "PRINT":
                        if not printed_prefix:
                            if prefix:
                                print(prefix, end="", flush=True)
                            printed_prefix = True
                        # Stop printing if we hit the JSON block marker
                        scan_buf += token
                        if JSON_FENCE in scan_buf:
                            state = "DONE"
                            before_json = scan_buf.split(JSON_FENCE, 1)[0]
                            if before_json.strip():
                                print(before_json, end="", flush=True)
                            print()
                            scan_buf = ""
                        else:
                            if len(scan_buf) > len(JSON_FENCE) + 5:
                                print(scan_buf[:-len(JSON_FENCE)], end="", flush=True)
                                scan_buf = scan_buf[-len(JSON_FENCE):]
                    # state == "DONE": silently buffer the rest
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                usage = chunk_usage

        if state == "PRINT" and scan_buf.strip():
            print(scan_buf, end="", flush=True)
            print()
        elif state == "PRINT":
            print()

        elapsed = time.time() - t0
        content = "".join(chunks)
        self._record_telemetry(usage, ttft=ttft, elapsed=elapsed)
        return _LLMResponse(content, usage=usage, ttft=ttft, elapsed=elapsed)

    def _invoke_streaming(self, messages) -> _LLMResponse:
        t0 = time.time()
        ttft = None
        chunks: list[str] = []
        usage = None
        stream = _get_client(self._purpose).chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
            seed=42,
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta if chunk.choices[0] else None
                if delta is not None and getattr(delta, "content", None):
                    if ttft is None:
                        ttft = time.time() - t0
                    chunks.append(delta.content)
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                usage = chunk_usage
        elapsed = time.time() - t0
        content = "".join(chunks)
        self._record_telemetry(usage, ttft=ttft, elapsed=elapsed)
        return _LLMResponse(content, usage=usage, ttft=ttft, elapsed=elapsed)

    def _record_telemetry(self, usage, ttft, elapsed):
        prompt_tokens = 0
        cached = 0
        if usage is not None:
            _cache_stats["calls"] += 1
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            _cache_stats["prompt_tokens"] += prompt_tokens
            details = getattr(usage, "prompt_tokens_details", None)
            if details is not None:
                cached = getattr(details, "cached_tokens", 0) or 0
            elif isinstance(usage, dict):
                cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
            _cache_stats["cached_tokens"] += cached
        _ttft_samples.setdefault(self._purpose, []).append({
            "ttft": ttft,
            "elapsed": elapsed,
            "prompt_tokens": prompt_tokens,
            "cached_tokens": cached,
        })


def get_llm(temperature: float = 0.0, purpose: str = "agent") -> _LLMClient:
    return _LLMClient(
        purpose=purpose,
        model=os.getenv("LLM_MODEL", "gpt-4"),
        temperature=temperature,
    )


def get_fast_llm(temperature: float = 0.0, purpose: str = "fast") -> _LLMClient:
    return _LLMClient(
        purpose=purpose,
        model=os.getenv("FAST_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4")),
        temperature=temperature,
    )

