import os
import sys
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict

from apple_xml_tools.iphoto_xml_tools import (
    AlbumCompositionFileConfig,
    AppleXMLKeyedPart,
    FieldsFilter,
    IphotoListOfAlbums,
    IphotoListOfAlbumsWithMasterImageInfo,
    IphotoMasterImageList,
    OutputCsvConfig,
    TargetFieldsConfig,
)


class TargetXMLKeyInfoDictConfig(BaseModel):
    """Configuration for the input XML parts.
    'INPUT' > 'TARGET_XML_KEY_INFO' in YAML.

    Attributes:
        MASTER_IMAGE_LIST: Configuration for the master image list XML part.
        LIST_OF_ALBUMS: Configuration for the list of albums XML part.
    """

    MASTER_IMAGE_LIST: AppleXMLKeyedPart
    LIST_OF_ALBUMS: AppleXMLKeyedPart

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class InputConfig(BaseModel):
    """Input section of the configuration.
    'INPUT' in YAML.

    Attributes:
        TARGET_XML_KEY_INFO: Configuration for the input XML parts.
    """

    TARGET_XML_KEY_INFO: TargetXMLKeyInfoDictConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class FieldsFilterDictConfig(BaseModel):
    """Configuration for FieldsFilters.
    'PROCESS' > 'FIELDS_FILTER' in YAML.

    Attributes:
        MASTER_IMAGE_LIST (optional):
            Configuration for filtering fields of the master image list. Default to None.
        LIST_OF_ALBUMS (optional):
            Configuration for filtering fields of the list of albums. Default to None.
    """

    MASTER_IMAGE_LIST: FieldsFilter | None = None
    LIST_OF_ALBUMS: FieldsFilter | None = None

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class ProcessConfig(BaseModel):
    """Processing section of the configuration.
    'PROCESS' in YAML.

    Attributes:
        FIELDS_FILTER (optional): Configuration for FieldsFilters. Default to None.
        TARGET_FIELDS: Configuration for TargetFields (target column names).
    """

    FIELDS_FILTER: FieldsFilterDictConfig | None = None
    TARGET_FIELDS: TargetFieldsConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class OutputCsvDictConfig(BaseModel):
    """Configuration for output CSV.
    'OUTPUT' > 'CSV' in YAML.

    Attributes:
        MASTER_IMAGE_LIST: Configuration for the master image list CSV file.
        LIST_OF_ALBUMS: Configuration for the list of albums CSV file.
    """

    MASTER_IMAGE_LIST: OutputCsvConfig
    LIST_OF_ALBUMS: OutputCsvConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class OutputTxtDictConfig(BaseModel):
    """Configuration for output TXT.
    'OUTPUT' > 'TXT' in YAML.

    Attributes:
        ALBUM_COMPOSITION: Configuration for album composition TXT files.
    """

    ALBUM_COMPOSITION: AlbumCompositionFileConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class OutputConfig(BaseModel):
    """Output section of the configuration.
    'OUTPUT' in YAML.

    Attributes:
        CSV: Configuration for the output CSV files.
        TXT: Configuration for the output TXT files.
    """

    CSV: OutputCsvDictConfig
    TXT: OutputTxtDictConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class Config(BaseModel):
    """Main configuration object loaded from YAML.

    Attributes:
        INPUT: Input file configuration.
        PROCESS: Processing parameters configuration.
        OUTPUT: Output file configuration.
    """

    INPUT: InputConfig
    PROCESS: ProcessConfig
    OUTPUT: OutputConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @classmethod
    def from_yaml(cls, path: str | Path) -> 'Config':
        """Loads the configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Returns:
            Config: Parsed configuration object.
        """

        with open(path, 'r', encoding='utf-8') as fr:
            content = yaml.safe_load(fr)
        return cls(**content)


def __read_arg_config_path() -> Config:
    """Parses the configuration file path from command-line arguments and loads the config.

    Returns:
        Config: Loaded configuration object.

    Raises:
        SystemExit: If the config path is not provided or cannot be parsed.
    """

    logger = getLogger(__name__)

    if len(sys.argv) != 2:
        logger.error('This script needs a config file path as an arg.')
        sys.exit(1)
    config_path = Path(sys.argv[1])

    try:
        CONFIG: Final[Config] = Config.from_yaml(config_path)
    except Exception:
        logger.exception(f'Failed to parse the config file.: "{config_path}"')
        sys.exit(1)

    return CONFIG


def __parse_iphoto_album_data_xml():

    basicConfig(level=INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = getLogger(__name__)

    logger.info(f'"{os.path.basename(__file__)}" start!')

    CONFIG: Final[Config] = __read_arg_config_path()

    logger.info('Processing the "Master Image List" part in an XML...')
    try:
        iphoto_master_image_list = IphotoMasterImageList.from_xml(
            CONFIG.INPUT.TARGET_XML_KEY_INFO.MASTER_IMAGE_LIST
        )
        if CONFIG.PROCESS.FIELDS_FILTER:
            iphoto_master_image_list = iphoto_master_image_list.filter(
                CONFIG.PROCESS.FIELDS_FILTER.MASTER_IMAGE_LIST
            )
        iphoto_master_image_list.to_csv(CONFIG.OUTPUT.CSV.MASTER_IMAGE_LIST)
    except Exception:
        logger.exception('Failed to process the "Master Image List" part in an XML.')
        sys.exit(1)

    logger.info('Processing the "List of Albums" part in an XML...')
    try:
        iphoto_list_of_albums = IphotoListOfAlbums.from_xml(
            CONFIG.INPUT.TARGET_XML_KEY_INFO.LIST_OF_ALBUMS
        )
        if CONFIG.PROCESS.FIELDS_FILTER:
            iphoto_list_of_albums = iphoto_list_of_albums.filter(
                CONFIG.PROCESS.FIELDS_FILTER.LIST_OF_ALBUMS
            )
        iphoto_list_of_albums.to_csv(CONFIG.OUTPUT.CSV.LIST_OF_ALBUMS)
    except Exception:
        logger.exception('Failed to process the "List of Albums" part in an XML.')
        sys.exit(1)

    logger.info('Joining master images info to albums...')
    try:
        iphoto_list_of_albums_with_master_image_info = IphotoListOfAlbumsWithMasterImageInfo(
            iphoto_master_image_list,
            iphoto_list_of_albums,
            CONFIG.PROCESS.TARGET_FIELDS,
        )
        iphoto_list_of_albums_with_master_image_info.create_album_composition_txts(
            CONFIG.OUTPUT.TXT.ALBUM_COMPOSITION,
        )
    except Exception:
        logger.exception('Failed to join master images info to albums.')
        sys.exit(1)

    logger.info(f'"{os.path.basename(__file__)}" done!')


if __name__ == '__main__':
    __parse_iphoto_album_data_xml()
