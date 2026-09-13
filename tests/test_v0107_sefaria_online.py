from quarries.sefaria_online import manuscript_image_urls, version_text


def test_version_text_flattens_nested_segments_and_cleans_html():
    payload={"hebrew":{"versions":[{"text":["<b>שלום</b>",["עולם&nbsp;טוב"]]}]}}
    assert version_text(payload,"hebrew")==["שלום","עולם טוב"]


def test_manuscript_image_urls_find_and_dedupe_nested_images():
    payload={"manuscripts":[{"image_url":"https://example.org/a.jpg"},{"nested":{"image":"https://example.org/b.png"}},{"image_url":"https://example.org/a.jpg"}]}
    assert manuscript_image_urls(payload)==["https://example.org/a.jpg","https://example.org/b.png"]
