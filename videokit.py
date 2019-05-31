#!/usr/bin/env python
# -*- coding:utf-8 -*-

from utils import runCommand

class VideoMaker:

    def __init__(self):
        self.videoList = None

    def appendVideo(self, srcVideoPath):

        if self.videoList is None:
            self.videoList = list()

        self.videoList.append(srcVideoPath)
        return self

    def merge(self, dstVideoPath):

        if self.videoList is None:
            return

        configPath = '{}.txt'.format(dstVideoPath)

        with open(configPath, 'w') as fp:
            for video in self.videoList:
                fp.write('file \'{}\'\n'.format(video))

        print('Merge all to', dstVideoPath, 'from', configPath)

        cmd = 'ffmpeg -y -f concat -safe 0 -i {} -c copy {}'.format(configPath, dstVideoPath)

        runCommand(cmd)

class VideoKit:

    @staticmethod
    def createLoopVideo(dstVideoPath, srcImagePath, videoLength):

        print('Create video to', dstVideoPath, 'from', srcImagePath, 'with length', videoLength)

        cmd = 'ffmpeg -y -loop 1 -i {} -c:v libx264 -t {:.2f} -pix_fmt yuv420p {}'.format(srcImagePath,
                videoLength, dstVideoPath)

        runCommand(cmd)

        return dstVideoPath

    @staticmethod
    def appendVideo(srcVideoPath, videoMaker=None):
        if videoMaker is None:
            videoMaker = VideoMaker()

        videoMaker.appendVideo(srcVideoPath)
        return videoMaker

    @staticmethod
    def merge(dstVideoPath, srcVideoPath, srcAudioPath):

        print('Merge', srcVideoPath, 'and', srcAudioPath, 'to', dstVideoPath)

        cmd = 'ffmpeg -y -i {} -i {} -c copy -map \'0:v:0\' -map \'1:a:0\' {}'.format(srcVideoPath,
                srcAudioPath, dstVideoPath)

        runCommand(cmd)

