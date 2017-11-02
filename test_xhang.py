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
        self.xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port)
        
    def test_send_form(self):
        iq = Iq(stype='set')
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        username = 'user'
        password = 'pass'
        form = self.xmpp.register_create_form(
            iq,
            username=username, password=password)
        query_payload = form.xml.find('{jabber:iq:register}query')
        query_children = query_payload.getchildren()
        data = self.xmpp.register_parse_form_payload(query_children[0])
        self.assertEqual(username, data['username'])
        self.assertEqual(password, data['password'])

    def test_start_registration(self):
        iq = Iq(stype='set')
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')

        # send bare register request
        reply = self.xmpp.register(iq)
        payload = reply.get_payload()
        data = self.xmpp.register_parse_form_payload(payload[0])
        self.assertEqual(len(data), 0)

    def test_start_unregsitered(self):
        iq = Iq(stype='set')
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')

        # send bare register request
        reply = self.xmpp.register(iq)
        payload = reply.get_payload()
        data = self.xmpp.register_parse_form_payload(payload[0])
        self.assertEqual(len(data), 0)

    def test_already_registered(self):
        username = 'username'
        password = 'password'
        self.xmpp.registered = {'user@example.com': {'username': username,
                                                     'password': password}}
        iq = Iq(stype='set')
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')

        # send bare register request
        reply = self.xmpp.register(iq)
        payload = reply.get_payload()[0]
        xml_payload = reply.xml.find('{jabber:iq:register}query')
        self.assertEqual(payload, xml_payload)
        data = self.xmpp.register_parse_form_payload(payload[0])
        self.assertEqual(len(data), 2)
        self.assertEqual(data['username'], 'username')
        self.assertEqual(data['password'], 'password')
    
    def test_unregiser(self):
        username = 'username'
        password = 'password'
        self.xmpp.registered = {'user@example.com': {'username': username,
                                                     'password': password}}
        iq = Iq(stype='set')
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')
        iq.set_payload(ET.Element('remove'))
        result = self.xmpp.register(iq)
        self.assertEqual(len(self.xmpp.registered), 0)
class TestUtils(TestCase):
    def test_get_query_contents(self):
        iq = Iq(stype='get')
        self.assertEqual(get_query_contents(iq), [])

        iq = Iq(stype='set')
        iq.set_query('http://jabber.org/protocol/disco#info')
        self.assertEqual(get_query_contents(iq), [])

        iq = Iq(stype='set')
        iq.set_payload(ET.fromstring('<query ns="jabber:x:register"><remove/></query>'))
        remove = ET.Element('remove')
        contents = get_query_contents(iq)
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0].tag, 'remove')
