from selenium import webdriver
from bs4 import BeautifulSoup as BS

# we need to create the BeautifulSoup object
base_url = 'http://dota2.gamepedia.com/'  # create the base url
main_page = 'Dota_2_Wiki'  # the page that will get all the hero names

driver = webdriver.Firefox()  # create the webdriver
driver.get(base_url + main_page)  # load the page
soup_html = BS(driver.page_source, 'html.parser')  # parse the page

for hero_div in soup_html.findAll('div', class_='heroentry'):
    hero_link = hero_div.find('a').get('href').replace('/', '')  # gets the hero name
    driver.get(base_url + hero_link)  # load the hero page
    with open('hero_htmls/' + hero_link.replace('_', ' ').title().encode('utf-8') + '.html', 'w') as file:
        file.write(driver.page_source.encode('utf-8'))

driver.close()