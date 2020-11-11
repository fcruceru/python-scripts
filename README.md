
# A collection of python utility scripts I have written since first learning Python in 2020
Please note these have (for the most part) been solutions for very specific use-cases. Comments have been put in to assist with understanding the code and design choices, as well as how to set up and utilise these.

## Dependency Usage Stats Parser

#### Note a working connection to an instance of [OpenGrok](https://oracle.github.io/opengrok/) is needed, which is used to search and visualize project source code for different repositories.
This script will run different OpenGrok queries and aggregate dependency statistics (per repo) based on the package and name specified (currently set to *http-core*). It will then convert these statistics into Bokeh charts, and export them (as PNGs) to each individual dependency's folder. The 3 statistics are:

 - Number of Imports Used
 - Number of Classes the package is used in
 - Number of Statements Used

![Example of one set of generated charts](https://i.imgur.com/Xi6KbKu.png)
An extra set of charts is generated for a comparison view of normalized, aggregated values for all of the 3 main statistics to serve to gain a better understanding of the relative weight of each repo compared to its peers.
![Example of another, normalized set of generated charts](https://i.imgur.com/O48Fll3.png)

## Log Parser
This script analyzes large (tested on 1M+ lines files) log files and aggregates similar messages based on a SequenceMatcher. The output format is: 

> logMessageCount timestamp Message

e.g.:

> 57 2020-06-11 \<LogMessage\>

Note the log file path(s) will need to be specified in the script, as well as the format of the incoming log messages.

## Render Engine Output (HTML) Parser
Similarly, this script consumes very large HTML files (up to ~50 MB) from generated [Redshift](https://www.redshift3d.com/) render engine log files and creates interactive Bokeh charts for in-depth frame and performance analysis. The format of these usually varies, with some frames containing statistics others might not, and the delimiters themselves being rather inconsistent. The script will take in these files and generate frame statistics for the current scene based on the outputted information, such as:

 - Number of triangles, meshes, textures used
 - Time for render profile update/output/total
 - GPU VRAM (available/used) per device

The data is normalized on maximum (scaled from 0 to 1) to give a better sense of relative resource usage.
![Example of a chart created from a medium-sized log file](https://i.imgur.com/7GDq3jK.png)

## Build Stats Visualizer
This script connects to the specified CI/CD tool and gets the build numbers of the latest couple of builds. It then runs queries against an InfluxDB instance storing build statistics in order to convert the time-series information into per-build graphs. These graphs consist of different smoothing algorithms (Savitsky-Golay, Moving Average, Exponential Moving Average, etc.) for the specified metric(s). The output images are then uploaded to an imgur album (that must be defined as part of the configuration) and in turn, are used to update a Grafana panel with weekly build performance data.
## Light Show
This was a fun little experiment I conducted to test functionality for the program above. It generates a random image based on the [placeholder](https://placeholder.com/) parameters and updates a Grafana dashboard panel every 5 seconds. An extension such as [Easy Auto Refresh](https://chrome.google.com/webstore/detail/easy-auto-refresh/aabcgdmkeabbnleenpncegpcngjpnjkc?hl=en) is recommended to observe the changes in image in the Grafana panel.
