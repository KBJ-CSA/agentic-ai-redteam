"""
promptfoo custom provider that drives the vulnerable MCP server.

Why a custom provider instead of promptfoo's native `mcp` target?
  - It uses ONLY the Python standard library, so the promptfoo side needs no
    extra install and works on any promptfoo version.
  - It doubles as a readable reference for the MCP stdio/JSON-RPC wire format,
    which is exactly what you want to understand when red-teaming MCP.

promptfoo calls `call_api(prompt, options, context)` once per test row.
The `prompt` is a JSON string chosen by the test, e.g.:

    {"tool": "read_file", "args": {"path": "../../etc/passwd"}}

Special forms:
    {"op": "list"}                      -> return the server's tool catalog
                                           (surfaces poisoned descriptions)
    {"tool": "get_api_key", "args": {}} -> call a tool with arguments

The provider spawns the server, performs the MCP initialize handshake, runs
the requested operation, and returns the raw tool output as `output` so
promptfoo assertions can inspect it.
"""

import json
import subprocess
import sys
from pathlib import Path

PROTOCOL_VERSION = "2024-11-05"


class MCPStdioClient:
    """Minimal MCP client over stdio: newline-delimited JSON-RPC 2.0."""

    def __init__(self, command, args):
        self.proc = subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            cwd=str(Path(__file__).parent),
        )
        self._id = 0

    def _send(self, method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self._id += 1
            msg["id"] = self._id
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        if notify:
            return None
        return self._read_result(msg["id"])

    def _read_result(self, want_id):
        # Read lines until we see the response with our id (skip notifications).
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed the connection")
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("id") == want_id:
                if "error" in data:
                    raise RuntimeError(f"MCP error: {data['error']}")
                return data.get("result")

    def initialize(self):
        self._send(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "promptfoo-redteam", "version": "1.0"},
            },
        )
        self._send("notifications/initialized", notify=True)

    def list_tools(self):
        return self._send("tools/list", {})

    def call_tool(self, name, arguments):
        return self._send("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            self.proc.kill()


def _flatten(result):
    """Turn an MCP tools/call or tools/list result into plain text."""
    if result is None:
        return ""
    # tools/list -> {"tools": [{"name","description",...}, ...]}
    if isinstance(result, dict) and "tools" in result:
        return json.dumps(result["tools"], indent=2)
    # tools/call -> {"content": [{"type":"text","text": "..."}], ...}
    if isinstance(result, dict) and "content" in result:
        parts = []
        for item in result["content"]:
            parts.append(item.get("text", json.dumps(item)))
        return "\n".join(parts)
    return json.dumps(result)


def call_api(prompt, options, context):
    config = (options or {}).get("config", {}) or {}
    command = config.get("server_command", sys.executable)
    args = config.get("server_args", ["vulnerable_mcp_server.py"])

    try:
        request = json.loads(prompt)
    except json.JSONDecodeError:
        # Allow a bare tool name as a convenience: "get_api_key"
        request = {"tool": prompt.strip(), "args": {}}

    client = MCPStdioClient(command, args)
    try:
        client.initialize()
        if request.get("op") == "list":
            output = _flatten(client.list_tools())
        else:
            output = _flatten(
                client.call_tool(request["tool"], request.get("args", {}))
            )
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    finally:
        client.close()

    return {"output": output}
