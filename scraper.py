#######################################  Imports  ##################################################
from selenium import webdriver
from time import sleep
import pandas as pd
import datetime
from bs4 import BeautifulSoup
import numpy as np
####################################################################################################

################################## Magic numbers and Constants #####################################
URL_MACCABI = 'https://serguide.maccabi4u.co.il'
URL_BEGINNING = 'https://serguide.maccabi4u.co.il/heb/doctors?SearchText='
SRC_FEMALE_PICTURE =\
    "/media/a0c04626f2734055aa80ea34b632fb40.svg?v=bd81a3f8-1d30-46a1-98c1-fb26a842c345"
EXTRACTING_HTML_SCRIPT = "return document.getElementsByTagName('html')[0].innerHTML"
MAN = '0'
WOMAN = '2'
FAILED_SEARCH_HEADER = 'לא נמצאו רופאים'
FAILED_SEARCH_MESSAGE = 'לא נמצאו תוצאות התואמות את בקשתך: '
WAITING_TIME_AFTER_PAGE_LOAD = 5 ##give the page time to
# load, if connection's slow might need >10
MAXIMAL_NUM_OF_MAIN_SPECIALITIES = 3
MAXIMAL_NUM_OF_SUB_SPECIALITIES = 4
EMPTY_FIELD = '.'
KEY = 4289
####################################################################################################

#####################################  Program's Functions  ########################################
def create_driver():
    """
    Creates an automated Chrome web browser
    @return: the automated browser with the page url opened
    """

    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    options.add_argument('--headless')
    driver = webdriver.Chrome('chromedriver.exe')
    driver.maximize_window()
    return driver

def chane_page(driver, url):
    """
    Opens the web page with the address url with driver
    @param driver: an automated Chrome web driver with the result page of a search
    @param url: a string representing a url address
    """
    driver.get(url)
    sleep(WAITING_TIME_AFTER_PAGE_LOAD)

def next_page(driver, cur_page_num, num_of_pages, cur_url):
    """
    Changes the web page of driver from the current result page to the next one
    @param driver: an automated Chrome web driver with the result page of a search
    @param cur_page_num: the number of the current result page
    @param num_of_pages: the number of results pages in the current search
    @param cur_url: the url address of the current web page in driver
    @return: true if the driver is open on the last result page, false otherwise
    """

    is_last_page = (cur_page_num == num_of_pages) ##TODO add try and catch in a while loop + cer_num test
    if not is_last_page:
        new_page_num = str(cur_page_num + 1)
        new_url = cur_url.replace('PageNumber=1', 'PageNumber=' + new_page_num)
        not_loaded = True
        while not_loaded:
            try:
                driver.get(new_url)
                sleep(WAITING_TIME_AFTER_PAGE_LOAD)
                soup = BeautifulSoup(driver.execute_script(EXTRACTING_HTML_SCRIPT), "html.parser")
                check = soup.find_all('div', class_='tooltip-inner')[0].text
                not_loaded = False
            except:
                not_loaded = True

    return is_last_page

def extract_doctor_specialization(doc_sections,data):
    """
    Extracts the specializations of the doctor whose details are in doc_sections into data
    @param doc_sections: a list of subsections in a single doctor's details as shown in result page
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    doc_specializations = doc_sections[1].find_all('li')
    for i in range(MAXIMAL_NUM_OF_SUB_SPECIALITIES):
        to_append = doc_specializations[i].text if len(doc_specializations) >= i +1 else EMPTY_FIELD
        to_append = EMPTY_FIELD if to_append == '' else to_append
        data['sub_speciality_' + str(i + 1)].append(to_append)

def extract_doctors_closest_appointment(row, data):
    """
    Extracts the date of the closest appointment of the doctor whose details are in row into data
    @param row: the details of one doctor, as shown in the results page of the current search
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    raw_appointments = row.find_all(class_='t_G_1 closestAppointMentText')
    to_append = False if len(raw_appointments) == 0 else raw_appointments[0].text
    data['next_spot_DOW'].append(EMPTY_FIELD if not to_append else to_append[:7])
    data['next_spot_date'].append(EMPTY_FIELD if not to_append else to_append[8:])


def extract_doctors_address(data, doc_sections): ##TODO change documentation
    """
    Extracts the address of the doctor whose details are in doc_sections into data
    @param doc_sections:  a list of subsections in a single doctor's details as shown in result page
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    full_address = EMPTY_FIELD
    for section in doc_sections:
        if 'כתובת' in section.text:
            full_address = section.find_all('div', class_='t_G_1')[0].text.split(',')
            break
    street, locality = full_address[0], full_address[1]
    data['clinic_street'].append(street)
    data['clinic_locality'].append(locality[1:])

def extract_languages(doctors_page, data):
    """
    Extracts the languages a doctors speak from his page in Maccabi's website and adds them to data
    @param doctors_page: a BeautifulSoup object representing a doctor's page
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    languages_raw = doctors_page.find_all('li', class_='languages')
    i = 1
    for language in languages_raw:
        data['language_' + str(i)].append(language.text[:-1] if language.text[-1:] == ',' else
                                                                                    language.text)
        i += 1
    for j in range(i, 9):
        data['language_' + str(j)].append('.')
        j += 1

def extract_visitation_cost(soup, data):
    """
    Extracts the visitation cost of a doctors from his page in Maccabi's website and adds it to data
    @param soup: a BeautifulSoup object - a mapping of a web page as a search tree
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    consult_costs_divs = soup.find_all('div', class_='ConsultCosts')
    consult_costs = EMPTY_FIELD if len(consult_costs_divs) == 0 else consult_costs_divs[0].text[12:]
    data['fee'].append(consult_costs)

def is_maccabi_clinic(soup, data):
    """
    Checks whether a doctor's clinic is a Maccabi's clinic and updates data accordingly
    @param soup: a BeautifulSoup object representing a doctor's page
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    is_maccabi_clinic = bool(soup.find_all('img', class_='branchIcon'))
    is_Maccabi = 'כן' if is_maccabi_clinic else 'לא'
    data['is_Maccabi_clinic'].append(is_Maccabi)

def fill_empty_reception_columns(data, i, cur_day, days):
    """
    Fills the data columns of the form 'cur_day + _from_/_until_/_frequency_/_comments_ + number'
    whch do not appear in th reception table or should be empty with EMPTY_FIELD
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param i: the row number in the reception table inside a specific day
    @param cur_day: a string representing the day of which rows we want to fill with EMPTY_FIELD
    @param days: dictionary with the hebrew names of days as keys and their English names as values
    """
    for j in range(i, 4):
        data[days[cur_day] + '_from_' + str(j)].append(EMPTY_FIELD)
        data[days[cur_day] + '_until_' + str(j)].append(EMPTY_FIELD)
        data[days[cur_day] + '_frequency_' + str(j)].append(EMPTY_FIELD)
        data[days[cur_day] + '_comments_' + str(j)].append(EMPTY_FIELD)

def fill_reception_column(data, i, cur_day, days, columns):
    """
    Fills the data columns of the form 'cur_day + _from_/_until_/_frequency_/_comments_ + i'
    according to the information in the table, meaning columns
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param i: the row number in the reception table inside a specific day
    @param cur_day:  a string representing the day of which rows we want to fill with EMPTY_FIELD
    @param days: dictionary with the hebrew names of days as keys and their English names as values
    @param columns: the columns of the current row in reception table
    """
    begin = columns[1].text if columns[1].text.strip(',') != '----' else EMPTY_FIELD
    until = columns[2].text if columns[2].text.strip(',') != '----' else EMPTY_FIELD
    freq = columns[3].text if columns[3].text.strip(',') != '----' else EMPTY_FIELD
    comments = columns[4].text if columns[4].text != ' ' else EMPTY_FIELD
    data[days[cur_day] + '_from_' + str(i)].append(begin)
    data[days[cur_day] + '_until_' + str(i)].append(until)
    data[days[cur_day] + '_frequency_' + str(i)].append(freq)
    data[days[cur_day] + '_comments_' + str(i)].append(comments)
    i += 1

def extract_reception_of_the_public(soup, data):
    """
    Extract the reception hours table from the doctor's page soup represent into data
    @param soup: a BeautifulSoup object - a mapping of a web page as a search tree
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    receptions_table_rows = soup.find_all(class_='ActivityTimeRow')
    days = {'א':'Sunday', 'ב':'Monday', 'ג':'Tuesday', 'ד':'Wednesday', 'ה':'Thursday',
            'ו':'Friday', 'ש':'Saturday',}
    cur_day, begin, until, freq, comments = 'א', '', '', '', ''
    i = 1
    for row in receptions_table_rows[1:]:
        columns = row.find_all(class_='ActivityTimeCol')
        row_day = columns[0].text[:-2]
        if row_day == '' or row_day == cur_day: ##TODO or ' '
            fill_reception_column(data, i, cur_day, days, columns)
        else:
            fill_empty_reception_columns(data, i, cur_day, days)
            i = 1
            cur_day = row_day
            fill_reception_column(data, i, cur_day, days, columns)
        i += 1
        if row == receptions_table_rows[-1]:
            fill_empty_reception_columns(data, i, cur_day, days)
            break

def extract_doctor_education(data, soup):
    """
    Extract the education details from the doctor's page soup represent into data
    @param soup: a BeautifulSoup object - a mapping of a web page as a search tree
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    education_data = (soup.find(attrs={"role": "dialog"}))
    try:
        edu_r_col= education_data.find_all(attrs={"class": "secondDiv"})
    except:
        education_left_col,edu_r_col=[],[]
    num, i = 1, 0
    while i < len(edu_r_col):
        data['Education_' + str(num)].append(EMPTY_FIELD if edu_r_col[i].text == '' else
                                                                                  edu_r_col[i].text)
        data['Institution_Name_' + str(num)].append(EMPTY_FIELD if edu_r_col[i + 1].text== '' else
                                                                            edu_r_col[i + 1].text)
        data['Education_Year_' + str(num)].append(EMPTY_FIELD if edu_r_col[i + 2].text == '' else
                                                                            edu_r_col[i + 2].text)
        i += 3
        num += 1
    while num <= 4:
        data['Education_' + str(num)].append(EMPTY_FIELD)
        data['Institution_Name_' + str(num)].append(EMPTY_FIELD)
        data['Education_Year_' + str(num)].append(EMPTY_FIELD)
        num += 1

def extract_and_cipher_id(soup):
    """
    Extract the doctor's id (license number), encrypts it be multiplication in KEY
    @param soup: a BeautifulSoup object - a mapping of a web page as a search tree
    @return: the encrypted license number
    """
    license_num = soup.find_all(class_='t_G_11_BF')[0].text[11:]
    license_num = license_num[2:] if '1-' in license_num else license_num
    try: ## for if the doctor if rofe toran and has no id number
        license_num = int(license_num)
    except:
        license_num = 0
    chiphered_license_num = license_num * KEY ##TODO problem
    return chiphered_license_num


def extract_details_from_docs_page(row, data, driver):
    """
    Extracts relevant data from a page of a doctor (as opposed to from the results page) and
    updates it in data
    @param row: a BeautifulSoup object which contains the details of a doctor, as shown in the
    results page of the current search
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param driver: an automated Chrome web driver with the result page of a search
    """
    page_unloaded = True ## if license_num is out of range, it means the page didn't load->try again
    while page_unloaded:
        doctor_url = URL_MACCABI + row.find_all('a')[0]['href']
        driver.get(doctor_url)
        sleep(WAITING_TIME_AFTER_PAGE_LOAD)
        soup = BeautifulSoup(driver.execute_script(EXTRACTING_HTML_SCRIPT), "html.parser")

        try:
           license_num = soup.find_all(class_='t_G_11_BF')[0].text[11:]
           page_unloaded = False
        except:
            sleep(10)
            page_unloaded = True
    data['doctor_ID'].append(extract_and_cipher_id(soup))
    try:
        edu_cbutton = driver.find_element_by_xpath("//div[@class='sectionDocTxt']")
        edu_cbutton.click()
    except:
        pass
    sleep(2)
    soup = BeautifulSoup(driver.execute_script(EXTRACTING_HTML_SCRIPT), "html.parser")
    extract_doctor_education(data, soup)
    extract_languages(soup, data)
    extract_visitation_cost(soup, data)
    is_maccabi_clinic(soup, data)
    extract_reception_of_the_public(soup, data)


def extract_doctor_main_specialities(doc_sections, data):
    """
    Extract doctor's main specialities (what's written right under his name)
    @param doc_sections: a list of subsections in a single doctor's details as shown in result page
    @param data:a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    specialities = doc_sections[0].find_all('li')
    for i in range(MAXIMAL_NUM_OF_MAIN_SPECIALITIES):
        to_append = specialities[i].text if len(specialities) >= i + 1 else EMPTY_FIELD
        data['main_speciality_' + str(i + 1)].append(to_append)

def convert_name_to_probability(name, data, df_first_names, df_last_names, gender): ##TODO document
    """
    Checks in df_first_names and  df_last_names the probability a person's name of gender 'gender'
    is arab, updates data accordingly
    @param name: a string representing a full name of a doctor
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param df_first_names: a pandas' data frame containing three columns: 'gender',
    with an int (0 = man, 2 = woman, 1 = ?), 'name' with strings representing Hebrew private names,
    and 'probabilty' with ints representing the probability the private name in the row foe e
    person of the gender in the row is arab.
    @param df_last_names: same as df_first_names but with last names
    @param gender: the doctor's gander
    """

    name_components = name.split()
    first_name, last_name = name_components[-1], name_components[0]
    relevant_rows = df_first_names.loc[(df_first_names['name'] == first_name)]
    relevant_row = relevant_rows.loc[relevant_rows['gender'] == int(gender)]
    try:
        private_prob = relevant_row.iloc[0][2]
    except:
        private_prob = EMPTY_FIELD ##TODO what should be here?
    data['first_name_arab_prob'].append(private_prob)
    relevant_rows_last = df_last_names.loc[(df_last_names['name'] == last_name)]
    relevant_row_last = relevant_rows_last.loc[relevant_rows_last['gender'] == int(gender)]
    try:
        last_prob = relevant_row_last.iloc[0][2]
    except:
        last_prob = EMPTY_FIELD
    data['last_name_arab_prob'].append(last_prob)


def extract_data_from_page(rows, data, driver_2, df_first_names, df_last_names):
    """

    Extracts the relevant details from a single results page and updates data with them
    @param rows: a list, containing BeautifulSoup object which contains the details of each
    doctor, as shown in the results page of the current search
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param driver_2: an automated Chrome web driver with the result page of a search
    @param df_first_names: a pandas' data frame (for more details see convert_name_to_probability)
    @param df_last_names: a pandas' data frame (for more details see convert_name_to_probability)
    """

    place_in_page = 0
    for row in rows:
        place_in_page += 1
        data['position_in_page'].append(place_in_page)
        doc_sections = row.find_all('div', class_='sectionDoc')
        extract_doctors_closest_appointment(row, data)
        extract_doctor_specialization(doc_sections, data)
        extract_doctor_main_specialities(doc_sections, data)
        name_and_title = row.find_all('a', class_='docPropTitle')[0].text.split(' ', 1)
        title, name = name_and_title[0], name_and_title[1]
        gender = WOMAN if row.find_all('img')[0]['src'] == SRC_FEMALE_PICTURE else MAN
        convert_name_to_probability(name, data, df_first_names, df_last_names, gender)
        data['title'].append(title)
        extract_doctors_address(data, doc_sections)
        data['gender'].append(gender)
        extract_details_from_docs_page(row, data, driver_2)

def extract_data_for_entire_single_search(driver_1, driver_2, soup, num_of_pages, data,
                                          df_first_names, df_last_names):
    """
    Extracts the relevant data for a single search (for a locality and speciality) and updates data
    with it
    @param driver_1: an automated Chrome web driver with the result page of a search
    @param driver_2: an automated Chrome web driver
    @param soup: a BeautifulSoup object - a mapping of a web page as a search tree
    @param num_of_pages: the number of results pages for the current search
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param df_first_names: a pandas' data frame (for more details see convert_name_to_probability)
    @param df_last_names: a pandas' data frame (for more details see convert_name_to_probability)
    """
    cur_page_num, cur_url =  1, ''
    while cur_page_num <= num_of_pages:
        rows = soup.find_all(class_='docResualtWrap')
        data['current_page'].extend([str(cur_page_num) for row in rows]) ## extract page in search
        extract_data_from_page(rows, data, driver_2, df_first_names, df_last_names)
        links = soup.find_all('link', href=True)
        cur_url = links[0]['href'] if cur_page_num == 1 else cur_url
        is_last_page = next_page(driver_1, cur_page_num, num_of_pages, cur_url)
        sleep(WAITING_TIME_AFTER_PAGE_LOAD)
        cur_page_num += 1
        if not is_last_page:
            soup = BeautifulSoup(driver_1.execute_script(EXTRACTING_HTML_SCRIPT), "html.parser")

def handle_general_details_of_search(search_locality, search_speciality, now, data, num_of_pages,
                                     soup, num_of_results):
    """
    Extracts details regarding the entire search (not a specific doctor), updates data accordingly
    @param search_locality: a string, representing a city in which to search doctors
    @param search_speciality: a string, representing a medical speciality in which to search doctors
    @param now: the time and date at the moment of the search (string)
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param num_of_pages: the number of results pages for the current search
    @param soup: a BeautifulSoup object - a mapping of a web page as a search tree
    @param num_of_results: the number of results in the results page
    """

    search_range = soup.find_all('div', class_='tooltip-inner')[0].text
    num_of_doctors = soup.find_all('h1')[0].text[5:-20]
    num_of_macabi_docs = soup.find_all('li', class_='t_B_11 maccabi maccabiActive')[0].text[:-11]
    date_and_hour = now.split(' ', 1)
    date, hour = date_and_hour[0], date_and_hour[1]
    col_length = len(data['first_name_arab_prob']) - num_of_results
    data['search_range_(km)'].extend([search_range for i in range(col_length)])
    data['num_of_doctors_in_search'].extend([num_of_doctors for i in range(col_length)])
    data['maccabi_doctors_in_search'].extend([num_of_macabi_docs for i in range(col_length)])
    data['search_time'].extend([hour for i in range(col_length)])
    data['search_date'].extend([date for i in range(col_length)])
    data['num_of_result_pages'].extend([num_of_pages for i in range(col_length)])
    data['search_locality'].extend([search_locality for i in range(col_length)])
    data['search_speciality'].extend([search_speciality for i in range(col_length)])

def check_search_failure(soup, search_locality, search_speciality):
    """
    Checks whether or not any results were found
    @param soup: a BeautifulSoup object - a mapping of a web page as a search tree
    @param search_locality: a string, representing a city in which to search doctors
    @param search_speciality: a string, representing a medical speciality in which to search doctors
    @return: true if there were no results for the search. false otherwise
    """
    headers_in_page = soup.find_all('h1')
    failed = headers_in_page[0].text == FAILED_SEARCH_HEADER
    if failed:
        print(FAILED_SEARCH_MESSAGE + search_speciality + ' ב' + search_locality + '\n')
    return failed

def export_to_excel(data):
    """
    Exports data to an excel file named after the date of the search
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    df = pd.DataFrame(data)
    df.index = np.arange(1, len(df) + 1)
    writer = pd.ExcelWriter(datetime.date.today().strftime("%d-%m-%Y")+'.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name = datetime.date.today().strftime("%d-%m-%Y"))
    writer.save()

def single_search(data, locality, speciality, num_of_results, driver_1, driver_2,
                  df_first_names, df_last_names):
    """
    Executes a search for a given a locality and medical speciality and adds the results to data
    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param locality: the locality for which the current search is being executed.
    @param speciality: the medical filed for which the current search is being executed.
    @param num_of_results: the number of results in the results page
    @param driver_1: an automated Chrome web driver with the result page of a search
    @param driver_2: an automated Chrome web driver
    @param df_first_names: a pandas' data frame (for more details see convert_name_to_probability)
    @param df_last_names: a pandas' data frame (for more details see convert_name_to_probability)
    """

    driver_1.get(URL_BEGINNING + speciality + ' ב'+ locality)
    sleep(WAITING_TIME_AFTER_PAGE_LOAD)
    now = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) ## hour and date of search
    driver_1.find_element_by_id('SearchBtn').click() ## hit 'search'
    sleep(WAITING_TIME_AFTER_PAGE_LOAD)
    soup = BeautifulSoup(driver_1.execute_script(EXTRACTING_HTML_SCRIPT), "html.parser")
    num_of_pages_text = soup.find_all(class_='pageText')
    num_of_pages = 1 if len(num_of_pages_text) == 0 else int(num_of_pages_text[0].text[7:-7])
    if not check_search_failure(soup, locality, speciality): ##nothing will happen if no results
        extract_data_for_entire_single_search(driver_1, driver_2, soup, num_of_pages, data,
                                                                    df_first_names, df_last_names)
        handle_general_details_of_search(locality, speciality, now, data, num_of_pages, soup,
                                                                                    num_of_results)

    
def create_empty_data_dictionary():
    """
    Creates the dictionary 'data', which is the base of the finale excel file
    @return: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    """
    data = {'search_date': [], 'search_time': [],'search_speciality': [], 'search_locality': [],
            'search_range_(km)':[], 'doctor_ID':[], 'first_name_arab_prob':[],
            'last_name_arab_prob':[], 'title':[], 'gender':[], 'main_speciality_1':[],
            'main_speciality_2':[], 'main_speciality_3':[], 'sub_speciality_1':[],
            'sub_speciality_2':[], 'sub_speciality_3':[], 'sub_speciality_4':[],'clinic_street':[],
            'clinic_locality': [], 'is_Maccabi_clinic':[], 'next_spot_date':[], 'next_spot_DOW':[],
            'language_1': [], 'language_2': [], 'language_3': [], 'language_4': [], 'language_5':[],
            'language_6': [],'language_7': [], 'language_8': [], 'fee': [], 'Education_1':[],
            'Institution_Name_1':[], 'Education_Year_1': [], 'Education_2': [],
            'Institution_Name_2': [], 'Education_Year_2': [], 'Education_3': [],
            'Institution_Name_3': [], 'Education_Year_3': [], 'Education_4': [],
            'Institution_Name_4': [], 'Education_Year_4': [], 'num_of_result_pages':[],
            'current_page':[], 'position_in_page':[] , 'num_of_doctors_in_search': [],
            'maccabi_doctors_in_search':[]}

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    table_words = ['_from_', '_until_', '_frequency_', '_comments_']
    for day in days:
        for i in range (1,4):
            for word in table_words:
                data[day + word + str(i)] = []
    return data

def read_name_files():
    """

    @return:
    """
    df_first_names = pd.read_csv('first_names2.csv')
    df_first_names.columns = ['gender', 'name', 'prob']
    df_last_names = pd.read_csv('last_names2.csv')
    df_last_names.columns = ['gender', 'name', 'prob']
    return df_first_names, df_last_names


def run_multiple_searches(data, localities, specialities):
    """

    @param data: a dictionary, containing lists as values and strings as keys which are the
    the columns of the output excel's file and their headers respectively.
    @param localities: a list of strings, representing names of cities
    @param specialities: a list of strings, representing names of medical fields
    """
    df_first_names, df_last_names = read_name_files()
    num_of_results = 0
    driver_1 = create_driver()
    driver_2 = create_driver()
    for search_locality in localities:
        for speciality in specialities:
            single_search(data, search_locality, speciality, num_of_results, driver_1, driver_2,
                                                                    df_first_names, df_last_names)
            num_of_results = len(data['first_name_arab_prob'])
    export_to_excel(data)
    driver_1.quit()
    driver_2.quit()

####################################################################################################

def main():
    """
    the main function of the program, its driver
    """
    data = create_empty_data_dictionary()
    localities = ['פתח תקווה','ראשון לציון','תל אביב','ירושלים','חיפה']
    specialities = ['גינקולוגיה','כירורגיה','עיניים','ילדים','משפחה, פנימית וכללית', 'אורתופדיה',
                    'אף אוזן גרון','עור ומין','נוירולוגיה','קרדיולוגיה']

    run_multiple_searches(data, localities, specialities)


if __name__ == '__main__':
    main()
