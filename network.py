import os
import random
import requests
import time

from utils import chmod

class Network:

    _instance = None
    timeout = 10

    def __init__(self):
        self.isEnabled = True

    @staticmethod
    def setIsEnabled(isEnabled):

        if Network._instance is None:
            Network._instance = Network()

        Network._instance.isEnabled = isEnabled

    @staticmethod
    def get(url, params=None, retries=1, **kwargs):

        if not Network._instance.isEnabled:
            return None

        for i in range(retries):
            try:
                return requests.get(url, params=params, timeout=Network.timeout, **kwargs)
            except Exception as e:
                print('Error to get', url, ':', e)

            if i > 0:
                # Sleep a while
                time.sleep(30 * i)

        return None

    @staticmethod
    def post(url, data=None, json=None, **kwargs):

        if not Network._instance.isEnabled:
            return None

        try:
            return requests.post(url, data=data, json=json, **kwargs)
        except Exception as e:
            print('Error to post', url, ':', e)

        return None

    @staticmethod
    def getUrl(url, params=None, headers=None, retries=1):

        if Network._instance is None:
            Network._instance = Network()

        content = Network._instance.getUrlImpl(url, params, headers, retries)

        # Sleep for a while
        if content is not None:
            time.sleep(random.random())

        return content

    def getUrlImpl(self, url, params, headers, retries):

        r = Network.get(url, params=params, headers=headers, retries=retries)

        if r is None:
            return ''

        # TODO: add other judgement for http response
        return r.text

    @staticmethod
    def saveUrl(pathPrefix, url, retries=1):

        if Network._instance is None:
            Network._instance = Network()

        path = Network._instance.saveUrlImpl(pathPrefix, url, retries)

        # Sleep for a while
        if path is not None:
            time.sleep(random.random())

        return path 

    def saveUrlImpl(self, pathPrefix, url, retries):

        r = Network.get(url, retries=retries)
        if r is None:
            return None

        # TODO: add other judgement for http response

        contentType = r.headers['Content-Type']

        if 'image/jpeg' == contentType:
            pathname = '{}.jpg'.format(pathPrefix)
        elif 'image/png' == contentType:
            pathname = '{}.png'.format(pathPrefix)
        elif 'image/gif' == contentType:
            pathname = '{}.gif'.format(pathPrefix)
        elif 'audio/mpeg' == contentType:
            pathname = '{}.mp3'.format(pathPrefix)
        else:
            print('Not support', contentType)
            return None

        with open(pathname, 'wb') as fp:
            fp.write(r.content)

        chmod(pathname)

        print('Downloaded:', pathname)

        return pathname

