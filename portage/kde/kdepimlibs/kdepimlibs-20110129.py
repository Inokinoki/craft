import info
import kdedefaults as kd

class subinfo(info.infoclass):
    def setTargets( self ):
        self.svnTargets['gitHEAD'] = '[git]kde:%s|%s|' % (self.package, kd.kdebranch)
        for ver in ['0', '1', '2', '3', '4', '5']:
            self.targets[kd.kdeversion + ver] = "http://download.kde.org/stable/" + kd.kdeversion + ver + "/src/" + self.package + "-" + kd.kdeversion + ver + ".tar.xz"
            self.targetInstSrc[kd.kdeversion + ver] = self.package + '-' + kd.kdeversion + ver
            self.targetDigestUrls[ kd.kdeversion + ver  ] = 'http://download.kde.org/stable/' + kd.kdeversion + ver + '/src/' + self.package + '-' + kd.kdeversion + ver + '.tar.xz.sha1'
            self.patchToApply['4.12.0'] = [('0001-fix-wrong-MAKE_KABC_LIB-macro-this-is-now-kabc_EXPOR.patch', 1),
                                           ('0001-fix-build-error-on-windows-about-undefined-KSslError.patch', 1)]
        self.patchToApply['gitHEAD'] = [('0001-Add-support-for-gpgme_set_offline.patch', 1),
                                        ('0001-Fix-generate_export_header-port.patch',1)]

        self.defaultTarget = 'gitHEAD'

    def setDependencies( self ):
        self.dependencies['kde/kdelibs'] = 'default'
# Stripped down for gpg4win TODO make options out of this.
#        self.dependencies['kdesupport/akonadi'] = 'default'
#        self.dependencies['win32libs/cyrus-sasl'] = 'default'
#        self.dependencies['win32libs/libical'] = 'default'
        self.dependencies['binary/gpg4win-e5'] = 'default'
#        self.dependencies['win32libs/openldap'] = 'default'
        self.dependencies['win32libs/boost-graph'] = 'default'

        self.shortDescription = "the base libraries for PIM related services"

from Package.CMakePackageBase import *

class Package(CMakePackageBase):
    def __init__( self ):
        self.subinfo = subinfo()
        CMakePackageBase.__init__( self )
        self.boost = portage.getPackageInstance('win32libs','boost')
        path = self.boost.installDir()
        os.putenv( "BOOST_ROOT", path )
        self.subinfo.options.configure.defines = " -DKDEPIM_ONLY_KLEO=True"

if __name__ == '__main__':
    Package().execute()