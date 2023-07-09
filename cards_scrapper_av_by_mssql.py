import pymssql

from bs4 import BeautifulSoup
import requests
import time
import json

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
PROCESS_DESC = "cards_scrapper_av_by.py"
MIN_RESCRAP_TIME = 24


def get_info_from_next_data(text):
    next_data = json.loads(text)

    advert = next_data["props"]["initialState"]["advert"]["advert"]

    advert_id = advert["id"]
    publicUrl = advert["publicUrl"]

    # photos =  {}
    # photos["id"] = advert_id
    # photos["publicUrl"] = publicUrl
    # photos["photos"] = advert["photos"].copy()

    # properties = {}
    # properties["id"] = advert_id
    # properties["publicUrl"] = publicUrl
    # properties["properties"] = advert["properties"].copy()

    similarAdverts = [{"id": ad["id"], "publicUrl": ad["publicUrl"]} for ad in next_data["props"]["initialState"]["advert"]["similarAdverts"]]

    return advert, similarAdverts


def get_parsed_card(url, debug=0, headers=DEFAULT_HEADER):
    card_dict = {}

    page = requests.get(url, headers=headers)
    # if debug:
    #     print(page.status_code,"\n")

    if page.status_code == 200:
        page_text = page.text.replace("<!-- -->", "")
        soup = BeautifulSoup(page_text, "html.parser")

        card = soup.find("div", class_="card")
        # print(card,"\n")

        card_gallery = card.find("div", class_="gallery__stage-shaft")
        card_dict["gallery"] = []
        # if debug:
        #     print("Галлерея")
        try:
            for div_img in card_gallery.find_all("div", class_="gallery__frame"):
                img = div_img.find("img")
                # if debug:
                #     print(img["data-srcset"])
                card_dict["gallery"].append(img["data-srcset"].split()[0])
        except:
            pass

        try:
            card_title = card.find(class_="card__title")
            card_dict["title"] = card_title.text
        except:
            card_dict["title"] = ""

        # if debug:
        #     print(f"card_title: {card_title.text}")

        card_price_primary = card.find(class_="card__price-primary")
        # if debug:
        #     print(f"card_price_primary: {card_price_primary.text}")
        try:
            card_dict["price_primary"] = card_price_primary.text
        except:
            card_dict["price_primary"] = ""

        card_price_secondary = card.find(class_="card__price-secondary")
        # if debug:
        #     print(f"card__price-secondary: {card_price_secondary.text}")
        try:
            card_dict["price_secondary"] = card_price_secondary.text
        except:
            card_dict["price_secondary"] = ""

        card_comment = card.find("div", class_="card__comment-text")
        # if debug:
        #     print(f"card_comment: {card_comment.text}")
        try:
            card_dict["comment"] = card_comment.get_text(separator='|', strip=True).replace("\n", " ").replace("\r", " ")
        except:
            card_dict["comment"] = ""

        card_location = card.find("div", class_="card__location")
        try:
            card_dict["location"] = card_location.text
        except:
            card_dict["location"] = ""

        labels = []
        card_labels = card.find("div", class_="card__labels")
        try:
            # check why does exception happen
            for div in card_labels.find_all("div"):
                if div.has_attr('class') and len(div['class']) > 1 and div['class'][1] in ["badge--top", "badge--parts", "badge--wreck", "badge--vin", "badge--new"]:
                    if  div['class'][1] == "badge--top":
                        labels += ["Top"]
                    else:
                        labels += [div.text]
        except:
            pass
        card_dict["labels"] = "|".join(labels)

        try:
            card_params = card.find("div", class_="card__params")
            card_dict["description"] = card_params.text
        except:
            card_dict["description"] = ""

        try:
            card_description = card.find("div", class_="card__description")
            card_dict["description"] += (" | " if card_dict["description"] != "" else "") + card_description.text
        except:
            pass

        # if debug:
        #     print(f"card_description: {card_params.text}\n{card_description.text}")

        try:
            card_exchange = card.find(class_="card__exchange-title")
            card_dict["exchange"] = card_exchange.text
        except:
            card_dict["exchange"] = ""

        # if debug:
        #     print(f"card_exchange: {card_exchange.text}")


        card_options = card.find(class_="card__options-wrap")
        card_dict["options"] = []
        # print(card_options)

        try:
            for section in card_options.find_all("div", class_="card__options-section"):
                section_dict = {}

                category = section.find(class_="card__options-category")
                # if debug:
                #     print(f"category: {category.text}")
                section_dict["category"] = category.text

                section_dict["items"] = []
                for option in section.find_all(class_="card__options-item"):
                    # if debug:
                    #     print(f"   - {option.text}")
                    section_dict["items"].append(option.text)

                card_dict["options"].append(section_dict)
        except:
            pass

        card_dict["json"] = {}
        try:
            next_data = soup.find("script", id="__NEXT_DATA__")
            advert, similarAdverts = get_info_from_next_data(next_data.text)

            card_dict["json"]["advert"] = advert
            # card_dict["json"]["photos"] = photos
            # card_dict["json"]["properties"] = properties
            card_dict["json"]["similarAdverts"] = similarAdverts
        except:
            pass
        #
        # if debug:
        #     print("\n",str(card_dict).replace("\\xa0", " ").replace("\\u2009", " "))

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


def json_corrected(json):
    if not (isinstance(json, dict) or isinstance(json, list)):
        result = str(json) \
                    .replace("\xa0", " ") \
                    .replace("\u2009", " ") \
                    .replace("\u2013", "-") \
                    .replace("\u2026", "") \
                    .replace('"', '``') \
                    .replace("'", '`') \
                    .replace("\n", "|")

    if isinstance(json, dict):
        result = {}

        for key, value in json.items():
            result[key] = json_corrected(value)

    if isinstance(json, list):
        result = []

        for el in json:
            result += [json_corrected(el)]

    return result


def main():
    with open("config.json") as config_file:
        configs = json.load(config_file)

    con = pymssql.connect(**configs["mssql_audit_db"], autocommit=True)

    init_db_connection(con, configs.get("mssql_scrapper_init_db_script"))

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
                                (ad_status = 2 and datediff(hour, change_status_date, getdate()) > {MIN_RESCRAP_TIME})
                              ) and source_id = N'{SOURCE_ID}'
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
                                (ad_status = 2 and datediff(hour, change_status_date, getdate()) > {MIN_RESCRAP_TIME})
                              ) and source_id = N'{SOURCE_ID}';
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
                            select top 1 
                                   ad_group_id as ad_group_id
                            from ads
                            where (
                                    ad_status = 0 or 
                                    (ad_status = 2 and datediff(hour, change_status_date, getdate()) > {MIN_RESCRAP_TIME})
                                  ) and 
                                  source_id = N'{SOURCE_ID}' and
                                  ad_group_id >= {random_ad_group_id}
                        )
                        select a.ads_id, concat(a.source_id, a.card_url) as url, g.group_url 
                        from ads a
                        join ad_groups g on a.ad_group_id = g.ad_group_id
                        join cte_random_group rg on g.ad_group_id = rg.ad_group_id    
                        where a.ad_status = 0 or 
                              (ad_status = 2 and datediff(hour, change_status_date, getdate()) > {MIN_RESCRAP_TIME});                    
                    """
            )
            if cur.rowcount == 0:
                break

            records_fetched = cur.fetchall()

            for ads_id, url, group_url in records_fetched:
                num += 1

                url_parts = url.split("?")

                parsed_card = {}
                ad_status = None
                try:
                    if len(url_parts) == 1:
                        parsed_card = get_parsed_card(url)
                except:
                    # error when parsing the card (url)
                    ad_status = -1

                card = {}
                if parsed_card != {}:
                    # successfully parsed the card (url)
                    ad_status = 2

                    card = json_corrected(parsed_card)

                    card = f"{card}" \
                        .replace("'", '"') \
                        .replace("`", "'") \
                        .replace(": False", ": 0") \
                        .replace(": True", ": 1")

                try:
                    print(f"{time.strftime('%X', time.gmtime(time.time() - start_time))}, {ad_status}, num: {num}, ads_id: {ads_id}, year: {parsed_card['description'][:4]}, card size: {len(card)}, {url}")

                    sql_string = f"""
                            update ads
                               set ad_status = {ad_status},
                                   change_status_date = getdate(),
                                   change_status_process_log_id = {process_log_id},
                                   card = N'{card}'
                            where ads_id = {ads_id};
                        """
                    cur.execute(sql_string)
                except:
                    if card == '{}':
                        ad_status = 1
                    else:
                        ad_status = -1

                    print(f"{time.strftime('%X', time.gmtime(time.time() - start_time))}, {ad_status}, num: {num}, ads_id: {ads_id}, year: -, card size: {len(card)}, {url}")

                    sql_string = f"""
                            update ads
                               set ad_status = {ad_status},
                                   change_status_date = getdate(),
                                   change_status_process_log_id = {process_log_id}                                   
                            where ads_id = {ads_id};
                        """
                    cur.execute(sql_string)


        cur.execute(
            f"""
                update process_log 
                    set end_date = getdate() 
                where process_log_id = {process_log_id};
            """
        )


if __name__ == "__main__":
    main()
