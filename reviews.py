#!/usr/bin/env python
import gc
import re
import os
import sys
import time
import config
import pickle
import logging
import logging.config
import requests
import grequests
from pymongo import MongoClient
from pprint import pprint


config.configure_logging()
mc = MongoClient(config.MONGO_CONNECTION_STRING)
db = mc[config.MONGO_DB]

def parse_feed(feed):
	if 'feed' not in feed:
		raise Exception('The feed seems to be messed up. Here\'s the raw JSON:\n%s ' % r.text)
	return feed['feed']

def extract_single_value(regex, data):
	match = re.match(regex, data)
	if match is None:
		logging.warning('Unable to extract data using regex /{0}/ for data `{1}`'.format(regex, data))
		return None
	return match.group(1)

def generate_probe_urls():
	if os.path.exists('probe_urls.p'):
		logging.info('Loading list of probe URLs from file')
		return pickle.load(open('probe_urls.p', 'rb'))
	else:
		logging.info('Building list of probe URLs')
		probe_urls = []
		docs = db['app_data'].find({'reviews':{'$exists':0}}, timeout=False)
		total = docs.count()
		i = -1
		for doc in docs:
			i += 1
			if 'app_id' not in doc:
				doc['app_id'] = int(extract_single_value('.*?/id=?([0-9]+)/?.*$', doc['application_url']))
				db['app_data'].save(doc, w=1)
			app_id = doc['app_id']
			logging.info('{0:.2f}%'.format(100.0*i/total))
			probe_urls.append(config.RSS_URL.format(app_id))
		logging.info('Done. Got {0} URLs to probe'.format(len(probe_urls)))
		pickle.dump(probe_urls, open('probe_urls.p', 'wb'))
		return probe_urls

if __name__ == '__main__':
	gc.enable()
	os.system('clear')

	probe_urls = generate_probe_urls()
	exit()

	scrape_urls = []
	if os.path.exists('scrape_urls.p'):
		logging.info('Loading scrape URLs from file')
		scrape_urls = pickle.load(open('scrape_urls.p', 'rb'))
	else:
		logging.info('Generating scrape URLs from {0} probe URLs'.format(len(probe_urls)))
		
		def _extract_scrape_url(r, **kwargs):
			app_id = int(extract_single_value('.*?/id=([0-9]+)/.*$', r.url))
			if r.status_code != 200:
				logging.warning('Status was {0} for appID {1}'.format(r.status_code, app_id))
				return
			feed = parse_feed(r.json())
			page_url = [x for x in feed['link'] if x['attributes']['rel'] == 'last'][-1]['attributes']['href']
			num_pages = 1
			if len(page_url) > 0:
				num_pages = int(extract_single_value('.*?/page=([0-9]+)/.*$', page_url))
			reviews = []
			for i in xrange(1, num_pages+1):
				scrape_urls.append(config.REVIEWS_URL.format(i, app_id))

		scrape_urls = []
		pool_size = 200
		i = 0
		while i < 50: #len(probe_urls):
			logging.info('{0}%'.format(100*(i/len(probe_urls))))
			rs = [grequests.get(probe_urls[j], callback=_extract_scrape_url) for j in xrange(i, i+pool_size)]
			grequests.map(rs, size=pool_size)
			i += pool_size

		logging.info('Dumping scrape URLs to file'.format(len(scrape_urls)))
		pickle.dump(scrape_urls, open('scrape_urls.p', 'wb'))

	logging.info('Got {0} URLs to scrape'.format(len(scrape_urls)))

	exit()

	rs = (grequests.get(u) for u in scrape_urls)
	for r in grequests.map(rs, size=50):
		app_id = int(extract_single_value('.*?/id=([0-9]+)/.*$', r.url))
		logging.info('Scraping appID {0}'.format(app_id))
		if r.status_code != 200:
			logging.warning('Status was {0}\n'.format(r.status_code))
			continue
		feed = parse_feed(r.json())
		if 'entry' not in feed:
			logging.warning('No reviews in feed\n')
			continue
		for raw_review in feed['entry']:
			if 'rights' in raw_review:
				continue
			if 'im:version' not in raw_review:
				raw_review['im:version'] = {'label': 'UNKNOWN'}
			author_id = int(extract_single_value('.*?/id([0-9]+)', raw_review['author']['uri']['label']))
			review = {
				'id': int(raw_review['id']['label']),
				'app_version_id': raw_review['im:version']['label'],
				'author_id': author_id,
				'author_name': raw_review['author']['name']['label'],
				'rating': int(raw_review['im:rating']['label']),
				'title': raw_review['title']['label'],
				'content': raw_review['content']['label']
			}
			reviews.append(review)
		gc.collect()
		logging.info('----+ Updating database for appID {0}'.format(app_id))
		db['app_data'].update({'app_id': app_id}, {'$set': {'reviews': reviews}}, w=1)
		logging.info('----o Done')
		exit()
