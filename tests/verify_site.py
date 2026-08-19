from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGES = {
    "index.html",
    "datascrub.html",
    "nonprofitreports.html",
    "downloads.html",
    "support.html",
    "privacy-policy.html",
    "terms-of-service.html",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.images: list[tuple[str, str]] = []
        self.ids: list[str] = []
        self.title_depth = 0
        self.title = ""
        self.description = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag in {"img", "script", "link"}:
            source = values.get("src") or values.get("href")
            if source:
                self.links.append(source)
        if tag == "img":
            self.images.append((values.get("src", ""), values.get("alt", "")))
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "title":
            self.title_depth += 1
        if tag == "meta" and values.get("name", "").lower() == "description":
            self.description = values.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_depth:
            self.title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title += data


def is_external(value: str) -> bool:
    return value.startswith(("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "#"))


def local_target(page: Path, value: str) -> Path | None:
    if not value or is_external(value):
        return None
    path = unquote(urlsplit(value).path)
    if not path:
        return None
    target = (ROOT / path.lstrip("/")) if path.startswith("/") else (page.parent / path)
    target = target.resolve()
    if target.is_dir():
        target = target / "index.html"
    return target


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    failures: list[str] = []
    pages = sorted(ROOT.rglob("*.html"))
    for page in pages:
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        relative = page.relative_to(ROOT).as_posix()
        if relative in PUBLIC_PAGES:
            if not parser.title.strip():
                failures.append(f"{relative}: missing title")
            if not parser.description:
                failures.append(f"{relative}: missing meta description")
        if len(parser.ids) != len(set(parser.ids)):
            failures.append(f"{relative}: duplicate element id")
        for source, alt in parser.images:
            if not alt.strip():
                failures.append(f"{relative}: image without alt text ({source})")
        for value in parser.links:
            target = local_target(page, value)
            if target is not None and not target.exists():
                failures.append(f"{relative}: broken local reference {value}")

    for name in ("DataScrub", "NonprofitReports"):
        executable = ROOT / "downloads" / f"{name}.exe"
        sidecar = ROOT / "downloads" / f"{name}.exe.sha256"
        expected = sidecar.read_text(encoding="utf-8").split()[0].upper()
        actual = sha256(executable)
        if expected != actual:
            failures.append(f"{name}: SHA-256 sidecar does not match executable")

    stale_terms = (
        "DataScrub64-packed.xll",
        "NonprofitReports64-packed.xll",
        "Download the .xll",
        "Both products include a free 3-day trial",
        "100% Offline",
    )
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for term in stale_terms:
            if term.lower() in text.lower():
                failures.append(f"{page.relative_to(ROOT)}: stale copy '{term}'")

    if failures:
        raise SystemExit("SITE VERIFICATION FAILED\n" + "\n".join(f"- {item}" for item in failures))
    print(f"PASS: {len(pages)} HTML pages, local links, image text, executable hashes, and stale-copy checks.")


if __name__ == "__main__":
    main()
