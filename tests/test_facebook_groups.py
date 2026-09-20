"""Tests for Facebook Groups source (no browser / no login needed)."""
import os
import tempfile

from scrapers.facebook_groups import (
    absolutize,
    build_result,
    group_search_url,
    group_token,
    is_profile_href,
    normalize_post_url,
)
from core.listing_classifier import classify


def test_group_token():
    assert group_token("https://www.facebook.com/groups/1234567890/") == "1234567890"
    assert group_token("https://www.facebook.com/groups/madinaty-owners/?q=x") == "madinaty-owners"
    assert group_token("1234567890") == "1234567890"
    assert group_token("") == ""
    assert "query=%D8%B4%D9%82%D8%A9" in group_search_url("123", "شقة مدينتي")
    print("token/url OK")


def test_post_url():
    assert normalize_post_url("/groups/1/posts/234/?ref=x") == \
        "https://www.facebook.com/groups/1/posts/234"
    assert normalize_post_url("https://www.facebook.com/posts/999/") == \
        "https://www.facebook.com/posts/999"
    assert normalize_post_url("/marketplace/item/1/") is None
    assert normalize_post_url("") is None
    print("post url OK")


def test_profile_href():
    assert is_profile_href("/Ahmed.Broker/")
    assert is_profile_href("/profile.php?id=123")
    assert is_profile_href("https://www.facebook.com/user/456/")
    assert not is_profile_href("/groups/123/posts/456")
    assert not is_profile_href("/marketplace/item/1/")
    assert not is_profile_href("/hashtag/madinaty/")
    assert not is_profile_href("")
    print("profile href OK")


def test_build_result():
    r = build_result({
        "post_url": "/groups/1/posts/2/",
        "author_name": "Ahmed Samy",
        "author_url": "/ahmed.samy.9/",
        "text": "شقة 120 متر مدينتي B7 من المالك 01001234567",
        "time": "2h",
    }, "madinaty-group")
    assert r and r.author == "Ahmed Samy"
    assert r.author_url == "https://www.facebook.com/ahmed.samy.9/"
    assert r.phone_number == "01001234567"
    assert "120" in (r.area or "")
    assert r.source == "Facebook Group (madinaty-group)"
    # non-profile author links are dropped
    r2 = build_result({"post_url": "/posts/3/", "author_name": "X",
                       "author_url": "/groups/1/", "text": "شقة مدينتي"}, "g")
    assert r2 and r2.author_url is None
    # junk without post link / without text
    assert build_result({"post_url": "", "text": "شقة"}, "g") is None
    assert build_result({"post_url": "/posts/4/", "text": "   "}, "g") is None
    print("build_result OK")


def test_author_classifier_signal():
    c = classify("شقة للبيع مدينتي", "وصف عادي", author="مكتب النور للتسويق العقاري")
    assert c["label"] == "broker", c
    c = classify("شقة للبيع مدينتي", "وصف عادي", author="Ahmed Samy")
    assert c["label"] == "unknown", c
    print("author signal OK")


def test_groups_config():
    from core import config
    old = config.CONFIG_FILE
    with tempfile.TemporaryDirectory() as tmp:
        config.CONFIG_FILE = os.path.join(tmp, "cfg.json")
        try:
            assert config.load_fb_groups() == []
            config.save_fb_groups(["https://www.facebook.com/groups/123/", "  ", "456"])
            assert config.load_fb_groups() == ["https://www.facebook.com/groups/123/", "456"]
        finally:
            config.CONFIG_FILE = old
    print("groups config OK")


def test_no_session_clean_error():
    from core.fb_session import FacebookNotLoggedIn, run_facebook_groups_search
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            try:
                run_facebook_groups_search("شقة", groups=["123"], max_pages=1)
                raise AssertionError("should have raised")
            except FacebookNotLoggedIn as e:
                assert "fb_login" in str(e) or "جروبات" in str(e), e
        finally:
            os.chdir(cwd)
    print("no-session error OK")


if __name__ == "__main__":
    test_group_token()
    test_post_url()
    test_profile_href()
    test_build_result()
    test_author_classifier_signal()
    test_groups_config()
    test_no_session_clean_error()
    print("ALL FACEBOOK GROUPS TESTS PASSED")
