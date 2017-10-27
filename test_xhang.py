from unittest import TestCase
from pprint import pprint

from slixmpp.stanza.iq import Iq
from slixmpp.plugins.xep_0004.stanza.form import Form

from xhang import EchoComponent

class TestXHang(TestCase):

    def setUp(self):
        self.jid = 'server'
        self.secret = 'secret'
        self.jabber_server = '127.0.0.1'
        self.port = 1234
        self.xmpp = EchoComponent(self.jid, self.secret, self.jabber_server, self.port)
        
    def test_send_form(self):
        iq = Iq()
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        username = 'user'
        password = 'pass'
        form = self.xmpp.register_create_form(
            iq,
            username=username, password=password)
        query_payload = form.xml.find('{jabber:iq:register}query').getchildren()
        u, p = self.xmpp.register_parse_form_payload(query_payload[0])
        self.assertEqual(username, u)
        self.assertEqual(password, p)

    def test_start_registration(self):
        iq = Iq()
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')

        # send bare register request
        reply = self.xmpp.register(iq)
        payload = reply.get_payload()
        u, p = self.xmpp.register_parse_form_payload(payload[0])
        self.assertIsNone(u)
        self.assertIsNone(p)

    def test_start_unregistration(self):
        iq = Iq()
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')

        # send bare register request
        reply = self.xmpp.register(iq)
        payload = reply.get_payload()
        u, p = self.xmpp.register_parse_form_payload(payload[0])
        self.assertIsNone(u)
        self.assertIsNone(p)

    def test_start_registration(self):
        self.xmpp.registered = { 'user@example.com/asdf': 'pw' }
        iq = Iq()
        iq['from'] = 'user@example.com/asdf'
        iq['to'] = 'hangups.example.net'
        iq.set_query('jabber:iq:register')

        # send bare register request
        reply = self.xmpp.register(iq)
        payload = reply.get_payload()
        u, p = self.xmpp.register_parse_form_payload(payload[0])
        self.assertIsNone(u)
        self.assertIsNone(p)
    
