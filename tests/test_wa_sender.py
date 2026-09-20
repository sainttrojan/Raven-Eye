"""Tests for WhatsApp sender (no browser / no session needed)."""
import os
import tempfile

from core.wa_sender import (
    WaNotLoggedIn,
    build_send_url,
    load_subscribers,
    parse_targets,
    render_listing,
    save_subscribers,
    send_messages,
)


def test_parse_targets():
    assert parse_targets("01001234567") == ["201001234567"]
    assert parse_targets("+201001234567") == ["201001234567"]
    assert parse_targets("00201001234567") == ["201001234567"]
    assert parse_targets("كلمني 01001234567 أو 01111111111") == ["201001234567", "201111111111"]
    assert parse_targets("01001234567 01001234567") == ["201001234567"]
    assert parse_targets("12345") == []
    assert parse_targets("") == []
    print("parse OK")


def test_send_url():
    u = build_send_url("201001234567", "شقة مدينتي")
    assert u.startswith("https://web.whatsapp.com/send?phone=201001234567&text=")
    assert "%D8%B4%D9%82%D8%A9" in u
    assert build_send_url("201001234567") == "https://web.whatsapp.com/send?phone=201001234567"
    print("url OK")


def test_render():
    msg = render_listing({"Title": "شقة B7", "Price": "5 مليون",
                          "Phone Number": "01001234567", "URL": "http://x"})
    assert "شقة B7" in msg and "01001234567" in msg and "http://x" in msg
    print("render OK")


def test_dry_run():
    r = send_messages(["201001234567", "201111111111"], "تجربة", dry_run=True)
    assert r["dry_run"] and r["sent"] == 2 and r["failed"] == 0 and not r["error"]
    r = send_messages([], "x", dry_run=True)
    assert r["error"]
    r = send_messages(["201001234567"], "   ", dry_run=True)
    assert r["error"]
    print("dry-run OK")


def test_sheet_extraction():
    import pandas as pd
    from core.wa_sender import extract_numbers_from_frame, load_numbers_file
    df = pd.DataFrame({"name": ["Ahmed", "Mona"],
                       "phone": ["01001234567", "+201111111111"],
                       "note": ["كلمني على 01222222222", "لا يوجد"]})
    nums = extract_numbers_from_frame(df)
    assert nums == ["201001234567", "201111111111", "201222222222"], nums
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "nums.xlsx")
        df.to_excel(p, index=False)
        assert load_numbers_file(p) == nums
        c = os.path.join(tmp, "nums.csv")
        df.to_csv(c, index=False)
        assert load_numbers_file(c) == nums
    print("sheet OK")


def test_needs_login_and_subs():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            try:
                send_messages(["201001234567"], "x", dry_run=False)
                raise AssertionError("should have raised")
            except WaNotLoggedIn as e:
                assert "wa_login" in str(e), e
            assert load_subscribers() == []
            save_subscribers(["201001234567", "201001234567", "201111111111"])
            assert load_subscribers() == ["201001234567", "201111111111"]
        finally:
            os.chdir(cwd)
    print("login-guard + subs OK")


def test_login_check_strictness():
    # The QR landing page must NEVER count as logged in (regression:
    # grid-ish elements on it fooled the old check and saved dead sessions).
    import asyncio
    from playwright.async_api import async_playwright
    from core.wa_sender import check_logged_in_now

    async def go():
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            try:
                pg = await b.new_page()
                await pg.set_content(
                    "<html><body><div role='grid'>x</div>"
                    "<p>Scan to log in</p></body></html>")
                assert await check_logged_in_now(pg) is False
                await pg.set_content(
                    "<html><body><div data-testid='chat-list'>chats</div></body></html>")
                assert await check_logged_in_now(pg) is True
            finally:
                await b.close()

    asyncio.run(go())
    print("login strictness OK")


if __name__ == "__main__":
    test_parse_targets()
    test_send_url()
    test_render()
    test_dry_run()
    test_sheet_extraction()
    test_needs_login_and_subs()
    test_login_check_strictness()
    print("ALL WA SENDER TESTS PASSED")
