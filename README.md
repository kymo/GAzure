g_azure
=======

a platform for gpu computing(based on bottle and mongodb)


Attentions:
--------------------------------------------------------
1 start application server first : python com_server.py
 
2 start web application : python g_azure.py
 
3 attention: all the commands are just used for debugging.
 
Statement:
------------------------------------------------------------

### Anyone can change these codes and apply them in your own project.

Introduction:
------------------------------------------------------------
### com_server.py 

  defined the lightweighted server engine to compile c/c++/cuda files and run them.
  and save the compile information or the running information into collection(table) in mongo

### g_azure.py
  the main framework of the project. It contains more reasonable url mapping method.
 
 in it, you can find the process of build a index database, and the process of search a key word 
  
  in a file collection.
   also, you can find the method to use monkey(a plugin written for projects with mongo).
   and of cousrse, how to comunicate with a application server will be found in it too.

### func.py
contain a thread class for sending email and change search content to html file(for emphasize)

### monkey.py
plugin for mongo,the document of it will be find https://github.com/kymo/monkey

### mon_config.py 
by name we can know it is the definition of you database
  
  no sql doesn't means no structural unity.

### test_*.py ignore it


have fun:)
