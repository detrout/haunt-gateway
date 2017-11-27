import asyncio
from unittest import TestCase
from unittest.mock import patch
from pprint import pprint

from xml.etree import ElementTree as ET
from slixmpp.stanza.iq import Iq

from .component import XHauntComponent, get_query_contents


def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper


def get_mock_coroutine(return_value):
    """Wrap a mock function to act as a coroutine

    From: https://stackoverflow.com/a/29905620
    """
    async def mock_coro(*args, **kwargs):
        return return_value

    return mock_coro


class TestXHang(TestCase):
    def setUp(self):
        self.jid = 'server'
        self.secret = 'secret'
        self.jabber_server = '127.0.0.1'
        self.port = 1234
        self.database = 'testxhang'

    @async_test
    async def test_send_form(self):
        xmpp = XHauntComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)

        iq = Iq(stype='set')
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        username = 'user'
        password = 'pass'
        form = await xmpp.register_create_form(
            iq,
            username=username, password=password)
        query_payload = form.xml.find('{jabber:iq:register}query')
        query_children = query_payload.getchildren()
        data = await xmpp.register_parse_form_payload(query_children[0])
        self.assertEqual(username, data['username'])
        self.assertEqual(password, data['password'])

    @async_test
    async def test_registration_start_never_registered(self):
        xmpp = XHauntComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)
        with patch.object(xmpp.users, 'find_account', wraps=get_mock_coroutine(return_value=None)) as find_account:
            iq = Iq(stype='set')
            iq['from'] = 'user@example.com/asdf'
            iq['to'] = 'hangups.example.net'
            iq.set_query('jabber:iq:register')

            # send bare register request
            reply = await xmpp.registration_start(iq)
            find_account.assert_called_with(iq['from'].bare)
            payload = get_query_contents(reply)
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0].tag, '{jabber:x:data}x')
            data = await xmpp.register_parse_form_payload(payload[0])
            self.assertEqual(len(data), 0)

    @async_test
    async def test_registration_start_already_registered(self):
        xmpp = XHauntComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)
        jid = 'user_registered@example.com'
        username = 'username'
        password = 'password'

        with patch.object(
                xmpp.users,
                'find_account',
                wraps=get_mock_coroutine(
                    return_value={'username': username, 'password': password})) as find_account:
            # construct initial registration iq
            iq = Iq(stype='set')
            iq['from'] = jid + '/asdf'
            iq['to'] = 'hangups.example.net'
            iq.set_query('jabber:iq:register')

            # start registration
            reply = await xmpp.registration_start(iq)
            find_account.assert_called_with(jid)
            reply_payload = get_query_contents(reply)

            # parse resulting form
            data = await xmpp.register_parse_form_payload(reply_payload[0])
            self.assertEqual(len(data), 2)
            self.assertEqual(data['username'], 'username')
            self.assertEqual(data['password'], 'password')

    @async_test
    async def test_create_account_new_account(self):
        xmpp = XHauntComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)

        r = xmpp.users
        with patch.object(r, 'add_account', wraps=get_mock_coroutine(return_value=None)) as add_account, \
             patch.object(xmpp, 'get_auth_async',
                   wraps=get_mock_coroutine(return_value={'fix': 'tokens'})) as get_auth_async:
            jid = 'user@example.com'
            jid_resource = jid + '/asdf'
            username = 'finish'
            password = 'registration'

            iq = Iq(stype='set')
            iq['from'] = jid_resource
            iq['to'] = 'hangups.example.net'
            iq.set_payload(ET.fromstring('''
<query xmlns="jabber:iq:register">
  <x xmlns="jabber:x:data">
    <field type="text-single" var="username"><value>{username}</value></field>
    <field type="text-private" var="password"><value>{password}</value></field>
  </x>
</query>'''.format(username=username, password=password)))
            query_payload = get_query_contents(iq)
            reply = await xmpp.register_create_account(iq, query_payload)

            get_auth_async.assert_called_with(jid=jid, username=username, password=password)
            add_account.assert_called_with(jid, username)

            self.assertEqual(reply['type'], 'result')

    @async_test
    async def test_unregister_registered(self):
        jid = 'user_unregister@example.com'

        xmpp = XHauntComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)
        r = xmpp.users
        with patch.object(r, 'remove_account', wraps=get_mock_coroutine(return_value=1)) as remove_account:
            iq = Iq(stype='set')
            iq['from'] = jid + '/asdf'
            iq['to'] = 'hangups.example.net'
            iq.set_payload(ET.fromstring('<query xmlns="jabber:iq:register"><remove/></query>'))
            result = await xmpp.register_unregister(iq)
            self.assertEqual(result['type'], 'result')

            remove_account.assert_called_with(jid)

    @async_test
    async def test_unregister_unregistered(self):
        xmpp = XHauntComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)
        jid = 'baduser@example.com'
        jid_resource = jid + '/asdf'
        with patch.object(xmpp.users, 'remove_account', wraps=get_mock_coroutine(return_value=0)) as remove_account:
            iq = Iq(stype='set')
            iq['from'] = jid_resource
            iq['to'] = 'hangups.example.net'
            iq.set_payload(ET.fromstring('<query xmlns="jabber:iq:register"><remove/></query>'))
            result = await xmpp.register_unregister(iq)
            self.assertEqual(result['type'], 'error')
            remove_account.assert_called_with(jid)


class TestUtils(TestCase):
    def test_get_query_contents(self):
        iq = Iq(stype='get')
        self.assertEqual(get_query_contents(iq), [])

        iq = Iq(stype='set')
        iq.set_query('http://jabber.org/protocol/disco#info')
        self.assertEqual(get_query_contents(iq), [])

        iq = Iq(stype='set')
        iq.set_payload(ET.fromstring('<query xmlns="jabber:x:register"><remove/></query>'))
        contents = get_query_contents(iq)
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0].tag, '{jabber:x:register}remove')
