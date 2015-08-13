'''
Created on Mar 21, 2010

@author: Konstantin Skaburskas
'''
import os
import re
import sys
import unittest

sys.path.insert(1, re.sub('/\w*$','',os.getcwd()))

from gridmon.template import TemplatedFile

class TestTemplate(unittest.TestCase):

    def testCheckPatterns(self):
        'Check patterns.'
        for p in [{'foo' : ''}, {'foo' : None}]:
            try:
                TemplatedFile('a', 'b', p)
            except TypeError:
                pass
            except Exception, e:
                self.fail('TypeError exception expected. Given: %s' % \
                          type(e).__name__)
            else:
                self.fail('TypeError exception expected.')
        try:
            TemplatedFile('a', 'b', {'foo' : 'bar'})
        except Exception, e:
            self.fail('Failed with exception: %s' % type(e).__name__)
        else:
            pass

    def testLoadSubst(self):
        'Load and substitute.'
        templ_file = 'file.template'
        templ = 'foo = <bar>;\nbar = <foo>;'
        patterns = {'bar' : 'foo', 'foo' : 'bar'}
        subst = 'foo = foo;\nbar = bar;'
        
        fp = open(templ_file, 'w')
        fp.write(templ)
        fp.close()
        
        tf = TemplatedFile(templ_file, '', patterns)
        tf.load()
        tf.subst()
        self.assertEqual(subst, tf.substitution)
        
        os.unlink(templ_file)

if __name__ == "__main__":
    testcases = [TestTemplate]
    for tc in testcases:
        unittest.TextTestRunner(verbosity=2).\
            run(unittest.TestLoader().loadTestsFromTestCase(tc))
