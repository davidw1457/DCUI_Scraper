import bs4
from selenium import webdriver
from selenium.webdriver.common.by import By
import datetime
import time
import database
import getpass
import re
import logging

class DCUIScraper:

    _SCROLL_UP = "window.scrollTo(0,document.body.scrollHeight-100)"
    _SCROLL_TO_BOTTOM = ("window.scrollTo(0,document.body.scrollHeight);var "
                         "lenOfPage=document.body.scrollHeight;return "
                         "lenOfPage;")
    _SCROLL_TO_TOP = "window.scrollTo(0,0)"
    _months = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
               "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
               "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"}
    FIELD_UPDATE = {}

    def __init__(self, user, password, databaseName="dcui"):
        connection = {"database": databaseName, "user": user
                      , "password": password}
        self._dcui_database = database.Database(connection)
        self.FIELD_UPDATE["publication_date"] = self._update_publication_date
        logging.basicConfig(filename="dcui_scraper.log",
                            format="%(asctime)s %(message)s",
                            filemode="w")

    def update_all_series(self):
        source = self._open_page(("https://www.dcuniverseinfinite.com/browse/"
                                 "comics"), True)
        series_count = len(source
                           .find_all(class_ = "thumbnail__description-container"))
        current_series = 0
        for series in source.find_all(class_=
                                    "thumbnail__description-container"):
            current_series += 1
            series_metadata = {}
            series_metadata["series_title"] = (series
                                                .find("h3")
                                                .next_element
                                                .replace("'","''"))
            series_metadata["series_url"] = ("https://www."
                                                "dcuniverseinfinite.com"
                                                + series.find("a")["href"])
            series_metadata["series_url_id"] = (series_metadata
                                                ["series_url"][-36:])
            series_metadata["date_updated"] = (datetime
                                                .datetime
                                                .today()
                                                .date())
            logging.info(("Updating series {current_series} of {series_count}: "
                          "Title: {series_title} URL: {series_url}")
                          .format(current_series = current_series,
                                  series_count = series_count,
                                  **series_metadata))
            
            sql = ("SELECT date_updated FROM series WHERE series_url_id = "
                   "'{series_url_id}';").format(**series_metadata)
            results = self._dcui_database.select(sql)
            if (len(results) > 0 and
                results[0]["date_updated"] == series_metadata["date_updated"]):
                continue

            series_metadata["issue_count"] = (self
                                              ._get_issue_count
                                              (series_metadata["series_url_id"]))

            sql = ("SELECT series_id, issue_count FROM series WHERE "
                    "series_title = '{series_title}' AND series_url = "
                    "'{series_url}';").format(**series_metadata)
            results = self._dcui_database.select(sql)

            if len(results) == 0:
                sql = (("SELECT series_url_id FROM series WHERE "
                        "series_url_id = '{series_url_id}';")
                        .format(**series_metadata))
                results = self._dcui_database.select(sql)
                if len(results) == 0:
                    sql = ("INSERT INTO series (series_title, series_url, "
                            "series_url_id, issue_count, date_updated) "
                            "VALUES ('{series_title}', '{series_url}', "
                            "'{series_url_id}', {issue_count}, "
                            "'{date_updated}');").format(**series_metadata)
                    self._dcui_database.insert(sql)
            else:
                series_metadata["series_id"] = results[0]["series_id"]
            
                if (int(results[0]["issue_count"]) !=
                        series_metadata["issue_count"]):
                    sql = (("UPDATE series SET issue_count = "
                            "{issue_count}, date_updated = "
                            "'{date_updated}', need_update = 1 WHERE "
                            "series_id = {series_id};")
                            .format(**series_metadata))
                else:
                    sql = (("UPDATE series SET date_updated = "
                            "'{date_updated}', need_update = 0 WHERE "
                            "series_id = {series_id};")
                            .format(**series_metadata))
                
                self._dcui_database.update(sql)
    
    def update_all_issues(self):
        sql = ("SELECT series_id, series_url, issue_count, series_url_id FROM "
               "series WHERE need_update = 1;")
        results = self._dcui_database.select(sql)
        series_count = len(results)
        current_series = 0
        for row in results:
            current_series += 1
            logging.info(("Updating issues for series {current_series} of "
                          "{series_count}: series_id: {series_id} series_url: "
                          "{series_url}").format(current_series = current_series,
                                                 series_count = series_count,
                                                 **row))
            self.update_issues(**row)

    def update_issues(self, series_id, series_url, issue_count, series_url_id):
        source = self._open_page(series_url, True, True)
        
        for item in zip((source.find_all
                         (class_="thumbnail__description-container")),
                         source.find_all(class_="thumbnail__container")):
            issue_metadata = {}
            issue_metadata["series_id"] = series_id
            issue_metadata["issue_title"] = (item[0]
                                             .find("h3")
                                             .next_element
                                             .replace("'","''"))
            issue_metadata["issue_url"] = ("https://www.dcuniverseinfinite.com"
                                           + item[0].find("a")["href"])
            issue_metadata["issue_url_id"] = issue_metadata["issue_url"][-38:-2]
            pub_date = item[0].find(class_="thumbnail__meta").find("span")
            if pub_date is None:
                issue_metadata["publication_date"] = "1901-01-01"
            else:
                pub_date = pub_date.next_element.strip().split(" ")
                if (len(pub_date) == 3) & (pub_date[0].upper() in self._months):
                    pub_date[1] = pub_date[1].strip(",")
                    pub_date[0] = self._months[pub_date[0].upper()]
                    issue_metadata["publication_date"] = (pub_date[2]
                                                          + '-' + pub_date[0]
                                                          + '-' + pub_date[1])
                else:
                    issue_metadata["publication_date"] = "1901-01-01"
            subscription = item[1].find(class_="display-badge plan-badge")
            if subscription is None:
                issue_metadata["subscription"] = "Basic"
            else:
                issue_metadata["subscription"] = subscription.next_element
            sql = (("SELECT issue_id FROM issue WHERE series_id = "
                           "{series_id} and issue_url_id = '{issue_url_id}';")
                           .format(**issue_metadata))
            results = self._dcui_database.select(sql)
            if len(results) == 0:
                insert_sql = ("INSERT INTO issue (series_id, issue_title, "
                              "publication_date, issue_url, issue_url_id, "
                              "subscription) VALUES ({series_id}, "
                              "'{issue_title}', '{publication_date}', "
                              "'{issue_url}', '{issue_url_id}', "
                              "'{subscription}')").format(**issue_metadata)
                self._dcui_database.insert(insert_sql)
                results = self._dcui_database.select(sql)
                issue_id = results[0]["issue_id"]

                creators = item[0].find(class_="thumbnail__people").find("span")
                if creators is not None:
                    creators = creators.next_element.strip().split(", ")
                    for x in range(len(creators)):
                        creators[x] = creators[x].replace("'","''")
                        sql = ("SELECT creator_id FROM creator WHERE "
                               "creator_name = '{}';").format(creators[x])
                        results = self._dcui_database.select(sql)
                        if len(results) == 0:
                            insert_sql = ("INSERT INTO creator (creator_name) "
                                          "VALUES ('{}');").format(creators[x])
                            self._dcui_database.insert(insert_sql)
                            results = self._dcui_database.select(sql)
                        creators[x] = results[0]["creator_id"]
                
                for creator in creators:
                    insert_sql = (("INSERT INTO issues_creators (issue_id, "
                                  "creator_id) VALUES ({}, {});")
                                  .format(issue_id, creator))
                    self._dcui_database.insert(insert_sql)

        sql = ("SELECT count(*) as database_count FROM issue WHERE "
                f"series_id = {series_id};")
        results = self._dcui_database.select(sql)
        if results[0]["database_count"] != issue_count:
            self.update_issues_fallback(series_id, series_url_id)
        else:
            sql = ("UPDATE series SET need_update = 0 WHERE series_id = "
                    f"{series_id};")
            self._dcui_database.update(sql)

    def update_issues_fallback(self, series_id, series_url_id):
        source = self._open_page(("https://www.dcuniverseinfinite.com/"
                        f"browse/comics?series={series_url_id}"), True)
        for item in zip((source.find_all
                         (class_="thumbnail__description-container")),
                         source.find_all(class_="thumbnail__container")):
            issue_metadata = {}
            issue_metadata["series_id"] = series_id
            issue_metadata["issue_title"] = (item[0]
                                             .find("h3")
                                             .next_element
                                             .replace("'","''"))
            issue_metadata["issue_url"] = ("https://www.dcuniverseinfinite.com"
                                           + item[0].find("a")["href"])
            issue_metadata["issue_url_id"] = issue_metadata["issue_url"][-38:-2]
            subscription = item[1].find(class_="display-badge plan-badge")
            if subscription is None:
                issue_metadata["subscription"] = "Basic"
            else:
                issue_metadata["subscription"] = subscription.next_element

            sql = ("SELECT issue_url_id FROM issue WHERE issue_url_id = "
                   "'{issue_url_id}';").format(**issue_metadata)
            results = self._dcui_database.select(sql)
            if len(results) == 0:
                issue_metadata["publication_date"] = (self._get_publication_date
                                                      (**issue_metadata))
                insert_sql = ("INSERT INTO issue (series_id, issue_title, "
                              "publication_date, issue_url, issue_url_id, "
                              "subscription) VALUES ({series_id}, "
                              "'{issue_title}', '{publication_date}', "
                              "'{issue_url}', '{issue_url_id}', "
                              "'{subscription}')").format(**issue_metadata)
                self._dcui_database.insert(insert_sql)

    def update_subset(self, select_criteria, update_field):
        if self.FIELD_UPDATE.get(update_field) == None:
            raise NotImplementedError
        
        sql = (f"SELECT issue_id, issue_url, {update_field} FROM issue WHERE "
               f"{select_criteria};")
        results = self._dcui_database.select(sql)
        func = self.FIELD_UPDATE.get(update_field)
        func(results)

    def _update_publication_date(self, records):
        for record in records:
            publication_date = self._get_publication_date(record["issue_url"])
            if (publication_date != str(record["publication_date"])):
                issue_id = record["issue_id"]
                sql = ("UPDATE issue SET publication_date = "
                       f"'{publication_date}' WHERE issue_id = {issue_id}")
                try:
                    self._dcui_database.update(sql)
                except:
                    print(f"SQL error: {sql}")

    @classmethod
    def _open_page(cls, url, fully_load=False, series_page = False):
        with webdriver.Chrome() as driver:
            driver.get(url)
            if fully_load:
                cls._fully_load(driver)
            if series_page:
                try:
                    for x in range(2, 4):
                        clickable = (driver
                                    .find_element
                                    (By.CSS_SELECTOR,
                                     f".tab-nav-item:nth-child({x})"))
                        (webdriver
                         .ActionChains(driver)
                         .click(clickable)
                         .perform())
                        cls._fully_load(driver)
                except:
                    pass
            return bs4.BeautifulSoup(markup=driver.page_source,
                                     features="html.parser")

    @classmethod
    def _get_publication_date(cls, issue_url, **kwargs):
        source = cls._open_page(issue_url)
        try:
            pub_date = (source
                        .find(class_=("comic-issue__info-container "
                                      "rating-released"))
                        .find(string=re.compile("Released\n"))
                        .strip()
                        .split(" ")[-3:])
            pub_date[1] = pub_date[1].strip(",")
            pub_date[0] = cls._months[pub_date[0].upper()]
            return pub_date[2] + '-' + pub_date[0]  + '-' + pub_date[1]
        except:
            return "1901-01-01"
            
    @classmethod
    def _fully_load(cls, driver):
        pageLen = -1
        newPageLen = driver.execute_script(cls._SCROLL_TO_BOTTOM)
        while pageLen != newPageLen:
            pageLen = newPageLen
            driver.execute_script(cls._SCROLL_UP)
            newPageLen = driver.execute_script(cls._SCROLL_TO_BOTTOM)
            time.sleep(1)
            if (pageLen == newPageLen):
                try:
                    clickable = (driver.find_element(
                                            By.ID,
                                            "embeddable-modal-accept-button"))
                    webdriver.ActionChains(driver).click(clickable).perform()
                except:
                    pass
                driver.execute_script(cls._SCROLL_TO_TOP)
                newPageLen = (driver
                              .execute_script(cls._SCROLL_TO_BOTTOM))
                time.sleep(1)
        driver.execute_script(cls._SCROLL_TO_TOP)
        time.sleep(1)
    
    @classmethod
    def _get_issue_count(cls, series_url_id):
        source = cls._open_page(("https://www.dcuniverseinfinite.com/browse/"
                                 f"comics?series={series_url_id}"))
        try:
            issue_count = int((source
                    .find(class_="category-name")
                    .next_element
                    .split("(")[1][:-1]))
            return issue_count
        except:
            print(f"Get Issue Count failed for {series_url_id}\n")
            return 0


def main():
    dcui_scraper = DCUIScraper(input("User: "), getpass.getpass("Password: "))
    dcui_scraper.update_all_series()
    dcui_scraper.update_all_issues()
    # dcui_scraper.update_subset(select_criteria="publication_date='1901-01-01'"
    #                            , update_field="publication_date")

if __name__ == "__main__":
    main()