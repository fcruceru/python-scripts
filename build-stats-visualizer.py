import json
import os
import sys
import webbrowser
import requests
from influxdb import InfluxDBClient
from bokeh.plotting import figure
from bokeh.io import export_png, show
from scipy.signal import savgol_filter

os.system('cls')  # Clears CLI text on startup
CLIENT = InfluxDBClient(host='<INFLUXDB_IP_ADDRESS>', port=<"INFLUX_DB_PORT>")
CLIENT.switch_database('<INFLUXDB_DB_NAME>')
BUILDS = []
METRIC = ""
CLIENT_ID = '<IMGUR_CLIENT_ID>'
CLIENT_SECRET = '<IMGUR_CLIENT_SECRET>'
ALBUM_ID = ""
grafanaAPIKey = "<GRAFANA_API_KEY>"
baseURL = '<GRAFANA_BASE_URL>
grafana_headers = {
    "Authorization": "Bearer " + grafanaAPIKey,
    "Accept": "application/json",
    "Content-Type": "application/json"
}
SERVICE = ""
ACCESS_TOKEN = ""


def set_global_constants():
    global SERVICE
    global ACCESS_TOKEN
    with open('script/config.json') as json_file:
        data = json.load(json_file)
        SERVICE = data['service']
        ACCESS_TOKEN = data['access_token']
    print("Retrieved values from config file")


def set_album_id():
    global ALBUM_ID
    if METRIC == "<METRIC1>":
        ALBUM_ID = "<ALBUM_ID>"
    elif METRIC == "<METRIC2>":
        ALBUM_ID = "<ALBUM_ID>"


def set_metric():
    global METRIC
    if len(sys.argv) > 1:
        value = sys.argv[1]
        if value == "<METRIC1>" or value == "<METRIC2>":
            METRIC = value
            print("Metric is %s" % METRIC)
        else:
            sys.exit("Invalid argument specified, quitting.")
    else:  # If no command line arguments, quit
        sys.exit("Must specify metric via command line parameter (<METRIC1>/<METRIC2>).")


def init_builds():
    global BUILDS
    print("Getting list of builds.")
    query = 'SHOW TAG VALUES FROM "three_month".\"' + METRIC + '\" WITH KEY = "<BUILD_NUMBER>"'
    results = CLIENT.query(query)
    points = list(results.get_points())
    for point in points:
        BUILDS.append(int(point.get('value')))
    print("Finished getting list of builds.")


def get_timestamp_from_influxDB(mode, build_nr):
    # Influx queries must include TAF regex to filter out results without square brackets
    query = 'SELECT %s("value") FROM "three_month".\"' % mode + METRIC + '\" WHERE "svc" = \'%s\' AND "<BUILD_NUMBER>" = \'%d\' AND "<SUCCESS>" =~ /\[/' % (
        SERVICE, build_nr)
    print(query)
    result = CLIENT.query(query)
    points = list(result.get_points())
    if not points:
        return 0
    else:
        for point in points:
            return point.get('time')


def get_moving_average_from_influxDB(build_nr, steps, mode):
    last_index = BUILDS.index(build_nr)
    first_index = last_index - steps + 1
    print(first_index, last_index)
    print(BUILDS[first_index], BUILDS[last_index])
    start = get_timestamp_from_influxDB("first", BUILDS[first_index])
    end = get_timestamp_from_influxDB("last", BUILDS[last_index])
    print("First point(%d): %s" % (BUILDS[first_index], start))
    print("Last point(%d): %s" % (BUILDS[last_index], end))
    query = 'SELECT MOVING_AVERAGE("%s", %d) FROM (SELECT %s("value") FROM "three_month".\"' % (
        mode, steps,
        mode) + METRIC + '\" WHERE ("svc" = \'%s\' AND TIME >= \'%s\' AND TIME <= \'%s\' AND "<SUCCESS>" =~ /\[/) GROUP BY "<BUILD_NUMBER>", "taf")' % (
                SERVICE,
                start, end)
    print(query)
    result = CLIENT.query(query)
    points = list(result.get_points())
    if not points:
        return 0
    else:
        for point in points:
            mov_avg = round(point.get('moving_average'), 2)
            print("Build: %d, Mode: %s, MA: %.2f" % (build_nr, mode, mov_avg))
            return mov_avg


def get_exponential_moving_average_from_influxDB(build_nr, steps, mode):
    last_index = BUILDS.index(build_nr)
    first_index = last_index - steps + 1
    print(first_index, last_index)
    print(BUILDS[first_index], BUILDS[last_index])
    start = get_timestamp_from_influxDB("first", BUILDS[first_index])
    end = get_timestamp_from_influxDB("last", BUILDS[last_index])
    print("First point(%d): %s" % (BUILDS[first_index], start))
    print("Last point(%d): %s" % (BUILDS[last_index], end))
    query = 'SELECT EXPONENTIAL_MOVING_AVERAGE("%s", %d) FROM (SELECT %s("value") FROM "three_month".\"' % (
        mode, steps,
        mode) + METRIC + '\" WHERE ("svc" = \'%s\' AND TIME >= \'%s\' AND TIME <= \'%s\' AND "<SUCCESS>" =~ /\[/) GROUP BY "<BUILD_NUMBER>", "<SUCCESS>")' % (
                SERVICE,
                start, end)
    print(query)
    result = CLIENT.query(query)
    points = list(result.get_points())
    if not points:
        return 0
    else:
        for point in points:
            mov_avg = round(point.get('exponential_moving_average'), 2)
            print("Build: %d, Mode: %s, MA: %.2f" % (build_nr, mode, mov_avg))
            return mov_avg


def get_double_exponential_moving_average_from_influxDB(build_nr, steps, mode):
    last_index = BUILDS.index(build_nr)
    first_index = last_index - steps + 1
    print(first_index, last_index)
    print(BUILDS[first_index], BUILDS[last_index])
    start = get_timestamp_from_influxDB("first", BUILDS[first_index])
    end = get_timestamp_from_influxDB("last", BUILDS[last_index])
    print("First point(%d): %s" % (BUILDS[first_index], start))
    print("Last point(%d): %s" % (BUILDS[last_index], end))
    query = 'SELECT DOUBLE_EXPONENTIAL_MOVING_AVERAGE("%s", %d) FROM (SELECT %s("value") FROM "three_month".\"' % (
        mode, steps,
        mode) + METRIC + '\" WHERE ("svc" = \'%s\' AND TIME >= \'%s\' AND TIME <= \'%s\' AND "taf" =~ /\[/) GROUP BY "<BUILD_NUMBER>", "<SUCCESS>")' % (
                SERVICE,
                start, end)
    print(query)
    result = CLIENT.query(query)
    points = list(result.get_points())
    if not points:
        return 0
    else:
        for point in points:
            mov_avg = round(point.get('double_exponential_moving_average'), 2)
            print("Build: %d, Mode: %s, MA: %.2f" % (build_nr, mode, mov_avg))
            return mov_avg


def get_triple_exponential_moving_average_from_influxDB(build_nr, steps, mode):
    last_index = BUILDS.index(build_nr)
    first_index = last_index - steps + 1
    print(first_index, last_index)
    print(BUILDS[first_index], BUILDS[last_index])
    start = get_timestamp_from_influxDB("first", BUILDS[first_index])
    end = get_timestamp_from_influxDB("last", BUILDS[last_index])
    print("First point(%d): %s" % (BUILDS[first_index], start))
    print("Last point(%d): %s" % (BUILDS[last_index], end))
    query = 'SELECT TRIPLE_EXPONENTIAL_MOVING_AVERAGE("%s", %d) FROM (SELECT %s("value") FROM "three_month".\"' % (
        mode, steps,
        mode) + METRIC + '\" WHERE ("svc" = \'%s\' AND TIME >= \'%s\' AND TIME <= \'%s\' AND "<SUCCESS>" =~ /\[/) GROUP BY "<BUILD_NUMBER>", "<SUCCESS>")' % (
                SERVICE,
                start, end)
    print(query)
    result = CLIENT.query(query)
    points = list(result.get_points())
    if not points:
        return 0
    else:
        for point in points:
            mov_avg = round(point.get('triple_exponential_moving_average'), 2)
            print("Build: %d, Mode: %s, MA: %.2f" % (build_nr, mode, mov_avg))
            return mov_avg


def get_mean_from_influxDB(build_nr):
    query = 'SELECT MEAN("value") FROM "three_month".\"' + METRIC + '\" WHERE ("svc" = \'%s\' AND "<BUILD_NUMBER>" = \'%s\' AND "<SUCCESS>" =~ /\[/)' % (
        SERVICE, build_nr)
    print(query)
    result = CLIENT.query(query)
    points = list(result.get_points())
    if not points:
        return 0
    else:
        for point in points:
            mean = round(point.get('mean'), 2)
            print("Build Nr: %d, Mean: %.2f" % (build_nr, mean))
            return mean


def get_ma_xy_values(start, end, steps, mode):
    x = []
    y = []
    for current in range(start, end):
        print("\nCurrent: %d" % current)
        if current not in BUILDS:
            print("Not in list of builds, skipping.")
            continue
        x.append(current)
        y.append(get_moving_average_from_influxDB(current, steps, mode))
    return x, y


def get_expoma_xy_values(start, end, steps, mode):
    x = []
    y = []
    for current in range(start, end):
        print("\nCurrent: %d" % current)
        if current not in BUILDS:
            print("Not in list of builds, skipping.")
            continue
        x.append(current)
        y.append(get_exponential_moving_average_from_influxDB(current, steps, mode))
    return x, y


def get_dexpoma_xy_values(start, end, steps, mode):
    x = []
    y = []
    for current in range(start, end):
        print("\nCurrent: %d" % current)
        if current not in BUILDS:
            print("Not in list of builds, skipping.")
            continue
        x.append(current)
        y.append(get_double_exponential_moving_average_from_influxDB(current, steps, mode))
    return x, y


def get_texpoma_xy_values(start, end, steps, mode):
    x = []
    y = []
    for current in range(start, end):
        print("\nCurrent: %d" % current)
        if current not in BUILDS:
            print("Not in list of builds, skipping.")
            continue
        x.append(current)
        y.append(get_triple_exponential_moving_average_from_influxDB(current, steps, mode))
    return x, y


def get_mean_xy_values(start, end):
    x = []
    y = []
    for current in range(start, end):
        print("\nCurrent: %d" % current)
        if current not in BUILDS:
            print("Not in list of builds, skipping.")
            continue
        x.append(current)
        y.append(get_mean_from_influxDB(current))
    return x, y


def init_plot(start, end, steps, mode, legend, color, plot):
    x, y = get_ma_xy_values(start, end, steps, mode)
    a, b = get_mean_xy_values(start, end)
    c, d = get_expoma_xy_values(start, end, steps, mode)
    e, f = get_dexpoma_xy_values(start, end, steps, mode)
    g, h = get_texpoma_xy_values(start, end, steps, mode)
    sgwl1 = 15
    sgwl2 = 25
    sgwl3 = 35
    sgwl4 = 45
    b_interp1 = savgol_filter(b, sgwl1, 4)
    b_interp2 = savgol_filter(b, sgwl2, 4)
    b_interp3 = savgol_filter(b, sgwl3, 4)
    b_interp4 = savgol_filter(b, sgwl4, 4)
    plot.line(a, b_interp1, legend="SG Mean " + str(sgwl1), line_color="orange", muted_alpha=0.1, alpha=0.8)
    plot.line(a, b_interp2, legend="SG Mean " + str(sgwl2), line_color="orange", muted_alpha=0.1, alpha=0.8)
    plot.line(a, b_interp3, legend="SG Mean " + str(sgwl3), line_color="orange", muted_alpha=0.1, alpha=0.8)
    plot.line(a, b_interp4, legend="SG Mean " + str(sgwl4), line_color="orange", muted_alpha=0.1, alpha=0.8)
    plot.line(x, y, legend="Moving Average", line_color="red", muted_alpha=0.1, alpha=0.8)
    plot.line(a, b, legend="Mean", line_color="blue", muted_alpha=0.2, alpha=0.8)
    plot.line(c, d, legend="Exponential Moving Average", line_color="green", muted_alpha=0.1, alpha=0.8)
    plot.line(e, f, legend="Double Exponential Moving Average", line_color="orange", muted_alpha=0.1, alpha=0.8)
    plot.line(g, h, legend="Triple Exponential Moving Average", line_color="olive", muted_alpha=0.1, alpha=0.8)
    # For stems:
    # for point in x:
    #    plot.line(point, [y[0], 0])


def plot_values(start, end, steps):
    title = ""
    y_label = ""
    if METRIC == "<METRIC1>":
        title = "<METRIC1> Moving Average (n = " + str(steps) + ")"
        y_label = "<METRIC1_DESCRIPTION>"
    elif METRIC == "<METRIC2>":
        title = "<METRIC2> (n = " + str(steps) + ")"
        y_label = "<METRIC2_DESCRIPTION>"
    p = figure(title=title, x_axis_label='Build Number', y_axis_label=y_label, sizing_mode='stretch_both')
    init_plot(start, end, steps, "max", "Max", "red", p)
    init_plot(start, end, steps, "mean", "Mean", "blue", p)
    init_plot(start, end, steps, "min", "Min", "green", p)
    p.legend.location = 'top_right'
    export_png(p, filename="script/plot.png")
    p.width_policy = 'fit'
    p.x_range.range_padding = 0
    p.legend.click_policy = "mute"
    p.toolbar.autohide = True
    show(p)


def get_latest_build():
    # Connect to the CICD tool and retrieve latest Build number
    print("Retrieving Build number.")
    response = requests.get(
        "<URL_TO_GET_BUILD_INFO>")
    read = json.loads(response.text)
    buildnum = build.get("<BUILD_NR_PROPERTY>")
    print("Retrieved Build Number: " + str(buildnum))
    return buildnum


def update_access_token(token):
    data = {
        "access_token": token,
        "service": "<SERVICE>"
    }
    with open('script/config.json', 'w') as json_file:
        json.dump(data, json_file)


def imgur_authorize():
    url = "https://api.imgur.com/oauth2/authorize?client_id=" + CLIENT_ID + "&response_type=token"
    webbrowser.open(url)
    ar = input("Enter the full callback URL:\n")
    token = ar[ar.find('#access_token') + 14:ar.find('&expires_in')]  # Extracting token from key-value pair
    update_access_token(token)
    print("Updated .json with new access token")
    return token


def upload_image(album_id, title, auth):
    if auth is True:
        access_token = imgur_authorize()
    else:
        access_token = ACCESS_TOKEN
    url = "https://api.imgur.com/3/upload"
    data = open('script/plot.png', 'rb').read()
    payload = {
        'image': data,
        'album': album_id,
        'title': title
    }
    headers = {
        'Authorization': 'Bearer ' + access_token
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    img_id = response.json().get('data').get('id')
    if img_id is None:
        print("Failed to get access token, please log in and obtain the access token.")
        upload_image(album_id, title, auth=True)
    else:
        print("Image ID: %s" % img_id)
        update_dashboard(img_id)


def upload_plot(metric, start, end):
    title = "%s Moving Average for Builds %s - %s" % (metric, start, end)
    upload_image(ALBUM_ID, title, False)


def update_dashboard(img_id):
    position = -1
    if METRIC == "<METRIC1>":
        position = 1
    elif METRIC == "<METRIC2>":
        position = 2
    img_link = "https://i.imgur.com/" + img_id + ".png"
    new_content = '<img src="' + img_link + '">'
    dashboard = get_dashboard()
    dashboard.get('dashboard').get('panels')[position]['content'] = new_content
    print(dashboard.get('dashboard').get('panels')[position]['content'])
    response = requests.post(baseURL + 'dashboards/db', headers=grafana_headers, json=dashboard)
    print(response.headers)
    print(response.json())


def get_dashboard():
    response = requests.get(baseURL + 'dashboards/uid/<GRAFANA_DASHBOARD_UID>', headers=grafana_headers)
    return response.json()


def main():
    print("********* Started script **********")
    set_metric()
    set_global_constants()
    set_album_id()
    init_builds()
    latestBuild = get_latest_build() - 1
    plot_values(latestBuild - 150, latestBuild + 1, 5)
    upload_plot(METRIC, (latestBuild - 50), latestBuild)


main()
