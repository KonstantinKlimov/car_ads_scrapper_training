import pymssql

from bs4 import BeautifulSoup
import requests
import json
import time


start_time = time.time()

headers = requests.utils.default_headers()
headers.update({
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'TGTG/22.2.1 Dalvik/2.1.0 (Linux; U; Android 9; SM-G955F Build/PPR1.180610.011)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive'
})

DEFAULT_HEADER = headers
SOURCE_ID = "https://www.cars.com"
PROCESS_DESC = "cards_finder_cars_com.py"


def get_card_url_list(url, site_url=SOURCE_ID, headers=DEFAULT_HEADER):
    url_list = []

    page = requests.get(url, headers=headers)
    if page.status_code == 200:
        soup = BeautifulSoup(page.text, "html.parser")

        listing_items = soup.find_all("div", class_="vehicle-card")
        try:
            for item in listing_items:
                item_href = item.find("a", class_="image-gallery-link")["href"]
                url_list.append(site_url + item_href)
        except:
            pass

    return url_list


def init_db_connection(con, sql_script_path):
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


def main():
    with open("config.json") as config_file:
        configs = json.load(config_file)

    con = pymssql.connect(**configs["mssql_audit_db"], autocommit=True)

    init_db_connection(con, configs.get("mssql_finder_init_db_script"))

    with con:
        cur = con.cursor()

        cur.execute(
            f"""
                insert into process_log(process_desc, [user], host, connection_id)         
                select '{PROCESS_DESC}', 
                       SYSTEM_USER, 
                       HOST_NAME(),
                       @@spid;
            """
        )
        cur.execute("select scope_identity() as process_log_id;")
        process_log_id = cur.fetchone()[0]

        curr_year = int(time.strftime("%Y", time.gmtime()))
        page_size = 20

        num = 0
        for year in range(curr_year, 1900, -1):
            for price_usd in range(0, 500001, 10000):
                for page_num in range(1, 500):
                    num += 1

                    group_url = f"{SOURCE_ID}/shopping/results/?list_price_max={price_usd + 9999}&list_price_min={price_usd}&maximum_distance=all&page_size={page_size}&page={page_num}&stock_type=used&year_max={year}&year_min={year}&zip=60606"

                    card_url_list = get_card_url_list(group_url)

                    print(f"time: {time.strftime('%X', time.gmtime(time.time() - start_time))}, num: {num}, num cards: {len(card_url_list)}, url: {group_url}")

                    if card_url_list == []:
                        print(f"time: {time.strftime('%X', time.gmtime(time.time() - start_time))}, no cards found")
                        break

                    cur.execute(f"insert into ad_groups(group_url, process_log_id) values(N'{group_url}', {process_log_id});")
                    cur.execute("select scope_identity() as ad_group_id;")
                    ad_group_id = cur.fetchone()[0]

                    for card_url in card_url_list:
                        cur.execute(
                            f"""
                                with cte_new_card
                                as
                                ( 
                                    select N'{card_url[len(SOURCE_ID):]}' as card_url
                                )
                                insert into ads(source_id, card_url, ad_group_id, insert_process_log_id)
                                select N'{SOURCE_ID}' as source_id, 
                                       card_url, 
                                       {ad_group_id} as ad_group_id, 
                                       {process_log_id} as insert_process_log_id
                                from cte_new_card
                                where card_url not in (select card_url from ads where source_id=N'{SOURCE_ID}');
                            """
                        )

                    if len(card_url_list) < page_size:
                        break

        print(f"\nend time (GMT): {time.strftime('%X', time.gmtime())}")

        cur.execute(
            f"""
                update process_log 
                    set end_date = getdate() 
                where process_log_id = {process_log_id};
            """
        )


if __name__ == "__main__":
    main()
