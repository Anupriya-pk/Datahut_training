import json


with open("products.json", "r", encoding="utf-8") as file:
    products = json.load(file)


with open("cleaned_data.txt", "w", encoding="utf-8") as file:
    for product in products:
        file.write(f"Name: {product['name']}\n")
        file.write(f"Price: {product['price']}\n")
        file.write(f"Currency: {product['currency']}\n")
        file.write("\n")


print("cleaned_data.txt created successfully")