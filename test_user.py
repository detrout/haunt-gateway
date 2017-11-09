import aiopg
from psycopg2.sql import SQL, Identifier
from unittest import TestCase

from test_xhang import async_test

from users import Users


class TestUser(TestCase):
    def setUp(self):
        self.database = 'xhangtest'

    @async_test
    async def test_not_exists(self):
        users = Users(database=self.database)
        self.assertFalse(await users._does_database_exist())

    @async_test
    async def test_create_db(self):
        users = Users(database=self.database)
        try:
            print('a')
            await users._create_database_if_needed()
            print('b')
            await users.create_table_if_needed()
            print('c')
        finally:
            await users._drop_database()
