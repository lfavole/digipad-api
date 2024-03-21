from dataclasses import dataclass, field
from typing import TypeVar, overload

from .edit import Pad, PadList
from .session import Session

NOT_PROVIDED = object()
DefaultT = TypeVar("DefaultT")


@dataclass
class PadsOnAccount:
    """
    A list of all pads in an account.
    """
    session: Session = field(default_factory=Session)
    created: PadList = field(default_factory=PadList)
    visited: PadList = field(default_factory=PadList)
    admin: PadList = field(default_factory=PadList)
    favourite: PadList = field(default_factory=PadList)
    folder_names: dict[str, str] = field(default_factory=dict)
    folders: dict[str, PadList] = field(default_factory=dict)
    pad_hashes: dict[int, str] = field(default_factory=dict)

    @property
    def all(self):
        """
        All the known pads on the account.
        """
        return PadList([
            *self.created,
            *self.visited,
            *self.admin,
            *self.favourite,
        ])

    @overload
    def get(self, pad_id: "int | str", default=NOT_PROVIDED) -> Pad:
        pass

    @overload
    def get(self, pad_id: "int | str", default: DefaultT) -> "Pad | DefaultT":
        pass

    def get(self, pad_id: "int | str", default=NOT_PROVIDED):
        """
        Return ONE pad with its ID, URL, folder name... (see the documentation for `get_all`).
        You can specify a default value.

        If more than one pad is returned, the function raises an error.
        """
        ret = self.get_all([pad_id])
        if len(ret) > 1:
            raise ValueError("Multiple pads returned")
        if not ret:
            if default is not NOT_PROVIDED:
                return default
            raise KeyError(f"Couldn't find pad {pad_id}")
        return ret[0]

    def get_all(self, pad_ids: "list[int] | list[str] | list[int | str]"):
        """
        Return the pad IDs and hashes corresponding to the given IDs.
        You must give the URL (at least its end with the ID and the hash)
        if you haven't ever opened the pad on the account.

        You can use the keywords `created`, `visited`, `admin`, `favourite`, `all` or a folder name.
        """
        ret = []

        for pad_id in pad_ids:
            if pad_id in ("created", "visited", "admin", "favourite", "all"):
                ret.extend(getattr(self, pad_id))
                continue

            try:
                ret.append(self.all.get(pad_id, self.session))
            except ValueError:
                ret.extend(self.get_pads_in_folder(pad_id))

        # deduplicate the list
        ret2 = []
        for pad in ret:
            if pad not in ret2:
                ret2.append(pad)

        return PadList(ret2)

    def get_pads_in_folder(self, folder_name):
        """
        Return the pad IDs and hashes in a folder.
        """
        if folder_name in self.folders:
            # folder ID
            return self.folders[folder_name]

        # folder name
        for folder_id, folder_name_to_try in self.folder_names.items():
            if folder_name_to_try == folder_name:
                return self.folders[folder_id]

        raise ValueError(f"Can't find folder {folder_name}")
