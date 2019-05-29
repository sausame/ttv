#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import sys
import time
import traceback

from combiner import Combiner, Tts
from datetime import datetime
from network import Network
from utils import reprDict, OutputPath, ThreadWritableObject

def run(name, configFile, ttsConfigFile, contentFile, videoFile, logFile):

    OutputPath.init(configFile)

    #thread = ThreadWritableObject(configFile, name, logFile)
    #thread.start()

    #sys.stdout = thread
    #sys.errout = thread # XXX: Actually, it does NOT work

    try:
        print('Now: ', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        Network.setIsEnabled(True)
        tts = Tts(ttsConfigFile)
        combiner = Combiner(configFile)
        combiner.combine(tts, contentFile, videoFile)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print('Error occurs at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        traceback.print_exc(file=sys.stdout)
    finally:
        pass

    #thread.quit()
    #thread.join()

if __name__ == '__main__':

    if len(sys.argv) < 5:
        print('Usage:\n\t', sys.argv[0], 'config-file tts-config-file content-file video-file [log-file]\n')
        exit()

    os.environ['TZ'] = 'Asia/Shanghai'
    time.tzset()

    name = os.path.basename(sys.argv[0])[:-3] # Remove ".py"
    configFile = os.path.realpath(sys.argv[1])
    ttsConfigFile = os.path.realpath(sys.argv[2])
    contentFile = os.path.realpath(sys.argv[3])
    videoFile = os.path.realpath(sys.argv[4])

    logFile = None

    if len(sys.argv) > 5:
        logFile = sys.argv[5]

    run(name, configFile, ttsConfigFile, contentFile, videoFile, logFile)

