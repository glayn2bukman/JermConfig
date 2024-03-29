# JermConfig
this sctipt attempts to parse jerm-config files

the script should work fine for both Python2 and Python3. if not, fix the arising issues :)

the general format and rules are as follows:

## RULES
1) supported types are **bool**,**int**,**float** and **string**

        bool is denoted by   :b
        int is denoted by    :i
        float is denoted by  :f
        string is denoted by :s (this is the default type)
        
        NB: - bool can be any of true/false or yes/no (case insensitive)
        
2) supported containers are dictionaries and lists.
        dictionaries are denoted by {} while
        lists are denoted by []
        
        NB: 
            - for lists, you can specify the type of items eg [i] declares a list of integers
            - for dictionaries, the type is implied if the variable is not in a list
            - each item in a list is on a separate line
            - a container can be in another container but if a container is in a list
              then it wont have a name as lists dont support key-value pairs, as such, 
              containers declared in lists may not have names
              
3) magic words can be used to set global variables. these begin and end with __(like `__name__`)
        supported magic words are;
    1. `__nonstrictindent__`
    2. `__quiet__`
    3. `__nonstrictsyntax__`

    NB:
        - provide these special indicators before the actual config starts as they will be
          considered when they are found!

4) the type/container comes after the variable eg;
        age:i    declares age as an int
        height:f declares height as a float
        
        marks[]  declares `marks` as a list
        marks[f] declares `marks` as a list of floats unless an item in the list specifies its type

        data{}   declares data as a dictionary

5) commented lines start with `#`

6) "scope" is determined from indentation(like python)

7) use `$` to refer to environment variables as values eg
        `user = $USER`

8) use `` `var` `` to reference variables eg

        root = /tmp/$USER/prg
        
        # reference root in another path (logdir)
        logdir = `root`/log
        # the line above is equevalent to
        # logdir = /tmp/$USER/prg/log
        
        images = img
        
        # reference more than one variable
        media = `root`/`images`
        # the line above is equevalent to
        # media = /tmp/$USER/prg/img
        
        data{}
                size:i = 1024
                types[]
                        wav
                        mp3

        # reference full variable path
        max-size:i = `data/size`
        # the line above is equevalent to
        # max-size:i = 1024

        default-type = `data/types[1]`
        # the line above is equevalent to
        # default-type = mp3

## EXAMPLE 1
### config data
```
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
```

#### parsed data
```python
{
    'data':{
        'type':'student data', 
        'names':'Dummy Student',
        'age': 21,                # notice that 21 is an integer as age was declared as age:i
        'marks':[78,84,98,63]     # notice that all makrs are ints as marks was declared as marks[i]
    }, 

    'metadata':{}
}
```

## EXAMPLE 2
### config data
```
#data does not have the dict specifier {} as its not in a list

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
```        
### parsed data
```python
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
```

## EXAMPLE 3 (modified version of exmaple 2)
### config data
```
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
```        
### parsed data
```python
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
```

## Show me the code...
### run test(test config files are in test/)
```python
from JermConfig import test
test()
```

### pass config file to __init__
```python
from JermConfig import JCParser
parser = JCParser("PATH/TO/MY/CONFIG")

if parser.warnings:
    # check for warnings
    print parser.warnings

if parser.status:
    # always check if nothing went wrong
    print(parser.parsed_data)
else:
    print parser.errors
```

### create parser object then parse config file later with _verbose_ set to true 
```python
from JermConfig import JCParser
parser = JCParser(verbose=True)
parser.parse("PATH/TO/MY/CONFIG")
print(parser.parsed_data)
```

### write and then parse config file
```python
from JermConfig import JCParser

parser = JCParser(verbose=True)
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

fpath = "/tmp/JermConfig.dummy-conf.jconf"

print("\n\nwritting data to {}...".format(fpath))
parser.write(data,fpath)
print("\nparsing {}...".format(fpath))
parser.parse(fpath)
print(parser.parsed_data)
```

### use the inbuilt auto-update feature of JermConfig
```python
from JermConfig import JCParser

data,_data = {}, {};

# the keyword 'container' represents the data object to be updated whenever the config file changes
# for this to work, 'autoupdate' has to be set to True and a filepath HAS to be given to JCParser
JCParser('/tmp/test.jconf', verbose=False, autoupdate=True, container=data)

while 1:
    if data != _data: # this will be true when the config file is updated/edited and the update is PARSABLE
        _data = data
        print data
```

### pass a container to JCParser without using the auto-update feature
```python
from JermConfig import JCParser
import sys

data= {};

# this will parse the config file and if sucessfull, will store the parsed data in 'container'
if not JCParser('/tmp/test.jconf', container=data).status:
    sys.exit("failed to parse config file")

print "config file data: {}".format(data)

```

## Installation
1. Download this repo
2. Extract the repo(JermConfig) from the zip file
3. Copy and paste the library to your Python's import directories;
        * Python2
            - ~/.local/lib/python2*
            - /usr/local/lib/python2*/dist-packages
        * Python3
            - ~/.local/lib/python3*
            - /usr/local/lib/python3*/dist-packages
            
_NB_:
1. Windows and Mac users should install the library in their respective locations
2. Linux users who dont want the hastle of manual installations should check the [releases](https://github.com/glayn2bukman/JermConfig/releases) for this repo

for more info or questions, please send me an email at **glayn2bukman@gmail.com**
