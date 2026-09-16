class PropertyItem:

    def __init__(
        self,
        url="",
        title="",
        price="",
        location="",
        bedrooms="",
        bathrooms="",
        area=""
    ):
        self.url = url
        self.title = title
        self.price = price
        self.location = location
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.area = area

    def to_dict(self):

        return {
            "url": self.url,
            "title": self.title,
            "price": self.price,
            "location": self.location,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "area": self.area
        }