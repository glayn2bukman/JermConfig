# JermConfig
write and parse complex config files

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
### parsed data ------
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
    }, 

    'metadata':{}
}
```