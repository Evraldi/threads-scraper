import argparse
import json
import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "automation-lab/threads-scraper")


def env_required(name):
    value = os.getenv(name)
    if not value:
        sys.exit(f"Missing {name}. Copy .env.example to .env and set it.")
    return value


def parse_queries(value):
    if os.path.isfile(value):
        with open(value, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return [q.strip() for q in value.split(",") if q.strip()]


def main():
    parser = argparse.ArgumentParser(description="Scrape Threads posts by keyword via Apify")
    parser.add_argument(
        "queries",
        help="Comma-separated keywords or path to a .txt file (one keyword per line)",
    )
    parser.add_argument("--max-posts", type=int, default=20, help="Max posts per search query (default 20)")
    parser.add_argument("--posted-after", default=None, help="ISO date/timestamp (e.g. 2026-05-01)")
    parser.add_argument("--posted-before", default=None, help="ISO date/timestamp (e.g. 2026-06-01)")
    parser.add_argument("--output", "-o", default="results.json", help="Output file (default results.json)")
    args = parser.parse_args()

    queries = parse_queries(args.queries)
    if not queries:
        sys.exit("No search queries provided.")

    run_input = {
        "mode": "search",
        "searchQueries": queries,
        "maxPosts": args.max_posts,
        "includeProfile": False,
    }
    if args.posted_after:
        run_input["postedAfter"] = args.posted_after
    if args.posted_before:
        run_input["postedBefore"] = args.posted_before

    client = ApifyClient(env_required("APIFY_API_TOKEN"))
    print(f"Running {ACTOR_ID} for queries: {queries}")
    run = client.actor(ACTOR_ID).call(run_input=run_input)

    if run.get("status") != "SUCCEEDED":
        sys.exit(f"Run failed with status: {run.get('status')}")

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(items)} posts to {args.output}")

    print("\n--- Preview (first 10) ---")
    for item in items[:10]:
        username = item.get("username") or item.get("username") or ""
        text = (item.get("text") or "")[:80].replace("\n", " ")
        likes = item.get("likeCount")
        url = item.get("url", "")
        print(f"@{username} | likes={likes} | {text} | {url}")


if __name__ == "__main__":
    main()
