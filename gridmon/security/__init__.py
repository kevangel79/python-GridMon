"""Grid SSL context.
"""

import os
import glob
import tempfile

class _TemporaryFileUnlinker:
    """Based on TemporaryFileWrapper from python 2.3 tempfile implementation.

    This class provides a wrapper around files opened for
    temporary use.  In particular, it seeks to automatically
    remove the file when it is no longer needed.
    """

    def __init__(self, name):
        self.name = name

    # Cache the unlinker so we don't get spurious errors at
    # shutdown when the module-level "os" is None'd out.  Note
    # that this must be referenced as self.unlink, because the
    # name TemporaryFileWrapper may also get None'd out before
    # __del__ is called.
    unlink = os.unlink

    def close(self):
        self.unlink(self.name)

    def __del__(self):
        self.close()

def validator_hostname(cert, hostname):
    cn = filter(lambda x : x[0][0] == u'commonName' ,cert['subject'])[0][0]
    if not cn or cn != (u'commonName', hostname):
        return (False, "CN wrong for host. Connecting to %s but have CN: %s"%(hostname,cn[1]))
    return (True, None)

class GridSSLContext:
    """Hold the various bits and pieces which are the grid specific part of the SSL Context.
    In particular we setup the host&key files, along with creating a single temporary cacerts file
    with the contenets of X509_CERT_DIR/*.0.

    finally, we plug in our own xcustom server cert validator which is used to check the hostname of the
    server cert id equal to the hostname we're trying to connect to."""
    def __init__(self):
        self.key_file = None
        self.cert_file = None
        try:
            self.key_file = os.environ['X509_USER_KEY']
            self.cert_file = os.environ['X509_USER_CERT']
        except KeyError:
            try:
                proxy = os.environ['X509_USER_PROXY']
            except KeyError:
                proxy = '/tmp/x509up_u'+ repr(os.getuid())
            self.key_file = self.cert_file = proxy
        try:
            ca_path = os.environ['SSL_CERT_DIR']
        except KeyError:
            try:
                ca_path = os.environ['X509_CERT_DIR']
            except:
                ca_path = os.sep + os.path.join('etc', 'grid-security', 'certificates')

        ca_path_list = glob.glob(os.path.join(ca_path, '*.0'))
        self.ca_cert_file = _TemporaryFileUnlinker(self._make_cacerts(ca_path_list))

    def get_context(self):
        return {'key_file': self.key_file, 'cert_file': self.cert_file, 'ca_certs': self.ca_cert_file.name,
        'cert_validator': validator_hostname}

    def _make_cacerts(self, cert_list):
        """Create a single file with all CA Certificates inside the files in 'cert_list'.
        This will return the name of a temporary file which can be passed to the SSL library."""
        (tmp_fd, tmp_file) = tempfile.mkstemp(suffix=".cacert")
        for cert in cert_list:
            try:
                content = open(cert).read()
                os.write(tmp_fd, content)
            except Exception, e:
                pass
        os.close(tmp_fd)
        return tmp_file

