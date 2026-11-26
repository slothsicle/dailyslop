"""/checkperms: telling a missing role permission from a channel override."""

import discord

from dailyslop.permcheck import check_members, check_permissions, render

FULL = discord.Permissions(
    view_channel=True,
    send_messages=True,
    send_messages_in_threads=True,
    embed_links=True,
    read_message_history=True,
    manage_messages=True,
)


def bad(findings):
    return {f.label: f for f in findings if not f.ok}


def test_everything_granted_is_all_ok():
    findings = check_permissions(FULL, FULL)
    assert not bad(findings)
    assert render("#general", findings).startswith("✅")


def test_missing_server_wide_blames_the_role():
    channel = discord.Permissions(FULL.value & ~discord.Permissions(manage_messages=True).value)
    problems = bad(check_permissions(channel, channel))
    assert set(problems) == {"Manage Messages"}
    assert "role doesn't have it" in problems["Manage Messages"].problem


def test_granted_server_wide_but_missing_here_blames_an_override():
    channel = discord.Permissions(FULL.value & ~discord.Permissions(view_channel=True).value)
    problems = bad(check_permissions(channel, FULL))
    assert set(problems) == {"View Channel"}
    assert "override" in problems["View Channel"].problem


def test_threads_need_send_in_threads_not_send_messages():
    channel = discord.Permissions(FULL.value & ~discord.Permissions(send_messages=True).value)
    assert not bad(check_permissions(channel, FULL, thread=True))
    channel = discord.Permissions(
        FULL.value & ~discord.Permissions(send_messages_in_threads=True).value
    )
    assert set(bad(check_permissions(channel, FULL, thread=True))) == {"Send Messages in Threads"}


def test_timeout_is_reported():
    assert "Timeout" in bad(check_permissions(FULL, FULL, timed_out=True))


def test_report_lists_each_problem_with_a_fix():
    channel = discord.Permissions.none()
    text = render("#general", check_permissions(channel, FULL))
    assert text.startswith("❌ 5 problems")
    assert text.count("↳ Fix:") == 5


def test_members_cache_must_cover_most_of_the_server():
    assert check_members(95, 100).ok
    assert check_members(0, 0).ok  # unknown total: nothing to compare
    assert not check_members(3, 100).ok
