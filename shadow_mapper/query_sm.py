# ----------------------------- START: COPY PASTING render.py -----------------------------------


#!/usr/bin/python

from datetime import datetime, timedelta
from .heightmap import HeightMap
from .suncalc import solar_position
from math import sin, cos, sqrt, atan2
import numpy
from os import path
from PIL import Image, ImageChops, ImageDraw
import argparse
import pickle


class Map(object):
    def __init__(self, lat, lng, resolution, size, proj):
        self.lat = lat
        self.lng = lng
        self.resolution = resolution
        self.size = size
        self.psize = size * resolution
        self.proj = proj
        cx, cy = proj(lng, lat)

        self.bounds = (
            cx - self.psize / 2,
            cy - self.psize / 2,
            cx + self.psize / 2,
            cy + self.psize / 2,
            )

        w, s = proj(self.bounds[0], self.bounds[1], inverse=True)
        e, n = proj(self.bounds[2], self.bounds[3], inverse=True)

        self.ll_bounds = (s, w, n, e)

    def _latLngToIndex(self, lat, lng):
        x, y = self.proj(lng, lat)
        return (
            (x - self.bounds[0]) / self.psize * self.size,
            (y - self.bounds[1]) / self.psize * self.size)

    def save(self, f):
        pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(f):
        return pickle.load(f)


use_native = False

class ShadowMap(Map):
    def __init__(self, lat, lng, resolution, size, proj, sun_x, sun_y, sun_z, heightmap, view_alt):
        Map.__init__(self, lat, lng, resolution, size, proj)
        self.sun_x = sun_x
        self.sun_y = sun_y
        self.sun_z = sun_z * self.resolution
        self.heightmap = heightmap
        self.view_alt = view_alt
        self.max_height = numpy.amax(self.heightmap.heights)
        self.min_height = numpy.amin(self.heightmap.heights)

    def render(self):
        shadowmap = numpy.zeros((self.size, self.size), dtype=int)
        for y in range(0, self.size):
            for x in range(0, self.size):
                shadowmap[(y, x)] = 1 if self.is_lit(x, y) else 0

        return shadowmap

    def to_image(self):
        data = self.render()
        rescaled = (255.0 / data.max() * (data - data.min())).astype(numpy.uint8)
        return Image.fromarray(rescaled).transpose(Image.FLIP_TOP_BOTTOM)

    def is_lit(self, x0, y0):
        # print(x0,y0)
        x1 = x0 + self.sun_x * self.size
        y1 = y0 + self.sun_y * self.size
        x0 = int(x0)
        y0 = int(y0)
        z = self.heightmap.heights[y0][x0] + self.view_alt
        zv = self.sun_z / sqrt(self.sun_x * self.sun_x + self.sun_y * self.sun_y)

        # print("shadowmap.py/is_lit - coords x0,y0: ",x0,y0)

        # Following is a Bresenham's algorithm line tracing.
        # This avoids performing lots of float calculations in
        # favor or integers, which is at least 10x faster.
        # Basic implementation taken from
        # http://stackoverflow.com/questions/2734714/modifying-bresenhams-line-algorithm
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1

        if y0 < y1:
            ystep = 1
        else:
            ystep = -1

        deltax = abs(x1 - x0)
        deltay = abs(y1 - y0)
        error = -deltax / 2
        y = y0

        xdir = 1 if x0 < x1 else -1
        x = x0
        while x > 0 and x < self.size and y > 0 and \
            y < self.size and z > self.min_height and z < self.max_height:
            if (steep and self.heightmap.heights[x, y] > z) or \
                (not steep and self.heightmap.heights[y, x] > z):
                return False

            error = error + deltay
            if error > 0:
                y = y + ystep
                error = error - deltax

            x += xdir
            z += zv

        return True



def get_projection_north_deviation(proj, lat, lng):
    x1, y1 = proj(lng, lat - 0.2)
    x2, y2 = proj(lng, lat + 0.2)
    return atan2(x2-x1, y2-y1)
