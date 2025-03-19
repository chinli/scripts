#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import requests
import json
import urllib3
from urllib.parse import quote
import re

class Gerrit:
    def __init__(self, gerrit_url=None, username=None, password=None):
 
        if (gerrit_url is None):
            raise
 
        self.URL_SUFFIX_REST = "https://" + gerrit_url + "/a"
        self.URL_SUFFIX_HTTP = "https://" + gerrit_url
        self.xmlProjectBranch={}
 
        self.session = requests.Session()
        self.header_query = {
            'Host': gerrit_url,
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;',
        }
 
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
        login_url = 'https://' + gerrit_url +'/login/'
 
        r = self.session.get(login_url, headers=self.header_query, verify=False)
 
        data = 'username=%s&password=%s' %(username, quote(password, 'utf-8'))
 
        r = self.session.post(login_url, data, headers=self.header_query)
 
        self.session_cookies = r.cookies
 
        self.header_set = self.header_query.copy()
        self.header_set.update({'Content-Type': 'application/json;charset=UTF-8'})
 
        if 'scgit' in gerrit_url: # gerrit version 2.11
            x_gerrit_auth = re.findall(r'xGerritAuth="(.*)";', str(r.content))[0]
        else: # gerrit version 2.16
            x_gerrit_auth = r.cookies.get_dict()['XSRF_TOKEN']
        self.header_set.update({"x-gerrit-auth": x_gerrit_auth})
        self.header_query.update({"x-gerrit-auth": x_gerrit_auth})

    def _decode_response(self, ret):
        content = ret.strip()
        if not content:
            print("no content in response")
            return content
 
        if content.startswith(")]}\'\n"):
            content = content[len(")]}\'\n"):]
        #print(content)
        try:
            return json.loads(content)
        except ValueError:
            print('Invalid json content: %s' %content)

    def _get_rest(self, api):
        url = self.URL_SUFFIX_REST + api
        r = self.session.get(url, headers=self.header_query, cookies=self.session_cookies)
        return self._decode_response(r.text)

    def _get_http(self, api):
        url = self.URL_SUFFIX_HTTP + api
        r = self.session.get(url, headers=self.header_query, cookies=self.session_cookies)
        return self._decode_response(r.text)

    def _post_rest(self, api, data,returnRawData=False):
        url = self.URL_SUFFIX_REST + api
        r = self.session.post(url, data=json.dumps(data), headers=self.header_set, cookies=self.session_cookies)
        if returnRawData:
            return self._decode_response(r.text),r.text
        else:
            return self._decode_response(r.text)

    def _put_rest(self, api, data,returnRawData=False):
        url = self.URL_SUFFIX_REST + api
        r = self.session.put(url, data=json.dumps(data), headers=self.header_set, cookies=self.session_cookies)
        if returnRawData:
            return self._decode_response(r.text),r.text
        else:
            return self._decode_response(r.text)

    def get_change_detail(self, params):
            # cl_id: params[0]
            api = '/changes/%s/detail' %params
            print(api)
            return self._get_rest(api)

    def get_review(self, params):
        cl_detail_dic = self.get_change_detail(params)
        revison_id = 1
        for message_item in cl_detail_dic['messages']:
            if message_item['_revision_number'] > revison_id:
                revison_id = message_item['_revision_number']
        api = '/changes/%s/revisions/%s/review' %(params, revison_id)
        print(api)
        return self._get_rest(api)

    def post_review_pass_message(self, cl_id, messages):
            cl_review_info_dic = self.get_review(cl_id)
            try:
                api = '/changes/%s/revisions/%s/review' %(cl_id, cl_review_info_dic['current_revision'])
                print(api)
            except:
                return "{'INFO' :'CL was rebased or submited but not verify +2}"
            data = {
                "message": messages,
                "labels": {
                    "Verified": "+2",
                }
            }
            return self._post_rest(api, data)