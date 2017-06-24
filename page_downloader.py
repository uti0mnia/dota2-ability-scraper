from selenium import webdriver
import urllib2
from bs4 import BeautifulSoup as BS
import thread

def download_url(url, hfile):
    req = urllib2.Request(url, headers={'User-Agent' : "Magic Browser"})
    con = urllib2.urlopen(req)
    soup = BS(con.read(), 'html.parser')
    file = open(hfile, 'wb')
    file.write(soup.prettify('utf-8'))
    file.close()

def get_all_heroes():
    hero_urls = []
    # we need to create the BeautifulSoup object
    base_url = 'http://dota2.gamepedia.com/'  # the page that will get all the hero names

    req = urllib2.Request(base_url, headers={'User-Agent' : "Magic Browser"})
    con = urllib2.urlopen(req)
    soup_html = BS(con.read(), 'html.parser')  # parse the page

    # get each link
    for hero_div in soup_html.findAll('div', class_='heroentry'):
        hero_link = hero_div.find('a').get('href').replace('/', '')  # gets the hero name
        hero_urls.append(base_url + hero_link)  # load the hero page

    return hero_urls


def get_all_items():
    base_url = 'http://dota2.gamepedia.com'  # items sub domain
    items_url = '/Items'
    urls = {}  # where we will save the urls for each item

    req = urllib2.Request(base_url + items_url, headers={'User-Agent': "Magic Browser"})
    con = urllib2.urlopen(req)
    soup_html = BS(con.read(), 'html.parser')  # parse the page
    for div in soup_html.findAll('div', class_='itemlist')[0:10]:
        for d in div.findAll('div'):
            a = d.findAll('a')[-1]
            name = a.get('title').encode('utf-8')
            href = a.get('href')
            urls[name] = base_url + href

    return urls

def download_heroes(hero_urls):
    print 'Heroes:'
    i = 0
    for url in hero_urls:
        i += 1
        print str(i) + '/' + str(len(hero_urls))
        download_url(url, 'htmls/heroes/' + url.split('/')[-1].split('.')[0].replace('_', ' ') + '.html')

def download_items(item_urls):
    print 'Items:'
    i = 0
    for key in item_urls:
        i += 1
        print str(i) + '/' + str(len(item_urls))
        download_url(item_urls[key.encode('utf-8')], 'htmls/items/' + key + '.html')


download_heroes(get_all_heroes())
download_items(get_all_items())