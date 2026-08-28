"""Unit tests for lib/extract.py (T13).

Verifies URL deobfuscation (10+ patterns), phone number extraction, and bank account detection.
"""

import pytest

from lib.extract import extract_entities, normalize_phone_number, normalize_url


def test_10_obfuscated_url_cases():
    """DoD: Test 10 distinct obfuscated URL formats normalized into canonical URLs."""
    test_cases = [
        # 1. Scheme hxxps with bracketed dots -> https://
        (
            "Segera verifikasi akun di hxxps://bank-bca[.]login-aman[.]xyz/auth sekarang!",
            "https://bank-bca.login-aman.xyz/auth",
        ),
        # 2. Scheme h**p with parenthesized dots -> http://
        (
            "Klik link bantuan: h**p://bri-mo(.)verifikasi-pribadi(.)online/update",
            "http://bri-mo.verifikasi-pribadi.online/update",
        ),
        # 3. Spaces inside scheme and host
        (
            "Buka http : // mandiri-livin . top / secure untuk ubah tarif",
            "http://mandiri-livin.top/secure",
        ),
        # 4. Word [dot] obfuscation
        (
            "Cek mutasi bca[dot]promo-tarif[dot]xyz/login",
            "https://bca.promo-tarif.xyz/login",
        ),
        # 5. Spaced shortlink
        (
            "Silakan klik bit .ly / 3XYZabc untuk info promo",
            "https://bit.ly/3XYZabc",
        ),
        # 6. WhatsApp direct link
        (
            "Hubungi CS via wa.me/6281234567890?text=halo",
            "https://wa.me/6281234567890?text=halo",
        ),
        # 7. Telegram link
        (
            "Gabung grup t.me/layanan_bca_resmi",
            "https://t.me/layanan_bca_resmi",
        ),
        # 8. Indonesian shortlink s.id
        (
            "Update data di s.id/tarif-baru-bni.",
            "https://s.id/tarif-baru-bni",
        ),
        # 9. Curly brackets and hxxp
        (
            "Hadiah DANA Kaget di hxxp://dana-kaget{.}vip/klaim",
            "http://dana-kaget.vip/klaim",
        ),
        # 10. Schemeless domain with query param and trailing punctuation
        (
            "Pemberitahuan: klik-bca-verif.xyz/login?ref=sms, jangan abaikan!",
            "https://klik-bca-verif.xyz/login?ref=sms",
        ),
    ]

    for raw_text, expected_url in test_cases:
        entities = extract_entities(raw_text)
        assert len(entities.urls) >= 1, f"Failed to extract URL from: {raw_text}"
        assert expected_url in entities.urls, (
            f"Expected {expected_url} in {entities.urls} from input: '{raw_text}'"
        )


def test_extract_phone_numbers():
    """Test extraction and normalization of various Indonesian phone number formats."""
    text = (
        "Hubungi call center di 0812-3456-7890 atau CS WhatsApp di +6281311223344. "
        "Alternatif lain hubungi 0857.9988.7766."
    )
    entities = extract_entities(text)
    assert "081234567890" in entities.phone_numbers
    assert "081311223344" in entities.phone_numbers
    assert "085799887766" in entities.phone_numbers


def test_extract_bank_accounts():
    """Test extraction of bank names and account numbers from Indonesian text."""
    text = (
        "Silakan transfer ke Rekening BCA: 1234567890 atas nama PT Promo. "
        "Atau ke No Rek Mandiri 1370012345678 a/n Budi. "
        "VA BRI: 001201001234501."
    )
    entities = extract_entities(text)
    assert len(entities.bank_accounts) >= 3

    bca_acc = next((a for a in entities.bank_accounts if a["bank"] == "BCA"), None)
    assert bca_acc is not None
    assert bca_acc["account_number"] == "1234567890"

    mandiri_acc = next((a for a in entities.bank_accounts if a["bank"] == "MANDIRI"), None)
    assert mandiri_acc is not None
    assert mandiri_acc["account_number"] == "1370012345678"

    bri_acc = next((a for a in entities.bank_accounts if a["bank"] == "BRI"), None)
    assert bri_acc is not None
    assert bri_acc["account_number"] == "001201001234501"


def test_empty_and_clean_text():
    """Test empty input and text without entities."""
    assert extract_entities("").urls == []
    assert extract_entities(None).urls == []
    clean_text = "Selamat pagi bapak ibu, semoga hari Anda menyenangkan."
    res = extract_entities(clean_text)
    assert res.urls == []
    assert res.phone_numbers == []
    assert res.bank_accounts == []
