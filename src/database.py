import mysql.connector

class Database():

    def __init__(self, connection):
        self._db = mysql.connector.connect(**connection)

    def __del__(self):
        try:
            self._db.close()
        except AttributeError:
            pass

    @staticmethod
    def _bad_statement(sql, type):
        if sql.split()[0] != type:
            return True
        elif ';' in sql[:-2]:
            return True
        return False

    def select(self, sql):
        sql = sql.strip()
        if Database._bad_statement(sql, "SELECT"):
            raise ValueError(f"{sql} is not a valid SELECT statement")
        with self._db.cursor(dictionary=True) as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
        
    def insert(self, sql):
        sql = sql.strip()
        if Database._bad_statement(sql, "INSERT"):
            raise ValueError(f"{sql} is not a valid INSERT statement")
        with self._db.cursor() as cursor:
            cursor.execute(sql)
            self._db.commit()
            return cursor.rowcount
        
    def update(self, sql):
        sql = sql.strip()
        if Database._bad_statement(sql, "UPDATE"):
            raise ValueError(f"{sql} is not a valid UPDATE statement")
        with self._db.cursor() as cursor:
            cursor.execute(sql)
            self._db.commit()
            return cursor.rowcount
