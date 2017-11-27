import psycopg2

from hangups import auth


class CredentialsPrompt:
    def __init__(self, email, password, verification_code=None):
        self.email = email
        self.password = password
        self.verification_code = verification_code

    def get_email(self):
        return self.email

    def get_password(self):
        return self.password

    def get_verification_code(self):
        return self.verification_code


class RefreshTokenCache:
    def __init__(self, database, jid, token=None):
        self.jid = jid
        self.database = database
        self.token = None

    def get(self):
        # shortcut for testing
        if self.token is not None:
            return self.token

        with psycopg2.connect(database=self.database) as conn:
            with conn.cursor() as cur:
                cur.execute('select token from users where jid=%s', (self.jid,))
                if cur.rowcount == 1:
                    return cur.fetchone()[0]

    def set(self, refresh_token):
        with psycopg2.connect(database=self.database) as conn:
            with conn.cursor() as cur:
                cur.execute('insert into users ("token") values (%s) where jid=%s',
                            (refresh_token, self.jid,))


def get_auth(database, jid, username, password=None, validation_code=None, token=None):
    creds = CredentialsPrompt(username, password, validation_code)
    tokens = RefreshTokenCache(database, jid, token)
    cookies = auth.get_auth(creds, tokens)
    return cookies
