"""Bounded child processes with process-group cleanup, including cancellation."""

import asyncio
import os
import signal


async def run_process(
    argv: list[str], *, cwd: str, env: dict[str, str], timeout: int, max_bytes: int = 100000
) -> dict:
    process = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=(os.name == "posix"),
    )

    async def read_limited(stream):
        chunks, size = [], 0
        while chunk := await stream.read(4096):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("Child process exceeded output limit")
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")

    async def collect():
        stdout, stderr, code = await asyncio.gather(
            read_limited(process.stdout), read_limited(process.stderr), process.wait()
        )
        return {"exit_code": code, "stdout": stdout, "stderr": stderr}

    try:
        return await asyncio.wait_for(collect(), timeout)
    finally:
        # Children could remain after their parent exits; terminate the entire group.
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            elif process.returncode is None:
                process.kill()
        except ProcessLookupError:
            pass
        await process.wait()
