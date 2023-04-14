import unittest
import getpass
from database import Database
from mysql.connector.errors import ProgrammingError
import datetime


class TestCommon(unittest.TestCase):
    _username = input("User: ")
    _password = getpass.getpass("Password: ")


class TestDBInit(TestCommon):

    def setUp(self):
        self._connection = {"user": self._username, "passwd": self._password}

    def test_create_db_success(self):
        db = Database(self._connection)

    def test_create_db_bad_user(self):
        self._connection["user"] = "invalid"
        with self.assertRaises(ProgrammingError):
            db = Database(self._connection)

    def test_create_db_bad_password(self):
        self._connection["passwd"] = "invalid"
        with self.assertRaises(ProgrammingError):
            db = Database(self._connection)
            

class TestDBExecute(TestCommon):

    def setUp(self):
        self._connection = {"user": self._username, "passwd": self._password}

    def test_execute_select_good(self):
        select_sql = "SELECT * FROM test.selecttest;"
        results = Database(self._connection).select(select_sql)
        self.assertTrue(isinstance(results, list)
                        & len(results) > 0
                        & isinstance(results[0], dict))
    
    def test_execute_select_bad(self):
        select_sql = ("INSERT INTO test.inserttest(varcharcol, datecol, intcol)"
                      " VALUES ('a string', '2021-2-3', 3);")
        with self.assertRaises(ValueError):
            Database(self._connection).select(select_sql)

    def test_execute_select_multiple(self):
        select_sql = ("SELECT * from test.selecttest;\nSELECT * from "
                      "test.selecttest;")
        with self.assertRaises(ValueError):
            Database(self._connection).select(select_sql)
        
    def test_execute_insert_good(self):
        select_sql = "SELECT * FROM test.inserttest;"
        length_before = len(Database(self._connection).select(select_sql))
        insert_sql = ("INSERT INTO test.inserttest(varcharcol, datecol, intcol)"
                      " VALUES ('a string', '2021-2-3', 3);")
        inserted_count = Database(self._connection).insert(insert_sql)
        self.assertEqual(length_before + inserted_count,
                         len(Database(self._connection).select(select_sql)))

    def test_execute_insert_bad(self):
        insert_sql = "SELECT * FROM test.inserttest;"
        with self.assertRaises(ValueError):
            Database(self._connection).insert(insert_sql)

    def test_execute_update_good(self):
        update_sql = ("UPDATE test.updatetest SET varcharcol = 'UPDATED', "
                      "datecol = '{}' WHERE id "
                      "= 1").format(datetime.date.today())
        update_count = Database(self._connection).update(update_sql)
        select_sql = "SELECT * FROM test.updatetest WHERE id = 1"
        results = Database(self._connection).select(select_sql)
        print(results[0]['datecol'].date())
        print(datetime.date.today())
        print(len(results) > 0)
        print(update_count == 1)
        self.assertTrue((len(results) > 0)
                         & (update_count == 1)
                         & (results[0]['varcharcol'] == 'UPDATED')
                         & (results[0]['datecol'].date() == datetime.date.today()))
        
    def test_execute_update_bad(self):
        update_sql = "SELECT * FROM test.updatetest;"
        with self.assertRaises(ValueError):
            Database(self._connection).insert(update_sql)

if __name__ == '__main__':
    unittest.main()
    # hwXcKx252h^P