from otto.validation import FormErrors, optional_phone, parse_slot, require_email, safe_link


def test_email_rules() -> None:
    errors = FormErrors()
    require_email("andi@theottoagency.com", errors)
    assert not errors
    require_email("not-an-email", errors)
    assert "email" in errors.by_field


def test_phone_is_optional_but_must_be_ten_digits() -> None:
    errors = FormErrors()
    optional_phone("", errors)
    optional_phone("(937) 610-0088", errors)
    assert not errors
    optional_phone("12345", errors)
    assert "phone" in errors.by_field


def test_slot_must_carry_a_time_zone() -> None:
    assert parse_slot("2026-11-02T10:00:00-05:00") is not None
    assert parse_slot("2026-11-02T10:00:00") is None
    assert parse_slot("garbage") is None


def test_links_reject_script_urls() -> None:
    assert safe_link("https://www.grangeinsurance.com/")
    assert safe_link("tel:+19376100088")
    assert not safe_link("javascript:alert(1)")
    assert not safe_link("https://")
