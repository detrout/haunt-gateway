from pprint import pprint
import asyncio
import logging
from slixmpp.componentxmpp import ComponentXMPP
from slixmpp.plugins.base import BasePlugin
from slixmpp.xmlstream import register_stanza_plugin, ElementBase, JID, ET
from slixmpp.xmlstream.handler.callback import Callback
from slixmpp.xmlstream.matcher.xpath import MatchXPath

logger = logging.getLogger('xmpp')

class EchoComponent(ComponentXMPP):
    def __init__(self, jid, secret, server, port):
        logger.debug('init')
        super(EchoComponent, self).__init__(jid, secret, server, port)
            
        self.registered = { }

        self.add_event_handler('message', self.message)
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('presence_probe', self.probe)
        self.add_event_handler('presence_available', self.presence_available)

        self.register_plugin('xep_0004') # Data Forms
        self.register_plugin('xep_0077') # In-Band Registration
        self.register_handler(
            Callback('In-Band Registration',
                     MatchXPath('{%s}iq/{jabber:iq:register}query' % (self.default_ns,)),
                     self.register_cb))
        self.register_plugin('xep_0199') # Ping
        self.register_plugin('xep_0092') # Software Version
        self.register_plugin('xep_0030') # Service Discovery
        self.plugin['xep_0030'].add_identity(
            category='gateway',
            itype='hangouts',
            name='Hangouts Gateway')
        self.plugin['xep_0030'].add_feature('jabber:iq:register')
        #pprint(dir(self))
        print(self.plugin['xep_0077'])

    def message(self, msg):
        msg.reply('Poke').send()

    def start(self, event):
        logger.debug('starting')
        #self.send_message(mto='diane@ghic.org',
        #                  mbody='test message',
        #                  mfrom='server@hangups.ghic.org')
        logger.debug(self.roster)

    def probe(self, event):
        logger.debug('probe %s', event)

    def presence_available(self, *args, **kwargs):
        logger.debug('pa %s',str(args))


    def register_cb(self, iq):
        reply = self.register(iq)
        if reply is not None:
            reply.send()
            
    def register(self, iq):
        if iq is None:
            return
        
        reply = None
        pprint(iq)
        query = iq.xml.find('{jabber:iq:register}query')
        if query is None:
            return
        query_payload = query.getchildren()

        username=None
        password = None
        if iq['from'].bare in self.registered:
            username = 'asdf'
            password = 'asdf'

        print('qp', len(query_payload))
        if len(query_payload) == 0:
            reply = self.register_create_form(
                iq,
                username=username,
                password=password)
            print('reply', type(reply))
        elif len(query_payload) == 1:
            username, password = self.register_parse_form_payload(query_payload[0])

        return reply
    
    def register_create_form(self, iq, username=None, password=None):
        f = self.plugin['xep_0004'].make_form(
            title='register',
            instructions='Please provide username & password')
        f['type'] = 'form'
        f.add_field('username', type='text-single', label='username', value=username)
        f.add_field('password', type='text-private', label='password', value=password)
        f.add_field('cookie', type='text-single', label='cookie')
        query = ET.Element('{jabber:iq:register}query')
        query.insert(0, f.xml)
        reply = iq.reply()
        reply.set_payload(query)
        return reply

    def register_parse_form_payload(self, x):
        print('x.tag', x.tag)
        username = None
        password = None
        if x.tag == '{jabber:x:data}x':
            for field in x.getchildren():
                for value in field.getchildren():
                    print(field.attrib['var'], value.text)
                    if field.attrib['var'] == 'username':
                        username = value.text
                    elif field.attrib['var'] == 'password':
                        password = value.text
        return (username, password)

    def unregister(self, iq):
        pprint(iq['register'])
        msg = 'Goodbye %s' % (iq['register']['username'])
        self.send_message(iq['from'], msg, mfrom=self.boundjid.full)
        
def main():
    from configparser import ConfigParser
    config = ConfigParser()
    config.read('xhang.ini')
    service_name = config['DEFAULT'].get('service_name')
    secret = config['DEFAULT'].get('secret')
    jabber_server = config['DEFAULT'].get('jabber_server', '127.0.0.1')
    jabber_port = config['DEFAULT'].get('jabber_port', 5347)
    
    logging.basicConfig(level=logging.DEBUG)

    xmpp = EchoComponent(service_name, secret, jabber_server, jabber_port)
    
    xmpp.connect()
    xmpp.process()

if __name__ == '__main__':
    main()
