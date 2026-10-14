class ProductItem:

    def __init__(self):
        self.product_id = ""
        self.product_name = ""
        self.brand = ""
        self.price = ""
        self.currency = ""
        self.colour = ""
        self.product_code = ""
        self.description = ""
        self.composition = ""
        self.fit = ""
        self.image = ""
        self.product_url = ""

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "brand": self.brand,
            "price": self.price,
            "currency": self.currency,
            "colour": self.colour,
            "product_code": self.product_code,
            "description": self.description,
            "composition": self.composition,
            "fit": self.fit,
            "image": self.image,
            "product_url": self.product_url,
        }