# CSE-467-Project Website List and Categorization

In this section we will show how we convert multiple jsons into a db file

We Use jsonToDB.py and save it to a SQLite known as (`example.db`)

By going into the same directory as both the python file and your jsons, you can run:
```console
$ python jsonToDB.py example.db *.json
```

This will create a db file named (`example.db`) which will contain a database of all the forms, elements, and overall general info of all jsons.