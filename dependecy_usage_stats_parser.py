import json
import os
import shutil
from datetime import datetime
from json import JSONDecodeError
import requests
import pprint
import numpy as np
from bokeh.transform import factor_cmap
from sklearn.preprocessing import MinMaxScaler
from bokeh.io import export_svgs
from bokeh.plotting import figure
from bokeh.palettes import Category10, Category20
from bokeh.models import ColumnDataSource, FactorRange
import glob

# This library is needed for converting the Bokeh-exported svg's to png's
# For some reason the library refuses to load environment variable so loading it manually here fixes it
# Change this according to your own location of vips, see full instructions here https://pypi.org/project/pyvips/
# TODO: Find a better way of doing this
vips_home = "<PATH_TO_YOUR_VIPS_INSTALL>\\bin"
os.environ['PATH'] = vips_home + ';' + os.environ['PATH']
import pyvips # This needs to be imported after the library's path is set correctly

pp = pprint.PrettyPrinter(indent=4)

DEPENDENCY_NAME = "Http-core"  # TODO: Remove hardcoding
BASE_URL = "http://localhost:8080/api/v1/search?"  # /api/v1 is the OpenGrok API path, see https://github.com/oracle/opengrok/wiki/Web-services
REPOS = []
REPO_STATS = []
PACKAGE = "org.apache.http"  # TODO: Remove hardcoding
NR_OF_BARS_PER_PAGE = 8
DEPENDENCY_STATS = {
    "name": DEPENDENCY_NAME,
    "repos": 0,
    "classes": 0,
    "imports": 0,
    "statements": 0
}


def get_list_of_repos():
    # Getting list of repos by finding which repos import this package in their Java classes
    params = {
        "full": "\"" + PACKAGE + "\"",
        "type": "java"
    }
    response = requests.get(BASE_URL, params=params)
    data = json.loads(response.text)
    results = data.get('results')
    for key in results:
        repo_name = key[1:]  # Removing first "/"
        repo_name = repo_name[:repo_name.index('/')]
        if repo_name not in REPOS:
            REPOS.append(repo_name)


def update_nr_statements(repo, classes_used):
    # Querying all the repos for each class is the same as querying each repo for each class since you'd need to run the
    # query for each class you have
    # This should be probably be adapted for future use in ENM Athlone's OpenGrok to avoid spamming them with requests
    # Could run this query for all repos, then matching the results to the correct repos
    # Could try checking each repo's classes_used property and then querying OpenGrok for missing classes?
    # Haven't found a way (syntax) to query a repo with multiple classes (symbols)
    for c in classes_used:
        params = {
            "projects": repo,
            "symbol": c,
            "type": "java"
        }
        response = requests.get(BASE_URL, params=params)
        data = {}
        try:
            data = json.loads(response.text)
        except JSONDecodeError as e:
            print(e)
            exit(0)
        results = data.get('results')
        for key in results:  # Class
            for entry in results[key]:  # Statement
                line = entry["line"]
                words = line.split()  # TODO: Could probably remove this
                if words[0] != "import" and line.find(c) > -1:  # Excluding import statements
                    increment_repo_stat(repo, "statements")


def generate_repo_stats_structure():
    for repo in REPOS:
        REPO_STATS.append({
            "name": repo,
            "classes": 0,  # Number of classes this package is used in
            "imports": 0,  # Number of classes imported from the package
            "statements": 0,  # Number of classes (not unique) from the package used in the repo
            "classes_used": []  # Exact list of package classes used (unique)
            # TODO: Could make each entity in classes_used a dict with name & count to get per-class usage statistics
        })

repo = {
    "classes": 0,
    "imports": 0,
    "statements": 0,
    "classes_used": []
}

def update_nr_classes_imports(repos, package):
    # This could be combined with get_list_of_repos() and changing the list to a set but you can't use dicts as set keys
    # The alternative would be converting the dict to a json string and putting it in the set, but having to re-update the set of strings would be messy
    params = {
        "projects": repos,
        "full": "\"" + package + "\"",
        "type": "java"
    }
    response = requests.get(BASE_URL, params=params)
    data = ""
    try:
        data = json.loads(response.text)
    except JSONDecodeError as e:
        print(e)
        exit(0)
    results = data.get('results')
    # Use "/" as a project divider
    for key in results:  # Each result is a class
        repo_name = key[1:]  # Removing first "/"
        repo_name = repo_name[:repo_name.index('/')]
        # Incrementing class count
        increment_repo_stat(repo_name, "classes")
        for import_statement in results[key]:
            #  Making the assumption here that all statements are unique (so only using the class name)
            words = import_statement.get('line').split(".")
            if words[0].split(' ')[0] != 'import':  # TODO: Fix this?
                continue
            statement = words[len(words) - 1]
            statement = statement.replace(";", "").replace("\r", "").replace("</b>", "").replace("<b>",
                                                                                                 "")  # Getting exact class name
            if statement == 'gson</b>':
                print(statement)
            for repo in REPO_STATS:
                if repo_name == repo.get('name'):
                    if statement not in repo.get('classes_used'):
                        repo["classes_used"].append(statement)  # TODO: Get exact times each class is used?
            increment_repo_stat(repo_name, "imports")


def increment_repo_stat(repo_name, stat):
    if stat == "classes" or stat == "imports" or stat == "statements":
        for repo in REPO_STATS:
            if repo_name == repo.get('name'):
                repo[stat] += 1
    else:
        raise ValueError("Invalid arguments specified")


def collate_dependency_stats(repo_stats):
    for repo in repo_stats:
        DEPENDENCY_STATS["repos"] += 1  # Set this some other way? Could do len(repo_stats)
        DEPENDENCY_STATS["classes"] += repo["classes"]
        DEPENDENCY_STATS["imports"] += repo["imports"]
        DEPENDENCY_STATS["statements"] += repo["statements"]


def scale_data(data):
    # Transforms data to fit in a relative 0-1 range
    scaler = MinMaxScaler(feature_range=(0, 1))
    r_data = np.array(data).reshape((-1, 1))  # Converting to 2D array necessary for Scaler
    scaled_data = scaler.fit_transform(r_data)
    # Try normalized_list = minmax_scale(list_numpy) ?
    # return scaled_data.flatten().tolist()
    return {"data": data, "scaled_data": scaled_data}


def normalize_data(data):
    # Transforms data so that all values add up to 1
    # See https://medium.com/@rrfd/standardize-or-normalize-examples-in-python-e3f174b65dfc for a better explanation
    multiplier = 1 / float(sum(data))
    normalized_data = [x * multiplier for x in data]
    # Alt: norm = [float(i) / sum(data) for i in data]
    return normalized_data


def get_normalized_repo_stats(repos):
    normalized_repos = []
    # Converting list of repos into each of its own list (e.g. list of classes)
    cls = [r["classes"] for r in repos]
    imports = [r["imports"] for r in repos]
    statements = [r["statements"] for r in repos]
    # Normalizing data to a 0-1 range (sum of values = 1)
    cls = normalize_data(cls)
    imports = normalize_data(imports)
    statements = normalize_data(statements)
    for idx, val in enumerate(repos):
        normalized_repos.append({
            "name": val["name"],
            "classes": cls[idx],
            "imports": imports[idx],
            "statements": statements[idx]
        })
    return normalized_repos


def create_basic_bar_chart(stats, names, stat_name, idx, total):
    sorted_names = sorted(names, key=lambda x: stats[names.index(x)], reverse=True)
    title = stat_name.capitalize() + " Used Per Repo " + "(" + idx + " out of " + total + ")"
    color = Category10[3]  # Cause for some reason Category10 only includes palettes of size > 3
    if len(stats) > 3:
        color = Category10[
            len(stats)]  # No need to check for upper bounds since max of this will be NR_OF_BARS_PER_PAGE
    source = ColumnDataSource(data=dict(names=sorted_names, stats=sorted(stats, reverse=True),
                                        color=color))  # TODO: Change this if changing NR_OF_BARS_PER_PAGE

    plot = figure(x_range=sorted_names, title=title, toolbar_location=None, sizing_mode='stretch_both')
    plot.vbar(x='names', top='stats', width=0.5, source=source, color='color')
    plot.xgrid.grid_line_color = None
    plot.y_range.start = 0  # Remove annoying padding below y-axis
    plot.width_policy = 'fit'  # Fit to whole screen
    plot.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
    plot.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
    return plot


def save_chart(plot, filename):
    # Exporting plot to svg then converting to png
    # This was done because exporting a png with ~70 bar charts removed the labels and the ticks, maybe this wouldn't
    # be an issue now that the highest number of bars per chart is 20?
    plot.output_backend = "svg"
    export_svgs(plot, filename=filename + ".svg")
    image = pyvips.Image.new_from_file(filename + ".svg", dpi=110)
    image.write_to_file(filename + ".png")
    os.replace(os.getcwd() + "\\" + filename + ".png",
               os.getcwd() + "\\charts" + "\\" + DEPENDENCY_NAME + "\\" + filename + ".png")
    # Removing unnecessary svg's
    for svg in glob.iglob(os.path.join(os.getcwd(), '*.svg')):
        os.remove(svg)


def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def generate_basic_charts(repo_stats, stat_name):
    # Split list into list of lists
    # Sort those lists so the charts are in descending order of values
    stats = [r[stat_name] for r in repo_stats]  # list of dicts with values -> list of values
    stats = sorted(stats, reverse=True)
    split_stats = split_list(stats, NR_OF_BARS_PER_PAGE)
    names = [r["name"] for r in repo_stats]
    sorted_names = sorted(names, key=lambda x: stats[names.index(x)], reverse=True)
    split_sorted_names = list(split_list(sorted_names, NR_OF_BARS_PER_PAGE))
    for idx, val in enumerate(split_stats):
        plot = create_basic_bar_chart(val, split_sorted_names[idx], stat_name, str(idx + 1),
                                      str(len(split_sorted_names)))
        save_chart(plot, stat_name + "_" + str(idx + 1))
    # For every part:
    #   - create basic bar chart
    #   - export to svg
    #   - convert to png


def generate_large_bar_chart(repo_stats, stat_name):
    # Generate lists of values and sort so the charts are in descending order
    stats = [r[stat_name] for r in repo_stats]
    stats = sorted(stats, reverse=True)
    names = [r["name"] for r in repo_stats]
    sorted_names = sorted(names, key=lambda x: stats[names.index(x)], reverse=True)[:20]
    stats = stats[:20]
    title = stat_name.capitalize() + " Used Per Repo - Top " + str(len(sorted_names)) + " out of " + str(len(names))
    color = Category20[3]
    if 3 <= len(names) <= 20:
        color = Category20[len(names)]
    else:
        color = Category20[20]
    source = ColumnDataSource(data=dict(names=sorted_names, stats=stats, color=color))

    plot = figure(x_range=sorted_names, title=title, toolbar_location=None, sizing_mode='stretch_both')
    plot.vbar(x='names', top='stats', width=0.2, source=source, color='color', legend_field="names")
    plot.xgrid.grid_line_color = None
    plot.y_range.start = 0
    plot.width_policy = 'fit'
    plot.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
    plot.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
    plot.xaxis.major_label_text_font_size = '0pt'  # turn off x-axis tick labels
    save_chart(plot, stat_name)


def generate_grouped_bar_charts(repo_stats):
    totals = [r["imports"] + r["classes"] + r["statements"] for r in repo_stats]
    imports = [r["imports"] for r in repo_stats]
    imports = sorted(imports, key=lambda x: totals[imports.index(x)], reverse=True)
    split_imports = list(split_list(imports, 5))
    cls = [r["classes"] for r in repo_stats]
    cls = sorted(cls, key=lambda x: totals[cls.index(x)], reverse=True)
    split_cls = list(split_list(cls, 5))
    statements = [r["statements"] for r in repo_stats]
    statements = sorted(statements, key=lambda x: totals[statements.index(x)], reverse=True)
    split_statements = list(split_list(statements, 5))
    names = [r["name"] for r in repo_stats]
    names = sorted(names, key=lambda x: totals[names.index(x)], reverse=True)
    split_names = list(split_list(names, 5))
    for idx, val in enumerate(split_names):
        data = {
            "names": split_names[idx],
            "imports": split_imports[idx],
            "classes": split_cls[idx],
            "statements": split_statements[idx]
        }
        plot = create_grouped_bar_chart(data, str(idx + 1), str(len(split_names)))
        save_chart(plot, "grouped" + "_" + str(idx + 1))


def create_grouped_bar_chart(data, idx, total):
    title = "Normalized Imports, Classes, Statements (" + idx + " out of " + total + ")"
    stats = ["imports", "classes", "statements"]
    x = [(name, stat) for name in data["names"] for stat in stats]
    counts = sum(zip(data['imports'], data['classes'], data['statements']), ())  # like an hstack
    source = ColumnDataSource(data=dict(x=x, counts=counts))
    plot = figure(x_range=FactorRange(*x), title=title, toolbar_location=None, sizing_mode='stretch_both')
    plot.vbar(x='x', top='counts', width=0.5, source=source,
              fill_color=factor_cmap('x', palette=Category10[3], factors=stats, start=1, end=2))
    plot.xgrid.grid_line_color = None
    plot.y_range.start = 0
    plot.width_policy = 'fit'
    plot.x_range.range_padding = 0.1
    plot.xaxis.major_label_orientation = 1
    # plot.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
    # plot.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
    return plot


def main():
    start_time = datetime.now()
    print("Started script at %s" % start_time)
    # Getting list of repos and generating repo structure
    # TODO: Consider merging these two
    get_list_of_repos()
    generate_repo_stats_structure()
    # Getting nr of classes and nr of imports
    update_nr_classes_imports(REPOS, PACKAGE)
    # Getting nr of statements
    for repo in REPO_STATS:
        update_nr_statements(repo["name"], repo["classes_used"])
    print("Repo stats:\n")
    pp.pprint(REPO_STATS)
    # Normalizing repo stats (on sum)
    norm_data = get_normalized_repo_stats(REPO_STATS)
    # Creating charts folder if it doesn't exist
    if not os.path.isdir("charts"):
        os.mkdir(os.getcwd() + "\\charts")
    # Deleting existing dependency folder and its contents
    if os.path.isdir(os.getcwd() + "\\charts\\" + DEPENDENCY_NAME):
        shutil.rmtree(os.getcwd() + "\\charts\\" + DEPENDENCY_NAME)
    # Creating dependency folder
    for retry in range(100):
        try:
            os.mkdir(os.getcwd() + "\\charts\\" + DEPENDENCY_NAME)
            break
        except:
            print("Failed to make directory, retrying...")
    # Generating basic bar charts (NR_OF_BARS_PER_PAGE for each stat)
    generate_basic_charts(REPO_STATS, "imports")
    generate_basic_charts(REPO_STATS, "classes")
    generate_basic_charts(REPO_STATS, "statements")
    # Generating large bar charts (one for each stat)
    generate_large_bar_chart(REPO_STATS, "imports")
    generate_large_bar_chart(REPO_STATS, "classes")
    generate_large_bar_chart(REPO_STATS, "statements")
    # Generating grouped bar charts (5 per page)
    generate_grouped_bar_charts(norm_data)
    print("Normalized repo stats:\n")
    pp.pprint(norm_data)
    end_time = datetime.now()
    # Tallying up dependency stats
    collate_dependency_stats(REPO_STATS)
    print("Dependency {} has {} imports, is used in {} classes {} times ({} repos).".format(
        DEPENDENCY_STATS["name"], DEPENDENCY_STATS["imports"], DEPENDENCY_STATS["classes"],
        DEPENDENCY_STATS["statements"], DEPENDENCY_STATS["repos"]))
    avg_imports = int(DEPENDENCY_STATS["imports"] / DEPENDENCY_STATS["repos"])
    avg_classes = int(DEPENDENCY_STATS["classes"] / DEPENDENCY_STATS["repos"])
    avg_statements = int(DEPENDENCY_STATS["statements"] / DEPENDENCY_STATS["repos"])
    print("Average stats for {} repos: {} imports, {} classes and {} statements".format(DEPENDENCY_STATS["repos"],
                                                                                        avg_imports, avg_classes,
                                                                                        avg_statements))
    print("Finished script at %s" % end_time)
    print("Script took %d seconds" % (end_time - start_time).total_seconds())
    os._exit(-1)


main()
