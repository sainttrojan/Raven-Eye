"""Phone-site checks: is this number registered on websites?

Same idea as user-scanner (email/username) and ignorant (phone), but as a
pluggable Raven-Eye package so new phone-capable sites can be added as
modules. Each module exposes NAME, DOMAIN and:
    async def check(e164, national, cc, client, out)
and appends {"name", "domain", "exists", "rate_limited", "error"} to out.

A check NEVER alerts the target number — these are unauthenticated
registration/recovery probes, same class as the email/username scans.
"""

from core.phone_sites import facebook as _facebook

MODULES = [_facebook]


def module_list():
    return list(MODULES)
