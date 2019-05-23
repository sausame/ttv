#!/usr/bin/env python
# -*- coding:utf-8 -*-

import hashlib
import json
import os
import urllib.parse

from network import Network
from utils import duration2srttime, getMatchString, getProperty, reprDict, runCommand, OutputPath

class ContentGenerator:

    def __init__(self, configFile, contentConfig):

        self.width = contentConfig['width']
        self.height = contentConfig['height']

        self.logo = contentConfig['logo']
        if self.logo is None or '' == self.logo:
            self.logo = getProperty(configFile, 'logo-path')

        self.backgroundPath = contentConfig['background']
        if self.backgroundPath is None or '' == self.backgroundPath:
            self.backgroundPath = getProperty(configFile, 'background-path')

        self.font = contentConfig['font']
        if self.font is None or '' == self.font:
            self.font = getProperty(configFile, 'font-path')

    def generate(self, tts, coding, content, silencePath):

        self.name = content['name']

        OutputPath.createDataPath(self.name)

        self.saveImages(coding, content['image-urls-list'])
        self.generateTts(tts, coding, content['text'], silencePath)

        self.createSlider()
        self.merge()

    def merge(self):

        path = OutputPath.getDataPath(self.name)

        # Merge image and audio
        pathname = os.path.join(path, 'temp.mp4')

        print('Merge', self.imagePath, 'and', self.audioPath, 'to', pathname)

        cmd = 'ffmpeg -y -i {} -i {} -c copy -map \'0:v:0\' -map \'1:a:0\' {}'.format(self.imagePath,
                self.audioPath, pathname)

        runCommand(cmd)

        # Add title
        imageVideoPath = os.path.join(path, 'image.mp4')

        print('Add title for', imageVideoPath)

        cmd = ''' ffmpeg -y -i {} -max_muxing_queue_size 2048 -vf drawtext="fontfile={}: \
                  text='{}': fontcolor=white: fontsize=48: box=1: boxcolor=black@0.5: \
                  boxborderw=5: x=(w-text_w)/2: y=20" -codec:a copy {} '''.format(pathname,
                          self.font, self.name, imageVideoPath)

        runCommand(cmd)

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
        assPath = os.path.join(path, 'subtitle.ass')

        print('Tranlate', self.subtitlePath, 'to', assPath)

        cmd = 'ffmpeg -y -i {} {}'.format(self.subtitlePath, assPath)
        runCommand(cmd)

        # Add subtitle
        subtitleVideoPath = os.path.join(path, 'ass.mp4')

        print('Add subtitle to', subtitleVideoPath)
        cmd = 'ffmpeg -y -i {} -vf "ass={}" {}'.format(imageVideoPath, assPath, subtitleVideoPath)

        runCommand(cmd)

        # Add logo
        self.videoPath = os.path.join(path, 'video.mp4')

        if self.logo is not None and '' != self.logo:

            print('Add logo to', self.videoPath)
            cmd = 'ffmpeg -y -i {} -i {} -filter_complex "overlay=10:10" {}'.format(subtitleVideoPath,
                    self.logo, self.videoPath)
        else:
            print('Rename', subtitleVideoPath, 'to', self.videoPath)
            cmd = 'mv {} {}'.format(subtitleVideoPath, self.videoPath)

        runCommand(cmd)

    def createSlider(self):

        if self.imageCount is 0:
            return

        duration = self.length / self.imageCount

        path = OutputPath.getDataPath(self.name)
        configPath = os.path.join(path, 'image.txt')

        with open(configPath, 'w') as fp:

            for index in range(self.imageCount):

                imagePath = os.path.join(path, '{}.png'.format(index))

                if index > 0:
                    fp.write('duration {:.2f}\n'.format(duration))

                fp.write('file \'{}\'\n'.format(imagePath))

                if index is 0:
                    fp.write('duration 0\n')
                    fp.write('file \'{}\'\n'.format(imagePath))
            else:
                if index > 0:
                    fp.write('duration 0\n')
                    fp.write('file \'{}\'\n'.format(imagePath))

        self.imagePath = os.path.join(path, 'image.mp4')

        cmd = 'ffmpeg -y -f concat -safe 0 -i {} -s {}x{} -vsync vfr -pix_fmt yuv420p {}'.format(configPath,
                self.width, self.height, self.imagePath)

        runCommand(cmd)

    def saveImages(self, coding, urls):

        def saveImage(path, index, url):

            prefix = os.path.join(path, '{}.original'.format(index))

            # TODO: if it already exists
            pathname = '{}.original.png'.format(prefix)
            if os.path.exists(pathname):
                return pathname

            pathname = '{}.original.jpg'.format(prefix)
            if os.path.exists(pathname):
                return pathname

            return Network.saveUrl(prefix, url)

        path = OutputPath.getDataPath(self.name)

        index = 0
        for url in urls:

            imagePath = saveImage(path, index, url)

            if imagePath is not None:

                if self.backgroundPath is not None and '' != self.backgroundPath:

                    # Scale image
                    scalePath = os.path.join(path, '{}.scale.png'.format(index))

                    print('Scale', imagePath, 'to', scalePath)

                    cmd = 'ffmpeg -y -i {0} -vf scale="\'if(gt(a,{1}/{2}),{1},-1)\':\'if(gt(a,{1}/{2}),-1,{2})\'" {3}'.format(imagePath,
                            self.width, self.height, scalePath)

                    runCommand(cmd)

                    # Overlay background
                    overlayPath = os.path.join(path, '{}.png'.format(index))

                    print('Overlay', self.backgroundPath, 'to', overlayPath)

                    cmd = 'ffmpeg -y -i {} -i {} -filter_complex "overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2" {}'.format(self.backgroundPath,
                            scalePath, overlayPath)

                    runCommand(cmd)
                else:

                    # Scale image
                    scalePath = os.path.join(path, '{}.png'.format(index))

                    print('Scale', imagePath, 'to', scalePath)

                    cmd = 'ffmpeg -y -i {0} -vf "scale={1}:{2}:force_original_aspect_ratio=decrease,pad={1}:{2}:(ow-iw)/2:(oh-ih)/2" {3}'.format(imagePath,
                            self.width, self.height, scalePath)

                    runCommand(cmd)

            index += 1

        self.imageCount = index

    def generateTts(self, tts, coding, text, silencePath):

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
        path = OutputPath.getDataPath(self.name)

        try:

            audioConfigPath = os.path.join(path, 'audio.txt')
            audioFp = open(audioConfigPath, 'w')

            self.subtitlePath = os.path.join(path, 'subtitle.srt')
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

                        audioPath = generateTtsWithIndex(tts, path, index, segment)

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
        pathname = os.path.join(path, 'audio.mp3')

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

    def combine(self, tts, contentFile):

        with open(contentFile) as fp:
            contentConfig = json.loads(fp.read())

            if contentConfig is None:
                print('No content')
                return

        coding = contentConfig['coding']

        silencePath = os.path.join(OutputPath.DATA_OUTPUT_PATH, 'silence.mp3')

        cmd = 'ffmpeg -y -f lavfi -i anullsrc=r=22050:cl=mono -t 1 -q:a 9 -acodec libmp3lame {}'.format(silencePath)
        runCommand(cmd)

        for content in contentConfig['contents-list']:

            tts.switchVoice()

            generator = ContentGenerator(self.configFile, contentConfig)
            generator.generate(tts, coding, content, silencePath)

class Tts:

    def __init__(self, pathname):

        with open(pathname) as fp:
            self.config = json.loads(fp.read())

            self.maxLength = int(self.config['max-length'])
            self.voiceIndex = None

    def switchVoice(self):

        if self.voiceIndex is None:
            self.voiceIndex = 0
        else:
            self.voiceIndex += 1

            if self.voiceIndex >= len(self.config['voiceIds']):
                self.voiceIndex = 0

    def generateTts(self, prefix, text):

        url = self.config['url']

        accountId = self.config['accountId'] 
        secretId = self.config['secretId'] 

        preparation = self.config['preparation']
        download = self.config['download']

        languageId = self.config['languageId']
        voiceId = self.config['voiceIds'][self.voiceIndex]

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


