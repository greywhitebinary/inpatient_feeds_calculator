"""Checks for feed handling before it can replace public homepage content."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from update_writing import END, START, read_posts, render_posts, update_homepage


def item(title="Post", slug="post", date="Sat, 04 Jul 2026 06:14:36 GMT", **kwargs):
    link = kwargs.get("link", f"https://feedformflow.substack.com/p/{slug}")
    description = kwargs.get("description", "A short description.")
    return (
        f"<item><title>{title}</title><link>{link}</link><pubDate>{date}</pubDate>"
        f"<description>{description}</description></item>"
    )


def feed(*items):
    return ("<rss><channel>" + "".join(items) + "</channel></rss>").encode()


class WritingFeedTests(unittest.TestCase):
    def test_two_latest_unique_posts_and_local_date(self):
        posts = read_posts(
            feed(
                item("Old", "old", "Tue, 23 Jun 2026 21:34:17 GMT"),
                item("Latest", "latest"),
                item("Duplicate", "latest"),
                item("Older", "older", "Mon, 01 Jun 2026 12:00:00 GMT"),
            )
        )
        self.assertEqual([post[1] for post in posts], ["Latest", "Old"])
        self.assertIn('datetime="2026-07-03">3 July 2026', render_posts(posts))

    def test_unsafe_links_invalid_dates_and_future_posts_are_excluded(self):
        posts = read_posts(
            feed(
                item(link="javascript:alert(1)"),
                item(link="https://feedformflow.substack.com.evil.test/p/post"),
                item(date="invalid"),
                item(date="Sat, 04 Jul 2099 06:14:36 GMT"),
                item("Valid", "valid"),
            )
        )
        self.assertEqual([post[1] for post in posts], ["Valid"])

    def test_feed_markup_is_not_executable_and_long_summary_is_bounded(self):
        posts = read_posts(
            feed(
                item(
                    title="&lt;b&gt;Food &amp; care&lt;/b&gt;",
                    description="word " * 100,
                )
            )
        )
        rendered = render_posts(posts)
        self.assertIn("Food &amp; care", rendered)
        self.assertNotIn("<b>", rendered)
        self.assertLessEqual(len(posts[0][3]), 240)

    def test_update_preserves_the_rest_of_the_homepage(self):
        with TemporaryDirectory() as temp:
            home = Path(temp) / "index.html"
            home.write_text(f"Before {START}\nold\n{END} After", encoding="utf-8")
            update_homepage(home, feed(item()))
            result = home.read_text(encoding="utf-8")
            self.assertTrue(result.startswith(f"Before {START}"))
            self.assertTrue(result.endswith(f"{END} After"))
            update_homepage(home, feed(item()))
            self.assertEqual(home.read_text(encoding="utf-8"), result)

    def test_bad_feed_or_markers_do_not_destroy_existing_content(self):
        with TemporaryDirectory() as temp:
            home = Path(temp) / "index.html"
            for original, data in [
                (f"{START}original{END}", feed()),
                ("missing markers", feed(item())),
                (f"{END}wrong order{START}", feed(item())),
            ]:
                home.write_text(original, encoding="utf-8")
                with self.assertRaises(ValueError):
                    update_homepage(home, data)
                self.assertEqual(home.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
