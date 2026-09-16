
class PropertyItem:

    def __init__(
        self,
        url="",
        title="",
        price="",
        location="",
        property_type="",
        bedrooms="",
        bathrooms="",
        area=""
    ):
        self.url = url
        self.title = title
        self.price = price
        self.location = location
        self.property_type = property_type
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.area = area

    def to_dict(self):

        return {
            "url": self.url,
            "title": self.title,
            "price": self.price,
            "location": self.location,
            "property_type": self.property_type,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "area": self.area
        }

