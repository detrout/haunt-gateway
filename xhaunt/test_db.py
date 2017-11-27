from unittest import TestCase

from .test_component import async_test
from .db import Users, Roster

from hangups.user import UserID


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
        roster = Roster(database=self.database)
        try:
            test_user = 'test@example.org'
            legacy_user = 'hangouts1'
            password = 'pw1'
            roster1 = UserID(gaia_id="1234567890", chat_id="1234567890")
            roster2 = UserID(gaia_id="0987654321", chat_id="0987654321")
            roster_set = set((roster1, roster2))

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

            # add roster entries
            await roster._create_database_if_needed()
            await roster.create_table_if_needed()
            await roster.add_user_id(test_user, roster1)
            await roster.add_user_id(test_user, roster2)

            count = await roster.count(test_user)
            self.assertEqual(count, 2)
            count = await roster.count()
            self.assertEqual(count, 2)

            # find roster
            async for user_id in roster.find_user_ids(test_user):
                roster_set.remove(user_id)

            self.assertEqual(roster_set, set())

            # delete roster
            await roster.delete_user_id(test_user, roster1)
            await roster.delete_user_id(test_user, roster2)
            count = await roster.count(test_user)
            self.assertEqual(count, 0)

            deleted = await users.remove_account(test_user)
            self.assertEqual(deleted, 1)
            count = await users.count()
            self.assertEqual(count, 1)
        finally:
            users.close()
            roster.close()
            await users._drop_database()
