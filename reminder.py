import argparse
from argparse import RawTextHelpFormatter
from selenium import webdriver
from time import sleep
import re
import pandas as pd
from datetime import date, timedelta, datetime

import smtplib


# Const
BASE_URL = 'https://www.reddit.com/r/'
VISITED = pd.read_csv('visited_links.csv', sep=',', header=(0))
today = date.today()
threshold = timedelta(days=14)  # erase entries from csv that were input prior to this value

cell_provider = {'verizon': '@vtext.com', 'sprint': '@page.nextel.com',
                 'att': '@mms.att.net', 'tmobile': ' @tmomail.net'
                 }


def get_parser():
    '''Build a parser for command line use

    :returns parser: reads in command line options
    '''

    parser = argparse.ArgumentParser(
                description='subreddit messaging bot',
                formatter_class=RawTextHelpFormatter
                )

    parser.add_argument('subreddit',
                        help='the name of the subreddit, without any prefixes ex. piano'
                        )

    parser.add_argument('cell_phone_number',
                        help='cell phone number without dashes ex. 5555555555'
                        )

    parser.add_argument('--provider', choices=['verizon', 'sprint', 'att', 'tmobile'],
                        help='the name of the cell phone provider', required=True
                        )

    parser.add_argument('gmail_address',
                        help='full gmail address'
                        )

    parser.add_argument('gmail_password',
                        help='password to login to the gmail account'
                        )

    return parser


def generate_filter_list(posts):
    '''Check if a post passes a filter by not having a sticky tag

    :param posts: list containing all of the posts from the page
    :paramtype selenium webelement list

    :returns filter_list: contains boolean values for if a post passed the filter
    '''

    filter_list = []
    for post in posts:
        html = post.get_attribute('innerHTML')
        filt = re.findall(r'id="PostBadges--Sticky.*?>', html)

        filter_list.append(len(filt) == 0)

    return filter_list


def get_urls(meta_post):
    '''Check if post contains a sticky tag and return the link url

    :param meta_post: the first div from the list which encompasses all of the posts
    :paramtype selenium webelement

    :returns list of urls
    '''

    url_list = []
    for item in meta_post.find_elements_by_xpath('//a[@data-click-id="body"]'):
        html = item.get_attribute('outerHTML')
        url = re.search(r'/r/.*?"', html).group()[:-1]
        url_list.append(BASE_URL + url[3:])

    return url_list


def get_post(subreddit):
    '''Check subreddit for top posts and return link to unvisited top post

    :param subreddit: topic of interest
    :paramtype str

    :returns link: url for post that gets sent out
    '''

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    navigate = webdriver
    driver = navigate.Chrome(options=chrome_options)

    driver.get(BASE_URL + subreddit)
    sleep(5)

    posts = driver.find_elements_by_xpath('//div[@data-click-id="background"]')

    url_list = get_urls(posts[0])
    filter_list = generate_filter_list(posts)
    post_list = [url for (url, filt) in zip(url_list, filter_list) if filt]

    driver.quit()

    for url in post_list:
        if url not in VISITED.loc[:, 'URL']:  # just return the first post that isn't a repeat

            for index, day in VISITED.iterrows():
                format_str = '%Y-%m-%d'
                new_date = datetime.strptime(day['DATE'], format_str).date()
                VISITED.loc[index, 'DATE'] = new_date

            VISITED[VISITED.loc[:, 'DATE'] <= (today - threshold)]
            new_visited = VISITED.append({'URL': url, 'DATE': today}, ignore_index=True)
            new_visited.to_csv('visited_links.csv', index=False)

            return(url[8:])  # colon character acts as an escape value in emails
        else:
            return('No new posts')


def send_text(parser_options, url):
    '''Use gmails smtp server to send messages to a cell phone
    method found on:
    https://www.reddit.com/r/Python/comments/8gb88e/free_alternatives_to_twilio_for_sending_text/
    by: ForsakenOne
    modified to fit the use case of the project

    :param parser_options: output of parsing command line args from argparse
    :param url: the message to send
    '''

    cell_number = parser_options.cell_phone_number + cell_provider[parser_options.provider]

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(parser_options.gmail_address, parser_options.gmail_password)
    server.sendmail(parser_options.gmail_address, cell_number, url)


if __name__ == '__main__':
    parser_options = get_parser().parse_args()
    send_text(parser_options, get_post(parser_options.subreddit))
