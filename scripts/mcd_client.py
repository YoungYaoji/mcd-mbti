"""mcd-almanac 的麦当劳 MCP 客户端（仅依赖 Python 标准库）。

实现 MCP Streamable HTTP 协议的最小子集：
initialize -> notifications/initialized -> tools/list -> tools/call

用法：
    client = McDClient(token)
    client.initialize()
    tools = client.list_tools()
    data = client.call_tool("campaign-calendar", {})
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_URL = "https://mcp.mcd.cn"

# 按优先级尝试的协议版本；服务器不兼容时自动回退
PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]

# 单次调用的超时（秒）
DEFAULT_TIMEOUT = 30


class McpError(Exception):
    """MCP 调用失败。"""


class McDClient:
    """麦当劳 MCP（mcp.mcd.cn）最小客户端。"""

    def __init__(self, token: str, url: str = DEFAULT_URL, timeout: int = DEFAULT_TIMEOUT):
        if not token or not token.strip():
            raise McpError("缺少 MCP Token。请从 https://open.mcd.cn/mcp 申请，并通过环境变量 MCD_MCP_TOKEN 提供。")
        self.url = url.rstrip("/")
        self.token = token.strip()
        self.timeout = timeout
        self.session_id: str | None = None
        self.protocol_version: str | None = None
        self._id = 0
        self._initialized = False

    # ------------------------------------------------------------------ #
    # 底层传输
    # ------------------------------------------------------------------ #
    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _post(self, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        req.add_header("Authorization", f"Bearer {self.token}")
        if self.session_id:
            req.add_header("mcp-session-id", self.session_id)

        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            if exc.code == 401:
                raise McpError("MCP Token 无效或已过期（HTTP 401），请重新申请。")
            if exc.code == 429:
                raise McpError("触发限流（HTTP 429，每分钟最多 600 次请求），请稍后再试。")
            raise McpError(f"HTTP {exc.code}: {detail}")
        except urllib.error.URLError as exc:
            raise McpError(f"网络错误：{exc.reason}")

        sid = resp.headers.get("mcp-session-id")
        if sid:
            self.session_id = sid
        raw = resp.read().decode("utf-8", "replace")
        ctype = resp.headers.get("Content-Type", "")

        if "text/event-stream" in ctype:
            return self._parse_sse(raw)
        if not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise McpError(f"响应不是合法 JSON：{raw[:200]}") from exc

    @staticmethod
    def _parse_sse(raw: str) -> dict:
        """从 text/event-stream 中提取最后一个 JSON-RPC 消息。"""
        data_lines = [line[5:].strip() for line in raw.splitlines() if line.startswith("data:")]
        for chunk in reversed(data_lines):
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue
        raise McpError(f"无法解析 SSE 响应：{raw[:200]}")

    # ------------------------------------------------------------------ #
    # 协议方法
    # ------------------------------------------------------------------ #
    def initialize(self) -> dict:
        last_err: Exception | None = None
        for version in PROTOCOL_VERSIONS:
            payload = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": version,
                    "capabilities": {},
                    "clientInfo": {"name": "mcd-almanac", "version": "1.0.0"},
                },
            }
            try:
                resp = self._post(payload)
            except McpError as exc:
                last_err = exc
                continue
            if "error" in resp:
                last_err = McpError(str(resp["error"]))
                continue
            result = resp.get("result", {})
            self.protocol_version = result.get("protocolVersion", version)
            # 完成握手
            self._notify("notifications/initialized")
            self._initialized = True
            return result
        raise McpError(f"initialize 失败：{last_err}")

    def _notify(self, method: str, params: dict | None = None) -> None:
        payload: dict = {"jsonrpc": "2.0", "method": method}
        if params:
            payload["params"] = params
        self._post(payload)

    def _rpc(self, method: str, params: dict) -> dict:
        if not self._initialized:
            self.initialize()
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params}
        resp = self._post(payload)
        if "error" in resp:
            raise McpError(f"{method} 调用失败：{resp['error']}")
        return resp.get("result", {})

    def list_tools(self) -> list[dict]:
        return self._rpc("tools/list", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        """调用工具并返回解析后的 JSON（失败时返回 {"_raw": ...}）。"""
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        texts = [item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except (json.JSONDecodeError, TypeError):
            return {"_raw": joined}


def safe_call(client: McDClient, name: str, arguments: dict | None = None) -> tuple[dict | None, str | None]:
    """带容错的工具调用：返回 (data, error)。data 为 None 表示该工具本次不可用。"""
    try:
        return client.call_tool(name, arguments), None
    except McpError as exc:
        return None, str(exc)
