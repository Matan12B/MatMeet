import sqlite3


class DB:
    def __init__(self):
        self.DBname = "users.db"
        self.conn = None
        self.curr = None
        self._createDB()

    def _createDB(self):
        """
        connect db and create table if not exist
        """
        self.conn = sqlite3.connect(self.DBname, check_same_thread=False)
        self.curr = self.conn.cursor()

        sql = (
            "CREATE TABLE IF NOT EXISTS users ("
            "userName TEXT PRIMARY KEY, "
            "password TEXT)"
        )

        self.curr.execute(sql)
        self.conn.commit()

    def close(self):
        """
        Commit changes and close DB
        """
        self.conn.commit()
        self.conn.close()

    def user_exists(self, userName):
        """
        return user row if exists else None
        """
        sql = "SELECT userName FROM users WHERE userName = ?"
        self.curr.execute(sql, (userName,))
        return self.curr.fetchone()

    def add_user(self, userName, password):
        """
        add user to db
        """
        status = False

        if not self.user_exists(userName):
            sql = "INSERT INTO users VALUES (?, ?)"
            self.curr.execute(sql, (userName, password))
            self.conn.commit()
            status = True

        return status

    def update_password(self, userName, new_password):
        """
        update user password
        """
        status = False

        if self.user_exists(userName):
            sql = "UPDATE users SET password = ? WHERE userName = ?"
            self.curr.execute(sql, (new_password, userName))
            self.conn.commit()
            status = True

        return status

    def verify_user(self, userName, password):
        """
        check if username and password match
        """
        sql = "SELECT password FROM users WHERE userName = ?"
        self.curr.execute(sql, (userName,))
        row = self.curr.fetchone()

        if row and row[0] == password:
            return True

        return False

    def get_all_users(self):
        """
        return list of all usernames
        """
        sql = "SELECT userName FROM users"
        self.curr.execute(sql)

        names = []
        for user in self.curr.fetchall():
            names.append(user[0])

        return names


if __name__ == "__main__":
    myDB = DB()

    print("Adding user:", myDB.add_user("user1", "123456"))
    print("Verify:", myDB.verify_user("user1", "123456"))
    print("All users:", myDB.get_all_users())

    myDB.close()