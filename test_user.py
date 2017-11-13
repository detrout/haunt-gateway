import aiopg
from psycopg2.sql import SQL, Identifier
from unittest import TestCase

from test_xhang import async_test

from users import Users


class TestUser(TestCase):
    def setUp(self):
        self.database = 'xhangtest'

    @async_test
    async def test_db_missing(self):
        users = Users(database="i-probably-don't-exist")
        self.assertFalse(await users._does_database_exist())

    @async_test
    async def test_db_exists(self):
        users = Users(database="template1")
        self.assertTrue(await users._does_database_exist())

    @async_test
    async def test_create_db(self):
        users = Users(database=self.database)
        try:
            test_user = 'test@example.org'
            legacy_user = 'hangouts1'
            password = 'pw1'
            await users._create_database_if_needed()
            await users.create_table_if_needed()
            await users.add_account(test_user, legacy_user, password)
            await users.add_account('other@example.org', 'other1', password)

            count = await users.count()
            self.assertEqual(count, 2)

            # find accounts
            data = await users.find_account(test_user)
            self.assertEqual(data['username'], legacy_user)
            self.assertEqual(data['password'], password)

            deleted = await users.remove_account(test_user)
            self.assertEqual(deleted, 1)
            count = await users.count()
            self.assertEqual(count, 1)
        finally:
            users.close()
            await users._drop_database()
