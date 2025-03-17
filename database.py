import mysql.connector
from mysql.connector import Error
from PySide6.QtWidgets import QMessageBox
import json

class Database:
    def __init__(self):
        self.host = "localhost"
        self.user = "root"
        self.password = "root"  # Change this to your MySQL password
        self.database = "billing_system"
        self.connection = None
        self.check_mysql_server()
        self.setup_database()

    def check_mysql_server(self):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            connection.close()
        except Error as e:
            error_msg = f"""
MySQL Connection Error: {str(e)}

Please ensure:
1. MySQL Server is installed and running
2. MySQL credentials are correct in database.py:
   - host: {self.host}
   - user: {self.user}
   - password: {self.password}

To fix:
1. Install MySQL if not installed
2. Start MySQL service:
   - Windows: Open Services app and start MySQL
   - Command: net start MySQL80 (or your MySQL service name)
3. Update credentials in database.py if needed
"""
            QMessageBox.critical(None, "Database Error", error_msg)
            raise Exception("Failed to connect to MySQL server")

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False

    def setup_database(self):
        if self.connect():
            cursor = self.connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")
            
            # Create customers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    phone VARCHAR(15),
                    email VARCHAR(100),
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create bills table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bills (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    customer_id INT,
                    bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_amount DECIMAL(10, 2),
                    items_json TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)

            # Create items table for suggestions with default price
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    default_price DECIMAL(10, 2),
                    last_price DECIMAL(10, 2),
                    usage_count INT DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            self.connection.commit()
            cursor.close()
            self.connection.close()

    def get_connection(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            return self.connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None

    def add_customer(self, name, phone, email, address):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                # First check if customer exists with this phone number
                if phone:  # Only check if phone is provided
                    cursor.execute("SELECT id FROM customers WHERE phone = %s", (phone,))
                    existing_customer = cursor.fetchone()
                    
                    if existing_customer:
                        # Update existing customer
                        sql = """UPDATE customers 
                                SET name = %s, email = %s, address = %s 
                                WHERE id = %s"""
                        cursor.execute(sql, (name, email, address, existing_customer['id']))
                        connection.commit()
                        return existing_customer['id']
                
                # If no phone match or no phone provided, insert new customer
                sql = """INSERT INTO customers (name, phone, email, address) 
                        VALUES (%s, %s, %s, %s)"""
                cursor.execute(sql, (name, phone, email, address))
                connection.commit()
                return cursor.lastrowid
            except Error as e:
                print(f"Error: {e}")
                return None
            finally:
                cursor.close()
                connection.close()

    def get_customers(self):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM customers ORDER BY created_at DESC")
                return cursor.fetchall()
            except Error as e:
                print(f"Error: {e}")
                return []
            finally:
                cursor.close()
                connection.close()

    def add_bill(self, customer_id, total_amount, items_json):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                sql = """INSERT INTO bills (customer_id, total_amount, items_json) 
                        VALUES (%s, %s, %s)"""
                cursor.execute(sql, (customer_id, total_amount, items_json))
                connection.commit()
                return cursor.lastrowid
            except Error as e:
                print(f"Error: {e}")
                return None
            finally:
                cursor.close()
                connection.close()

    def get_bills(self):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                sql = """SELECT b.*, c.name as customer_name 
                        FROM bills b 
                        JOIN customers c ON b.customer_id = c.id 
                        ORDER BY bill_date DESC"""
                cursor.execute(sql)
                return cursor.fetchall()
            except Error as e:
                print(f"Error: {e}")
                return []
            finally:
                cursor.close()
                connection.close()

    def search_customers(self, search_term):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                # Search in name, phone, and email fields
                sql = """SELECT * FROM customers 
                        WHERE name LIKE %s 
                        OR phone LIKE %s 
                        OR email LIKE %s 
                        LIMIT 5"""
                search_pattern = f"%{search_term}%"
                cursor.execute(sql, (search_pattern, search_pattern, search_pattern))
                return cursor.fetchall()
            except Error as e:
                print(f"Error: {e}")
                return []
            finally:
                cursor.close()
                connection.close()

    def search_items(self, search_term):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                sql = """SELECT name, last_price, default_price 
                        FROM items 
                        WHERE name LIKE %s AND is_active = TRUE
                        ORDER BY usage_count DESC, last_used DESC 
                        LIMIT 5"""
                search_pattern = f"%{search_term}%"
                cursor.execute(sql, (search_pattern,))
                return cursor.fetchall()
            except Error as e:
                print(f"Error: {e}")
                return []
            finally:
                cursor.close()
                connection.close()

    def get_all_items(self):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                    SELECT id, name, default_price, last_price, usage_count, is_active 
                    FROM items 
                    ORDER BY name
                """)
                return cursor.fetchall()
            except Error as e:
                print(f"Error: {e}")
                return []
            finally:
                cursor.close()
                connection.close()

    def update_item_dictionary(self, item_id, name, default_price, is_active):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                if item_id:  # Update existing item
                    sql = """UPDATE items 
                            SET name = %s, default_price = %s, is_active = %s 
                            WHERE id = %s"""
                    cursor.execute(sql, (name, default_price, is_active, item_id))
                else:  # Add new item
                    sql = """INSERT INTO items (name, default_price, last_price, is_active) 
                            VALUES (%s, %s, %s, %s)"""
                    cursor.execute(sql, (name, default_price, default_price, is_active))
                connection.commit()
                return True
            except Error as e:
                print(f"Error: {e}")
                return False
            finally:
                cursor.close()
                connection.close()

    def delete_item(self, item_id):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                # Soft delete by setting is_active to False
                sql = "UPDATE items SET is_active = FALSE WHERE id = %s"
                cursor.execute(sql, (item_id,))
                connection.commit()
                return True
            except Error as e:
                print(f"Error: {e}")
                return False
            finally:
                cursor.close()
                connection.close()

    def update_item_usage(self, item_name, price):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                # Update if exists, insert if not
                sql = """INSERT INTO items (name, last_price, usage_count, last_used) 
                        VALUES (%s, %s, 1, CURRENT_TIMESTAMP)
                        ON DUPLICATE KEY UPDATE 
                        last_price = %s,
                        usage_count = usage_count + 1,
                        last_used = CURRENT_TIMESTAMP"""
                cursor.execute(sql, (item_name, price, price))
                connection.commit()
            except Error as e:
                print(f"Error: {e}")
            finally:
                cursor.close()
                connection.close()

    def clear_bills(self):
        """Clear all bills from the database"""
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM bills")
                connection.commit()
                cursor.close()
                connection.close()
                return True
            except Exception as e:
                print(f"Error clearing bills: {e}")
                return False

    def clear_customers(self):
        """Clear all customers from the database"""
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                # First, delete all bills (due to foreign key constraint)
                cursor.execute("DELETE FROM bills")
                # Then delete all customers
                cursor.execute("DELETE FROM customers")
                connection.commit()
                cursor.close()
                connection.close()
                return True
            except Exception as e:
                print(f"Error clearing customers: {e}")
                return False

    def delete_bill(self, bill_id):
        """Delete a specific bill by ID"""
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM bills WHERE id = %s", (bill_id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
            except Exception as e:
                print(f"Error deleting bill: {e}")
                return False 