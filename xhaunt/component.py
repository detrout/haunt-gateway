import concurrent.futures
import asyncio
import logging

from slixmpp.componentxmpp import ComponentXMPP
from slixmpp.xmlstream import ET
from slixmpp.xmlstream.handler.callback import Callback
from slixmpp.xmlstream.matcher.xpath import MatchXPath

from .auth import get_auth
from .db import Users
logger = logging.getLogger('xmpp')


class XHauntComponent(ComponentXMPP):
    def __init__(self, jid, secret, server, port, database):
        super(XHauntComponent, self).__init__(jid, secret, server, port)

        self.database = database
        self.users = Users(self.database)

        self.add_event_handler('message', self.message)
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('presence_probe', self.probe)
        self.add_event_handler('presence_available', self.presence_available)

        self.register_plugin('xep_0004')  # Data Forms
        self.register_plugin('xep_0077')  # In-Band Registration
        self.register_handler(
            Callback('In-Band Registration',
                     MatchXPath('{%s}iq/{jabber:iq:register}query' % (self.default_ns,)),
                     self.register))
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
            iq = await self.registration_start(iq)
            await iq.send()
        # returning filled out form
        elif query_payload[0].tag == '{jabber:x:data}x':
            iq = await self.register_create_account(iq, query_payload)
            await iq.send()
            if iq.get('type') == 'result':
                p = await self.subscribe_to(iq['to'])
                await p.send()

        # removing already registered
        elif query_payload[0].tag == '{jabber:iq:register}remove':
            iq = await self.register_unregister(iq)
            await iq.send()
        else:
            print('else', query_payload[0].tag)

    async def registration_start(self, iq):
        """Start or edit a registration

        :returns:
           Registration form
        """
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

    async def register_create_account(self, iq, query_payload):
        """Create account if provided log in information succeeds

        :args:
            iq: incoming iq packet with filled in form
            query_payload: just the query payload
        :returns:
            iq: indicating success or error
        """
        data = await self.register_parse_form_payload(query_payload[0])
        # try logging in
        await self.users.add_account(iq['from'].bare, data['username'])
        result = await self.get_auth_async(
            jid=iq['from'].bare,
            username=data['username'],
            password=data['password'],)
        if result is not None:
            # schedule sending subscription
            return iq.reply()
        else:
            reply = iq.reply()
            reply['type'] = 'error'
            return reply

    async def register_unregister(self, iq):
        removed = await self.users.remove_account(iq.get('from').bare)
        if removed == 0:
            reply = iq.reply()
            reply.error()
            reply.set_payload(ET.fromstring('<error type="cancel"><item-not-found/></error>'))
            return reply

        return iq.reply()

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

    async def subscribe_to(self, jid):
        """Subscribe to user's presence

        :args:
           jid: jid to subscribe to

        :returns:
           subscribe presence stanza
        """
        return self.make_presence(pto=jid.bare, pfrom=self.xmpp.boundjid, ptype='subscribe')
    async def get_auth_async(self, jid, username, password=None, validation_code=None, token=None):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            task = self.loop.run_in_executor(
                executor,
                get_auth,
                self.database,
                jid,
                username,
                password,
                validation_code,
                token)
            result = await task
            return result


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
