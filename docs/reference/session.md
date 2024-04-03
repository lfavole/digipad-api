The `Session` class is the starting point to use this program.
It can authenticate to a Digipad server and do operations on it.

## Usage example

```python
from digipad.session import Session
session = Session("s:******")
# print information about the current logged-in user
print(session.userinfo)
```

::: digipad.session
