"""
DB_logger.py — saves the results of every evaluation script
(valuation, growth, profitability, ...) to the database.

Works with any QuantParameter subclass: the object says which table to use
(TABLE_NAME) and what to save (to_record()), so no new code is needed here
when a new evaluation is added.

Usage from another script:
    from DB_logger import DBLogger
    logger = DBLogger()           # once, before the loop
    logger.log(valuation_obj)     # once per ticker, any evaluation object
"""

import logging
import os
import sqlite3
import sys
from datetime import date

# config.py lives in the repo root, two levels up from data/quant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import QUANT_DB_PATH
log = logging.getLogger("DB_logger")



class DBLogger:
    def __init__(self, db_path=QUANT_DB_PATH):
        # Open the connection to the database once
        try:
            self.connection = sqlite3.connect(db_path)
        except sqlite3.Error as e:
            log.error(f"Error connecting to database: {e}")
            raise


    def create_table(self, table_name, columns):
    # Date column first (added by the logger), then the object's own columns
        all_columns = ["date TEXT NOT NULL"] + list(columns)
        cols_text = ", ".join(all_columns)
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_text}, PRIMARY KEY (date, ticker))"
        try:
            self.connection.execute(sql)
            self.connection.commit()
            log.info(f"Table {table_name} created or already exists.")
        except sqlite3.Error as e:
            log.error(f"Error creating table {table_name}: {e}")
            

    def log_row(self, table_name, dictionary):
        # Save one dictionary as one row of table_name
        today = date.today().isoformat()
        sql = f"INSERT OR REPLACE INTO {table_name} (date, {', '.join(dictionary.keys())}) VALUES (?, {', '.join(['?'] * len(dictionary))})"
        values = [today] + list(dictionary.values())
        try:
            self.connection.execute(sql, values)
            self.connection.commit()
            log.info(f"Row logged in {table_name}: {dictionary}")
        except sqlite3.Error as e:
            log.error(f"Error logging row in {table_name}: {e}")
            raise   # let log() know the save failed

    # log any quant evaluation object into the database
    def log(self, obj):
        try:
            parameters = obj.to_record()
            table_name = obj.TABLE_NAME
            self.log_row(table_name, parameters)
            log.info(f"Logged {obj.ticker} to {table_name}")
        except sqlite3.Error:
            pass   # database error: already logged by log_row
        except Exception as e:
            # anything else (e.g. to_record failed) is not logged anywhere else
            log.error(f"Error logging {obj.ticker}: {e}")

    def close(self):
        # Close the connection once, after the last ticker
        self.connection.close()
