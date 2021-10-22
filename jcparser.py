#!/usr/bin/env python
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
            __nonstrictsyntax__

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
    }
}
##########################################################

"""

__ALL__ = ["JCParser", "test"]
import os, sys
import threading, time # for when we need to monitor the config file for any automatic updates...

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

TAB_SIZE = 4 # spaces

AUTO_UPDATING = {} # 

def _autoupdate_jconfig():
    '''
    daemon that monitors all config files that needs autoupdating and 
    autoupdates em when their last modification time changes...
    
    this function should be run as a separate thread, OBVIOUSLY
    '''
    
    global AUTO_UPDATING
    pobj, obsolete = None, []
    while 1:
        obsolete = []
                
        try: 'x' in AUTO_UPDATING
        except: return # calling thread perhaps is dead

        for fpath in AUTO_UPDATING:
            if not os.path.isfile(fpath):
                obsolete.append(fpath)
                continue
                
            if ('mtime' not in AUTO_UPDATING[fpath]) or (
                os.stat(fpath).st_mtime != AUTO_UPDATING[fpath]['mtime']):
                    
                pobj = JCParser(fpath, verbose=False)
                if pobj.status:
                    AUTO_UPDATING[fpath]['obj'].parsed_data = pobj.parsed_data
                    AUTO_UPDATING[fpath]['obj'].status = pobj.status
                    AUTO_UPDATING[fpath]['obj'].warnings = pobj.warnings
                    AUTO_UPDATING[fpath]['obj'].errors = pobj.errors
                    AUTO_UPDATING[fpath]['mtime'] = os.stat(fpath).st_mtime
                    
                    AUTO_UPDATING[fpath]['obj'].container.clear()
                    for k in pobj.parsed_data:
                        AUTO_UPDATING[fpath]['obj'].container[k] = pobj.parsed_data[k]
                    
        
        for fpath in obsolete:
            print('deleting obsolete autp-update paths: {}'.format(fpath))
            del AUTO_UPDATING[fpath]

        time.sleep(0.1) # time delay for checking if a config file's been updated
    
def fdata(data):
    if sys.version_info[0]==3:
        return bytes(data, "utf-8")
    else: 
        return data

class JCParser:
    # types supported when writing config files
    PyTypes = [type(0),type(0.0),type(()),type([]),type({}),type(""),type(False)]
    
    # types supported when parsing config files
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
    
    def __init__(_, fpath="", verbose=False, autoupdate=False, container=None):
        '''
        autoupdate: if True/1, the config file will be monitore for any updates
                    if the file is updated and the new config data is parsable
                    without errors, the `container` will be updated to hold the
                    new parsed data
        container: an empty dictionary object that will contain the parsed data
                   this can be provided with or without the `autoupdate` flag
        '''
        # flag to show if parsing/writting was ok
        _.status = False
        
        # read this if status=True, error is empty string
        _.parsed_data = {}
        
        # errors encountered when parsing
        _.errors = ""

        # warnings, if any (these can be present even if status is True)
        _.warnings = ""
        
        _.verbose = verbose
        
        _.fpath = fpath
        _.autoupdate = autoupdate
        _.container = container

        if fpath:
            _.parse(fpath)

        _._operations = {
            'data': _.parsed_data,
            'autoupdate': autoupdate,
            'verbose': verbose,
        }

        #container = _.parsed_data
        #_.parsed_data = container

        if (container!=None) and autoupdate and (fpath not in AUTO_UPDATING)\
            and fpath and os.path.isfile(fpath):
                
            AUTO_UPDATING[fpath] = {'obj': _}
            time.sleep(0.1) # give _autoupdate_jconfig to effect changes

    def _reset(_):
        _.status = False
        _.errors = ""
        _.warnings = ""

    def parse(_, fpath):
        "attempt to parse a jerm-config-file"
        
        # initialize default magic-indicators....
        _.__strictindent__ = True # strict-indent = True
        _.__strictsyntax__ = True # strict-syntax = True
        #_.__verbose__     = True # verbose = True, set to False if __quiet__ is found in config file
        _.__verbose__      = _.verbose

        try:
            fin = open(fpath)
        except:
            _.errors = "could not open config file: <{}>".format(fpath)
            if _.verbose:
                _.log("could not open config file: <{}>".format(fpath))
            return

        data = fin.readlines(); fin.close()
        
        fin.close()

        if not data:
            _.errors = "config file is empty"
            if _.verbose:
                _.log("config file is empty")
            return 
        
        # reset old parsed data
        _._reset()
        _.parsed_data = {}

        indents = {-1: _.parsed_data} # indent: object; parent object is the max of the lower indents!
        default_type = "s"

        line_count = 0
        index = 0
        
        indent_unit = 0

        for line in data:
            line_count += 1
            if not(line.strip()and line.strip()[0]!="#"and not _._update_indicator(line.strip())):
                continue
    
            line = line.rstrip()

            indent = _._indent_level(line)
            
            if indent and not indent_unit:
                # first indented line sets indent unit to be used in the rest of the config
                indent_unit = indent

            # check for indentation error...
            if _.__strictindent__ and indent_unit and indent%indent_unit:
                _.errors += "indentation error(line {})\n".format(line_count)
                if _.__verbose__:
                    _.log("indentation error(line {})".format(line_count))
                if _.__strictsyntax__:
                    _.parsed_data = {}
                    return
                else: continue
                                
            _indents = [k for k in indents]; _indents.sort()
            if indent<_indents[-1] and (indent not in _indents):
                _.errors += "indentation error(line {})\n".format(line_count)
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
                    _.errors += "value error, key-value pair in list(line {})\n".format(line_count)
                    if _.__verbose__:
                        _.log("value error, key-value pair in list(line {})".format(line_count))
                    if _.__strictsyntax__:
                        _.parsed_data = {}
                        return
                    else: continue

                key,value = line[:line.index("=")].strip(), line[line.index("=")+1:].strip()
                
                # environment variables -------------------------------
                _env_vars = []
                _copy_vars = [] # variables that are references of others already parsed
                prev_pos, prev_copy_pos = 0, 0
                _scanning, _copy_scanning = 0, 0
                value += ' ' # prevent a rare bug where $ENVVAR was the last on the line
                for _pos, c in enumerate(value):
                    if '$'==c:
                        if _pos and (value[_pos-1] in ['\\']):
                            _scanning = 0
                            continue
                            
                        _scanning = 1
                        prev_pos  = _pos
                        continue

                    if _scanning and (c.lower() not in 'abcdefghijklmnopqrstuvwxyz_0123456789'):
                        _env_vars.append(value[prev_pos+1:_pos])
                        _scanning = 0

                    if '`'==c:
                        if _pos and (value[_pos-1] in ['\\']):
                            #if _copy_scanning = 0
                            continue
                            
                        if not _copy_scanning:
                            _copy_scanning = 1
                            prev_copy_pos  = _pos
                            continue

                        _copy_vars.append(value[prev_copy_pos+1:_pos])
                        _copy_scanning = 0

                for _env_var in _env_vars:
                    _ev = os.getenv(_env_var)
                    if not _ev: continue
                    value = value.replace('$'+_env_var, _ev)

                for _cv in _copy_vars:
                    if not _cv: continue
                    _parts = [i.strip() for i in _cv.split('/')] # we can have paths
                    _pd = _.parsed_data
                    for _pi,_part in enumerate(_parts):
                        _cpy = None
                        try:
                            if '[' in _part:
                                exec("_cpy = _pd.get(\"{}\",None)".format(_part[:_part.index('[')]));
                                if type(_cpy)!=type([]):
                                    _.warnings += "reference error, indexing non-list reference `{}` (line {})\n".format(_cv,line_count)
                                    if _.__verbose__:
                                        _.log("reference error, indexing non-list reference `{}` (line {})\n".format(_cv,line_count))
                                    break
                                try:
                                    exec("_cpy = _cpy{}".format(_part[_part.index('['):]))
                                except:
                                    _.warnings += "reference error, index out of range for list reference `{}` (line {})\n".format(_cv,line_count)
                                    if _.__verbose__:
                                        _.log("reference error, index out of range for list reference `{}` (line {})\n".format(_cv,line_count))
                                    break
                                    
                            else: exec("_cpy = _pd.get(\"{}\",None)".format(_part));
                        except:
                            _.warnings += "reference error, could not find reference `{}` (line {})\n".format(_cv,line_count)
                            if _.__verbose__:
                                _.log("reference error, could not find reference `{}` (line {})\n".format(_cv,line_count))
                            break

                        if None!=_cpy:
                            if type(_cpy) not in [type(""),type(0),type(0.0)]:
                                # _cpy is an object, not just a constant
                                if _pi==(len(_parts)-1):
                                    if ("`"+_cv+"`").strip()==value.strip():
                                        value = _cpy
                                    else:
                                        value = value.replace('`'+_cv+'`', str(_cpy))
                                else:
                                    _pd = _cpy
                            else:
                                value = value.replace('`'+_cv+'`', str(_cpy))

                value = value[:-1]
                # -----------------------------------------------------
                                        

                if ("{" in key)or("}" in key)or("[" in key)or("]" in key):
                    _.errors += "syntax error, key contains container characters(line {})\n".format(line_count)
                    if _.__verbose__:
                        _.log("syntax error, key contains container characters(line {})".format(line_count))
                    if _.__strictsyntax__:
                        _.parsed_data = {}
                        return
                    else: continue

                if ":" in key:
                    if len(key)<3 or key[-2]!=":":
                        _.errors += "key error(line {}); key is malformed! expected it to be in format key:TYPE eg age:i or pi:f\n".format(line_count)
                        if _.__verbose__:
                            _.log("key error(line {}); key is malformed! expected it to be in format key:TYPE eg age:i or pi:f".format(line_count))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                    
                    key,t = key[:-2].strip(), key[-1]
                    
                    if t not in JCParser.types:
                        _.errors += "type error(line {}); key has unknown type <{}>. supported types are {}\n".format(line_count, t, JCParser.basic_types)
                        if _.__verbose__:
                            _.log("type error(line {}); key has unknown type <{}>. supported types are {}".format(line_count, t, JCParser.basic_types))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                    
                    try:
                        value = JCParser.types[t](value)
                    except:
                        _.errors += "type error(line {}); key defined value as of type <{}> but value can't be parsed to this type\n".format(line_count, t)
                        if _.__verbose__:
                            _.log("type error(line {}); key defined value as of type <{}> but value can't be parsed to this type".format(line_count, t))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue

                parent[key] = value

            else:
                obj = None

                # environment variables -------------------------------
                _env_vars = []
                _copy_vars = [] # variables that are references of others already parsed
                prev_pos, prev_copy_pos = 0, 0
                _scanning, _copy_scanning = 0, 0
                line += ' ' # prevent a rare bug where $ENVVAR was the last on the line
                for _pos, c in enumerate(line):
                    if '$'==c:
                        if _pos and (line[_pos-1] in ['\\']):
                            _scanning = 0
                            continue
                            
                        _scanning = 1
                        prev_pos  = _pos
                        continue

                    if _scanning and (c.lower() not in 'abcdefghijklmnopqrstuvwxyz_0123456789'):
                        _env_vars.append(line[prev_pos+1:_pos])
                        _scanning = 0

                    if '`'==c:
                        if _pos and (line[_pos-1] in ['\\']):
                            #if _copy_scanning = 0
                            continue
                            
                        if not _copy_scanning:
                            _copy_scanning = 1
                            prev_copy_pos  = _pos
                            continue

                        _copy_vars.append(line[prev_copy_pos+1:_pos])
                        _copy_scanning = 0

                for _env_var in _env_vars:
                    _ev = os.getenv(_env_var)
                    if not _ev: continue
                    line = line.replace('$'+_env_var, _ev)

                for _cv in _copy_vars:
                    if not _cv: continue
                    _parts = [i.strip() for i in _cv.split('/')] # we can have paths
                    _pd = _.parsed_data
                    for _pi,_part in enumerate(_parts):
                        _cpy = None
                        try:
                            if '[' in _part:
                                exec("_cpy = _pd.get(\"{}\",None)".format(_part[:_part.index('[')]));
                                if type(_cpy)!=type([]):
                                    _.warnings += "reference error, indexing non-list reference `{}` (line {})\n".format(_cv,line_count)
                                    if _.__verbose__:
                                        _.log("reference error, indexing non-list reference `{}` (line {})\n".format(_cv,line_count))
                                    break
                                try:
                                    exec("_cpy = _cpy{}".format(_part[_part.index('['):]))
                                except:
                                    _.warnings += "reference error, index out of range for list reference `{}` (line {})\n".format(_cv,line_count)
                                    if _.__verbose__:
                                        _.log("reference error, index out of range for list reference `{}` (line {})\n".format(_cv,line_count))
                                    break
                                    
                            else: exec("_cpy = _pd.get(\"{}\",None)".format(_part));
                        except:
                            _.warnings += "reference error, could not find reference `{}` (line {})\n".format(_cv,line_count)
                            if _.__verbose__:
                                _.log("reference error, could not find reference `{}` (line {})\n".format(_cv,line_count))
                            break

                        if None!=_cpy:
                            if type(_cpy) not in [type(""),type(0),type(0.0)]:
                                # _cpy is an object, not just a constant
                                if _pi==(len(_parts)-1):
                                    if ("`"+_cv+"`").strip()==line.strip():
                                        line = _cpy
                                    else:
                                        line = line.replace('`'+_cv+'`', str(_cpy))
                                else:
                                    _pd = _cpy
                            else:
                                line = line.replace('`'+_cv+'`', str(_cpy))

                line = line[:-1]
                # -----------------------------------------------------

                if ("{" in line)or("}" in line):
                    if (not line.endswith("{}"))or (line.count("{")!=1 or line.count("}")!=1):
                        _.errors += "syntax error(line {}); dict containers are defined in format var{}\n".format(line_count,'{}')
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
                        
                        if line:
                            _.warnings += "warning (line {}); dict name <{}> will be abandoned since parent is a list\n".format(line_count, line)
                            if _.__verbose__:
                                _.log("warning (line {}); dict name <{}> will be abandoned since parent is a list".format(line_count, line))
                    else:
                        if not line:
                            _.errors += "name error(line {}); this dict must have a name as its a direct child of another dict\n".format(line_count)
                            if _.__verbose__:
                                _.log("name error(line {}); this dict must have a name as its a direct child of another dict".format(line_count))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue

                        parent[line] = {}
                        obj = parent[line]

                    indents[indent] = obj
                    
                elif ("[" in line)or("]" in line):
                    if line.count("[")!=1 or line.count("]")!=1 or line.index('[')>line.index('['):
                        _.errors += "syntax error(line {}); list containers are defined in format var[TYPE]\n".format(line_count)
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
                        _.errors += "type error(line {}); list container sets default unknown type <{}>. supported types are {}\n".format(line_count, t, JCParser.basic_types)
                        if _.__verbose__:
                            _.log("type error(line {}); list container sets default unknown type <{}>. supported types are {}".format(line_count, t, JCParser.basic_types))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                            
                    if not list_type_known:
                        _.errors += "syntax error(line {}); list containers are defined in format var[TYPE]\n".format(line_count)
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
                        
                        if line:
                            _.warnings += "warning (line {}); list name <{}> will be abandoned since parent is a list\n".format(line_count, line)
                            if _.__verbose__:
                                _.log("warning (line {}); list name <{}> will be abandoned since parent is a list".format(line_count, line))
                    else:
                        if not line:
                            _.errors += "name error(line {}); this list must have a name as its a direct child of another dict\n".format(line_count)
                            if _.__verbose__:
                                _.log("name error(line {}); this list must have a name as its a direct child of another dict".format(line_count))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue

                        parent[line] = []
                        obj = parent[line]

                    indents[indent] = obj
                    
                elif ":" in line:
                    if isinstance(parent, dict):
                        _.errors += "syntax error(line {}); dict container cannot have a type\n".format(line_count)
                        if _.__verbose__:
                            _.log("syntax error(line {}); dict container cannot have a type".format(line_count))
                        if _.__strictsyntax__:
                            _.parsed_data = {}
                            return
                        else: continue
                    else:
                        # this is a list item
                        if line.count(":")!=1 or len(line)<3 or line[-2]!=":":
                            _.errors += "syntax error(line {}); section is malformed! expected it to be in format section:TYPE eg age:i or pi:f\n".format(line_count)
                            if _.__verbose__:
                                _.log("syntax error(line {}); section is malformed! expected it to be in format section:TYPE eg age:i or pi:f".format(line_count))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue
                        
                        line,t = line[:-2].strip(), line[-1]
                        
                        if t not in JCParser.basic_types:
                            _.errors += "type error(line {}); section has unknown type <{}>. supported types are {}\n".format(line_count, t, JCParser.basic_types)
                            if _.__verbose__:
                                _.log("type error(line {}); section has unknown type <{}>. supported types are {}".format(line_count, t, JCParser.basic_types))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue
                        
                        try:
                            line = JCParser.types[t](line)
                        except:
                            _.errors += "type error(line {}); section declared with type <{}> but can't be parsed to this type\n".format(line_count, t)
                            if _.__verbose__:
                                _.log("type error(line {}); section declared with type <{}> but can't be parsed to this type".format(line_count, t))
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
                            _.errors += "value error(line {}); failed to parse <{}> to list default type <{}>\n".format(line_count, line, t)
                            if _.__verbose__:
                                _.log("value error(line {}); failed to parse <{}> to list default type <{}>".format(line_count, line, t))
                            if _.__strictsyntax__:
                                _.parsed_data = {}
                                return
                            else: continue

                        parent.append(line)

                    else:
                        parent[line] = {}
                        obj = parent[line]
                        indents[indent] = obj

        if _.container!=None:
            _.container.clear()
            for k in _.parsed_data:
                _.container[k] = _.parsed_data[k]
        _.status = True
                            
    def write(_, data, fout_path, tabsize=TAB_SIZE):
        "attempt to dump dictionary data to a jerm-config-file"
        
        _._reset()
        
        if not isinstance(data, dict):
            _.warnings += "warning, only dictionaries can be dumped to config files!\n"
            if _.verbose:
                _.log("warning, only dictionaries can be dumped to config files!")
            return
        
        try:
            fout = open(fout_path, "wb")
        except:
            _.warnings += "could not create config file: <{}>\n".format(fout_path)
            if _.verbose:
                _.log("could not create config file: <{}>".format(fout_path))
            return

        fout.write(fdata(HELP))
        
        if data:
            _._write(data, fout, tabsize, 0)
            
        fout.close()

        _.status = True
        
    def log(_,msg):
        if "error" in msg and not _.__strictsyntax__:
            msg += "(line treated as comment since __nonstrictsyntax__ was set)"

        if "win" in sys.platform.lower():
            print ("[JERM-PARSER] {}".format(msg))
        else:
            if "error" in msg:
                print ("\033[1;31m[JERM-PARSER]\033[0m {}".format(msg))
            else:
                print ("\033[1;33m[JERM-PARSER]\033[0m {}".format(msg))

    def template(_, fpath):
        try:
            with open(fpath, "wb") as fout: fout.write(fdata(HELP))
        except:
            _.log("could not create config file: <{}>".format(fpath))
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
        if (not line) or (line[0] not in [' ','\t']): return 0
        
        i, count = 0, 0
        while i<len(line):
            if (line[i] not in [' ','\t']): break
            count += 1
            i += 1
        
        return count

    def _write(_, data, fout, tabsize, indent):
        for k in data:
            if not isinstance(k, str):
                _.warnings += "warning, <{}> left out as its a key but NOT a string\n".format(k)
                if _.verbose:
                    _.log("warning, <{}> left out as its a key but NOT a string".format(k))
                continue
            
            if type(data[k])not in JCParser.PyTypes:
                _.warnings += "warning, <{}> left out as its not of supported types\n".format(data[k])
                if _.verbose:
                    _.log("warning, <{}> left out as its not of supported types".format(data[k]))
                continue
            
            # basic types...
            if isinstance(data[k], str):
                line =  "{}{} = {}".format(" "*indent+""*tabsize, k, data[k])
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
            elif str(data[k]) in ["True", "False"]:
                # this comes before checking is data[k] is int as bools are ints!
                line =  "{}{}:b = {}".format(" "*indent+""*tabsize, k, data[k])
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
            elif isinstance(data[k], int):
                line =  "{}{}:i = {}".format(" "*indent+""*tabsize, k, data[k])
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
            elif isinstance(data[k], float):
                line =  "{}{}:f = {}".format(" "*indent+""*tabsize, k, data[k])
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
                    
            # dict type...
            elif isinstance(data[k], dict):
                line =  " "*indent + k
                fout.write(fdata("\n\n"+line))
                line =  "{}{}".format(" "*indent+" "*tabsize, "# dict data is indented here...")
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
                _._write(data[k],fout,tabsize, indent+tabsize)

            # list/tuple type...
            elif isinstance(data[k], list) or isinstance(data[k], tuple):
                line =  "{}{}[]".format(" "*indent+""*tabsize, k)
                fout.write(fdata("\n\n"+line))
                if _.verbose:
                    print(line)
                _._write_list(data[k],fout,tabsize, indent+tabsize)

    def _write_list(_, data, fout, tabsize, indent):
        if type(data) not in [type([]), type(())]:
            _.log("warning, _write_list ONLY writes lists/tuples. <{}> is not!".format(data))
            return

        line =  "{}{}".format(" "*indent+""*tabsize, "# list data is indented here...")
        fout.write(fdata("\n"+line))
        
        for entry in data:
            if type(entry)not in JCParser.PyTypes:
                _.log("warning, <{}> left out as its not of supported types".format(entry))
                continue

            if isinstance(entry, str):
                line =  "{}{}".format(" "*indent+""*tabsize, entry)
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
            elif str(entry) in ["True", "False"]:
                # this comes before checking is data[k] is int as bools are ints!
                line =  "{}{}:b".format(" "*indent+""*tabsize, entry)
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
            elif isinstance(entry, int):
                line =  "{}{}:i".format(" "*indent+""*tabsize, entry)
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
            elif isinstance(entry, float):
                line =  "{}{}:f".format(" "*indent+""*tabsize, entry)
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
                    
            # dict type...
            elif isinstance(entry, dict):
                line =  "{}{}".format(" "*indent+""*tabsize, "{}")
                fout.write(fdata("\n\n"+line))
                line =  "{}{}".format(" "*indent+" "*tabsize, "# dict data is indented here...")
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
                _._write(entry,fout,tabsize, indent+tabsize)

            # list/tuple type...
            elif isinstance(entry, list) or isinstance(entry, tuple):
                line =  "{}[]".format(" "*indent+""*tabsize)
                fout.write(fdata("\n\n"+line))
                line =  "{}{}".format(" "*indent+" "*tabsize, "# list data is indented here...")
                fout.write(fdata("\n"+line))
                if _.verbose:
                    print(line)
                _._write_list(entry,fout,tabsize, indent+tabsize)

    
def test():
    path = os.path.realpath(__file__)
    path = os.path.split(path)[0]
    
    parser = JCParser()

    test_configs = os.listdir(os.path.join(path,"test"))
    for test_config in test_configs:
        print("\nparsing {}...".format(os.path.join(path,"test",test_config)))
        parser.parse(os.path.join(path,"test",test_config))

        if parser.warnings:
            print (parser.warnings)
        if not parser.status:
            print (parser.errors)

        #print ("output:\n{}".format(parser.parsed_data))


_jconf_auto_update_daemon = threading.Thread(target=_autoupdate_jconfig, args=())
_jconf_auto_update_daemon.daemon = True
_jconf_auto_update_daemon.start()
        
if __name__ == "__main__":
    import sys
    if len(sys.argv)>1:
        parser = JCParser(sys.argv[1])
        print ("[warnings]")
        print (parser.warnings)

        print ("[errors]")
        print (parser.errors)

        print ("[data]")
        print (parser.parsed_data)

    else:
        test()
        
        # now dumping config file and then parsing it afterwards...
        parser = JCParser()
        data = {
            2: 'hello', # should be skipped as key is not a string

            'N.O.S': 2,
            'login-handler': lambda x:x, # should be skipped as functions aint supported
            
            'graduates': True,
            
            'students':{            
                'bukman':{
                    'grades':[89,72,['other',56,12.08,{'inner':{'deeper':[1,2,3]}}],64,94],
                    'average': 79.75,
                    'units': ('CS101', 'CS103', 'CS107', 'CS202'),
                    'credentials':{
                        'username': 'bukman?',
                        'passcode': '1603'
                    }
                },

                'glayn':{
                    'grades':[80,32,69,72, {'name':'data', 'results':[15,98,False,63.0]}],
                    'average': 63.25,
                    'units': ('CS101', 'CS103', 'CS107', 'CS202'),
                    'credentials':{
                        'username': 'glayn!!',
                        'passcode': '0628'
                    }
                }
            },
            
            'tutors':['arthur','sofia','jimmy']
        }
        
        print("\n\nwritting data to {}...".format("/tmp/JermConfig.dummy-conf.jconf"))
        parser.write(data,"/tmp/JermConfig.dummy-conf.jconf")
        if parser.warnings:
            print (parser.warnings)
        if not parser.status:
            print (parser.errors)

        print("\nparsing {}...".format("/tmp/JermConfig.dummy-conf.jconf"))
        parser.parse("/tmp/JermConfig.dummy-conf.jconf")
        if parser.warnings:
            print (parser.warnings)
        if not parser.status:
            print (parser.errors)

        print(parser.parsed_data)

        xsettings = {}
        print('...')
        print(JCParser("/tmp/JermConfig.dummy-conf.jconf",container=xsettings).status)
        print('...')   
        print(xsettings)
