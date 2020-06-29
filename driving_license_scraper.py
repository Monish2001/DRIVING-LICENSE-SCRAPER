import requests
from bs4 import BeautifulSoup
import re
import json


def get_parsed_data(current_session):

    get_url = "https://parivahan.gov.in/rcdlstatus/?pur_cd=101"
    get_result = current_session.get(get_url).text
    soup_get_result = BeautifulSoup(get_result, 'lxml')
    return soup_get_result


def get_captcha(current_session, parsed_data, license_no):

    captcha_img = parsed_data.find('img', {'id': 'form_rcdl:j_idt32:j_idt38'})
    captcha_img_src = "https://parivahan.gov.in/" + captcha_img['src']
    captcha_img_result = current_session.get(captcha_img_src)

    filename = "captchaOf" + str(license_no) + ".png"
    captcha_img_file = open(filename, "wb")
    captcha_img_file.write(captcha_img_result.content)
    captcha_img_file.close()

    # INPUT OF THE CAPTCHA
    captcha = input("Enter the captcha (from file name : " + filename + "): ")
    return captcha

# FUNCTION FOR FORMATTING THE KEY STRING IN THE DICTIONARY


def string_key_format(string):

    string = string.lower()

    # REMOVES THE WHITE SPACE AT THE END
    string = string.strip()

    # REMOVES ALL WHITESPACE AND REPLACE IT BY UNDERSCORE
    string = re.sub(r"\s+", "_", string, flags=re.UNICODE)

    # REMOVES ALL SPECIAL CHARACTER
    string = (re.sub(r"\W+|/", "", string))

    return(string)


def get_error_list(soup_post_result, dl_error_list):

    error_list = soup_post_result.findAll(
        'div', {'id': 'form_rcdl:j_idt13', 'class': 'ui-messages ui-widget'})

    contains_table = soup_post_result.findAll("table", {
                                              'class': 'table table-responsive table-striped table-condensed table-bordered'})

    if (len(list(contains_table)) == 0):
        if(len(error_list) > 0):
            for error in error_list:
                if(error.find('span', {'class': 'ui-messages-error-detail'}) == None):
                    continue
                error_msg = error.find(
                    'span', {'class': 'ui-messages-error-detail'}).text
                dl_error_list.append(error_msg)
        if len(dl_error_list) == 0:
            alert_msg = "DL Details not found"
            dl_error_list.append(alert_msg)

    return dl_error_list


def retrieve_driving_license_information(license_no, dob):

    dl_error_list = list()

    if len(license_no) == 0:
        dl_error_list.append("License number is missing")
    if len(dob) == 0:
        dl_error_list.append("DOB is missing")

    if dl_error_list:
        return {'errors': dl_error_list}

    # MAINTAINING A SESSION
    current_session = requests.Session()

    parsed_data = get_parsed_data(current_session)

    captcha = get_captcha(current_session, parsed_data, license_no)

    # PARAMETER IN FORM DATA
    view_state = parsed_data.find(
        'input', {'id': 'j_id1:javax.faces.ViewState:0'})['value']

    # PARAMETERS OF FORM DATA
    parameters = {
        "form_rcdl:tf_dlNO": license_no,
        "form_rcdl:tf_dob_input": dob,
        "form_rcdl:j_idt32:CaptchaID": captcha,
        "javax.faces.partial.ajax": "true",
        "javax.faces.source: form_rcdl": "j_idt43",
        "javax.faces.partial.execute": "@all",
        "javax.faces.partial.render": "form_rcdl:pnl_show form_rcdl:pg_show form_rcdl:rcdl_pnl",
        "form_rcdl:j_idt43": "form_rcdl:j_idt43",
        "form_rcdl": "form_rcdl",
        "javax.faces.ViewState": view_state
    }

    # POSTING THE DATA AND GET BACK POST RESPONSE
    post_url = "https://parivahan.gov.in/rcdlstatus/vahan/rcDlHome.xhtml"
    post_result = current_session.post(post_url, data=parameters).text
    soup_post_result = BeautifulSoup(post_result, 'lxml')

    dl_error_list = get_error_list(soup_post_result, dl_error_list)
    if len(dl_error_list) > 0:
        return {'errors': dl_error_list}

    driving_license_details = get_driving_license_details(soup_post_result)

    driving_license_validity_details = get_driving_license_validity_details(
        soup_post_result)

    class_of_vechile_details_list = get_class_of_vehicle_details(
        soup_post_result)

    return {'driving_license_number': license_no,
            'driving_license_details': driving_license_details,
            'driving_license_validity_details': driving_license_validity_details,
            'class_of_vechile_details': class_of_vechile_details_list}


def get_driving_license_details(scraped_post_response):

    driving_license_details = dict()

    # SELECTING THE TABLE AND ITERATING OVER TR AND FORMING KEY VALUE PAIR
    driving_license_table = scraped_post_response.findAll(
        "table", {'class': 'table table-responsive table-striped table-condensed table-bordered'})

    tr_list = driving_license_table[0].findAll('tr')
    for tr in tr_list:
        td_list = tr.findAll('td')
        driving_license_details[string_key_format(
            td_list[0].text)] = td_list[1].text

    return driving_license_details


def get_driving_license_validity_details(scraped_post_response):

    driving_license_validity_details = dict()

    validity_details_tables = scraped_post_response.findAll(
        "table", {'class': 'table table-responsive table-striped table-condensed table-bordered data-table'})

    # GET THE TABLE DATA AND FORMING KEY VALUE PAIRS
    tr_list = validity_details_tables[0].findAll('tr')
    for tr in tr_list:
        td_list = tr.findAll('td')
        driving_license_validity_details[string_key_format(td_list[0].contents[0].text)] = {string_key_format(td_list[1].contents[0].text): td_list[1].contents[1],
                                                                                            string_key_format(td_list[2].contents[0].text): td_list[2].contents[1]}

    td_list = validity_details_tables[1].findAll('td')
    driving_license_validity_details[string_key_format(
        td_list[0].text)] = td_list[1].text
    driving_license_validity_details[string_key_format(
        td_list[2].text)] = td_list[3].text

    return driving_license_validity_details


def get_class_of_vehicle_details(scraped_post_response):

    header = scraped_post_response.findAll(
        "thead", {'id': 'form_rcdl:j_idt187_head'})

    # GETTING THE TABLE HEADERS
    categories = header[0].findAll('th')
    category_list = [category.text for category in categories]

    class_of_vechile_details = dict()
    class_of_vechile_details_list = list()

    # FORMING LIST OF DICTIONARIES WITH CATERGORY LIST AND THEIR CORRESPONDING VALUES
    for category in scraped_post_response.findAll("tbody", {'id': 'form_rcdl:j_idt187_data', 'class': 'ui-datatable-data ui-widget-content'}):
        row_category = category.findAll("tr")
        for tr in row_category:
            td = tr.findAll("td")
            for i, element in enumerate(category_list):
                class_of_vechile_details[string_key_format(
                    element)] = td[i].text
            class_of_vechile_details_list.append(class_of_vechile_details)
            class_of_vechile_details = dict()

    return class_of_vechile_details_list


if __name__ == '__main__':

    license_no = input("Please enter your driving license number : ")
    dob = input("Please enter your date of birth : ")

    retry_count = 0
    max_retry_count = 3
    driving_license_details = retrieve_driving_license_information(
        license_no, dob)
    for i in range(max_retry_count):
        if(driving_license_details.get("errors")):
            print([error for error in driving_license_details.get('errors')])
            retry_count = retry_count + 1
            if retry_count >= max_retry_count:
                print("Maximum retries exceeded")
                break
            print("\nPlease re-enter details again")
            license_no = input("Please enter your driving license number : ")
            dob = input("Please enter your date of birth : ")
            driving_license_details = retrieve_driving_license_information(
                license_no, dob)
        if(driving_license_details.get("errors") == None):
            print(json.dumps(driving_license_details))
            break
