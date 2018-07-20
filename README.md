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
    1. `__nonstrictindent__`
    2. `__quiet__`
    3. `__nonstrictsyntax__`

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
        'age': 21                 # notice that 21 is an integer as age was declared as age:i
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
print(parser.parsed_data)
```

### create parser object then parse config file later
```python
from JermConfig import JCParser
parser = JCParser()
parser.parse("PATH/TO/MY/CONFIG")
print(parser.parsed_data)
```

### write and then parse config file
```python
from JermConfig import JCParser

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
parser.write(data,"/tmp/JermConfig.dummy-conf.jconf", verbose=True)
print("\nparsing {}...".format("/tmp/JermConfig.dummy-conf.jconf"))
parser.parse("/tmp/JermConfig.dummy-conf.jconf")
print(parser.parsed_data)
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
            
        NB:
            * Windows and Mac users should install the library in their respective locations
            * Linux users who dont want the hastle of manual installations should use the deb
              package [here](https://github.com/glayn2bukman/JermConfig/releases/download/0.0.1/JermConfig-0.0.1-1.deb) or check the *releases* for this repo

for more info or questions, please send me an email at **glayn2bukman@gmail.com**