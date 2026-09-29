"""Static-page contracts: usable navigation and evidence without JavaScript."""

from html.parser import HTMLParser
from pathlib import Path


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.tags = []
        self.named_images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if attrs.get("role") == "img":
            self.named_images.append(
                attrs.get("aria-label") or attrs.get("aria-labelledby")
            )
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))


def test_project_page_navigation_and_evidence_work_without_scripts():
    source = Path(__file__).resolve().parents[1] / "docs" / "index.html"
    html = source.read_text(encoding="utf-8")
    page = Page()
    page.feed(html)

    assert "main" in page.tags
    assert "script" not in page.tags
    assert page.tags.count("h1") == 1
    assert len(page.ids) == len(set(page.ids))
    for section in ("main", "system", "evidence", "quickstart"):
        assert section in page.ids
        assert f"#{section}" in page.links
    for link in page.links:
        assert link
        if link.startswith("#"):
            assert link[1:] in page.ids
    assert any("final-mechanism-decision" in link for link in page.links)


def test_both_signal_illustrations_have_accessible_names():
    expected_illustrations = 2  # Signal timeline and feature ranking.
    source = Path(__file__).resolve().parents[1] / "docs" / "index.html"
    page = Page()
    page.feed(source.read_text(encoding="utf-8"))
    assert len(page.named_images) == expected_illustrations
    assert all(page.named_images)
