"""Jira utilities for Claude Code integration.

Creates, updates, and transitions Jira issues in the KAN project.
Reads credentials from .env file (never hardcoded).

Usage from Claude Code:
    python3 scripts/jira_utils.py create --type Task --summary "Fix bug" --desc "Details"
    python3 scripts/jira_utils.py create --type Feature --summary "Add X" --labels backend,sr-calculator
    python3 scripts/jira_utils.py transition KAN-5 --status Done
    python3 scripts/jira_utils.py comment KAN-5 --text "Fixed in commit abc123"
    python3 scripts/jira_utils.py list --status "To Do"
"""

import argparse
import base64
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def _load_env() -> dict[str, str]:
    """Load .env from project root."""
    env_path = Path(__file__).parent.parent / ".env"
    env: dict[str, str] = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _headers(env: dict[str, str]) -> dict[str, str]:
    """Build auth headers."""
    creds = base64.b64encode(
        f"{env['CONFLUENCE_EMAIL']}:{env['CONFLUENCE_API_TOKEN']}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _api(env: dict[str, str], method: str, path: str, body: dict | None = None) -> dict:
    """Make a Jira API call."""
    url = f"https://{env['CONFLUENCE_URL']}/rest/api/3{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(env), method=method)
    try:
        resp = urllib.request.urlopen(req)
        raw = resp.read()
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Jira API error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)


def create_issue(
    env: dict[str, str],
    issue_type: str,
    summary: str,
    description: str = "",
    labels: list[str] | None = None,
    epic_key: str | None = None,
) -> str:
    """Create a Jira issue. Returns the issue key (e.g., KAN-42)."""
    fields: dict = {
        "project": {"key": env.get("JIRA_PROJECT_KEY", "KAN")},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }

    if description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}],
                }
            ],
        }

    if labels:
        fields["labels"] = labels

    if epic_key:
        # Jira Cloud uses the "parent" field for epic links
        fields["parent"] = {"key": epic_key}

    result = _api(env, "POST", "/issue", {"fields": fields})
    key = result["key"]
    print(f"{key} https://{env['CONFLUENCE_URL']}/browse/{key}")
    return key


def transition_issue(env: dict[str, str], issue_key: str, target_status: str) -> None:
    """Transition an issue to a new status (e.g., 'In Progress', 'Done')."""
    # Get available transitions
    transitions = _api(env, "GET", f"/issue/{issue_key}/transitions")
    match = None
    for t in transitions.get("transitions", []):
        if t["name"].lower() == target_status.lower():
            match = t
            break

    if not match:
        available = [t["name"] for t in transitions.get("transitions", [])]
        print(f"Status '{target_status}' not found. Available: {available}", file=sys.stderr)
        sys.exit(1)

    _api(env, "POST", f"/issue/{issue_key}/transitions", {"transition": {"id": match["id"]}})
    print(f"{issue_key} -> {target_status}")


def add_comment(env: dict[str, str], issue_key: str, text: str) -> None:
    """Add a comment to an issue."""
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }
    }
    _api(env, "POST", f"/issue/{issue_key}/comment", body)
    print(f"Comment added to {issue_key}")


def list_issues(env: dict[str, str], status: str | None = None) -> list[dict]:
    """List issues in the project, optionally filtered by status."""
    project = env.get("JIRA_PROJECT_KEY", "KAN")
    jql = f"project = {project}"
    if status:
        jql += f' AND status = "{status}"'
    jql += " ORDER BY created DESC"

    result = _api(env, "POST", "/search/jql", {
        "jql": jql,
        "maxResults": 50,
        "fields": ["summary", "status", "issuetype", "labels"],
    })

    issues = []
    for issue in result.get("issues", []):
        fields = issue["fields"]
        i = {
            "key": issue["key"],
            "type": fields["issuetype"]["name"],
            "status": fields["status"]["name"],
            "summary": fields["summary"],
            "labels": fields.get("labels", []),
        }
        issues.append(i)
        labels_str = f" [{', '.join(i['labels'])}]" if i['labels'] else ""
        print(f"  {i['key']}  {i['status']:15s}  {i['type']:10s}  {i['summary']}{labels_str}")

    return issues


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jira CLI for Claude Code")
    sub = parser.add_subparsers(dest="command")

    # create
    c = sub.add_parser("create")
    c.add_argument("--type", default="Task", help="Issue type: Task, Feature, Bug, Story, Epic")
    c.add_argument("--summary", required=True)
    c.add_argument("--desc", default="")
    c.add_argument("--labels", default="", help="Comma-separated labels")
    c.add_argument("--epic", default=None, help="Parent epic key (e.g., KAN-10)")

    # transition
    t = sub.add_parser("transition")
    t.add_argument("issue_key")
    t.add_argument("--status", required=True, help="Target status: To Do, In Progress, Done")

    # comment
    m = sub.add_parser("comment")
    m.add_argument("issue_key")
    m.add_argument("--text", required=True)

    # list
    ls = sub.add_parser("list")
    ls.add_argument("--status", default=None)

    args = parser.parse_args()
    env = _load_env()

    if args.command == "create":
        labels = [l.strip() for l in args.labels.split(",") if l.strip()] if args.labels else None
        create_issue(env, args.type, args.summary, args.desc, labels, args.epic)
    elif args.command == "transition":
        transition_issue(env, args.issue_key, args.status)
    elif args.command == "comment":
        add_comment(env, args.issue_key, args.text)
    elif args.command == "list":
        list_issues(env, args.status)
    else:
        parser.print_help()
