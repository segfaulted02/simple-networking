## Running
In order to run the client, in bash terminal type in:

```bash
python3 client.py <address> <port>
```

## Using the client
In order to use the client, format your messages in the following two ways:

To send to a chat room:
```bash
<message> #<channel>

#Example
Hello Musicians! #music
```

To send to an individual user:
```bash
<message> @user

#Example
Hello Chad! @chad
```

In order to disconnect, simply hit Control-C to disconnect from the server.

## Grading Notes

Oddly, although the JSON data correctly sends to the server, messages cannot seem to be received from the chatrooms. I do not know the cause for these issues. However, when sending direct messages, it all works as intended.