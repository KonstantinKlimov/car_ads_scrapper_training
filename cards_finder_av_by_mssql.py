import pymssql

from bs4 import BeautifulSoup
import requests
import json
import time


start_time = time.time()

headers = requests.utils.default_headers()
headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive"
})

DEFAULT_HEADER = headers
SOURCE_ID = "https://cars.av.by"
PROCESS_DESC = "cards_finder_av_by.py"


def get_card_url_list(url, site_url=SOURCE_ID, headers=DEFAULT_HEADER):
    url_list = []

    page = requests.get(url, headers=headers)
    if page.status_code == 200:
        soup = BeautifulSoup(page.text, "html.parser")

        listing_top = soup.find_all("div", class_="listing-top")
        try:
            for item in listing_top:
                item_href = item.find("a", class_="listing-top__title-link")["href"]
                url_list.append(site_url + item_href)
        except:
            pass



        listing_items = soup.find_all("div", class_="listing-item")
        try:
            for item in listing_items:
                item_href = item.find("a", class_="listing-item__link")["href"]
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
                select N'{PROCESS_DESC}', 
                       SYSTEM_USER, 
                       HOST_NAME(),
                       @@spid;
            """
        )
        cur.execute("select scope_identity() as process_log_id;")
        process_log_id = cur.fetchone()[0]

        curr_year = int(time.strftime("%Y", time.gmtime()))
        page_size = 25

        num = 0
        for year in range(curr_year, 1900, -1):
            for price_usd in range(0, 500001, 10000):
                for page_num in range(1, 501):
                    num += 1

                    group_url = f"{SOURCE_ID}/filter?year[min]={year}&year[max]={year}&price_usd[min]={price_usd}&price_usd[max]={price_usd + 9999}&page={page_num}"

                    card_url_list = get_card_url_list(group_url)

                    print(f"time: {time.strftime('%X', time.gmtime(time.time() - start_time))}, num: {num}, num cards: {len(card_url_list)}, url: {group_url}")

                    if card_url_list == []:
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
