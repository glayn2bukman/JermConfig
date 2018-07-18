# this module parses and writes Jerm-Config files
# author: Glayn Bukman <glayn@bukman@gmail.com>
#
# should work fine for both Python2 and Python3. if not, fix the arising issues :)
# about
"""
this sctipt attempts to parse jerm-config files.
the general format and rules are as follows:

1) supported types are bool,int,float and string
        bool is denoted by   :b
        int is denoted by    :i
        float is denoted by  :f
        string is denoted by :s (this is the default type)
        
        NB: - bool can be any of true/false or yes/no (case insensitive)
        
2) supported containers are dictionaries and lists
        dictionaries are denoted by {}
        dictionaries are denoted by []
        
        NB: 
            - for lists, you can specify the type of items eg [i] declares a list of integers
            - for dictionaries, the type is implied if the variable is not in a list
            - each item in a list is on a separate line
            - a container can be in another container but lists if a container is in a list
              then it wont have a name as lists dont support key-value pairs, as such, 
              containers declared in lists may not have names
              
3) magic words can be used to set global variables. these begin and end with __(like __name__)
        supported magic words are;
            __nonstrictindent__
            __quiet__

        NB:
            - provide these special indicators before the actual config starts as they will be
              considered when they are found!

4) the type/container comes after the variable eg;
        age:i    declares age as an int
        height:f declares height as a float
        
        marks[]  declares marks as a list
        marks[f] declares marks as a list of floats unless an item specifies its type

        data{}   declares data as a dictionary

5) commented lines start with #

6) "scope" is determined from indentation(like python)

7) use $ to refer to environment variables as values eg
        user = $USER

##########################################################
EXAMPLE 1
------ config data ------
data{}
    type  = student data
    names = Dummy Student
    age:i  = 21
    marks[i]
        78
        84
        98
        63
        
metadata{}        

------ parsed data ------
{
    'data':{
        'type':'student data', 
        'names':'Dummy Student',
        'age': 21                 # notice that 21 is an integer as age was declared as age:i
        'marks':[78,84,98,63]     # notice that all makrs are ints as marks was declared as marks[i]
    }, 

    'metadata':{}
}
##########################################################

##########################################################
EXAMPLE 2
------ config data ------
# data does not have the dict specifier {} as its not in a list
data
    type = student data
    marks[]
        78:i
        84:f
        98
        63:i
        
        other[]
            my data{}
                key = value
        
            hello
        
        hi
    
    # inner dict also does not need the dict specifier {} as its not in a list
    innerdict
        name = inner dict
        
------ parsed data ------
{
    'data':{
        'type':'student data', 
        'marks':[
            78,84.0,'98',63, # notice that 84 is a float and 98 is a string
            
            [                # notice that the variable name (other) is dumped 
                             # as the parent container is a list(marks)
                
                {            # notice that the variable name (other) is dumped 
                             # as the parent container is a list(unamed as it also lost its name
                             # since its parent was also a list)
                    'key':'value'
                },
                
                'hello'
            
            ],
            
            'hi'
        ],
        
        'innerdict':{'name':'inner dict'}
    }, 

    'metadata':{}
}
##########################################################

##########################################################
EXAMPLE 3 (modified version of exmaple 2)
------ config data ------
data
    type = student data

    marks[i]
        78
        84:f
        98:s
        63
        
        []
            {}
                key = value
            hello

        hi    

    innerdict
        name = inner dict
        
------ parsed data ------
{
    'data':{
        'type':'student data', 
        'marks':[
            78,84.0,'98',63,
            
            [{'key':'value'}, 'hello'],
            
            'hi'
        ],
        
        'innerdict':{'name':'inner dict'}
    }, 

    'metadata':{}
}
##########################################################

"""

import os

HELP = """# this is a comment
# this config file uses indentation(spaces NOT tabs) to determine levels
# it supports containers (dictionaries and lists), integers, floats, bool and strings(default type)
# the config also supports special/magic indicators that start and end with two `_`s (eg __mm__)
# 
# NB: to assign environment variables as values, use $ eg 
#     user = $USER


# SPECIAL/MAGIC INDICATORS...
# dont be strict with syntax(not advisable), if not provided, syntax is strict ie anything that
# would raise an error in python also raises an error here
#__nonstrictsyntax__

# operate in verbose mode? provide this if you are in production mode...
#__quiet__

"""

class JCParser:
    types = {
        "i":int,"f":float,"s":str,
        'b':(lambda b:(
            True if b.lower()in['true','yes']else(False if b.lower()in['false','no']else thisshouldraiseanerror))),
        '[b]':(lambda b:(True if b.lower()in['true','yes']else(False if b.lower()in['false','no']else thisshouldraiseanerror))),
        '[]':str,'[i]':int,'[f]':float,'[s]':str,
        '{}':lambda x:x[:-2] # return variable name without the {}
    }

    basic_types = sorted([k for k in types.keys() if len(k)==1])
    list_types = sorted([k for k in types.keys() if ("["in k)])
    
    def __init__(_, fpath=""):
        _.parsed_data = {}
        
        if fpath:
            _.parse(fpath)

    def parse(_, fpath):
        "attempt to parse a jerm-config-file"
        
        # initialize default magic-indicators....
        _.__strictindent__ = True # strict-indent = True
        _.__strictsyntax__ = True # strict-syntax = True
        _.__verbose__      = True # verbose = True, set to False if __quiet__ is found in config file

        try:
            fin = open(fpath)
        except:
            _.log("could not open config file: <{}>".format(fpath))
            return

        data = fin.readlines(); fin.close()
        
        fin.close()

        if not data:
            _.log("config file is empty")
            return 
        
        # reset old parsed data
        _.parsed_data = {}

        indents = {-1: _.parsed_data} # indent: object; parent object is the max of the lower indents!
        default_type = "s"

        line_count = 0
        index = 0

        for line in data:
            line_count += 1
            if not(line.strip()and line.strip()[0]!="#"and not _._update_indicator(line.strip())):
                continue
    
            line = line.rstrip()

            indent = _._indent_level(line)

            # check for indentation error...
            #_indents = indents.keys(); _indents.sort()
            _indents = [k for k in indents]; _indents.sort()
            if indent<_indents[-1] and (indent not in _indents):
                if _.__verbose__:
                    _.log("indentation error(line {})".format(line_count))
                if _.__strictsyntax__:
                    _.parsed_data = {}
                    return
                else: continue
            
            parent = indents[[i for i in _indents if i<indent][-1]]

            line = line.strip()

            if "=" in line:
                if isinstance(parent, list):
                    if _.__verbose__:
                        _.log("syntax error, key-value pair in list(line {})".format(line_count))
                    if _.__strictsyntax__:
                        _.parsed_data = {}
                        return
                    else: continue

                key,value = line[:line.index("=")].strip(), line[line.index("=")+1:].strip()
                
                value = os.getenv(value[1:]) if value.startswith("$") else value

                if ("{" in key)or("}" in key)or("[" in key)or("]" in key):
                    if _.__verbose__:
                        _.log("syntax error, key contains container characters(line {})".format(line_count))
                    if _.__strictsyntax__:
                        _.parsed_data = {}
                        return
                    else: continue

                if ":" in key:
                    if len(key)<3 or key[-2]!=":":
                        if _.__verbose__:
                            _.log("syntax error(line {}); key is malformed! expected it to be in format key:TYPE eg age:i or pi:f".format(line_count))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                    
                    key,t = key[:-2].strip(), key[-1]
                    
                    if t not in JCParser.types:
                        if _.__verbose__:
                            _.log("type error(line {}); key has unknown type <{}>. supported types are {}".format(line_count, t, JCParser.basic_types))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                    
                    try:
                        value = JCParser.types[t](value)
                    except:
                        if _.__verbose__:
                            _.log("value error(line {}); key idefined value as of type <{}> but value can't be parsed to this type".format(line_count, t))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue

                parent[key] = value

            else:
                obj = None
                if ("{" in line)or("}" in line):
                    if (not line.endswith("{}"))or (line.count("{")!=1 or line.count("}")!=1):
                        if _.__verbose__:
                            _.log("syntax error(line {}); dict containers are defined in format var{}".format(line_count,'{}'))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue

                    line = JCParser.types["{}"](line)

                    if isinstance(parent, list):
                        parent.append({})
                        obj = parent[-1]
                    else:
                        if not line:
                            if _.__verbose__:
                                _.log("syntax error(line {}); dict container must have a name if embeded in another dict container".format(line_count))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue

                        parent[line] = {}
                        obj = parent[line]

                    indents[indent] = obj
                    
                elif ("[" in line)or("]" in line):
                    if line.count("[")!=1 or line.count("]")!=1 or line.index('[')>line.index('['):
                        if _.__verbose__:
                            _.log("syntax error(line {}); list containers are defined in format var[TYPE]".format(line_count))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                                       
                    list_type_known = False
                    for lt in JCParser.list_types:
                        if line.endswith(lt):                 
                            list_type_known = True
                            break
                    
                    t = line[line.index("[")+1:line.index("]")]
                    t = t if t else "s"
                    if t not in JCParser.basic_types:
                        if _.__verbose__:
                            _.log("syntax error(line {}); list container sets default unknown type <{}>. supported types are {}".format(line_count, t, JCParser.basic_types))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                            
                    if not list_type_known:
                        if _.__verbose__:
                            _.log("syntax error(line {}); list containers are defined in format var[TYPE]".format(line_count))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                    
                    default_type = t

                    line = line[:line.index("[")].strip()

                    if isinstance(parent, list):
                        parent.append([])
                        obj = parent[-1]
                    else:
                        if not line:
                            if _.__verbose__:
                                _.log("syntax error(line {}); list container must have a name if embeded in a dict container".format(line_count))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue

                        parent[line] = []
                        obj = parent[line]

                    indents[indent] = obj
                    
                elif ":" in line:
                    if isinstance(parent, dict):
                        if _.__verbose__:
                            _.log("syntax error(line {}); dict container cannot have a type".format(line_count))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                    else:
                        # this is a list item
                        if line.count(":")!=1 or len(line)<3 or line[-2]!=":":
                            if _.__verbose__:
                                _.log("syntax error(line {}); section is malformed! expected it to be in format section:TYPE eg age:i or pi:f".format(line_count))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue
                        
                        line,t = line[:-2].strip(), line[-1]
                        
                        if t not in JCParser.basic_types:
                            if _.__verbose__:
                                _.log("type error(line {}); section has unknown type <{}>. supported types are {}".format(line_count, t, JCParser.basic_types))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue
                        
                        try:
                            line = JCParser.types[t](line)
                        except:
                            if _.__verbose__:
                                _.log("value error(line {}); section declared with type <{}> but can't be parsed to this type".format(line_count, t))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue
                        
                        parent.append(line)
                        
                else:
                    if isinstance(parent, list):
                        try:
                            line = JCParser.types[default_type](line)
                        except:
                            if _.__verbose__:
                                _.log("value error(line {}); failed to parse this to list type <{}>".format(line_count, t))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue

                        parent.append(line)

                    else:
                        parent[line] = {}
                        obj = parent[line]
                        indents[indent] = obj
                            
    def write(_, data, fout_path):
        "attempt to dump dictionary data to a jerm-config-file"

    def log(_,msg):
        print ("[JERM-PARSER] {}".format(msg))

    def template(_, fpath):
        try:
            with open(fpath, "wb") as fout: fout.write(HELP)
        except:
            _.log("could not open config file: <{}>".format(fpath))
            return

    def _update_indicator(_, line):
        if line=="__nonstrictindent__": 
            _.__strictindent__ = False
            return True
        elif line=="__nonstrictsyntax__": 
            _.__strictsyntax__ = False
            return True
        elif line=="__quiet__": 
            _.__verbose__ = False
            return True
        
        return False

    def _indent_level(_,line):
        if (not line) or line[0]!=' ': return 0
        
        i, count = 0, 0
        while i<len(line):
            if line[i]!=' ': break
            count += 1
            i += 1
        
        return count
    
        
if __name__ == "__main__":

    path = os.path.realpath(__file__)
    path = os.path.split(path)[0]
    
    parser = JCParser()

    test_configs = os.listdir(os.path.join(path,"test"))
    for test_config in test_configs:
        print("\nparsing {}...".format(os.path.join(path,"test",test_config)))
        parser.parse(os.path.join(path,"test",test_config))
        print ("output:\n{}".format(parser.parsed_data))
