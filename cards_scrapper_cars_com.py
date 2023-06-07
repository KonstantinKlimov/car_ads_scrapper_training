import pymysql

from bs4 import BeautifulSoup
import requests
import time
import json


start_time = time.time()

headers = requests.utils.default_headers()
headers.update({
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "TGTG/22.2.1 Dalvik/2.1.0 (Linux; U; Android 9; SM-G955F Build/PPR1.180610.011)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive"
})

DEFAULT_HEADER = headers
SOURCE_ID = "https://www.cars.com"
PROCESS_DESC = "cards_scrapper_cars_com.py"
MIN_RESCRAP_TIME = 24


def get_parsed_card(url, debug=0, headers=DEFAULT_HEADER):
    card_dict = {}

    page = requests.get(url, headers=headers)

    if page.status_code == 200:
        soup = BeautifulSoup(page.text, "html.parser")

        card = soup.find("section", class_="listing-overview")
        # print(card,"\n")
        if card is None:
            return {} # {} - empty result

        card_gallery = card.find("div", class_="modal-slides-and-controls")
        card_dict["gallery"] = []
        try:
            for img in card_gallery.find_all("img", class_="swipe-main-image"):
                card_dict["gallery"].append(img["src"])
        except:
            pass

        basic_content = soup.find("div", class_="basics-content-wrapper")

        basic_section = basic_content.find("section", class_="sds-page-section basics-section")
        fancy_description_list = basic_section.find("dl", class_="fancy-description-list")
        dt_elements = [elem.text.strip() for elem in fancy_description_list.find_all("dt")]
        dd_elements = [elem.get_text(separator='|', strip=True).split("|")[0] for elem in fancy_description_list.find_all("dd")]
        for key, value in zip(dt_elements, dd_elements):
            card_dict[key.lower()] = value

        card_dict["card_id"] = card_dict.get("stock #")
        if not card_dict["card_id"] or card_dict["card_id"] == "-":
            card_dict["card_id"] = card_dict.get("vin")
        if not card_dict["card_id"] or card_dict["card_id"] == "-":
            return {}

        # card_dict["url"] = url

        card_title = card.find(class_="listing-title")
        card_dict["title"] = card_title.text

        card_price_primary = card.find("div", class_="price-section")
        card_dict["price_primary"] = card_price_primary.find("span", class_="primary-price").text

        price_history = ""
        card_price_history = soup.find("div", class_="price-history")
        try:
            card_price_history_rows = card_price_history.find_all("tr")
            for row in card_price_history_rows:
                date, _, price = row.find_all("td")
                price_history += f"{date.text}: {price.text} | "

            card_dict["price_history"] = price_history[0:-2]
        except:
            card_dict["price_history"] = ""

        card_dict["options"] = []
        try:
            feature_content = basic_content.find("section", class_="sds-page-section features-section")
            fancy_description_list = feature_content.find("dl", class_="fancy-description-list")
            dt_elements = [elem.text.strip() for elem in fancy_description_list.find_all("dt")]
            dd_elements = [elem.get_text(separator='|', strip=True).split("|") for elem in fancy_description_list.find_all("dd")]
            for category, values in zip(dt_elements, dd_elements):
                section_dict = {}
                section_dict["category"] = category
                section_dict["items"] = values

                card_dict["options"].append(section_dict)

            all_features = basic_content.find("div", class_="all-features-text-container")
            section_dict = {}
            section_dict["category"] = "features"
            section_dict["items"] = all_features.get_text("|", True).split("|")
            card_dict["options"].append(section_dict)
        except:
            pass

        try:
            card_vehicle_history = basic_content.find("section", class_="sds-page-section vehicle-history-section")
            fancy_description_list = card_vehicle_history.find("dl", class_="fancy-description-list")
            dt_elements = [elem.text.strip() for elem in fancy_description_list.find_all("dt")]
            dd_elements = [elem.get_text(separator='|', strip=True) for elem in fancy_description_list.find_all("dd")]
            vehicle_history = ""
            for record, value in zip(dt_elements, dd_elements):
                vehicle_history += f"{record}: {value} | "

            card_dict["vehicle_history"] = vehicle_history[0:-2]
        except:
            card_dict["vehicle_history"] = ""

        card_comment = basic_content.find("div", class_="sellers-notes")
        try:
            card_dict["comment"] = card_comment.get_text(separator="|", strip=True).replace("\n", "|")
        except:
            card_dict["comment"] = ""

        card_location = basic_content.find("div", class_="dealer-address")
        try:
            card_dict["location"] = card_location.text
        except:
            card_dict["location"] = ""

        card_labels_div = card.find("div", class_="vehicle-badging")
        data_override_payload_json = json.loads(card_labels_div["data-override-payload"])
        card_dict["bodystyle"] = data_override_payload_json["bodystyle"]

        labels = []
        try:
            for div in card_labels_div.find_all("span", class_="sds-badge__label"):
                labels += [div.text]

            labels += ["VIN: " + card_dict["vin"]]

            if basic_content.find("section", "sds-page-section warranty_section"):
                labels += ["Included warranty"]
        except:
            pass
        card_dict["labels"] = "|".join(labels)

        mpg = ""
        try:
            mpg = card_dict.get("mpg").strip().replace('0–0', "")
            if mpg == "–":
                mpg = ""
        except:
            pass

        card_dict["description"] = card_dict["title"].split()[0] + ", " + \
                                   card_dict["transmission"].replace(",", " ") + ", " + \
                                   card_dict["engine"].replace(",", " ") + ", " + \
                                   card_dict["fuel type"].replace(",", " ") + \
                                   ((" (" + mpg + " mpg)") if mpg else "") + ", " + \
                                   card_dict["mileage"].replace(",", " ") +" | " + \
                                   card_dict["bodystyle"].replace(",", " ") + ", " + \
                                   card_dict["drivetrain"].replace(",", " ") + ", " + \
                                   card_dict["exterior color"].replace(",", " ")

        del card_dict["transmission"]
        del card_dict["engine"]
        del card_dict["fuel type"]
        del card_dict["mileage"]
        del card_dict["bodystyle"]
        del card_dict["drivetrain"]
        del card_dict["exterior color"]
        del card_dict["interior color"]
        if card_dict.get("mpg"):
            del card_dict["mpg"]
        del card_dict["vin"]
        if card_dict.get("stock #"):
            del card_dict["stock #"]

        # card_dict["exchange"] = ""

        card_dict["scrap_date"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    return card_dict


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

    con = pymysql.connect(**configs["audit_db"])

    init_db_connection(con, configs.get("init_db_script"))

    with con:
        cur = con.cursor()

        cur.execute(
            f"""
                insert into process_log(process_desc, user, host, connection_id)         
                select '{PROCESS_DESC}', 
                       user, 
                       host,
                       connection_id()
                from information_schema.processlist
                where id = connection_id();
            """
        )

        cur.execute("select last_insert_id() as process_log_id;")
        process_log_id = cur.fetchone()[0]

        num = 0
        while True:
            # get new portion of not yet scrapped urls having the same ad_group_id
            cur.execute(
                f"""
                    with cte_cars_com_ad_group_ids
                    as
                    (
                        select distinct ad_group_id
                        from ads 
                        where (
                                ad_status = 0 or 
                                (ad_status = 2 and timestampdiff(hour, change_status_date, current_timestamp) > {MIN_RESCRAP_TIME})
                              ) and source_id = '{SOURCE_ID}'
                    )
                    select floor(rand() * (select max(ad_group_id) from cte_cars_com_ad_group_ids)) as random_ad_group_id;
                """
            )

            random_ad_group_id = cur.fetchone()[0]
            if random_ad_group_id is None:
                # check if there is what to do
                cur.execute(
                    f"""
                        select *
                        from ads 
                        where (
                                ad_status = 0 or 
                                (ad_status = 2 and timestampdiff(hour, change_status_date, current_timestamp) > {MIN_RESCRAP_TIME})
                              ) and source_id = '{SOURCE_ID}';
                    """
                )
                if cur.rowcount > 0:
                    continue
                else:
                    break


            cur.execute(
                    f"""
                        with cte_random_group
                        as
                        (
                            select ad_group_id as ad_group_id
                            from ads
                            where (
                                    ad_status = 0 or 
                                    (ad_status = 2 and timestampdiff(hour, change_status_date, current_timestamp) > {MIN_RESCRAP_TIME})
                                  ) and 
                                  source_id = '{SOURCE_ID}' and
                                  ad_group_id >= {random_ad_group_id}
                            limit 1
                        )
                        select a.ads_id, concat(a.source_id, a.card_url) as url, g.group_url 
                        from ads a
                        join ad_groups g on a.ad_group_id = g.ad_group_id
                        join cte_random_group rg on g.ad_group_id = rg.ad_group_id    
                        where a.ad_status = 0 or 
                              (ad_status = 2 and timestampdiff(hour, change_status_date, current_timestamp) > {MIN_RESCRAP_TIME});                    
                    """
                )
            if cur.rowcount == 0:
                break

            records_fetched = cur.fetchall()

            for ads_id, url, group_url in records_fetched:
                num += 1

                url_parts = url.split("?")

                parsed_card = {}
                ad_status = 1
                try:
                    if len(url_parts) == 1:
                        parsed_card = get_parsed_card(url)
                except:
                    # error when parsing the card (url)
                    ad_status = -1

                if parsed_card != {}:
                    # successfully parsed the card (url)
                    ad_status = 2
                    card = json.dumps(parsed_card).replace("\\xa0", " ").replace("\\u2009", " ").replace("'", "''")

                try:
                    sql_string = f"""
                            update ads
                               set ad_status = {ad_status},
                                   change_status_date = current_timestamp,
                                   change_status_process_log_id = {process_log_id},
                                   card = '{card}'
                            where ads_id = {ads_id};
                        """
                    cur.execute(sql_string)

                    print(f"{time.strftime('%X', time.gmtime(time.time() - start_time))}, {ad_status}, num: {num}, ads_id: {ads_id}, year: {parsed_card['description'][:4]}, card size: {len(card)}, {url}")
                except:
                    ad_status = -1

                    sql_string = f"""
                            update ads
                               set ad_status = {ad_status},
                                   change_status_date = current_timestamp,
                                   change_status_process_log_id = {process_log_id}                                   
                            where ads_id = {ads_id};
                        """
                    cur.execute(sql_string)

                    print(f"{time.strftime('%X', time.gmtime(time.time() - start_time))}, {ad_status}, num: {num}, ads_id: {ads_id}, year: -, card size: {len(card)}, {url}")

        cur.execute(
            f"""
                update process_log 
                    set end_date = current_timestamp 
                where process_log_id = {process_log_id};
            """
        )


if __name__ == "__main__":
    main()
