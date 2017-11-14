import asyncio
from unittest import TestCase
from pprint import pprint

from xml.etree import ElementTree as ET
from slixmpp.stanza.iq import Iq

from xhang import EchoComponent, get_query_contents


def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper

class TestXHang(TestCase):
    def setUp(self):
        self.jid = 'server'
        self.secret = 'secret'
        self.jabber_server = '127.0.0.1'
        self.port = 1234
        self.database = 'testxhang'

    @async_test
    async def test_send_form(self):
        xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)
        await xmpp.registered._create_database_if_needed()
        await xmpp.registered.create_table_if_needed()
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
    async def test_start_registration(self):
        xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)
        await xmpp.registered._create_database_if_needed()
        await xmpp.registered.create_table_if_needed()
        iq = Iq(stype='set')
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')

        # send bare register request
        reply = await xmpp.register(iq)
        payload = get_query_contents(reply)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0].tag, '{jabber:x:data}x')
        data = await xmpp.register_parse_form_payload(payload[0])
        self.assertEqual(len(data), 0)

    @async_test
    async def test_start_unregistered(self):
        xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port, self.database)
        await xmpp.registered._create_database_if_needed()
        await xmpp.registered.create_table_if_needed()
        iq = Iq(stype='set')
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')

        # send bare register request
        reply = await xmpp.register(iq)
        payload = reply.get_payload()
        data = await xmpp.register_parse_form_payload(payload[0])
        self.assertEqual(len(data), 0)

    @async_test
    async def test_already_registered(self):
        database = self.database + '_already_regisered'
        xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port, database)
        jid = 'user_registered@example.com'
        username = 'username'
        password = 'password'

        await xmpp.registered._create_database_if_needed()
        await xmpp.registered.create_table_if_needed()
        await xmpp.registered.connect()
        try:
            await xmpp.registered.add_account(jid, username, password)
            iq = Iq(stype='set')
            iq['from'] = 'user_registered@example.com/asdf'
            iq['to'] = 'hangups.example.net'
            iq.set_query('jabber:iq:register')

            # send bare register request
            reply = await xmpp.register(iq)
            payload = get_query_contents(reply)
            data = await xmpp.register_parse_form_payload(payload[0])
            self.assertEqual(len(data), 2)
            self.assertEqual(data['username'], 'username')
            self.assertEqual(data['password'], 'password')
        finally:
            await xmpp.registered.remove_account(jid)
            xmpp.registered.close()
            await xmpp.registered._drop_database()

    @async_test
    async def test_finish_registration(self):
        database = self.database + '_finish_registration'
        xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port, database)
        await xmpp.registered._create_database_if_needed()
        await xmpp.registered.create_table_if_needed()
        try:
            count = await xmpp.registered.count()
            self.assertEqual(count, 0)
            username = 'finish'
            password = 'registration'

            iq = Iq(stype='set')
            iq['from'] = 'user@example.com/asdf'
            iq['to'] = 'hangups.example.net'
            iq.set_query('jabber:iq:register')
            form = await xmpp.register_create_form(iq, username, password)
            reply = await xmpp.register(form)

            self.assertEqual(reply['type'], 'result')
            count = await xmpp.registered.count()
            self.assertEqual(count, 1)
        finally:
            xmpp.registered.close()
            await xmpp.registered._drop_database()

    @async_test
    async def test_unregister(self):
        database = self.database + '_unregister'
        xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port, database)
        jid = 'user_unregister@example.com'
        username = 'username'
        password = 'password'
        await xmpp.registered._create_database_if_needed()
        await xmpp.registered.create_table_if_needed()
        await xmpp.registered.connect()
        try:
            await xmpp.registered.add_account(jid, username, password)
            iq = Iq(stype='set')
            iq['from'] = 'user_unregister@example.com/asdf'
            iq['to'] = 'hangups.example.net'
            iq.set_payload(ET.fromstring('<query xmlns="jabber:iq:register"><remove/></query>'))
            result = await xmpp.register(iq)
            self.assertEqual(result['type'], 'result')
            count = await xmpp.registered.count()
            self.assertEqual(count, 0)
        finally:
            await xmpp.registered.remove_account(jid)
            xmpp.registered.close()
            await xmpp.registered._drop_database()

    @async_test
    async def test_unregister_wrong_user(self):
        database = self.database + '_unregister_wrong_user'
        xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port, database)
        jid = 'gooduser@example.com'
        username = 'username'
        password = 'password'
        await xmpp.registered._create_database_if_needed()
        await xmpp.registered.create_table_if_needed()
        await xmpp.registered.connect()
        try:
            await xmpp.registered.add_account(jid, username, password)

            iq = Iq(stype='set')
            iq['from'] = 'baduser@example.com/asdf'
            iq['to'] = 'hangups.example.net'
            iq.set_payload(ET.fromstring('<query xmlns="jabber:iq:register"><remove/></query>'))
            result = await xmpp.register(iq)
            self.assertEqual(result['type'], 'error')
            count = await xmpp.registered.count()
            self.assertEqual(count, 1)
        finally:
            await xmpp.registered.remove_account(jid)
            xmpp.registered.close()
            await xmpp.registered._drop_database()


class TestUtils(TestCase):
    def test_get_query_contents(self):
        iq = Iq(stype='get')
        self.assertEqual(get_query_contents(iq), [])

        iq = Iq(stype='set')
        iq.set_query('http://jabber.org/protocol/disco#info')
        self.assertEqual(get_query_contents(iq), [])

        iq = Iq(stype='set')
        remove = ET.Element('remove')
        iq.set_payload(ET.fromstring('<query xmlns="jabber:x:register"><remove/></query>'))
        contents = get_query_contents(iq)
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0].tag, '{jabber:x:register}remove')
