import random
import time

import requests

grafanaAPIKey = "<GRAFANA_API_KEY>"
baseURL = '<BASE_GRAFANA_URL>'
grafana_headers = {
    "Authorization": "Bearer " + grafanaAPIKey,
    "Accept": "application/json",
    "Content-Type": "application/json"
}


def update_dashboard(position):
    random_nr = random.randrange(500)
    colour = "%06x" % random.randint(0, 0xFFFFFF)
    img_link = "https://via.placeholder.com/600x600.png/" + str(colour) + "/000000/?text=Random+Number+" + str(
        random_nr)
    new_content = '<img src="' + img_link + '">'
    dashboard = get_dashboard()
    dashboard.get('dashboard').get('panels')[position]['content'] = new_content
    print(dashboard.get('dashboard').get('panels')[position]['content'])
    response = requests.post(baseURL + 'dashboards/db', headers=grafana_headers, json=dashboard)
    print(response.headers)
    print(response.json())


def get_dashboard():
    response = requests.get(baseURL + 'dashboards/uid/<DASHBOARD_UID>', headers=grafana_headers)
    return response.json()


def main():
    flag = True
    while flag is True:
        update_dashboard(1)
        update_dashboard(2)
        time.sleep(5)


main()
