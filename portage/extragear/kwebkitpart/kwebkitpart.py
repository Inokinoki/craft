import info

class subinfo(info.infoclass):
    def setTargets( self ):
        self.svnTargets['master'] = '[git]kde:kwebkitpart'
        self.shortDescription = 'A WebKit browser component for KDE (KPart)'
        self.defaultTarget = 'master'

    def setDependencies( self ):
        self.dependencies['kde/kdelibs'] = 'default'

from Package.CMakePackageBase import *

class Package(CMakePackageBase):
    def __init__( self ):
        CMakePackageBase.__init__( self )

