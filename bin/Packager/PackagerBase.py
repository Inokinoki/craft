#
# copyright (c) 2009 Ralf Habacker <ralf.habacker@freenet.de>
#
# Packager base

import datetime
import json
import glob
from pathlib import Path

from CraftBase import *

from Utils import CraftHash
from Utils.CraftManifest import *

from CraftDebug import deprecated


class PackagerBase(CraftBase):
    """ provides a generic interface for packagers and implements basic package creating stuff """

    @InitGuard.init_once
    def __init__(self):
        CraftBase.__init__(self)
        self.whitelist_file = []
        self.blacklist_file = []
        self.defines = {}
        self.ignoredPackages = []

    def setDefaults(self, defines: {str:str}) -> {str:str}:
        defines = dict(defines)
        defines.setdefault("setupname", os.path.join(self.packageDestinationDir(), self.binaryArchiveName(includeRevision=True, fileType="")))
        defines.setdefault("shortcuts", "")
        defines.setdefault("architecture", CraftCore.compiler.architecture)
        defines.setdefault("company", "KDE e.V.")
        defines.setdefault("productname", self.subinfo.displayName)
        defines.setdefault("display_name", self.subinfo.displayName)
        defines.setdefault("description", self.subinfo.description)
        defines.setdefault("icon", os.path.join(CraftCore.standardDirs.craftBin(), "data", "icons", "craft.ico"))
        defines.setdefault("icon_png", os.path.join(CraftCore.standardDirs.craftBin(), "data", "icons", "craftyBENDER.png"))
        defines.setdefault("icon_png_44", defines["icon_png"])
        defines.setdefault("license", "")
        defines.setdefault("version", self.sourceRevision() if self.subinfo.hasSvnTarget() else self.version)
        defines.setdefault("website",
                           self.subinfo.webpage if self.subinfo.webpage else "https://community.kde.org/Craft")

        # mac
        defines.setdefault("apppath", "")
        defines.setdefault("appname", self.package.name.lower())
        return defines

    def getMacAppPath(self, defines, lookupPath = None):
        lookPath = os.path.normpath(lookupPath if lookupPath else self.archiveDir())
        appPath = defines['apppath']
        if not appPath:
            apps = glob.glob(os.path.join(lookPath, f"**/{defines['appname']}.app"), recursive=True)
            if len(apps) != 1:
                CraftCore.log.error(f"Failed to detect {defines['appname']}.app for {self}, please provide a correct self.defines['apppath'] or a relative path to the app as self.defines['apppath']")
                return False
            appPath = apps[0]
        appPath = os.path.join(lookPath, appPath)
        return os.path.normpath(appPath)

    def preArchive(self):
        utils.abstract()

    def archiveDir(self):
        return os.path.join(self.buildRoot(), "archive")

    # """ create a package """
    def createPackage(self):
        utils.abstract()

    def _generateManifest(self, destDir, archiveName, manifestLocation=None, manifestUrls=None):
        if not manifestLocation:
            manifestLocation = destDir
        manifestLocation = os.path.join(manifestLocation, "manifest.json")
        archiveFile = os.path.join(destDir, archiveName)

        name = archiveName if not os.path.isabs(archiveName) else os.path.relpath(archiveName, destDir)

        manifest = CraftManifest.load(manifestLocation, urls=manifestUrls)
        entry = manifest.get(str(self))
        entry.addFile(name, CraftHash.digestFile(archiveFile, CraftHash.HashAlgorithm.SHA256), version=self.version, config=self.subinfo.options.dynamic)

        manifest.dump(manifestLocation)

    def _createArchive(self, archiveName, sourceDir, destDir, createDigests=True, extention=None) -> bool:
        if extention is None:
            extention = "." + CraftCore.settings.get("Packager", "7ZipArchiveType", "7z")
            if extention == ".7z" and CraftCore.compiler.isUnix:
                if self.package.path == "dev-utils/7zip" or not CraftCore.cache.findApplication("7za"):
                    extention = ".tar.xz"
                else:
                    extention = ".tar.7z"

        archiveName = str((Path(destDir) / archiveName)) + extention
        if not utils.compress(archiveName, sourceDir):
            return False

        if createDigests:
            if not CraftCore.settings.getboolean("Packager", "CreateCache"):
                self._generateManifest(destDir, archiveName)
                CraftHash.createDigestFiles(archiveName)
            else:
                if CraftCore.settings.getboolean("ContinuousIntegration", "UpdateRepository", False):
                    manifestUrls = [self.cacheRepositoryUrls()[0]]
                else:
                    manifestUrls = None
                self._generateManifest(destDir, archiveName, manifestLocation=self.cacheLocation(),
                                       manifestUrls=manifestUrls)
        return True
