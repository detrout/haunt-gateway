import aiopg
from psycopg2 import sql

class Users:
    def __init__(self, database, user=None, password=None, host=None):
        self.conn = None
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.default_database = 'template1'

    def __del__(self):
        self.close()

    async def connect(self):
        '''Connect to database'''
        if self.conn is None:
            self.conn = await self._connect()
        assert self.conn is not None

    async def _connect(self, database=None):
        '''Connect without caching connection

        :Parameter:
           database - database name, defaults to self.database
        '''
        if database is None:
            database = self.database
        return await aiopg.connect(
            database=database,
            user=self.user,
            password=self.password,
            host=self.host)

    def close(self):
        """Close database connection"""
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    async def _does_database_exist(self):
        """Test if self.database name exists
        """
        try:
            conn = await self._connect(self.default_database)
            cur = await conn.cursor()
            await cur.execute("SELECT datname FROM pg_database where datname=%s",
                              (self.database,))
            result = await cur.fetchone()
        finally:
            conn.close()
        return result is not None

    async def _create_database_if_needed(self):
        conn = None
        try:
            if not await self._does_database_exist():
                conn = await self._connect(self.default_database)
                cur = await conn.cursor()
                await cur.execute(sql.SQL('create database {}').format(sql.Identifier(self.database)))
        finally:
            if conn:
                conn.close()

    async def _drop_database(self):
        conn = None
        try:
            conn = await self._connect(self.default_database)
            cur = await conn.cursor()
            await cur.execute(sql.SQL('drop database {}').format(sql.Identifier(self.database)))
        finally:
            if conn:
                conn.close()

    async def create_table_if_needed(self):
        print(self.database)
        print(await self._does_database_exist())
        await self.connect()
        cur = await self.conn.cursor()
        await cur.execute("create sequence if not exists users_id_seq")
        await cur.execute("""
create table if not exists users (
            id serial primary key,
            jid varchar(255),
            username varchar(255),
            token varchar(255))
""")

