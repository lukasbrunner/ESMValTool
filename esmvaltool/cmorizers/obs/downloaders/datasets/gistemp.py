"""Script to download Duveiller2018 from its webpage."""
import logging
import os

from esmvaltool.cmorizers.obs.downloaders.wget import WGetDownloader
from esmvaltool.cmorizers.obs.utilities import unpack_files_in_folder

logger = logging.getLogger(__name__)


def download_dataset(config, dataset, start_date, end_date, overwrite):
    downloader = WGetDownloader(
        config=config,
        dataset=dataset,
        overwrite=overwrite,
    )
    downloader.tier = 2
    downloader.download_file(
        "https://data.giss.nasa.gov/pub/gistemp/gistemp250_GHCNv4.nc.gz",
        wget_options=[]

    )
    unpack_files_in_folder(downloader.local_folder)