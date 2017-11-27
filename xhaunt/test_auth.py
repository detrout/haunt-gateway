import asyncio
import os
from unittest import TestCase

from .db import Users
from .test_component import async_test

from hangups.auth import GoogleAuthError
import appdirs

import pytest


def get_hangups_token():
    token_path = os.path.join(appdirs.AppDirs('hangups', 'hangups').user_cache_dir, 'refresh_token.txt')
    with open(token_path) as instream:
        return instream.read()


@pytest.mark.skipif(
    os.environ.get('XHAUNT_GOOGLE_TEST') is None,
    reason="don't talk to google unless we know its a good idea")
class TestHangupsAuth(TestCase):
    def setUp(self):
        self.database = 'testxhang_auth'
        self.jid = 'user@example.org'
        self.username = 'user'
        self.token = get_hangups_token()
        self.xmpp = XHauntComponent('haunt.localhost', 'asdf', 'localhost', 1234, self.database)

        self._user = Users(self.database)
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._user._create_database_if_needed())
        self._loop.run_until_complete(self._user.create_table_if_needed())
        self._loop.run_until_complete(self._user.add_account(self.jid, self.username, self.token))

    def tearDown(self):
        self._user.close()
        self._loop.run_until_complete(self._user._drop_database())

    @async_test
    async def test_successful_auth(self, loop=None):
        result = await self.xmpp.get_auth_async(self.jid, self.username, token=self.token)
        print('login tokens', result)
        self.assertTrue(isinstance(result, dict))

    @async_test
    async def test_unsuccessful_auth(self, loop=None):
        jid = 'notauser@example.org'
        username = 'bureaucrat_of_the_ebon_monolith@example.org'
        password = 'u%`?J\yUsIs(8N@:B;P@j3gq'
        try:
            await self.xmpp.get_auth_async(jid, username, password)
        except GoogleAuthError:
            return

        assert False, 'GoogleAuthError Exception not raised'

