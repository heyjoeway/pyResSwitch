import os
import win32api
import win32con
from typing import OrderedDict

from importlib_metadata import functools
import pystray

from PIL import Image, ImageDraw

state = False

import dataclasses

@dataclasses.dataclass
class AspectRatio:
    width: int
    height: int

    def __eq__(self, other):
        return (self.width == other.width) and (self.height == other.height)

    def __repr__(self) -> str:
        return f"{self.width}:{self.height}"

    def __hash__(self):
        return hash((self.width, self.height))

    @property
    @functools.cache
    def decimal(self) -> float:
        return self.width / float(self.height)

    @property
    @functools.cache
    def closestCommonRatio(self):
        maxError = 0.1
        commonRatios = AspectRatio._commonRatios
        indexClosest = min(
            range(len(commonRatios)),
            key=lambda i: abs(commonRatios[i].decimal - self.decimal)
        )
        ratioClosest = commonRatios[indexClosest]
        if abs(ratioClosest.decimal - self.decimal) > maxError:
            return None
        return ratioClosest

    @property
    def icon(self, width: int = 64, height: int = 64):
        outerWidth = float(width)
        outerHeight = float(height)
        if self.decimal >= 1: # Wider than tall (almost all the time)
            outerHeight /= self.decimal
        else:
            outerWidth *= self.decimal

        outerWidth = round(outerWidth)
        outerHeight = round(outerHeight)

        innerWidth = outerWidth - (width / 32)
        innerHeight = outerHeight - (height / 32)

        image = Image.new('RGBA', (width, height), (0,0,0,0))
        dc = ImageDraw.Draw(image)
        dc.rectangle(
            (0, 0, outerWidth, outerHeight),
            fill='black'
        )
        dc.rectangle(
            (1, 1, innerWidth, innerHeight),
            fill='white'
        )

AspectRatio._commonRatios = [
    AspectRatio(4, 3),
    AspectRatio(5, 4),
    AspectRatio(3, 2),
    AspectRatio(16, 10),
    AspectRatio(16, 9),
    AspectRatio(17, 9),
    AspectRatio(21, 9),
    AspectRatio(32, 9),
    AspectRatio(1, 1),
    AspectRatio(4, 1)
]


class Resolution(AspectRatio):
    def __post_init__(self):
        if self.height > self.width:
            self.width, self.height = self.height, self.width
            
        self._ratio = self.closestCommonRatio()

    @property
    def pixels(self):
        return self.width * self.height

    @property
    def ratio(self):
        return self._ratio

    @staticmethod
    def sortResolutions(resolutions: list):
        ratiosSorted = OrderedDict({ "Unknown": [] })
        for ratio in AspectRatio._commonRatios:
            ratiosSorted[ratio] = []

        for resolution in resolutions:
            ratiosSorted[resolution.closestCommonRatio].append(resolution)

        for key in ratiosSorted:
            ratiosSorted[key].sort(key=lambda res: res.pixels)

        return ratiosSorted

    def __repr__(self) -> str:
        return f"{self.width}x{self.height}"


class Monitor:
    def __init__(self, index: int):

        self._index = index
        self._device = win32api.EnumDisplayDevices(None, index, 0)

        connected = self._device.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP
        if not connected:
            raise Exception("Invalid monitor index")

    @property
    def name(self):
        displayNum = int(self._device.DeviceName.split("DISPLAY")[1])
        return f"Display {displayNum}"

    def __repr__(self):
        return f"{self._index + 1}: {self.name}"

    def _getCurrentSettings(self):
        return win32api.EnumDisplaySettings(self._device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)

    def getCurrentResolution(self) -> Resolution:
        devmode = self._getCurrentSettings()
        return Resolution(devmode.PelsWidth, devmode.PelsHeight)

    def getCurrentOrientation(self) -> int:
        return self._getCurrentSettings().DisplayOrientation

    def getRefreshRate(self) -> float:
        return self._getCurrentSettings().DisplayFrequency

    def setResolutionLambda(self, resolution: Resolution):
        return lambda: self.setResolution(resolution)

    def setResolution(self, resolution: Resolution):
        devmode = self._getCurrentSettings()

        devmode.PelsWidth = resolution.width
        devmode.PelsHeight = resolution.height

        devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
        win32api.ChangeDisplaySettings(devmode, 0)

    def setOrientationLambda(self, orientation: int):
        return lambda: self.setOrientation(orientation)

    def setOrientation(self, orientation: int):
        print(orientation)

        devmode = self._getCurrentSettings()

        devmode.DisplayOrientation = orientation
        if (orientation == win32con.DMDO_90) or (orientation == win32con.DMDO_270):
            devmode.PelsWidth, devmode.PelsHeight = devmode.PelsHeight, devmode.PelsWidth 
        devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT | win32con.DM_DISPLAYORIENTATION

        win32api.ChangeDisplaySettings(devmode, 0)

    @staticmethod
    def getAvailableMonitors():
        i = 0
        try:
            while True:
                yield Monitor(i)
                i += 1
        except:
            pass

    def getAvailableResolutions(self):
        resolutions = set()
        try:
            i=0
            while True:
                ds = win32api.EnumDisplaySettings(self._device.DeviceName, i)
                resolutions.add(Resolution(ds.PelsWidth, ds.PelsHeight))
                i+=1
        except:
            pass

        for resolution in resolutions:
            yield resolution

    @property
    def menu(self):
        for item in self.resolutionMenu:
            yield item

        # yield pystray.Menu.SEPARATOR
        # yield pystray.MenuItem(
        #     "Orientation",
        #     pystray.Menu(lambda: self.orientationMenu)
        # )
        # yield pystray.MenuItem(
        #     "Refresh Rate",
        #     pystray.Menu(lambda: self.refreshRateMenu)
        # )

    @property
    def orientationMenu(self):
        currentOrientation = self.getCurrentOrientation()

        def orientationCheckedLambda(enumVal):
            return lambda _: currentOrientation == enumVal

        orientationData = [
            (0, win32con.DMDO_DEFAULT, "Landscape"),
            (90, win32con.DMDO_90, "Portrait"),
            (90, win32con.DMDO_180, "Landscape, flipped"),
            (90, win32con.DMDO_270, "Potrait, flipped")
        ]

        for item in orientationData:
            angle = item[0]
            enumVal = item[1]
            name = item[2]
            yield pystray.MenuItem(
                f"{angle}° ({name})",
                self.setOrientationLambda(enumVal),
                radio=True,
                checked=orientationCheckedLambda(enumVal)
            )

    @property
    def refreshRateMenu(self):
        pass

    @property
    def resolutionMenu(self):
        currentResolution = self.getCurrentResolution()

        def resolutionCheckedLambda(resolution):
            return lambda _: currentResolution == resolution

        sortedResolutions = Resolution.sortResolutions(self.getAvailableResolutions())

        for ratio in sortedResolutions:
            resolutions = sortedResolutions[ratio]
            if len(resolutions) == 0:
                continue

            yield pystray.MenuItem(
                str(ratio),
                None,
                enabled=False
            )
            for resolution in resolutions:
                yield pystray.MenuItem(
                    str(resolution),
                    self.setResolutionLambda(resolution),
                    radio=True,
                    checked=resolutionCheckedLambda(resolution)
                )
            yield pystray.Menu.SEPARATOR

def create_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 2, 0, width, height // 2),
        fill=color2)
    dc.rectangle(
        (0, height // 2, width // 2, height),
        fill=color2)

    return image

def showMenu():
    trayIcon._on_notify(None, pystray._util.win32.WM_RBUTTONUP)


def mainMenu():
    monitors = list(Monitor.getAvailableMonitors())
    if len(monitors) > 1:
        for monitor in monitors:
            yield pystray.MenuItem(
                str(monitor),
                pystray.Menu(lambda: monitor.menu)
            )
    else:
        monitor = monitors[0]
        for item in monitor.menu:
            yield item

    yield pystray.Menu.SEPARATOR
    yield pystray.MenuItem(
        'Exit',
        lambda icon, item: trayIcon.stop(),
    )
    yield pystray.MenuItem(
        'Open Menu',
        lambda icon, item: showMenu(),
        default=True,
        visible=False
    )

trayIcon = pystray.Icon(
    'pyResSwitch',
    Image.open(os.path.join(os.path.dirname(__file__), "icon.png")),
    menu=pystray.Menu(mainMenu)
)

trayIcon.run()