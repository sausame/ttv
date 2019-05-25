#!/usr/bin/env python
# -*- coding:utf-8 -*-

from wand.image import Image as WandImage
from wand.color import Color

class ImageKit:

    @staticmethod
    def resize(dstFile, srcFile, keepRatio=False, start=(0,0), size=None, newSize=None, resolution=300):
    
        with WandImage(filename=srcFile, resolution=resolution) as img:

            if size is None:
                size = (img.width - start[0], img.height - start[1])

            with WandImage(width=size[0], height=size[1], background=Color('white')) as bg:

                bg.composite(img, start[0], start[1])

                if newSize is not None:

                    if keepRatio:

                        ratio = float(size[0]) / float(size[1])

                        temp = int(float(newSize[1]) * ratio)

                        if temp <= newSize[0]:
                            newSize = (temp, newSize[1])
                        else:
                            newSize = (newSize[0], int(newSize[0] / ratio))

                    bg.resize(newSize[0], newSize[1])

                bg.save(filename=dstFile)

