from otto import media, site


def test_dial_formats_us_numbers() -> None:
    assert site.dial("(937) 610-0088") == "+19376100088"
    assert site.dial("1-800-422-0550") == "+18004220550"
    assert site.dial("") == ""


def test_image_sniffing_trusts_bytes_not_names() -> None:
    assert media.sniff(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert media.sniff(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert media.sniff(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert media.sniff(b"<svg xmlns=...>") is None


def test_every_section_has_a_label_and_every_theme_has_colours() -> None:
    assert set(site.DEFAULT_SETTINGS["sections"]["order"]) == set(site.SECTIONS)
    for theme in site.THEMES.values():
        assert {"primary", "deep", "accent", "on_accent", "label"} <= set(theme)
