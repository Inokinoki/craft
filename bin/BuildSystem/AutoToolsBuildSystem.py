# -*- coding: utf-8 -*-
# definitions for the autotools build system

from BuildSystem.BuildSystemBase import BuildSystemBase
from CraftCore import CraftCore
from CraftOS.osutils import OsUtils
from shells import BashShell
import utils

import os
import glob
import re


class AutoToolsBuildSystem(BuildSystemBase):
    def __init__(self):
        BuildSystemBase.__init__(self, "autotools")
        self._shell = BashShell()
        self.platform = ""# hope for auto detection
        if CraftCore.compiler.isGCC() and not CraftCore.compiler.isNative() and CraftCore.compiler.isX86():
            self.platform = "--host=i686-pc-linux-gnu "
        elif CraftCore.compiler.isWindows:
            if CraftCore.compiler.isX86():
                self.platform = "--host=i686-w64-mingw32 --build=i686-w64-mingw32 --target=i686-w64-mingw32 "
            else:
                self.platform = "--host=x86_64-w64-mingw32 --build=x86_64-w64-mingw32 --target=x86_64-w64-mingw32 "

    @property
    def makeProgram(self):
        return "make"

    # make sure shell cant be overwritten
    @property
    def shell(self):
        return self._shell

    def configureDefaultDefines(self):

        """defining the default cmake cmd line"""
        return ""

    def configure(self):
        """configure the target"""
        self.enterBuildDir()

        configure = os.path.join(self.sourceDir(), self.subinfo.options.configure.projectFile or "configure")
        self.shell.environment["CFLAGS"] = self.subinfo.options.configure.cflags + " " + self.shell.environment["CFLAGS"]
        self.shell.environment["CXXFLAGS"] = self.subinfo.options.configure.cxxflags + " " + self.shell.environment["CXXFLAGS"]
        self.shell.environment["LDFLAGS"] = self.subinfo.options.configure.ldflags + " " + self.shell.environment["LDFLAGS"]

        autogen = os.path.join(self.sourceDir(), "autogen.sh")
        if self.subinfo.options.configure.bootstrap and os.path.exists(autogen):
            self.shell.execute(self.sourceDir(), autogen)
        elif self.subinfo.options.configure.autoreconf:
            includesArgs = ""
            if self.subinfo.options.configure.useDefaultAutoreconfIncludes:
                includes = []
                for i in [f"{CraftCore.standardDirs.craftRoot()}/dev-utils/cmake/share", CraftCore.standardDirs.locations.data]:
                    aclocalDir = self.shell.toNativePath(i) + "/aclocal"
                    if os.path.isdir(aclocalDir):
                        includes += [f" -I'{aclocalDir}'"]
                includesArgs = "".join(includes)
            self.shell.execute(self.sourceDir(), "autoreconf", self.subinfo.options.configure.autoreconfArgs + includesArgs)

        return self.shell.execute(self.buildDir(), configure, self.configureOptions(self))


    def make(self, dummyBuildType=None):
        """Using the *make program"""
        self.enterBuildDir()

        command = self.makeProgram
        args = self.makeOptions(self.subinfo.options.make.args)

        # adding Targets later
        if not self.subinfo.options.useShadowBuild:
            if not self.shell.execute(self.buildDir(), self.makeProgram, "clean"):
                return False
        return self.shell.execute(self.buildDir(), command, args)

    def install(self):
        """Using *make install"""
        self.cleanImage()
        self.enterBuildDir()

        command = self.makeProgram
        args = self.makeOptions(self.subinfo.options.install.args)

        destDir = self.shell.toNativePath(self.installDir())
        args += f" DESTDIR={destDir}"
        with utils.ScopedEnv({"DESTDIR" : destDir}):
            if not self.shell.execute(self.buildDir(), command, args):
                return False

        # la files aren't relocatable and until now we lived good without them
        laFiles = glob.glob(os.path.join(self.imageDir(), "**/*.la"), recursive=True)
        for laFile in laFiles:
            if not utils.deleteFile(laFile):
                return False

        return self._fixInstallPrefix(self.shell.toNativePath(self.installPrefix()))

    def unittest(self):
        """running unittests"""
        return self.shell.execute(self.buildDir(), self.makeProgram, "check")

    def configureOptions(self, defines=""):
        """returns default configure options"""
        options = BuildSystemBase.configureOptions(self)
        prefix = self.shell.toNativePath(self.installPrefix())
        options += f" --prefix='{prefix}' "
        if OsUtils.isWin() and not self.subinfo.options.configure.noDataRootDir:
            options += f" --datarootdir='{self.shell.toNativePath(CraftCore.standardDirs.locations.data)}' "
        options += self.platform

        return options;

    def ccacheOptions(self):
        return " CC='ccache gcc' CXX='ccache g++' "

    def copyToMsvcImportLib(self):
        if not OsUtils.isWin():
            return True
        reDlla = re.compile(r"\.dll\.a$")
        reLib = re.compile(r"^lib")
        for f in glob.glob(f"{self.installDir()}/lib/*.dll.a"):
            path, name = os.path.split(f)
            name = re.sub(reDlla, ".lib", name)
            name = re.sub(reLib, "", name)
            if not utils.copyFile(f, os.path.join(path, name), linkOnly=False):
                return False
        return True
