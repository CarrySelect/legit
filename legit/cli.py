import os
import sys
from pathlib import Path

import click

from legit.cmd_base import Base


CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 120,
}

def run_cmd(cmd_name: str, *args: str) -> None:
    from legit.command import Command

    argv: list[str] = ["legit", cmd_name, *args]
    
    print(f"argv is {argv}")

    cmd: Base = Command.execute(
        Path.cwd(),
        os.environ.copy(),
        argv,
        sys.stdin,
        sys.stdout,
        sys.stderr,
    )
    
    sys.exit(cmd.status)



@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("path", type=click.Path(file_okay=False, path_type=Path), required=False)
def init(path: Path | None) -> None:
    """Create an empty Legit repository in *PATH* (defaults to current dir)."""

    run_cmd("init", *(str(path),) if path is not None else ())


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
def add(paths: tuple[Path, ...]) -> None:
    """Add file contents of *PATHS* to the index (staging area)."""

    # Git treats “legit add” with no paths as an error; here we mimic that.
    if not paths:
        click.echo("error: pathspec required", err=True)
        raise SystemExit(1)

    run_cmd("add", *(str(p) for p in paths))


@cli.command()
@click.pass_context
def commit(ctx: click.Context) -> None:
    """Record changes to the repository using the message from *STDIN*."""

    if sys.stdin.isatty():
        click.echo("error: commit message required via stdin", err=True)
        ctx.exit(1)

    run_cmd("commit")


@cli.command()
@click.option("--porcelain", is_flag=True, help="Machine‑readable output.")
def status(porcelain: bool) -> None:
    """Show the working tree status."""

    run_cmd("status", *("--porcelain",) if porcelain else ())



@cli.command(name="diff")
@click.option("--cached", "--staged", is_flag=True, help="Compare index with HEAD.")
def diff_cmd(cached: bool) -> None:
    """Show changes between index/HEAD or index/worktree."""

    run_cmd("diff", *("--cached",) if cached else ())


@cli.command()
@click.argument("name", required=False)
@click.argument("start", required=False)
def branch(name: str | None, start: str | None) -> None:
    """Create *NAME* at *START* (defaults to HEAD)."""

    run_cmd("branch", *(name, start,) if start and name else ())


@cli.command()
@click.argument("target")
def checkout(target: str) -> None:
    """Switch branches or restore files."""

    run_cmd("checkout", target)


if __name__ == '__main__':
    cli()
