from pprint import pprint
import asyncio
import json
import logging
import os

from slixmpp.componentxmpp import ComponentXMPP
from slixmpp.xmlstream import ET
from slixmpp.xmlstream.handler.callback import Callback
from slixmpp.xmlstream.matcher.xpath import MatchXPath

from .db import Users
logger = logging.getLogger('xmpp')


class XHauntComponent(ComponentXMPP):
    def __init__(self, jid, secret, server, port, database):
        super(XHauntComponent, self).__init__(jid, secret, server, port)

        self.users = Users(database)

        self.add_event_handler('message', self.message)
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('presence_probe', self.probe)
        self.add_event_handler('presence_available', self.presence_available)

        self.register_plugin('xep_0004')  # Data Forms
        self.register_plugin('xep_0077')  # In-Band Registration
        self.register_handler(
            Callback('In-Band Registration',
                     MatchXPath('{%s}iq/{jabber:iq:register}query' % (self.default_ns,)),
                     self.register_cb))
        self.register_plugin('xep_0199')  # Ping
        self.register_plugin('xep_0092')  # Software Version
        self.register_plugin('xep_0030')  # Service Discovery
        self.plugin['xep_0030'].add_identity(
            category='gateway',
            itype='hangouts',
            name='Hangouts Gateway')
        self.plugin['xep_0030'].add_feature('jabber:iq:register')

    def message(self, msg):
        msg.reply('Poke').send()

    def start(self, event):
        logger.debug('starting')
        logger.debug(self.roster)

    def probe(self, event):
        logger.debug('probe %s', event)

    def presence_available(self, *args, **kwargs):
        logger.debug('pa %s', str(args))

    async def register_cb(self, iq):
        """Callback for triggering registration

        This is seperate just to make it easier to test the
        registration logic.

        """
        reply = await self.register(iq)
        if reply is not None:
            reply.send()

    async def register(self, iq):
        """Logic for handling user registration to the component
        """
        if iq is None:
            return

        if iq.get('from') is None:
            logger.warning("Odd IQ packet. No From")
            return

        if iq.get('type') != 'set':
            logger.warning('Odd IQ type %s' % (iq.get('type'),))
            return

        query_payload = get_query_contents(iq)

        # starting to register
        if len(query_payload) == 0:
            data = await self.users.find_account(iq['from'].bare)
            if data is not None:
                username = data['username']
                password = data['password']
            else:
                username = None
                password = None
            return await self.register_create_form(
                iq,
                username=username,
                password=password)
        # returning filled out form
        elif query_payload[0].tag == '{jabber:x:data}x':
            data = await self.register_parse_form_payload(query_payload[0])
            # TODO Register
            # try logging in?
            await self.users.add_account(iq['from'].bare, data['username'], data['password'])
            return iq.reply()

        # removing already registered
        elif query_payload[0].tag == '{jabber:iq:register}remove':
            removed = await self.users.remove_account(iq.get('from').bare)
            if removed == 0:
                reply = iq.reply()
                reply.error()
                reply.set_payload(ET.fromstring('<error type="cancel"><item-not-found/></error>'))
                return reply

            return iq.reply()
        else:
            print('else', query_payload[0].tag)

    async def register_create_form(self, iq, username=None, password=None):
        """Prepare a registration form

        If username and password are set, use those for the default values.
        This path is used when the user is already registered.
        """
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
        reply['from'] = self.jid
        reply['type'] = 'set'
        reply.set_payload(query)
        return reply

    async def register_parse_form_payload(self, x):
        results = {}
        if x.tag == '{jabber:x:data}x':
            for field in x.getchildren():
                for value in field.getchildren():
                    results[field.attrib['var']] = value.text
        return results

    def unregister(self, iq):
        msg = 'Goodbye %s' % (iq['register']['username'])
        self.send_message(iq['from'], msg, mfrom=self.boundjid.full)


def get_query_contents(iq):
    """Return the contents of the iq query tag

    Given an IQ that looks like this:
    <iq><query><jabber:x:data><field>....</jabber:x:data></query></iq?
    It'll return the ElementTree elements between the query tag.

    Or the empty list if there was nothing
    """
    query = iq.get_payload()
    for element in query:
        # print('gqce', element, element.tag, type(element))
        if element.tag.endswith('query'):
            children = element.getchildren()
            return children

    return []


def main():
    from configparser import ConfigParser
    config = ConfigParser()
    config.read('xhang.ini')

    service_name = config['DEFAULT'].get('service_name')
    secret = config['DEFAULT'].get('secret')
    jabber_server = config['DEFAULT'].get('jabber_server', '127.0.0.1')
    jabber_port = config['DEFAULT'].get('jabber_port', 5347)
    database = config['DEFAULT'].get('database')

    logging.basicConfig(level=logging.DEBUG)

    xmpp = XHauntComponent(service_name, secret, jabber_server, jabber_port, database)

    xmpp.connect()
    xmpp.process()


if __name__ == '__main__':
    main()
