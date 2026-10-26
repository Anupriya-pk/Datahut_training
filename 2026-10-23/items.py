import json
from settings import FILE_URL, FILE_URL_FAILED, FILE_DATA


class BaseItem:
    """Replaces the MongoDB DynamicDocument: any field is accepted,
    save() appends the item as one JSON line to the collection file."""

    file = None
    required = ()

    def __init__(self, **kwargs):
        for field in self.required:
            if not kwargs.get(field):
                raise ValueError(f"{self.__class__.__name__}: '{field}' is required")
        self.data = kwargs

    def save(self):
        with open(self.file, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.data, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls):
        """Read all saved items (list of dicts)."""
        rows = []
        try:
            with open(cls.file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        except FileNotFoundError:
            pass
        return rows


class ProductItem(BaseItem):
    """Product detail data (parser output)"""
    file = FILE_DATA
    required = ("url",)


class ProductUrlItem(BaseItem):
    """Product url data (crawler output)"""
    file = FILE_URL
    required = ("product_url",)


class ProductFailedItem(BaseItem):
    """Urls that could not be fetched"""
    file = FILE_URL_FAILED
    required = ("url",)