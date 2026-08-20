#!/usr/bin/env python3
"""Regenerate the profile card SVGs (generated/*.svg) with live GitHub stats.

Runs daily via .github/workflows/update-profile.yml.
Env: ACCESS_TOKEN (or GITHUB_TOKEN), USER_NAME (default: bibhuti9).
"""
import datetime as dt
import json
import os
import time
from pathlib import Path

import requests

USER = os.environ.get("USER_NAME", "bibhuti9")
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
API = "https://api.github.com/graphql"
ROOT = Path(__file__).parent
CACHE_FILE = ROOT / "cache" / "loc_cache.json"
TEMPLATE = ROOT / "templates" / "profile.svg.tmpl"
OUT_DIR = ROOT / "generated"

THEMES = {
    "dark_mode.svg": {
        "C_BG": "#0d1117", "C_BORDER": "#30363d", "C_ART": "#61dafb",
        "C_TITLE": "#58a6ff", "C_KEY": "#ffa657", "C_VAL": "#c9d1d9",
        "C_MUTED": "#8b949e", "C_ADD": "#3fb950", "C_DEL": "#f85149",
    },
    "light_mode.svg": {
        "C_BG": "#ffffff", "C_BORDER": "#d0d7de", "C_ART": "#087ea4",
        "C_TITLE": "#0969da", "C_KEY": "#953800", "C_VAL": "#24292f",
        "C_MUTED": "#57606a", "C_ADD": "#1a7f37", "C_DEL": "#cf222e",
    },
}


def gql(query: str, variables: dict) -> dict:
    last = None
    for attempt in range(5):
        try:
            r = requests.post(
                API,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"bearer {TOKEN}"},
                timeout=60,
            )
            last = f"{r.status_code} {r.text[:200]}"
            if r.status_code == 200:
                payload = r.json()
                if "errors" not in payload:
                    return payload["data"]
        except requests.RequestException as e:
            last = str(e)
        time.sleep(2**attempt)
    raise RuntimeError(f"GraphQL failed after retries: {last}")


def get_user() -> dict:
    q = """
    query($login: String!) {
      user(login: $login) {
        id
        createdAt
        followers { totalCount }
        repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST], first: 1) { totalCount }
      }
    }"""
    return gql(q, {"login": USER})["user"]


def get_repos() -> list[dict]:
    q = """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        repositories(first: 100, after: $cursor, ownerAffiliations: [OWNER],
                     privacy: PUBLIC, isFork: false) {
          pageInfo { hasNextPage endCursor }
          nodes { name stargazerCount pushedAt defaultBranchRef { name } }
        }
      }
    }"""
    repos, cursor = [], None
    while True:
        page = gql(q, {"login": USER, "cursor": cursor})["user"]["repositories"]
        repos.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return repos
        cursor = page["pageInfo"]["endCursor"]


def repo_loc(name: str, user_id: str) -> dict:
    q = """
    query($owner: String!, $name: String!, $id: ID!, $cursor: String, $page: Int!) {
      repository(owner: $owner, name: $name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(author: {id: $id}, first: $page, after: $cursor) {
                pageInfo { hasNextPage endCursor }
                totalCount
                nodes { additions deletions }
              }
            }
          }
        }
      }
    }"""
    add = rm = commits = 0
    cursor, page_size = None, 100
    while True:
        try:
            data = gql(q, {"owner": USER, "name": name, "id": user_id,
                           "cursor": cursor, "page": page_size})
        except RuntimeError:
            if page_size > 25:  # big commits can exceed query cost; retry smaller
                page_size = 25
                continue
            raise
        ref = data["repository"]["defaultBranchRef"]
        if ref is None:
            return {"add": 0, "del": 0, "commits": 0}
        hist = ref["target"]["history"]
        commits = hist["totalCount"]
        for n in hist["nodes"]:
            add += n["additions"]
            rm += n["deletions"]
        if not hist["pageInfo"]["hasNextPage"]:
            return {"add": add, "del": rm, "commits": commits}
        cursor = hist["pageInfo"]["endCursor"]


def fmt(n: int) -> str:
    return f"{n:,}"


def relative(start: dt.datetime, now: dt.datetime) -> str:
    years, months, days = (now.year - start.year, now.month - start.month,
                           now.day - start.day)
    if days < 0:
        months -= 1
        days += (now.replace(day=1) - dt.timedelta(days=1)).day
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months, {days} days"


def main() -> None:
    user = get_user()
    repos = get_repos()
    cache = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}

    add = rm = commits = 0
    for i, repo in enumerate(repos, 1):
        name = repo["name"]
        cached = cache.get(name)
        if cached is None or cached["pushed_at"] != repo["pushedAt"]:
            try:
                loc = repo_loc(name, user["id"])
            except RuntimeError as e:
                print(f"  ! {name}: {e}")
                loc = cached or {"add": 0, "del": 0, "commits": 0}
            cache[name] = {"pushed_at": repo["pushedAt"], **{k: loc[k] for k in ("add", "del", "commits")}}
            print(f"  [{i}/{len(repos)}] {name}: {loc['commits']} commits")
        add += cache[name]["add"]
        rm += cache[name]["del"]
        commits += cache[name]["commits"]

    cache = {k: v for k, v in cache.items() if k in {r["name"] for r in repos}}
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=1))

    now = dt.datetime.now(dt.timezone.utc)
    created = dt.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    stats = {
        "UPTIME": relative(created, now),
        "REPOS": fmt(len(repos)),
        "CONTRIBUTED": fmt(user["repositoriesContributedTo"]["totalCount"]),
        "STARS": fmt(sum(r["stargazerCount"] for r in repos)),
        "COMMITS": fmt(commits),
        "FOLLOWERS": fmt(user["followers"]["totalCount"]),
        "LOC_NET": fmt(add - rm),
        "LOC_ADD": fmt(add),
        "LOC_DEL": fmt(rm),
        "UPDATED": now.strftime("%Y-%m-%d %H:%M UTC"),
    }

    template = TEMPLATE.read_text()
    OUT_DIR.mkdir(exist_ok=True)
    for filename, theme in THEMES.items():
        svg = template
        for key, value in {**theme, **stats}.items():
            svg = svg.replace("{{" + key + "}}", value)
        (OUT_DIR / filename).write_text(svg)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
