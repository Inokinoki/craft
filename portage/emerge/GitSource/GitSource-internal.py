import info

class subinfo(info.infoclass):
    def setDependencies( self ):
        self.hardDependencies['dev-util/git'] = 'default'     
        self.hardDependencies['dev-util/putty'] = 'default'     

from Package.InternalPackageBase import * 

class Package(InternalPackageBase):
    def __init__( self ):
        self.subinfo = subinfo()
        InternalPackageBase.__init__(self)

if __name__ == '__main__':
    Package().execute()
