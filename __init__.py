import sys
if sys.version_info[0]<3:
    from jcparser import JCParser, test
else:
    from . import jcparser
    JCParser = jcparser.JCParser
    test = jcparser.test