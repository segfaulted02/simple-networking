## Running
In order to run the server, in bash terminal type in:

```bash
python3 server.py <address> <port>

#Example
python3 server.py 127.0.0.1 5555
```

## Using the server
In order to use the server, it will automatically run and requires no user actions.
You must use a working client with the server.

In order to stop the server, just hit Ctrl-C to stop the server

## Grading Notes - IMPORTANT

~~Note that if you choose to grade this server against my client, there is a mismatch where the client, when testing on the compnet.cs.du.edu server, needed to a certain transliteration of received data from the server, noted on Line 62 and the command below.
```bash
new_msg = ast.literal_eval(msg)
```
In order to have my server code and client code work together, this string was not needed as my server handles and sends messages correctly. Replace this line with the command below, and all will work perfectly.
```bash
new_msg = msg
```
~~
Due to bug in server code, it fixed my issue. I submitted an updated client code (changed 1 functional line), however these grading notes are now no longer relevant, as my client and server code work together well.