# -*- coding: utf-8 -*-
# Copyright Hannah von Reth <vonreth@kde.org>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import tempfile

import CraftBase
from Blueprints.CraftDependencyPackage import CraftDependencyPackage
from Blueprints.CraftVersion import CraftVersion
from Utils.CraftTitleUpdater import CraftTitleUpdater
from Utils import CraftTimer
from options import *



def doExec(package, action):
    with CraftTimer.Timer("%s for %s" % (action, package), 1):
        CraftCore.debug.step("Action: %s for %s" % (action, package))
        ret = package.instance.execute(action)
        if not ret:
            if action == "fetch-binary":
                CraftCore.debug.step(f"{package} not found in cache")
                return False
            CraftCore.log.warning("Action: %s for %s FAILED" % (action, package))
        return ret


def handlePackage(package, buildAction, directTargets):
    with CraftTimer.Timer(f"HandlePackage {package}", 3) as timer:
        success = True
        actions = []
        timer.hook = lambda : utils.notify(f"Craft {buildAction} {'succeeded' if success else 'failed'}", f"{package} after {timer}", buildAction)
        CraftCore.debug.debug_line()
        CraftCore.debug.step(f"Handling package: {package}, action: {buildAction}")


        if buildAction == "all":
            if CraftCore.settings.getboolean("Packager", "UseCache", "False"):
                if doExec(package, "fetch-binary"):
                    return True
            actions = ["fetch", "unpack", "compile", "cleanimage", "install", "post-install"]

            if CraftCore.settings.getboolean("ContinuousIntegration", "ClearBuildFolder", False):
                actions += ["cleanbuild"]
            actions += ["qmerge", "post-qmerge"]
            if CraftCore.settings.getboolean("Packager", "CreateCache"):
                onlyDirect = CraftCore.settings.getboolean("Packager", "CacheDirectTargetsOnly")
                if not onlyDirect or (onlyDirect and package in directTargets):
                    actions += ["package"]
        else:
            actions = [buildAction]
        for action in actions:
            success = doExec(package, action)
            if not success:
                return False
        return True

def resolvePackage(packageNames : [str], version : str=None) -> [CraftPackageObject]:
    package = CraftPackageObject(None)
    def resolveChildren(child):
        if child.isCategory():
            for c in child.children.values():
                resolveChildren(c)
        else:
            if version:
                UserOptions.addPackageOption(child, "version", version)
            package.children[child.name] = child

    for packageName in packageNames:
        child = CraftPackageObject.get(packageName)
        if not child:
            raise BlueprintNotFoundException(packageName)
        resolveChildren(child)
    return package


def setOption(packageNames : [str], option : str) -> bool:
    if "=" not in option:
        CraftCore.log.error(f"Invalid option {option}")
        return False
    key, value = option.split("=", 1)
    for name in packageNames:
        package = CraftPackageObject.get(name)
        if not package:
            raise BlueprintNotFoundException(name)
        options = UserOptions.get(package)
        if not options.setOption(key, value):
            return False
        CraftCore.log.info(f"[{package}]\n{key}={getattr(options, key)}")
    return True

def addBlueprintsRepository(url : str, args) -> bool:
    templateDir = os.path.join(CraftCore.standardDirs.craftBin(), "..", "internal_blueprints" )
    with tempfile.TemporaryDirectory() as tmp:
        iniPath = os.path.join(tmp, "version.ini")
        parser = configparser.ConfigParser()
        parser.read(iniPath)
        parser.add_section("General")
        parser["General"]["branches"] = "master"
        parser["General"]["defaulttarget"] = "master"
        parser["General"]["gitUrl"] = url
        with open(iniPath, "wt+") as out:
            parser.write(out)
        CraftCore.settings.set("Blueprints", "Locations", templateDir)
        CraftCore.settings.set("InternalTemp", "add-bluprints-template.ini", iniPath)
        package = resolvePackage(["add-bluprints-template"])
        return run(package, "fetch", args)

def destroyCraftRoot() -> bool:
    settingsFiles = {"kdesettings.ini", "CraftSettings.ini", "BlueprintSettings.ini"}
    dirsToKeep = [CraftCore.standardDirs.downloadDir(),
                  os.path.join(CraftCore.standardDirs.craftBin(), ".."),
                  os.path.join(CraftCore.standardDirs.craftRoot(), "python"),
                  CraftCore.standardDirs.blueprintRoot()]
    # dirs with possible interesting sub dirs
    maybeKeepDir = [
        CraftCore.standardDirs.craftRoot(),
        CraftCore.standardDirs.etcDir(),
        os.path.join(CraftCore.standardDirs.etcDir(), "blueprints")# might contain blueprintRoot
        ]
    def deleteEntry(path):
        if utils.OsUtils.isLink(path):
            CraftCore.log.debug(f"Skipping symlink {path}")
            return
        if os.path.isdir(path):
            if any(os.path.exists(x) and os.path.samefile(path, x) for x in maybeKeepDir):
                CraftCore.log.debug(f"Path {path} in maybeKeepDir")
                for entry in os.listdir(path):
                    deleteEntry(os.path.join(path, entry))
            elif any(os.path.exists(x) and os.path.samefile(path, x) for x in dirsToKeep):
                CraftCore.log.debug(f"Path {path} in dirsToKeep")
            else:
                utils.cleanDirectory(path)
                utils.OsUtils.rmDir(path, True)
        else:
            if os.path.basename(path) not in settingsFiles:
                utils.OsUtils.rm(path, True)

    del CraftCore.installdb
    deleteEntry(CraftCore.standardDirs.craftRoot())
    return True


def readListFile(listFile):
    packageNames = []
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read(listFile)
    for sections in parser.keys():
        for packageName in parser[sections]:
            CraftCore.settings.set("BlueprintVersions", packageName, parser.get(sections, packageName))
            packageNames.append(packageName)
    return packageNames


def packageIsOutdated(package):
    installed = CraftCore.installdb.getInstalledPackages(package)
    if not installed:
        return True
    for pack in installed:
        version = pack.getVersion()
        if not version: continue
        if CraftCore.settings.getboolean("ContinuousIntegration", "Enabled", False):
            # automatically downgreade in ci mode
            return package.version != version
        else:
            cacheVersion = pack.getCacheVersion()
            if cacheVersion and cacheVersion != CraftBase.CraftBase.cacheVersion():
                # can only happen for packages installed from cache
                return True
            return CraftVersion(package.version) > CraftVersion(version)


def invoke(command : str, directTargets : [CraftPackageObject]) -> bool:
    key = command.replace("()", "")
    subs = key.split(".")
    for p in directTargets:
        instance = p.instance
        path = []
        for sub in subs:
            path += [sub]
            if hasattr(instance, sub):
                attr = getattr(instance, sub)
                if callable(attr):
                    instance = attr()
                else:
                    instance = attr
            else:
                CraftCore.debug.printOut(f"{p} has no member {'.'.join(path)}", file=sys.stderr)
                return False
        CraftCore.debug.printOut(instance)
        return True

def run(package : [CraftPackageObject], action : str, args) -> bool:
    if package.isIgnored():
        CraftCore.log.info(f"Skipping package because it has been ignored: {package}")
        return True
    directTargets = package.children.values()

    if action == "get":
        return invoke(args.get, directTargets)
    elif action in ["all", "install-deps"]:
        # work on the dependencies
        depPackage = CraftDependencyPackage(package)
        depList = depPackage.getDependencies()

        packages = []
        for item in depList:
            if (args.ignoreInstalled and item in directTargets) or packageIsOutdated(item):
                packages.append(item)
                CraftCore.log.debug(f"dependency: {item}")
        if not packages:
            CraftCore.log.debug("<none>")

        if action == "install-deps":
            # we don't intend to build the package itself
            for x in directTargets:
                packages.remove(x)

        CraftTitleUpdater.usePackageProgressTitle(packages)
        while packages:
            info = packages[0]
            # in case we only want to see which packages are still to be build, simply return the package name
            if args.probe:
                CraftCore.log.warning(f"pretending {info}: {info.version}")
            else:
                if CraftCore.settings.getboolean("ContinuousIntegration", "Enabled", False):
                    CraftCore.debug.debug_line()
                    CraftCore.log.info(f"Status: {CraftTitleUpdater.instance}")
                if action in ["install-deps"]:
                    action = "all"

                if not handlePackage(info, action, directTargets=directTargets):
                    CraftCore.log.error(f"fatal error: package {info} {action} failed")
                    return False
            packages.pop(0)
    else:
        for info in directTargets:
            if not handlePackage(info, action, directTargets=directTargets):
                return False

    CraftCore.debug.new_line()
    return True
