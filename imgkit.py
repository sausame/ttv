#!/usr/bin/env python
# -*- coding:utf-8 -*-

from wand.image import Image as WandImage
from wand.color import Color
from PIL import Image, ImageFilter
from resizeimage import resizeimage

class ImageKit:

    @staticmethod
    def crop(dstFile, srcFile, dstSize):

        with open(srcFile, 'rb') as srcFp:
            with Image.open(srcFp) as image:

                width = int(dstSize[1] * image.width / image.height)
                height = int(dstSize[0] * image.height / image.width)

                if width < dstSize[0]:
                    width = dstSize[0]
                elif height < dstSize[1]:
                    height = dstSize[1]

        pos = dstFile.rfind('.')
        tempFile = '{}.tmp{}'.format(dstFile[:pos], dstFile[pos:])
        ImageKit.stretch(tempFile, srcFile, (width, height))

        with open(tempFile, 'rb') as srcFp:

            with Image.open(srcFp) as image:

                cover = resizeimage.resize_cover(image, dstSize)
                cover.save(dstFile, image.format)

    @staticmethod
    def stretch(dstFile, srcFile, dstSize, resolution=300):
 
        with WandImage(filename=srcFile, resolution=resolution) as srcImg:

            with WandImage(width=srcImg.width, height=srcImg.height, background=Color('white')) as dstImg:

                dstImg.composite(srcImg, 0, 0)
                dstImg.resize(dstSize[0], dstSize[1])
                dstImg.save(filename=dstFile)


    @staticmethod
    def blurdim(dstFile, srcFile):

        with open(srcFile, 'rb') as srcFp:

            with Image.open(srcFp) as srcImage:

                blurredImage = srcImage.filter(ImageFilter.GaussianBlur(8))
                dimImage = blurredImage.point(lambda p: p * 0.5)

                dimImage.save(dstFile, srcImage.format)

