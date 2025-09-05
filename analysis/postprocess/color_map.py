import yaml
from glob import glob
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex


def color_generator(cmap_name="tab20"):
    # https://cms-analysis.docs.cern.ch/guidelines/plotting/colors/
    cms_colors = [
        "#3f90da",
        "#ffa90e",
        "#bd1f01",
        "#94a4a2",
        "#832db6",
        "#a96b59",
        "#e76300",
        "#b9ac70",
        "#717581",
        "#92dadd",
    ]
    used = set(c.lower() for c in cms_colors)
    for c in cms_colors:
        yield c
    cmap = plt.get_cmap(cmap_name)
    i = 0
    while True:
        c = to_hex(cmap(i % cmap.N))
        if c.lower() not in used:
            used.add(c.lower())
            yield c
        i += 1


def new_color_generator(used_colors, cmap_name="tab20"):
    cmap = plt.get_cmap(cmap_name)
    i = 0
    while True:
        c = to_hex(cmap(i % cmap.N))
        if c.lower() not in used_colors:
            used_colors.add(c.lower())
            yield c
        i += 1


def get_framework_processes():
    filesets_dir = Path.cwd() / "analysis" / "filesets"
    filesets_files = glob(f"{filesets_dir}/*_nano*.yaml")
    processes = []
    for ff in filesets_files:
        with open(ff, "r") as f:
            fileset_info = yaml.safe_load(f)
        for name in fileset_info:
            process = fileset_info[name]["process"]
            if process != "Data":
                if process not in processes:
                    processes.append(process)
    return processes


if __name__ == "__main__":
    color_map_file = Path.cwd() / "analysis" / "postprocess" / "color_map.yaml"
    processes = get_framework_processes()
    if not color_map_file.exists():
        gen = color_generator()
        color_map = {p: next(gen) for p in processes}
        with open(color_map_file, "w") as f:
            yaml.dump(color_map, f, default_flow_style=False, sort_keys=False)
    else:
        with open(color_map_file, "r") as f:
            color_map = yaml.safe_load(f)
        used_colors = set(c.lower() for c in color_map.values())
        gen = new_color_generator(used_colors)
        for process in processes:
            if process not in color_map:
                color_map[proc] = next(gen)
        with open(color_map_file, "w") as f:
            yaml.dump(color_map, f, default_flow_style=False, sort_keys=False)
