from digipad.app import app  # pylint: disable=W0611  # noqa
from digipad.utils import get_secret_key

app.secret_key = get_secret_key()
