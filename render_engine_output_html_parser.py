from bs4 import BeautifulSoup
from datetime import datetime
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource
from sklearn.preprocessing import MinMaxScaler
from bokeh.palettes import Dark2_5 as palette
import itertools
import numpy as np


def parse_log_file(file_path):
    with open(file_path) as file:
        print("Parsing frames for file %s" % file_path)
        data = file.read()
        html = BeautifulSoup(data, 'html.parser')
        text = html.get_text()
        initial_frames = parse_list_of_frames(text)
        print("Total number of frames: %d" % len(initial_frames))
        filtered_frames = remove_progressive_frames(initial_frames)
        print("Removed %d frames with progressive rendering. Number of frames is now at: %d " % (
            (len(initial_frames) - len(filtered_frames)), len(filtered_frames)))
        print("Parsing frame statistics.")
        frame_stats = []
        for frame in filtered_frames:
            frame_stats.append(parse_frame(frame))
        print("Finished parsing frame statistics.")
        for stats in frame_stats:
            stats.print_string()
        print("Setting up plot.")
        plot_stats(frame_stats)
        print("Finished setting up plot.")


def plot_stats(list_of_frames):
    # TODO: Look into adding to these lists first instead of creating objects then iterating over them
    frame_ids = []
    triangles = []
    ttp_meshes = []
    ttp_textures = []
    profile_update = []
    profile_render = []
    profile_output = []
    profile_total = []
    gpu_stats = []
    frame_counters = list(range(len(list_of_frames)))

    for frame in list_of_frames:
        frame_ids.append(frame.frame_id)
        triangles.append(frame.triangles)
        ttp_meshes.append(frame.ttp_meshes)
        ttp_textures.append(frame.ttp_textures)
        profile_update.append(frame.profile_update)
        profile_render.append(frame.profile_render)
        profile_output.append(frame.profile_output)
        profile_total.append(frame.profile_total)
        gpu_stats.append(frame.gpu_stats)

    # Normalizing
    triangles = setup_data(triangles)
    ttp_meshes = setup_data(ttp_meshes)
    ttp_textures = setup_data(ttp_textures)
    profile_update = setup_data(profile_update)
    profile_render = setup_data(profile_render)
    profile_output = setup_data(profile_output)
    profile_total = setup_data(profile_total)

    source = ColumnDataSource(data=dict(
        x=frame_counters,
        triangles=triangles.get("normalized"),
        triangles_tooltip=triangles.get("data"),
        ttp_meshes=ttp_meshes.get("normalized"),
        ttp_meshes_tooltip=ttp_meshes.get("data"),
        ttp_textures=ttp_textures.get("normalized"),
        ttp_textures_tooltip=ttp_textures.get("data"),
        profile_update=profile_update.get("normalized"),
        profile_update_tooltip=profile_update.get("data"),
        profile_render=profile_render.get("normalized"),
        profile_render_tooltip=profile_render.get("data"),
        profile_output=profile_output.get("normalized"),
        profile_output_tooltip=profile_output.get("data"),
        profile_total=profile_total.get("normalized"),
        profile_total_tooltip=profile_total.get("data"),
        frame_id=frame_ids,
    ))

    # Dealing with GPU memory stats
    nr_of_cards = len(gpu_stats[0])
    geo_pcie_max = []
    geo_cache_max = []
    tex_pcie_max = []
    tex_cache_max = []
    vram_max = []
    for x in range(nr_of_cards):
        vram = []
        geopcie = []
        geocache = []
        texpcie = []
        texcache = []
        for gpu_stat in gpu_stats:
            vram.append(gpu_stat[x].memory)
            geopcie.append(gpu_stat[x].geometry_pcie_uploads)
            geocache.append(gpu_stat[x].geometry_cache_size)
            texpcie.append(gpu_stat[x].textures_pcie_uploads)
            texcache.append(gpu_stat[x].textures_cache_size)
        # Transforming list of values into dict of normal data/normalized data lists
        geo_pcie_max.append(max(geopcie))
        geo_cache_max.append(max(geocache))
        tex_pcie_max.append(max(texpcie))
        tex_cache_max.append(max(texcache))
        vram_max.append(max(vram))
        vram = setup_data(vram)
        geopcie = setup_data(geopcie)
        geocache = setup_data(geocache)
        texpcie = setup_data(texpcie)
        texcache = setup_data(texcache)
        source.add(vram.get("normalized"), 'device_' + str(x) + '_vram')
        source.add(vram.get("data"), 'device_' + str(x) + '_vram_tooltip')
        source.add(geopcie.get("normalized"), 'device_' + str(x) + '_geometry_pcie_uploads')
        source.add(geopcie.get("data"), 'device_' + str(x) + '_geometry_pcie_uploads_tooltip')
        source.add(geocache.get("normalized"), 'device_' + str(x) + '_geometry_cache_size')
        source.add(geocache.get("data"), 'device_' + str(x) + '_geometry_cache_size_tooltip')
        source.add(texpcie.get("normalized"), 'device_' + str(x) + '_textures_pcie_uploads')
        source.add(texpcie.get("data"), 'device_' + str(x) + '_textures_pcie_ uploads_tooltip')
        source.add(texcache.get("normalized"), 'device_' + str(x) + '_textures_cache_size')
        source.add(texcache.get("data"), 'device_' + str(x) + '_textures_cache_size_tooltip')
    plot = setup_plot(source, frame_counters, gpu_stats[0], geo_pcie_max, geo_cache_max, tex_pcie_max, tex_cache_max, vram_max)
    show(plot)


def setup_data(data):
    scaler = MinMaxScaler() # feature_range=(0,1)
    data = np.array(data).reshape(-1, 1)
    normalized = scaler.fit_transform(data)
    return {"data": data, "normalized": normalized}


def setup_plot(source, frame_counters, gpu_stats, geo_pcie_max, geo_cache_max, tex_pcie_max, tex_cache_max, vram_max):
    tooltips = [
        ('Frame Counter', '$index'),
        ('Frame ID', '@frame_id'),
        ('Triangles', '@triangles_tooltip{0.00 a}'),
        ('Time to Process Meshes', '@ttp_meshes_tooltip ms'),
        ('Time to Process Textures', '@ttp_textures_tooltip ms'),
        ('Profile Update', '@profile_update_tooltip ms'),
        ('Profile Render', '@profile_render_tooltip ms'),
        ('Profile Output', '@profile_output_tooltip ms'),
        ('Profile Total', '@profile_total_tooltip ms')
    ]
    vram_tooltip = ['Available VRAM (Device ' + str(gpu_stats[0].device_id), '@device_' + str(gpu_stats[0].device_id) + '_vram_tooltip MB']
    geopcie_tooltip = ['Geometry PCIe Uploads (Device ' + str(gpu_stats[0].device_id), '@device_' + str(gpu_stats[0].device_id) + '_geometry_pcie_uploads_tooltip MB']
    geocache_tooltip = ['Geometry Cache Size (Device ' + str(gpu_stats[0].device_id), '@device_' + str(gpu_stats[0].device_id) + '_geometry_cache_size_tooltip MB']
    texpcie_tooltip = ['Textures PCIe Uploads (Device ' + str(gpu_stats[0].device_id), '@device_' + str(gpu_stats[0].device_id) + '_textures_pcie_uploads_tooltip MB']
    texcache_tooltip = ['Textures Cache Size (Device ' + str(gpu_stats[0].device_id), '@device_' + str(gpu_stats[0].device_id) + '_textures_cache_size_tooltip MB']

    for x in range(len(gpu_stats)):
        if len(gpu_stats) > 1 and x != 0:
            vram_tooltip[0] += " | " + str(gpu_stats[x].device_id)
            vram_tooltip[1] += " | " + '@device_' + str(gpu_stats[x].device_id) + '_vram_tooltip MB'
            geopcie_tooltip[0] += " | " + str(gpu_stats[x].device_id)
            geopcie_tooltip[1] += " | " + '@device_' + str(gpu_stats[x].device_id) + '_geometry_pcie_uploads_tooltip MB'
            geocache_tooltip[0] += " | " + str(gpu_stats[x].device_id)
            geocache_tooltip[1] += " | " + '@device_' + str(gpu_stats[x].device_id) + '_geometry_cache_size_tooltip MB'
            texpcie_tooltip[0] += " | " + str(gpu_stats[x].device_id)
            texpcie_tooltip[1] += " | " + '@device_' + str(gpu_stats[x].device_id) + '_textures_pcie_uploads_tooltip MB'
            texcache_tooltip[0] += " | " + str(gpu_stats[x].device_id)
            texcache_tooltip[1] += " | " + '@device_' + str(gpu_stats[x].device_id) + '_textures_cache_size_tooltip MB'

    vram_tooltip[0] += ")"
    geopcie_tooltip[0] += ")"
    geocache_tooltip[0] += ")"
    texpcie_tooltip[0] += ")"
    texcache_tooltip[0] += ")"
    # Adding per-GPU tooltips
    tooltips.append(tuple(vram_tooltip))
    tooltips.append(tuple(geopcie_tooltip))
    tooltips.append(tuple(geocache_tooltip))
    tooltips.append(tuple(texpcie_tooltip))
    tooltips.append(tuple(texcache_tooltip))

    plot = figure(x_axis_label='Frame Counter', sizing_mode='stretch_both', tooltips=tooltips)
    plot.line('x', 'triangles', line_width=2, source=source, color="blue", alpha=0.8, legend_label="Triangles")
    plot.line('x', 'ttp_meshes', line_width=2, source=source, color="green", alpha=0.8, legend_label="Time to Process Meshes")
    plot.line('x', 'ttp_textures', line_width=2, source=source, color="cyan", alpha=0.8, legend_label="Time to Process Textures")
    plot.line('x', 'profile_update', line_width=2, source=source, color="red", alpha=0.8, legend_label="Profile Update")
    plot.line('x', 'profile_render', line_width=2, source=source, color="purple", alpha=0.8, legend_label="Profile Render")
    plot.line('x', 'profile_output', line_width=2, source=source, color="brown", alpha=0.8, legend_label="Profile Output")
    plot.line('x', 'profile_total', line_width=2, source=source, color="orange", alpha=0.8, legend_label="Profile Total")

    # Adding per-gpu lines to the plot
    # TODO: fix device colors being the same
    colors = itertools.cycle(palette)  # Initialising colours to cycle through
    for gpu in gpu_stats:
        identifier = "Device " + str(gpu.device_id) + " (" + gpu.name + ") "
        plot.line('x', 'device_' + str(gpu.device_id) + '_vram', line_width=2, source=source, color=next(colors), alpha=0.8, legend_label=identifier + "Available VRAM (Max: " + str(round(vram_max[gpu.device_id],2)) + " MB)")
        plot.line('x', 'device_' + str(gpu.device_id) + '_geometry_pcie_uploads', line_width=2, source=source, color=next(colors), alpha=0.8, legend_label=identifier + "Geometry PCIe Uploads (Max: " + str(round(geo_pcie_max[gpu.device_id], 2)) + " MB)")
        plot.line('x', 'device_' + str(gpu.device_id) + '_geometry_cache_size', line_width=2, source=source, color=next(colors), alpha=0.8, legend_label=identifier + "Geometry Cache Size (Max: " + str(round(geo_cache_max[gpu.device_id], 2)) + " MB)")
        plot.line('x', 'device_' + str(gpu.device_id) + '_textures_pcie_uploads', line_width=2, source=source, color=next(colors), alpha=0.8, legend_label=identifier + "Textures PCIe Uploads (Max: " + str(round(tex_pcie_max[gpu.device_id], 2)) + " MB)")
        plot.line('x', 'device_' + str(gpu.device_id) + '_textures_cache_size', line_width=2, source=source, color=next(colors), alpha=0.8, legend_label=identifier + "Textures Cache Size (Max: " + str(round(tex_cache_max[gpu.device_id], 2)) + " MB)")
    # Basic plot settings
    plot.width_policy = 'fit'
    plot.x_range.range_padding = 0
    plot.y_range.range_padding = 0
    # plot.x_range.bounds = (0, float(frame_counters[len(frame_counters) - 1]))
    plot.title.text = 'Render Frame Statistics (Normalized)'
    plot.legend.location = "top_left"
    plot.legend.click_policy = "hide"
    return plot


def remove_progressive_frames(frames):
    frames_new = [x for x in frames if not determine(x)]
    return frames_new


def determine(frame):
    lines = frame.splitlines()
    flag = False
    for line in lines:
        if "Progressive rendering..." in line:
            return True
        if "MiniRender: Aborted" in line:
            return True
        if "Allocating GPU mem" in line:
            flag = True
    if flag is False:  # If frame does not contain this line, remove it from list of frames
        return True


def parse_list_of_frames(text):
    frames = []
    frame_starts = []
    for offs in find_offsets(text, "Rendering frame"):
        frame_starts.append(offs)
    for idx, val in enumerate(frame_starts):
        if idx == len(frame_starts) - 1:
            frame = text[frame_starts[idx - 1]:val]
            frames.append(frame)
        else:
            frame = text[val:frame_starts[idx + 1]]
            frames.append(frame)
    return frames


def find_offsets(haystack, needle):
    offs = -1
    while True:
        offs = haystack.find(needle, offs + 1)
        if offs == -1:
            break
        else:
            yield offs


def parse_frame(frame):
    lines = frame.splitlines()
    lines = [x for x in lines if x]  # Removing empty lines from string list
    gpu_stats = []
    stats = Frame(-1, -1, -1, -1, -1, 0, 0, 0, 0, 0, 0, gpu_stats)
    gpu_memory = []
    nrs = []
    vram_points = [i for i, j in enumerate(lines) if 'Allocating VRAM for device' in j]
    for pt in vram_points:
        nr = lines[pt]
        nr = int(nr[nr.find("device") + 6:nr.find("(")].strip())
        nrs.append(nr)
    nr_of_gpus = max(nrs)+1
    for idx, val in enumerate(lines):
        # Frame did not have "Rendering time" -> check for device x instead
        # if "Rendering time" in val:
        #     nr_of_gpus = int(val[val.find("(") + 1:val.find("GPU")].strip())

        if "Rendering frame" in val:
            frame_id = val[val.find('frame'):]
            frame_id = frame_id[-5:].replace('.', '').strip()
            stats.frame_id = int(frame_id)

        if "TriMeshes" in val:
            meshes = val[val.find('Meshes:') + 7:val.find('(')].strip()
            stats.meshes = int(meshes)

        if "Proxies: " in val:
            proxies = val[val.find('Proxies:') + 8:].strip()
            stats.proxies = int(proxies)

        if "Total triangles: " in val:
            triangles = val[val.find('Total triangles:') + 16:].strip()
            stats.triangles = int(triangles)

        if "Total hair strand segments: " in val:
            hair_strand_segments = val[val.find('Total hair strand segments:') + 27:].strip()
            stats.hair_strand_segments = int(hair_strand_segments)

        if "Time to process" in val:
            if "meshes" in val:
                res = val[val.find('meshes:') + 7:].strip()
                if "ms" in val:
                    res = int(res[:-2])
                elif "s" in val:
                    res = float(res[:-1]) / 1000
                stats.ttp_meshes = res  # Since we're looping through each line, the last line with stats will be saved
            if "textures" in val:
                res = val[val.find('textures:') + 9:-7].strip()
                res = float(res) * 1000
                stats.ttp_textures = round(res, 4)  # Millisecond precision

        if "Summary: Profile" in val:
            update = val[val.find('Update:') + 7:val.find('Update:') + 16].strip()
            update = int(datetime.strptime(update, '%M:%S.%f').microsecond / 1000)
            stats.profile_update = update

            render = val[val.find('Render:') + 7:val.find('Render:') + 16].strip()
            render = int(datetime.strptime(render, '%M:%S.%f').microsecond / 1000)
            stats.profile_render = render

            output = val[val.find('Output:') + 7:val.find('Output:') + 16].strip()
            output = int(datetime.strptime(output, '%M:%S.%f').microsecond / 1000)
            stats.profile_output = output

            total = val[val.find('Total:') + 7:val.find('Total:') + 16].strip()
            total = int(datetime.strptime(total, '%M:%S.%f').microsecond / 1000)
            stats.profile_total = total

        # if "Allocating VRAM for device" in val:
        #     if "Redshift" in lines[idx + 1]:
        #         indices.append(idx)

        if "GPU Memory" in val:
            for x in range(0, nr_of_gpus+1, 2):
                line_one = lines[idx + x + 1]
                geometry_pcie_uploads = line_one[line_one.find("uploads:") + 8:line_one.find("(cachesize")].strip()
                geometry_pcie_uploads = format_memory(geometry_pcie_uploads)
                geometry_cache_size = line_one[line_one.find("cachesize:") + 10:line_one.find(")")].strip()
                geometry_cache_size = format_memory(geometry_cache_size)

                line_two = lines[idx + x + 2]
                textures_pcie_uploads = line_two[line_one.find("uploads:") + 8:line_one.find("(cachesize")].strip()
                textures_pcie_uploads = format_memory(textures_pcie_uploads)
                textures_cache_size = line_two[line_one.find("cachesize:") + 10:line_one.find(")")].strip()
                textures_cache_size = format_memory(textures_cache_size)
                gpu_memory.append({
                    "geometry_pcie_uploads": geometry_pcie_uploads,
                    "geometry_cache_size": geometry_cache_size,
                    "textures_pcie_uploads": textures_pcie_uploads,
                    "textures_cache_size": textures_cache_size,
                })
    # Parsing Device VRAM stats
    # Only saving stats from the last <nr_of_gpus> "Allocating VRAM for device" blocks
    if len(vram_points) > nr_of_gpus:
        vram_points = vram_points[len(vram_points)-nr_of_gpus:]

    for ind, val in enumerate(vram_points):
        first_line = lines[val]
        device_id = int(first_line[first_line.find("device") + 6:first_line.find("(")].strip())
        device_name = first_line[first_line.find("(") + 1:first_line.find(")")]
        second_line = lines[val + 1]
        device_memory = int(second_line[second_line.find("up to") + 5:-3].strip())
        try:
            gpu_stats.append(GpuCard(device_id, device_name, device_memory, gpu_memory[ind].get("geometry_pcie_uploads"),
                    gpu_memory[ind].get("geometry_cache_size"),
                    gpu_memory[ind].get("textures_pcie_uploads"),
                    gpu_memory[ind].get("textures_cache_size")))
        except IndexError as e:
            print(e)

    return stats


def format_memory(val):
    if "KB" in val:
        return round(float(val[:-2].strip()) / 1000, 2)
    if "MB" in val:
        return round(float(val[:-2].strip()), 2)
    if "B" in val:
        res = float(val[:-1].strip())
        if res > 0:
            return round(res / 1000000, 2)
        return res
    return -1  # Error


def main():
    start = datetime.now()
    print("Started script.")
    parse_log_file("../logs/log_medium.html")
    end = datetime.now()
    print("Finished script in %.1f seconds." % ((end - start).total_seconds()))


class Frame:
    def __init__(self, frame_id, meshes, proxies, triangles, hair_strand_segments, ttp_meshes, ttp_textures,
                 profile_update, profile_render, profile_output, profile_total, gpu_stats):
        self.frame_id = frame_id
        self.meshes = meshes
        self.proxies = proxies
        self.triangles = triangles
        self.hair_strand_segments = hair_strand_segments
        self.ttp_meshes = ttp_meshes
        self.ttp_textures = ttp_textures
        self.profile_update = profile_update
        self.profile_render = profile_render
        self.profile_output = profile_output
        self.profile_total = profile_total
        self.gpu_stats = gpu_stats  # Must be a list of GpuCard types

    def print_string(self):
        gpu_cards_string = ""
        for card in self.gpu_stats:
            gpu_cards_string += "| " + card.to_string() + " "

        print(
            "Frame ID: %d | Meshes: %d | Proxies: %d | Triangles: %d | Hair Strand Segments: %d | Time to process "
            "Meshes: %d | Time to process Textures %.3f | Update: %d | Render: %d | Output: %d | Total: %d %s" % (
                self.frame_id, self.meshes, self.proxies, self.triangles, self.hair_strand_segments, self.ttp_meshes,
                self.ttp_textures, self.profile_update, self.profile_render, self.profile_output, self.profile_total,
                gpu_cards_string))


class GpuCard:
    def __init__(self, device_id, name, memory, geometry_pcie_uploads, geometry_cache_size, textures_pcie_uploads,
                 textures_cache_size):
        self.device_id = device_id
        self.name = name
        self.memory = memory
        self.geometry_pcie_uploads = geometry_pcie_uploads
        self.geometry_cache_size = geometry_cache_size
        self.textures_pcie_uploads = textures_pcie_uploads
        self.textures_cache_size = textures_cache_size

    def to_string(self):
        return "Device ID: {}, Name: {}, Memory (MB): {}, Geometry PCIe Uploads (MB): {}, Geometry Cache Size (MB): {}, " \
               "Texture PCIe Uploads (MB): {}, Texture Cache Size (MB): {}".format(
            self.device_id, self.name,
            self.memory, self.geometry_pcie_uploads, self.geometry_cache_size, self.textures_pcie_uploads,
            self.textures_cache_size)


main()
