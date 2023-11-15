#!/usr/bin/python3
import requests
from bs4 import BeautifulSoup
import re
from typing import Self
from dataclasses import dataclass
from json import dumps
from argparse import ArgumentParser, SUPPRESS
from sys import exit, argv

__version__ = 1.0

@dataclass
class ExitCode:
    succ: int = 0
    fail: int = 1

@dataclass
class PurAurURL:
    page: int
    query: str
    query_by: str
    outdated: str
    sort_by: str
    sort_order: str
    per_page: int
    only_orphans: bool

@dataclass
class PurRpcURL:
    v: int
    arg: str

@dataclass
class PurType:
    # Search by
    with_name_desc: str = "nd"
    with_name_only: str = "n"
    with_package_base: str = "b"
    with_exact_name: str = "N"
    with_exact_pkg_base: str = "B"
    with_keywords: str = "k"
    with_maintainer: str = "m"
    with_co_maintainer: str = "c"
    with_maintainer_co_maintainer: str = "M"
    with_submitter: str = "s"

    # Flags
    only_all: str = ""
    only_flagged: str = "on"
    only_not_flagged: str = "off"

    # Sort by
    sort_name: str = "n"
    sort_votes: str = "v"
    sort_popularity: str = "p"
    sort_voted: str = "w"
    sort_notify: str = "o"
    sort_maintainer: str = "m"
    sort_last_modified: str = "l"

    # Sort order
    sort_ascending: str = "a"
    sort_descending: str = "d"

class Pur:
    aur_url: str = "https://aur.archlinux.org/packages"
    rpc_url: str = "https://aur.archlinux.org/rpc"

    """Create a formatted AUR URL with additional parameters.
       @type: private
    """
    def __make_aur_url__(self: Self, url: PurAurURL) -> str:
        if "on" not in url.outdated:
            if "off" not in url.outdated:
                if len(url.outdated) > 0:
                    raise ValueError("outdated member contains a non-deterministic string.")

        if url.only_orphans:
            orphans = "Orphans"
        else:
            orphans = "Go"

        return (
            "{:s}?O={:d}&SeB={:s}&K={:s}&outdated={:s}"
            "&SB={:s}&SO={:s}&PP={:d}&submit={:s}").format(
                self.aur_url, url.page, url.query_by, url.query,
                url.outdated, url.sort_by, url.sort_order, url.per_page,
                orphans
            )

    """Create a formatted RPC suggesion URL with parameters
       @type: private
    """
    def __make_rpc_url__(self: Self, url: PurRpcURL) -> str:
        # API version
        url.v = 5
        return f"{self.rpc_url}?v={url.v}&type=suggest&arg={url.arg}"

    """Create HTTP(s) request and parse the response HTML.
       @type: private
    """
    def __make_request__(self: Self, url: PurAurURL) -> BeautifulSoup:
        req = requests.get(self.__make_aur_url__(url))
        if req.status_code != 200:
            raise ValueError(f"Error: HTTP(s) request failed, error code: {req.status_code}")

        soup = BeautifulSoup(req.text, "html.parser")
        return soup

    """Find every section of HTML table and print them/
       @type: private
    """
    def __get_sub_section__(self: Self, url: PurAurURL, start: int, end: int = 7) -> str:
        soup = self.__make_request__(url)
        lst = soup.find_all("td")
        le = len(lst)
        data = []

        for i in range(start, le, end):
            data.append(f"{lst[i].text.strip()}\n")

        return "".join(data).rstrip()

    """Get a list of package names based on the query and the parameters."""
    """show_ln is unused"""
    def find_pkgs(self: Self, url: PurAurURL, show_ln: bool = False) -> str:
        soup = self.__make_request__(url)
        lst = soup.find_all("a", {
            "href": re.compile(r"/packages/[a-z|-]")
        })
        data = []

        if show_ln:
            i = 1
            for e in lst:
                data.append(f"{i}. {e.text.strip()}\n")
                i += 1
        else:
            for e in lst:
                data.append(f"{e.text.strip()}\n")

        if len(data) > 0:
            return "".join(data).rstrip()
        else:
            return f"No packages with name \"{url.query}\" were found"

    """Get a list of package versions based on the query and the parameters."""
    def find_versions(self: Self, url: PurAurURL) -> str:
        return self.__get_sub_section__(url, 1)

    """Get a list of package votes based on the query and the parameters"""
    def find_votes(self: Self, url: PurAurURL) -> str:
        return self.__get_sub_section__(url, 2)

    """Get a list of package popularity based on the query and the parameters"""
    def find_popularities(self: Self, url: PurAurURL) -> str:
        return self.__get_sub_section__(url, 3)

    """Get a list of package description based on the query and the parameters"""
    def find_descriptions(self: Self, url: PurAurURL) -> str:
        return self.__get_sub_section__(url, 4)

    """Get a list of package maintainers based on the query and the parameters"""
    def find_maintainers(self: Self, url: PurAurURL) -> str:
        return self.__get_sub_section__(url, 5)

    """Get a list of package last updated date based on the query and the parameters"""
    def find_last_updates(self: Self, url: PurAurURL) -> str:
        return self.__get_sub_section__(url, 6)

    """Dump a JSON response of the query. The response includes,
       package name, version, votes, popularity, description, maintainers,
       and last updates.
    """
    def get_json_dump(self: Self, url: PurAurURL) -> str:
        soup = self.__make_request__(url)
        lst = soup.find_all("a", {
            "href": re.compile(r"/packages/[a-z|-]")
        })

        dlst = soup.find_all("td")
        le = len(dlst)
        data = {}
        j = 0

        for i in range(1, le, 7):
            data[j] = {
                "package": lst[j].text.strip(),
                "version": dlst[i].text.strip(),
                "votes": dlst[i + 1].text.strip(),
                "popularity": dlst[i + 2].text.strip(),
                "description": dlst[i + 3].text.strip(),
                "maintainer": dlst[i + 4].text.strip(),
                "last_update": dlst[i + 5].text.strip()
            }
            j += 1

        # Dump as JSON format
        return dumps(data)

    """Get suggesions of a package search (20 results per query)"""
    def find_suggestions(self: Self, url: PurRpcURL) -> str:
        req = requests.get(self.__make_rpc_url__(url))
        json = req.json()
        data = []

        for e in json:
            data.append(f"{e}\n")

        return "".join(data).rstrip()

def usage() -> None:
    print(f"""Usage: pur [OPTION]... [QUERY]
Parameters:
  --page       specify the page number, you'd like to retrive the data
  --query      a query of an AUR package
  --query-by   set the search type
  --outdated   set the search, out-of-date, active, or both type of packages
  --sort-by    set on what basis package list would be sorted
  --sort-order set the order of the sort
  --per-page   set how many results, you'd like per page

Markers:
  --packages, --versions, --votes, --popularities, --descriptions,
  --maintainers, --last-updates

Others:
   --dump-json, --only-orphans, --usage

Full documentation <https://github.com/rilysh/pur>""")
    exit(ExitCode.succ)

def main() -> None:
    if len(argv) == 1:
        print("Error: No arguments were specified.")
        exit(ExitCode.fail)

    parser = ArgumentParser(add_help=False, usage=SUPPRESS)

    """Arguments"""
    parser.add_argument("--packages", action="store_true", dest="find_packages")
    parser.add_argument("--versions", action="store_true", dest="find_versions")
    parser.add_argument("--votes", action="store_true", dest="find_votes")
    parser.add_argument("--popularities", action="store_true", dest="find_popularities")
    parser.add_argument("--descriptions", action="store_true", dest="find_descriptions")
    parser.add_argument("--maintainers", action="store_true", dest="find_maintainers")
    parser.add_argument("--last-updates", action="store_true", dest="find_last_updates")
    parser.add_argument("--dump-json", action="store_true", dest="dump_json")
    parser.add_argument("--suggestions", action="store_true", dest="find_suggestions")

    parser.add_argument("--only-orphans", action="store_true", dest="only_orphans")
    parser.add_argument("--page", type=int)
    parser.add_argument("--query", type=str)
    parser.add_argument("--query-by", type=str)
    parser.add_argument("--outdated", type=str)
    parser.add_argument("--sort-by", type=str)
    parser.add_argument("--sort-order", type=str)
    parser.add_argument("--per-page", type=int)

    parser.add_argument("--usage", action="store_true", dest="usage")

    args = parser.parse_args()
    pur = Pur()

    if args.usage:
        usage()
        # Unreachable

    """Non-optional arguments"""
    if not args.query:
        print("Error: --query is missing.")
        exit(ExitCode.fail)

    """Command"""
    if args.find_suggestions:
        rurl = PurRpcURL(
            arg=args.query,
            v=5
        )
        print(pur.find_suggestions(rurl))
        exit(ExitCode.succ)

    """Non-optional arguments (required for other commands)"""
    if not args.query_by:
        print("Error: --query-by is missing.")
        exit(ExitCode.fail)

    """Optional arguments"""
    if not args.page:
        args.page = 0
    if not args.outdated:
        args.outdated = PurType.only_all
    if not args.sort_by:
        args.sort_by = PurType.sort_popularity
    if not args.sort_order:
        args.sort_order = PurType.sort_descending
    if not args.per_page:
        args.per_page = 10

    arg_orphans = True if args.only_orphans else False

    url = PurAurURL(
        page=args.page, query=args.query, query_by=args.query_by,
        outdated=args.outdated, sort_by=args.sort_by,
        sort_order=args.sort_order, per_page=args.per_page,
        only_orphans=arg_orphans
    )

    """Action types"""
    if args.find_packages:
        print(pur.find_pkgs(url))
    elif args.find_versions:
        print(pur.find_versions(url))
    elif args.find_votes:
        print(pur.find_votes(url))
    elif args.find_popularities:
        print(pur.find_popularities(url))
    elif args.find_descriptions:
        print(pur.find_descriptions(url))
    elif args.find_maintainers:
        print(pur.find_maintainers(url))
    elif args.find_last_updates:
        print(pur.find_last_updates(url))
    elif args.dump_json:
        print(pur.get_json_dump(url))
    else:
        print("Error: No action type was specified.")

if __name__ == "__main__":
    main()
