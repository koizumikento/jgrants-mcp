import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence

import httpx

from .client import get_subsidy_detail, search_subsidies


def run_cli(argv: Sequence[str]) -> None:
    parser = ArgumentParser(prog="jgrants-mcp")
    commands = parser.add_subparsers(required=True)

    command = commands.add_parser("search-subsidies", argument_default=SUPPRESS)
    command.add_argument("--keyword", required=True)
    command.add_argument(
        "--sort",
        choices=["created_date", "acceptance_start_datetime", "acceptance_end_datetime"],
        default="acceptance_end_datetime",
    )
    command.add_argument("--order", choices=["ASC", "DESC"], default="ASC")
    command.add_argument("--acceptance", type=int, choices=[0, 1], default=1)
    command.add_argument("--industry")
    command.add_argument("--use-purpose", dest="use_purpose")
    command.add_argument("--target-number-of-employees", dest="target_number_of_employees")
    command.add_argument("--target-area-search", dest="target_area_search")
    command.set_defaults(handler=search_subsidies)

    command = commands.add_parser("get-subsidy-detail", argument_default=SUPPRESS)
    command.add_argument("--subsidy-id", required=True)
    command.add_argument("--version", choices=["v1", "v2"], default="v2")
    command.set_defaults(handler=get_subsidy_detail)

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    try:
        result = asyncio.run(handler(**arguments))
    except (ValueError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
