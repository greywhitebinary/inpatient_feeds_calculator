"""Render the two latest Substack posts into the static homepage before publishing."""

import argparse
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

FEED_URL = "https://feedformflow.substack.com/feed"
HOME = Path(__file__).resolve().parents[1] / "docs" / "index.html"
START = "<!-- writing-feed:start -->"
END = "<!-- writing-feed:end -->"
# Keep the approved editorial summaries for the existing articles.
SUMMARIES = {
    "https://feedformflow.substack.com/p/the-working-knowledge-behind-the": (
        "What building a regional menu generator taught me about AI, menu planning, "
        "and the work of making expertise explicit."
    ),
    "https://feedformflow.substack.com/p/feed-form-flow": (
        "Why inputs, forms and workflows are conditions of care."
    ),
}


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    parser = PlainText()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def read_posts(feed):
    root = ET.fromstring(feed)
    posts = []
    seen = set()
    now = datetime.now(timezone.utc)
    for item in root.findall("./channel/item"):
        title = plain_text(item.findtext("title", ""))
        link = item.findtext("link", "").strip()
        url = urlparse(link)
        if (
            not title
            or url.scheme != "https"
            or url.netloc != "feedformflow.substack.com"
            or not url.path.startswith("/p/")
            or link in seen
        ):
            continue
        try:
            published = parsedate_to_datetime(item.findtext("pubDate", ""))
        except (TypeError, ValueError, OverflowError):
            continue
        if published.tzinfo is None or published > now:
            continue
        summary = SUMMARIES.get(link, plain_text(item.findtext("description", "")))
        if len(summary) > 240:
            summary = summary[:237].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        posts.append((published, title, link, summary))
        seen.add(link)
    posts.sort(key=lambda post: post[0], reverse=True)
    if not posts:
        raise ValueError(
            "Feed has no valid published articles; homepage was not changed."
        )
    return posts[:2]


def render_posts(posts):
    articles = []
    for position, (published, title, link, summary) in enumerate(posts):
        kind = "lead" if position == 0 else "secondary"
        date = published.astimezone(ZoneInfo("America/Vancouver"))
        date_label = f"{date.day} {date.strftime('%B %Y')}"
        label = (
            "Read the first note"
            if link.endswith("/feed-form-flow")
            else "Read the piece"
        )
        articles.append(
            f'          <article class="fff-{kind}-note">\n'
            f'            <time datetime="{date.date().isoformat()}">{date_label}</time>\n'
            f'            <h3><a href="{escape(link, quote=True)}" target="_blank" '
            f'rel="noopener">{escape(title)}</a></h3>\n'
            f"            <p>{escape(summary)}</p>\n"
            f'            <a class="fff-text-link" href="{escape(link, quote=True)}" '
            f'target="_blank" rel="noopener">{label}</a>\n'
            "          </article>"
        )
    return (
        '        <div class="fff-writing-list">\n'
        + "\n".join(articles)
        + "\n        </div>"
    )


def update_homepage(homepage, feed):
    original = homepage.read_text(encoding="utf-8")
    if original.count(START) != 1 or original.count(END) != 1:
        raise ValueError("Expected one writing-feed region; homepage was not changed.")
    rendered = render_posts(read_posts(feed))
    updated, count = re.subn(
        re.escape(START) + r".*?" + re.escape(END),
        lambda _: f"{START}\n{rendered}\n        {END}",
        original,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError(
            "Writing-feed markers are out of order; homepage was not changed."
        )
    if updated != original:
        homepage.write_text(updated, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feed-file", type=Path, help="Read a saved RSS feed for local checks."
    )
    parser.add_argument("--homepage", type=Path, default=HOME)
    args = parser.parse_args()
    if args.feed_file:
        feed = args.feed_file.read_bytes()
    else:
        request = urllib.request.Request(
            FEED_URL, headers={"User-Agent": "FeedFormFlow-site/1.0"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            feed = response.read(2_000_001)
        if len(feed) > 2_000_000:
            raise ValueError("Feed exceeded the size limit; homepage was not changed.")
    update_homepage(args.homepage, feed)
    print("Homepage writing refreshed from Substack.")


if __name__ == "__main__":
    main()
