
import requests



url = "https://bh.opensooq.com/en/search/287014958"



headers = {

    "User-Agent": "Mozilla/5.0"

}



response = requests.get(url, headers=headers)



print("Status Code:", response.status_code)



with open("detail_raw.html", "w", encoding="utf-8") as f:

    f.write(response.text)



print("Detail HTML saved")

