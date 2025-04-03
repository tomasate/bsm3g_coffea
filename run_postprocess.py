import argparse
from analysis.postprocess import coffea_postprocess, root_postprocess

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w",
        "--workflow",
        dest="workflow",
        type=str,
        choices=["2b1e", "2b1mu"],
        help="workflow config to run",
    )
    parser.add_argument(
        "-y",
        "--year",
        dest="year",
        type=str,
        choices=["2016preVFP", "2016postVFP", "2017", "2018"],
        help="dataset year",
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable log scale for y-axis",
    )
    parser.add_argument(
        "--yratio_limits",
        dest="yratio_limits",
        type=float,
        nargs=2,
        default=(0.5, 1.5),
        help="Set y-axis ratio limits as a tuple (e.g., --yratio_limits 0 2)",
    )
    parser.add_argument(
        "--postprocess",
        action="store_true",
        help="Enable postprocessing",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Enable plotting",
    )
    parser.add_argument(
        "--extension",
        dest="extension",
        type=str,
        default="pdf",
        choices=["pdf", "png"],
        help="extension to be used for plotting",
    )
    parser.add_argument(
        "--output_format",
        type=str,
        default="coffea",
        choices=["coffea", "root"],
        help="format of output histograms",
    )
    args = parser.parse_args()

    postprocess_kwargs = {
        "workflow": args.workflow,
        "year": args.year,
        "yratio_limits": args.yratio_limits,
        "log": args.log,
        "extension": args.extension,
        "postprocess": args.postprocess,
        "plot": args.plot
    }
    if args.output_format == "coffea":
        coffea_postprocess(**postprocess_kwargs)
    elif args.output_format == "root":
        root_postprocess(**postprocess_kwargs)