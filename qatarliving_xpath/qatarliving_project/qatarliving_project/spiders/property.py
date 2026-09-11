import scrapy


class PropertySpider(scrapy.Spider):
    name = "property"

    api_url= "https://qlp-bo-prod.qatarliving.com//properties?category=1&cur_page=1&per_page=30"
    
    def start_requests(self):
        yield scrapy.Request(
            self.api_url,
            callback=self.parse_api
        )

    def parse_api(self, response):
        data = response.json()
        for ad in data.get("ads", []):
            alias = ad.get("urls", [{}])[0].get("urlAlias")
            if alias:
                property_url = "https://www.qatarliving.com/en" + alias
                yield scrapy.Request(
                    property_url,
                    callback=self.parse
                )

    def parse(self, response):

        yield {
            "url": response.url,

            "title": response.xpath(
                '//h1/text()'
            ).get(),

            "property_type": response.xpath(
                '//text()[normalize-space()="Property Type:"]'
                '/following::text()[normalize-space()][1]'
            ).get(),

            
            "price": response.xpath(
                '//p[contains(., "QAR") and contains(., "Per month")]/preceding-sibling::*[1]//text()[normalize-space()][1]'
            ).get(),

            "location": response.xpath(
                '//h1/following::text()[normalize-space()][1]'
            ).get(),

            "bedrooms": response.xpath(
                '//h1/following::text()[normalize-space()][2]'
            ).get(),

            

            "bathrooms": response.xpath(
                '//h1/following::text()[normalize-space()][4]'
            ).get(),

            

            "updated": response.xpath(
                '//text()[starts-with(normalize-space(),"Updated")]'
            ).getall(),
            
        }