This module contains the `Pad` class that can be used to edit a pad.

```python
from digipad.session import Session
session = Session("s:******")
for pad in session.pads.created:
    # rename the third column on all created pads
    pad.rename_column(2, "New title")
```

::: digipad.edit
