"""Allauth adapter — public registration is disabled.

Accounts are created by admins only (single-lecturer platform: public
content needs no login, so open signup would only attract spam/bot
accounts). To re-enable: return True here and restore the signup link
in templates/account/login.html.
"""

from allauth.account.adapter import DefaultAccountAdapter


class ClosedSignupAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request) -> bool:
        return False
