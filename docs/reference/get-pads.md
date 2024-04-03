The `PadsOnAccount` class in this module contains functions to get the pads on an account.

You don't need to import this module, you can use it directly from the `session.pads` property.

```python
from digipad.session import Session
session = Session("s:cNwv10UqJps4************")
for pad in session.pads.all:
    print(pad.title)
```

::: digipad.get_pads
