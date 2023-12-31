import argparse
import math
from datetime import datetime
import json
import pymysql
import time



DEFAULT_THREAD_ID = 16

STORAGE_CMD_DB = 0
STORAGE_CMD_LOCAL = 1

EXEC_INIT_SCRIPT = 1
NOT_EXEC_INIT_SCRIPT = 0

LEVEL_MSG_SHOW_CONSOLE_0 = 0  # Do not show message in console
LEVEL_MSG_SHOW_CONSOLE_1 = 1  # ! Show start time, counter commands and percent
LEVEL_MSG_SHOW_CONSOLE_2 = 2  # Show message with time and counter
LEVEL_MSG_SHOW_CONSOLE_3 = 3  # Show message with time, counter and SQL command

def get_args():
    """Get args command line"""

    parser = argparse.ArgumentParser(
        description="The script simulates workload on MySQL by reading slow_log"
    )

    parser.add_argument(
        "-thread_id", type=int, default=DEFAULT_THREAD_ID, help="Thread_id number"
    )

    parser.add_argument(
        "-storage_cmd",
        type=int,
        default=STORAGE_CMD_LOCAL,
        help="Get commands from local storage or from database",
    )
    parser.add_argument(
        "-exec_init_script",
        type=int,
        default=NOT_EXEC_INIT_SCRIPT,
        help="Execute initialaze script database before simulate recorded workload",
    )
    parser.add_argument(
        "-level_show_console",
        type=int,
        default=LEVEL_MSG_SHOW_CONSOLE_1,
        help="Level of message for show in console",
    )

    args = parser.parse_args()
    return vars(args)


def init_db_simulate(con, sql_script_path):
    """Execute initialaze script database before simulate recorded workload"""

    result_code = 0

    if sql_script_path is not None:
        cur = con.cursor()
        with open(sql_script_path) as init_db_file:
            for sql_stmt in init_db_file.read().split(";"):
                try:
                    cur.execute(sql_stmt)
                except:
                    result_code = -1

    return result_code


def show_log_message(level_show_console, sql_cmd, len_workload, cnt):
    """Print log message in console"""
    if level_show_console == LEVEL_MSG_SHOW_CONSOLE_0:
        return

    if level_show_console == LEVEL_MSG_SHOW_CONSOLE_1:
        if math.floor((cnt-1)*100/len_workload) == math.floor(cnt*100/len_workload):
            return
        else:
            msg = f"{time.strftime('%X', time.gmtime())}, Progress: {round(cnt/len_workload*100)}%."

    if level_show_console in {LEVEL_MSG_SHOW_CONSOLE_2, LEVEL_MSG_SHOW_CONSOLE_3}:
        msg = f"{time.strftime('%X', time.gmtime())}, No of commands executed: {cnt} / {len_workload}."

    if level_show_console == LEVEL_MSG_SHOW_CONSOLE_3:
        msg += sql_cmd[:100] + ("..." if len(sql_cmd) > 100 else "")

    print(msg)


def exec_commands_local(level_show_console, cur):  
    """Get list all commands recorded workload from database, save locally and execute"""

    sql_cmd = f"""
                SELECT `sql_cmd`
                FROM `cmd_for_exec`
                ORDER BY `cmd_id` ASC;"""
    cur.execute(sql_cmd)

    stmts_sql_for_exec = cur.fetchall()

    len_workload = len(stmts_sql_for_exec)

    for cnt, stmt_sql in enumerate(stmts_sql_for_exec, start=1):
        sql_cmd = stmt_sql[0]
        execute_cmd(level_show_console, cur, sql_cmd, len_workload, cnt)


def exec_commands_from_db(level_show_console, cur):
    """Get list of commands recorded workload from database by one and execute"""

    sql_cmd = """SELECT COUNT(cmd_id) FROM `cmd_for_exec`"""
    cur.execute(sql_cmd)
    len_workload = cur.fetchone()[0]

    for idx in range(1, len_workload + 1):
        sql_cmd = f"""
                    SELECT `sql_cmd`
                    FROM `cmd_for_exec`
                    WHERE `cmd_id` = {idx};"""
        cur.execute(sql_cmd)

        row = cur.fetchone()
        sql_cmd = row[0]

        execute_cmd(level_show_console, cur, sql_cmd, len_workload, idx)


def execute_cmd(level_show_console, cur, sql_cmd, len_workload, idx):
    """Execute SQL statment and show log message"""

    show_log_message(level_show_console, sql_cmd, len_workload, idx)
    try:
        cur.execute(sql_cmd)
    except pymysql.err.DataError as e:
        print("Caught a pymysql.err.DataError exception:", e)


def create_and_fill_commands_table(db, slow_log_table, thread_id, cur):
    sql_cmd = """DROP TABLE IF EXISTS `cmd_for_exec`;"""
    cur.execute(sql_cmd)

    sql_cmd = """
                CREATE TEMPORARY TABLE IF NOT EXISTS `cmd_for_exec` (
                    `cmd_id` INT NOT NULL AUTO_INCREMENT,
                    `start_time` timestamp(6) NOT NULL,
                    `sql_cmd`  mediumtext NOT NULL,
                    `thread_id` bigint unsigned NOT NULL,
                    PRIMARY KEY (cmd_id)
                );"""
    cur.execute(sql_cmd)

    sql_cmd = f"""
                INSERT INTO `cmd_for_exec` (
                    `start_time`,
                    `sql_cmd`,
                    `thread_id`
                )
                SELECT
                    `start_time`,
                    CONVERT(`sql_text` USING utf8),
                    `thread_id`
                FROM {db}.{slow_log_table}
                WHERE `thread_id` = {thread_id}
                    AND CONVERT(`sql_text` USING utf8) <> ''
                    AND CONVERT(`sql_text` USING utf8) NOT LIKE "--%"
                    ORDER BY `start_time` ASC;"""
    cur.execute(sql_cmd)


def main():
    """Main function"""

    # Get args command line
    args_app = get_args()
    thread_id = args_app["thread_id"]
    exec_init_script = args_app["exec_init_script"]
    level_show_console = args_app["level_show_console"]
    storage_cmd = args_app["storage_cmd"]

    # Load app config
    with open("config.json") as config_file:
        configs = json.load(config_file)

    # Connect to database
    con = pymysql.connect(**configs["simulator_db"])
    print(f"{time.strftime('%X', time.gmtime())}, Connected to database")

    # Execute initialaze script database
    print(f"{time.strftime('%X', time.gmtime())}, Initializing...")
    if exec_init_script:
        init_db_simulate(con, configs.get("simulator_init_db"))
    print(f"{time.strftime('%X', time.gmtime())}, Initialized    ")

    with con:
        cur = con.cursor()

        # Create and fill table with commands for following execute
        print(f"{time.strftime('%X', time.gmtime())}, Creating and filling `cmd_for_exec` temporary table...")
        create_and_fill_commands_table("car_ads_training_db", "slow_log", thread_id, cur)
        print(f"{time.strftime('%X', time.gmtime())}, Done")

        start_time = time.time()
        print("-------------------------")
        print(f"{time.strftime('%X', time.gmtime())}, Simulating the workload (thread_id = {thread_id})")

        # Execute the workload commands from local storage (RAM) or from DB
        if storage_cmd == STORAGE_CMD_LOCAL:
            exec_commands_local(level_show_console, cur)
        elif storage_cmd == STORAGE_CMD_DB:
            exec_commands_from_db(level_show_console, cur)
        else:
            print(f"{time.strftime('%X', time.gmtime())}, Workload wasn't simulated")

    print(f"{time.strftime('%X', time.gmtime())}, Time spent by simulator (pure workload): {time.strftime('%X', time.gmtime(time.time() - start_time))}")
    print("-------------------------")

    print(f"{time.strftime('%X', time.gmtime())}, Done!")


if __name__ == "__main__":
    main()
