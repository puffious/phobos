"""Minimal CLI for Phobos.

Provides basic commands without external dependencies:
- health: returns OK for quick sanity checks
- echo: prints a provided message
- version: shows a simple version string
"""

import argparse
import sys

VERSION = "0.0.0-dev"


def cmd_health(args: argparse.Namespace) -> int:
    print("OK")
    return 0


def cmd_echo(args: argparse.Namespace) -> int:
    print(args.message)
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    print(VERSION)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phobos", description="Phobos CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_health = sub.add_parser("health", help="Sanity check; prints OK")
    p_health.set_defaults(func=cmd_health)

    p_echo = sub.add_parser("echo", help="Echo a message")
    p_echo.add_argument("message", help="Message to print")
    p_echo.set_defaults(func=cmd_echo)

    p_version = sub.add_parser("version", help="Show CLI version")
    p_version.set_defaults(func=cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
