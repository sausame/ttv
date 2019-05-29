#!/usr/bin/env python
# -*- coding:utf-8 -*-

import base64
import hashlib
import json
import os
import urllib.parse

from imgkit import ImageKit
from network import Network
from urllib.parse import unquote
from utils import duration2srttime, getMatchString, getProperty, reprDict, runCommand, OutputPath

class ContentGenerator:

    def __init__(self, configFile, contentConfig, background):

        self.configFile = configFile
        self.contentConfig = contentConfig
        self.background = background

        self.coding = self.contentConfig['coding']

    def getValue(self, dictObj, key):

        def getDictValue(dictObj, key, coding='plate'):

            if 'plate' == coding.lower():
                return dictObj[key]

            if 'base64' == coding.lower():
                value = dictObj[key] 
                if not value:
                    return value

                return unquote(base64.b64decode(value).decode('utf-8'))

            print('Not support', coding)
            return None

        return getDictValue(dictObj, key, self.coding)

    def generate(self, tts, content, silencePath):

        text = self.getValue(content, 'text')

        self.name = self.getValue(content, 'name')
        name = self.name

        if not name:

            m = hashlib.md5()
            m.update(text.encode('utf-8'))
            name = m.hexdigest()[:8]

        OutputPath.createDataPath(name)
        self.path = OutputPath.getDataPath(name)

        self.prepare()

        self.saveImages(content['image-urls-list'])
        self.generateTts(tts, text, silencePath)

        self.createSlider()
        self.merge()

    def prepare(self):

        self.width = int(self.contentConfig['width'])
        self.height = int(self.contentConfig['height'])

        # Font
        self.font = self.contentConfig['font']
        if not self.font:
            self.font = getProperty(self.configFile, 'font-path')

    def merge(self):

        # Merge image and audio
        pathname = os.path.join(self.path, 'temp.mp4')

        print('Merge', self.imagePath, 'and', self.audioPath, 'to', pathname)

        cmd = 'ffmpeg -y -i {} -i {} -c copy -map \'0:v:0\' -map \'1:a:0\' {}'.format(self.imagePath,
                self.audioPath, pathname)

        runCommand(cmd)

        # Add title

        if self.name and self.font:

            titlePath = os.path.join(self.path, 'title.mp4')

            print('Add title for', titlePath)

            cmd = ''' ffmpeg -y -i {} -max_muxing_queue_size 10240 -vf drawtext="fontfile={}: \
                      text='{}': fontcolor=white: fontsize=48: box=1: boxcolor=black@0.5: \
                      boxborderw=5: x=(w-text_w)/2: y=20" -codec:a copy {} '''.format(pathname,
                              self.font, self.name, titlePath)

            runCommand(cmd)
        else:
            titlePath = pathname

        # Create subtitle
        '''
            When you create an SRT file in a text editor, you need to format the text
            correctly and save it as an SRT file. This format should include:

                [Section of subtitles number]
                [Time the subtitle is displayed begins]-->[Time the subtitle is displayed ends]
                [Subtitle]

            To format the timestamps correctly, show:
                [hours]:[minutes]:[seconds],[milliseconds]
        '''
        assPath = os.path.join(self.path, 'subtitle.ass')

        print('Tranlate', self.subtitlePath, 'to', assPath)

        cmd = 'ffmpeg -y -i {} {}'.format(self.subtitlePath, assPath)
        runCommand(cmd)

        # Add subtitle
        self.videoPath = os.path.join(self.path, 'video.mp4')

        print('Add subtitle to', self.videoPath)
        cmd = 'ffmpeg -y -i {} -max_muxing_queue_size 2048 -vf "ass={}" {}'.format(titlePath, assPath, self.videoPath)

        runCommand(cmd)

    def createSlider(self):

        self.imagePath = os.path.join(self.path, 'image.mp4')

        if self.imageCount is 0:
            print('Create slider to', self.imagePath, 'from', self.background)

            # TODO: Use background as image
            cmd = 'ffmpeg -y -loop 1 -i {} -c:v libx264 -t {:.2f} -pix_fmt yuv420p {}'.format(self.background,
                    self.length, self.imagePath)

            runCommand(cmd)

            return

        configPath = os.path.join(self.path, 'image.txt')

        with open(configPath, 'w') as fp:

            duration = self.length / self.imageCount

            count = -1

            for index in range(self.imageCount):

                imagePath = os.path.join(self.path, '{}.jpg'.format(index))

                if not os.path.exists(imagePath):
                    continue

                count += 1

                if count > 0:
                    fp.write('duration {:.2f}\n'.format(duration))

                fp.write('file \'{}\'\n'.format(imagePath))

                if count is 0:
                    fp.write('duration 0\n')
                    fp.write('file \'{}\'\n'.format(imagePath))
            else:
                if count > 0:
                    fp.write('duration 0\n')
                    fp.write('file \'{}\'\n'.format(imagePath))

        print('Create slider to', self.imagePath, 'from', configPath)

        cmd = 'ffmpeg -y -f concat -safe 0 -i {} -s {}x{} -vsync vfr -pix_fmt yuv420p {}'.format(configPath,
                self.width, self.height, self.imagePath)

        runCommand(cmd)

    def saveImages(self, urls):

        def saveImage(path, index, url):

            prefix = os.path.join(path, '{}.original'.format(index))

            # TODO: if it already exists
            pathname = '{}.original.png'.format(prefix)
            if os.path.exists(pathname):
                return pathname

            pathname = '{}.original.jpg'.format(prefix)
            if os.path.exists(pathname):
                return pathname

            pathname = '{}.original.gif'.format(prefix)
            if os.path.exists(pathname):
                return pathname

            return Network.saveUrl(prefix, url)

        index = 0
        for url in urls:

            if not url:
                continue

            imagePath = saveImage(self.path, index, url)

            if imagePath is not None:

                if self.background:

                    # Scale image
                    scalePath = os.path.join(self.path, '{}.scale.jpg'.format(index))

                    print('Scale', imagePath, 'to', scalePath)

                    cmd = 'ffmpeg -y -i {0} -vf scale="\'if(gt(a,{1}/{2}),{1},-1)\':\'if(gt(a,{1}/{2}),-1,{2})\'" {3}'.format(imagePath,
                            self.width, self.height, scalePath)

                    runCommand(cmd)

                    # Overlay background
                    overlayPath = os.path.join(self.path, '{}.jpg'.format(index))

                    print('Overlay', self.background, 'to', overlayPath)

                    cmd = 'ffmpeg -y -i {} -i {} -filter_complex "overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2" {}'.format(self.background,
                            scalePath, overlayPath)

                    runCommand(cmd)
                else:

                    # Scale image
                    scalePath = os.path.join(self.path, '{}.jpg'.format(index))

                    print('Scale', imagePath, 'to', scalePath)

                    cmd = 'ffmpeg -y -i {0} -vf "scale={1}:{2}:force_original_aspect_ratio=decrease,pad={1}:{2}:(ow-iw)/2:(oh-ih)/2" {3}'.format(imagePath,
                            self.width, self.height, scalePath)

                    runCommand(cmd)

                index += 1

        self.imageCount = index

    def generateTts(self, tts, text, silencePath):

        def generateTtsWithIndex(tts, path, index, segment):

            prefix = os.path.join(path, '{}'.format(index))

            # TODO: if it already exists
            pathname = '{}.mp3'.format(prefix)
            if os.path.exists(pathname):
                return pathname

            return tts.generateTts(prefix, segment)

        def getAudioLength(pathname):

            import re

            # Get length of audio
            print('Get length of', pathname)

            cmd = 'ffmpeg -v quiet -stats -i {} -f null -'.format(pathname)

            output = runCommand(cmd)

            timeString = b'time='
            start = output.find(timeString)

            if start > 0:
                start += len(timeString)
                end = output.find(b' ', start)

                if end > 0:
                    array = list(map(int, re.findall(b'\d+', output[start:end])))
                    if len(array) is 4:
                        length = array[0] * 360000 + array[1] * 6000 + array[2] * 100 + array[3]
                        return float(length) / 100

            return 0.0

        def getAudioLengthYet(pathname):

            # Get length of audio
            print('Get length of', pathname)

            cmd = 'sox {} -n stat'.format(pathname)

            output = runCommand(cmd)

            lengthString = b'\nLength (seconds):'
            start = output.find(lengthString)

            if start > 0:
                start += len(lengthString)
                end = output.find(b'\n', start)

                if end > 0:
                    return float(output[start:end])

            return 0.0

        self.length = 0.0

        try:

            audioConfigPath = os.path.join(self.path, 'audio.txt')
            audioFp = open(audioConfigPath, 'w')

            self.subtitlePath = os.path.join(self.path, 'subtitle.srt')
            srtFp = open(self.subtitlePath, 'w')

            length = len(text)

            start = 0
            index = 0

            while start < length:

                end = text.find('\n', start)
                if end < 0:
                    end = length - 1
                
                # TODO: text should NOT start with '\n'
                if index > 0:

                    self.length += 1.0 # Increase audio length

                    audioFp.write('file \'{}\'\n'.format(silencePath))

                if end > start:
                    segment = text[start:end]

                    if len(segment.encode('utf-8')) < tts.maxLength:

                        audioPath = generateTtsWithIndex(tts, self.path, index, segment)

                        if audioPath is not None:

                            audioFp.write('file \'{}\'\n'.format(audioPath))

                            audioLength = self.length + getAudioLength(audioPath)

                            srtFp.write('{}\n{} --> {}\n{}\n\n'.format((index + 1),
                                duration2srttime(self.length), duration2srttime(audioLength),
                                segment))

                            self.length = audioLength

                        index += 1

                    else:
                        print('A segment started from position', start,
                                'is longer than', tts.maxLength,
                                ':', segment)
                        break

                start = end + 1

        finally:
            if audioFp is not None:
                audioFp.close()

            if srtFp is not None:
                srtFp.close()

        if index is 0:
            return

        # Concat all audio
        pathname = os.path.join(self.path, 'audio.mp3')

        if index is 1:
            print('Rename', audioPath, 'to', pathname)
            cmd = 'mv {} {}'.format(audioPath, pathname)

        else:
            print('Create', pathname)
            cmd = 'ffmpeg -y -f concat -safe 0 -i {0} -c copy {1}'.format(audioConfigPath,
                    pathname)

        runCommand(cmd)

        # To m4a
        self.audioPath = '{}m4a'.format(pathname[:-3])

        print('Translate', pathname, 'to', self.audioPath)
        cmd = 'ffmpeg -y -i {} -vn -acodec aac -strict -2 \'-bsf:a\' aac_adtstoasc {}'.format(pathname,
                self.audioPath)

        runCommand(cmd)

class Combiner:

    def __init__(self, configFile):
        self.configFile = configFile

    def combine(self, tts, contentFile, videoFile):

        with open(contentFile) as fp:
            contentConfig = json.loads(fp.read())

            if contentConfig is None:
                print('No content')
                return

        self.contentConfig = contentConfig

        self.prepare()

        videos = list()

        self.coding = self.contentConfig['coding']

        tts.setLanguage(self.contentConfig['language'])

        for content in self.contentConfig['contents-list']:

            tts.switchVoice()

            generator = ContentGenerator(self.configFile, self.contentConfig, self.background)
            generator.generate(tts, content, self.silencePath)

            if generator.videoPath is not None:
                videos.append(generator.videoPath)

        self.postProcess(videos, videoFile)

    def prepare(self):

        self.width = int(self.contentConfig['width'])
        self.height = int(self.contentConfig['height'])

        # Logo:
        logo = self.contentConfig['logo']

        if logo:
            # TODO: download logo
            pass
        else:
            logo = getProperty(self.configFile, 'logo-path')

        if logo:
            self.logo = os.path.join(OutputPath.DATA_OUTPUT_PATH, 'logo.jpg')

            logoWidth = int(self.contentConfig['logo-width'])
            logoHeight = int(self.contentConfig['logo-height'])

            print('Create logo', self.logo, 'from', logo)

            '''
            cmd = 'ffmpeg -y -i {} -vf scale="{}:{}" {}'.format(logo,
                    logoWidth, logoHeight, self.logo)

            runCommand(cmd)
            '''

            ImageKit.resize(self.logo, logo, newSize=(logoWidth, logoHeight))
        else:
            self.logo = None

        # Background:
        background = self.contentConfig['background']

        if background:
            # TODO: download background
            pass
        else:
            background = getProperty(self.configFile, 'background-path')

        if background:
            self.background = os.path.join(OutputPath.DATA_OUTPUT_PATH, 'background.jpg')

            print('Create background', self.background, 'from', background)

            '''
            cmd = 'ffmpeg -y -i {} -vf scale="{}:{}" {}'.format(background,
                    self.width, self.height, self.background)

            runCommand(cmd)
            '''

            ImageKit.resize(self.background, background, newSize=(self.width, self.height))
        else:
            self.background = None

        # Create silence
        self.silencePath = os.path.join(OutputPath.DATA_OUTPUT_PATH, 'silence.mp3')

        print('Create silence in', self.silencePath)

        cmd = 'ffmpeg -y -f lavfi -i anullsrc=r=22050:cl=mono -t 1 -q:a 9 -acodec libmp3lame {}'.format(self.silencePath)
        runCommand(cmd)

        # To m4a
        audioPath = '{}m4a'.format(self.silencePath[:-3])

        print('Translate', self.silencePath, 'to', audioPath)
        cmd = 'ffmpeg -y -i {} -vn -acodec aac -strict -2 \'-bsf:a\' aac_adtstoasc {}'.format(self.silencePath,
                audioPath)

        runCommand(cmd)

        # Create separator between videos
        separatorPath = os.path.join(OutputPath.DATA_OUTPUT_PATH, 'image.mp4')

        print('Create separator in', separatorPath)

        cmd = 'ffmpeg -y -loop 1 -i {} -c:v libx264 -t 1 -pix_fmt yuv420p {}'.format(self.background,
                separatorPath)

        runCommand(cmd)

        # Merge image and audio
        self.separatorPath = os.path.join(OutputPath.DATA_OUTPUT_PATH, 'separator.mp4')

        print('Merge', separatorPath, 'and', audioPath, 'to', self.separatorPath)

        cmd = 'ffmpeg -y -i {} -i {} -c copy -map \'0:v:0\' -map \'1:a:0\' {}'.format(separatorPath,
                audioPath, self.separatorPath)

        runCommand(cmd)

    def postProcess(self, videos, videoFile):

        if len(videos) is 0:
            return

        # Merge all videos
        configPath = os.path.join(OutputPath.DATA_OUTPUT_PATH, 'video.txt')

        with open(configPath, 'w') as fp:
            for video in videos:
                fp.write('file \'{}\'\n'.format(video))
                fp.write('file \'{}\'\n'.format(self.separatorPath))
                fp.write('file \'{}\'\n'.format(self.separatorPath))

        videoPath = os.path.join(OutputPath.DATA_OUTPUT_PATH, 'all.mp4')

        print('Merge all to', videoPath, 'from', configPath)
        cmd = 'ffmpeg -y -f concat -safe 0 -i {} -c copy {}'.format(configPath, videoPath)

        runCommand(cmd)

        # Add logo
        self.videoPath = videoFile

        if self.logo:

            print('Add logo to', self.videoPath)
            cmd = 'ffmpeg -y -i {} -i {} -max_muxing_queue_size 10240 -filter_complex "overlay=10:10" {}'.format(videoPath,
                    self.logo, self.videoPath)
        else:
            print('Rename', videoPath, 'to', self.videoPath)
            cmd = 'mv {} {}'.format(videoPath, self.videoPath)

        runCommand(cmd)

class Tts:

    def __init__(self, pathname):

        with open(pathname) as fp:
            self.config = json.loads(fp.read())

            self.maxLength = int(self.config['max-length'])

    def setLanguage(self, language):

        for lang in self.config['languages']:
            if language.lower() == lang['name']:
                self.language = lang
                break
        else:
            print('Not support language', language)

        self.voiceIndex = None

    def switchVoice(self):

        if self.voiceIndex is None:
            self.voiceIndex = 0
        else:
            self.voiceIndex += 1

            if self.voiceIndex >= len(self.language['voiceIds']):
                self.voiceIndex = 0

    def generateTts(self, prefix, text):

        url = self.config['url']

        accountId = self.config['accountId'] 
        secretId = self.config['secretId'] 

        preparation = self.config['preparation']
        download = self.config['download']

        languageId = self.language['languageId']
        voiceId = self.language['voiceIds'][self.voiceIndex]

        m = hashlib.md5()

        m.update(preparation['EID'].encode('utf-8'))
        m.update(languageId.encode('utf-8'))
        m.update(voiceId.encode('utf-8'))
        m.update(text.encode('utf-8'))
        m.update(preparation['IS_UTF8'].encode('utf-8'))
        m.update(preparation['EXT'].encode('utf-8'))
        m.update(accountId.encode('utf-8'))
        m.update(secretId.encode('utf-8'))

        cs = m.hexdigest()

        preparation['LID'] = languageId
        preparation['VID'] = voiceId
        preparation['ACC'] = accountId
        preparation['TXT'] = text
        preparation['CS'] = cs

        download['LID'] = languageId
        download['VID'] = voiceId
        download['ACC'] = accountId
        download['TXT'] = text
        download['CS'] = cs

        preparationUrl = '{}{}'.format(url, urllib.parse.urlencode(preparation))

        Network.get(preparationUrl)

        downloadUrl = '{}{}'.format(url, urllib.parse.urlencode(download))

        return Network.saveUrl(prefix, downloadUrl)

