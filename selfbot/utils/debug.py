import ast
import asyncio
import inspect
import sys
import traceback


async def aexec(code: str, scopes: dict) -> any:
    body = ast.parse(code, "exec").body
    if body and isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(value=body[-1].value)

    name = "aexec"
    node = ast.Module(
        body=[
            ast.AsyncFunctionDef(
                name=name,
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg=key) for key in scopes],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[],
                ),
                body=body,
                decorator_list=[],
                returns=None,
                type_comments=[],
                type_params=[],
            )
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(node)

    temp = {}
    exec(compile(node, "<string>", "exec"), temp)

    coro = await temp[name](*scopes.values())
    return await coro if inspect.iscoroutine(coro) else coro


async def shell(cmd: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await proc.communicate()
        return (stdout + stderr).decode()
    finally:
        try:
            if not proc.returncode:
                proc.terminate()
        except ProcessLookupError:
            pass
        else:
            await proc.wait()


def fmtexc() -> str:
    exc = traceback.TracebackException(*sys.exc_info())
    fmt = exc.exc_type.__name__

    if exc._str:
        fmt += f":\n  {exc._str}"

    ftb = traceback.format_list(
        [
            frame
            for frame in exc.stack
            if not any(
                name in frame.filename for name in ["<string>", "/selfbot/", "/usr/"]
            )
        ]
    )

    if ftb:
        fmt += f"\n\nTraceback:\n{''.join(ftb)}"

    return fmt


def fmtsec(start: int) -> str:
    total = f"{(asyncio.get_event_loop().time() - start):.3f}".rstrip("0").rstrip(".")

    return f"{total} s"
