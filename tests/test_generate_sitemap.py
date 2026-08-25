"""Unit tests for generate_sitemap.py."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date

from pyscripts import load

generate_sitemap = load("generate_sitemap.py")
SITE_URL = generate_sitemap.SITE_URL


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<html></html>")


# ---------------------------------------------------------------------------
# find_html_files()
# ---------------------------------------------------------------------------

def test_root_index_html_maps_to_the_domain_root(tmp_path):
    _touch(tmp_path / "index.html")
    assert generate_sitemap.find_html_files(str(tmp_path)) == [f"{SITE_URL}/"]


def test_nested_index_html_maps_to_its_directory(tmp_path):
    _touch(tmp_path / "guides" / "index.html")
    urls = generate_sitemap.find_html_files(str(tmp_path))
    assert urls == [f"{SITE_URL}/guides/"]


def test_ordinary_page_maps_to_its_own_path(tmp_path):
    _touch(tmp_path / "about.html")
    urls = generate_sitemap.find_html_files(str(tmp_path))
    assert urls == [f"{SITE_URL}/about.html"]


def test_excluded_files_are_skipped(tmp_path):
    _touch(tmp_path / "404.html")
    _touch(tmp_path / "google7a99f5f52cfafe41.html")
    _touch(tmp_path / "real.html")
    urls = generate_sitemap.find_html_files(str(tmp_path))
    assert urls == [f"{SITE_URL}/real.html"]


def test_excluded_directories_are_not_descended_into(tmp_path):
    _touch(tmp_path / ".git" / "index.html")
    _touch(tmp_path / "node_modules" / "index.html")
    _touch(tmp_path / "real.html")
    urls = generate_sitemap.find_html_files(str(tmp_path))
    assert urls == [f"{SITE_URL}/real.html"]


def test_dot_directories_are_not_descended_into(tmp_path):
    _touch(tmp_path / ".github" / "workflows" / "ci.html")
    _touch(tmp_path / "real.html")
    urls = generate_sitemap.find_html_files(str(tmp_path))
    assert urls == [f"{SITE_URL}/real.html"]


def test_output_is_sorted_regardless_of_creation_order(tmp_path):
    _touch(tmp_path / "zebra.html")
    _touch(tmp_path / "apple.html")
    _touch(tmp_path / "mango.html")
    urls = generate_sitemap.find_html_files(str(tmp_path))
    assert urls == sorted(urls)
    assert urls == [f"{SITE_URL}/apple.html", f"{SITE_URL}/mango.html", f"{SITE_URL}/zebra.html"]


# ---------------------------------------------------------------------------
# build_sitemap()
# ---------------------------------------------------------------------------

def test_build_sitemap_includes_a_loc_and_todays_lastmod_per_url():
    xml_text = generate_sitemap.build_sitemap([f"{SITE_URL}/about.html"])
    assert f"<loc>{SITE_URL}/about.html</loc>" in xml_text
    assert f"<lastmod>{date.today().isoformat()}</lastmod>" in xml_text


def test_build_sitemap_output_is_well_formed_xml():
    xml_text = generate_sitemap.build_sitemap(
        [f"{SITE_URL}/", f"{SITE_URL}/about.html", f"{SITE_URL}/contact.html"]
    )
    root = ET.fromstring(xml_text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [el.text for el in root.findall("sm:url/sm:loc", ns)]
    assert locs == [f"{SITE_URL}/", f"{SITE_URL}/about.html", f"{SITE_URL}/contact.html"]


def test_build_sitemap_with_no_urls_is_still_well_formed_xml():
    xml_text = generate_sitemap.build_sitemap([])
    root = ET.fromstring(xml_text)
    assert root.tag.endswith("urlset")
    assert list(root) == []


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def test_main_writes_sitemap_when_pages_exist(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _touch(tmp_path / "index.html")
    _touch(tmp_path / "about.html")

    generate_sitemap.main()

    out_file = tmp_path / "sitemap.xml"
    assert out_file.exists()
    root = ET.fromstring(out_file.read_text())
    assert len(list(root)) == 2
    assert "Generated sitemap.xml with 2 URLs" in capsys.readouterr().out


def test_main_does_not_write_a_file_when_no_pages_exist(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    generate_sitemap.main()

    assert not (tmp_path / "sitemap.xml").exists()
    assert "No .html files found" in capsys.readouterr().out
