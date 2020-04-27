# -*- coding: utf-8 -*-
import csv
import time
from selenium import webdriver
from bs4 import BeautifulSoup
from decimal import Decimal
import requests
import pymongo
from selenium.webdriver.chrome.options import Options

# config
WEB_DRIVER_TIMEOUT = 0
MONGO_ACTIVE = False
RESET_DB = False
WEB_DRIVER_HEADLESS = True
TEST_RUN = False
ZIP_COUNTY_DATAFILE = "KSZipCodes.txt"
EXPORT_FILE = "HarvestersLocations.csv"

if MONGO_ACTIVE:
    # setup the database
    conn = 'mongodb://localhost:27017'
    client = pymongo.MongoClient(conn)
    db = client.Harvesters
    collection = db.Harvesters
    if RESET_DB:
        # reset the database
        collection.drop()

# set the location object
DistributionLocations = []

# setup browser
chrome_options = Options()
if WEB_DRIVER_HEADLESS:
    chrome_options.add_argument("--headless")

browser = webdriver.Chrome(chrome_options=chrome_options,)
detailBrowser = webdriver.Chrome(chrome_options=chrome_options,)
# load zip codes
with open(ZIP_COUNTY_DATAFILE) as f:
    reader = csv.reader(f)
    zips = list(reader)

# keep track of where we are
currentRecord = 0
totalRecords = zips.__len__()
# access a zip code
# print(zips[0][0])
for currentZip in zips:
    currentRecord = currentRecord + 1

    currentCounty = currentZip[1]
    currentZip = currentZip[0]

    print("Processing record: " + str(currentRecord) + " of " + str(totalRecords))

    if TEST_RUN == False:
        url = 'https://www.harvesters.org/Get-Help/Service-Locator.aspx'

        browser.get(url)
        time.sleep(WEB_DRIVER_TIMEOUT)
        inputField = browser.find_element_by_id(
            "ctl00_ctl00_cph_cphTop_locale")
        radiusField = browser.find_element_by_id(
            "ctl00_ctl00_cph_cphTop_radius")
        serviceTypeField = browser.find_elements_by_id(
            "ctl00_ctl00_cph_cphTop_serviceType")  # 1, 2, 3
        submitButton = browser.find_elements_by_id("action")

        inputField.send_keys(currentZip)  # zips[0][0]
        radiusField.send_keys("500")

        submitButton[0].click()
        time.sleep(WEB_DRIVER_TIMEOUT)
        searchResultHeader = browser.find_element_by_id(
            "ctl00_ctl00_cph_cphTop_results")
        searchResults = searchResultHeader.find_elements_by_class_name(
            "assistance-result")

        for results in searchResults:
            searchResult = results.text
            searchResult = searchResult.split("\n")
            DetailButton = results.find_elements_by_class_name(
                "btn-instructional")
            DetailURL = DetailButton[0].get_attribute("href")
            # Name	Address	Dates/Times	Details about food site
            location = {
                'Name': searchResult[0],
                'Address 1': searchResult[1],
                'City': searchResult[2].split(" ")[0],
                'State': searchResult[2].split(" ")[1],
                'ZipCode': searchResult[2].split(" ")[2],
                'DistanceFromSearchedZipCode': searchResult[4],
                'SearchedZipCode': currentZip,
                'ServiceType': "",
                'Phone': searchResult[3],
                'Hours': "",
                'County': currentCounty

            }
            # grab the details
            # spawn a new browser for that and then kill it when done.  fuck the children.
            detailBrowser.get(DetailURL)
            time.sleep(WEB_DRIVER_TIMEOUT)

            serviceType = detailBrowser.find_elements_by_css_selector(
                "#categories > div > div:nth-child(2) > div:nth-child(1) > div:nth-child(4)")
            location["ServiceType"] = serviceType[0].text.replace(
                "Service Type:", "")

            HoursContainer = detailBrowser.find_elements_by_class_name(
                "hours-container")

            location["Hours"] = HoursContainer[0].text

            DistributionLocations.append(location)

detailBrowser.quit()
browser.quit()

# print(DistributionLocations)

csv_columns = ['Name', 'Address 1', 'City', 'State',
               'ZipCode', "DistanceFromSearchedZipCode", "SearchedZipCode", "ServiceType", "Phone", "Hours", "County"]

try:
    with open(EXPORT_FILE, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for data in DistributionLocations:
            writer.writerow(data)
except IOError:
    print("I/O error")
