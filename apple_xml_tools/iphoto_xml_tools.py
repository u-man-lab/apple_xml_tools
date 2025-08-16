import codecs
import re
from logging import getLogger
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    NewPath,
    NonNegativeInt,
    StrictBool,
    StrictStr,
    field_validator,
    model_validator,
)

from apple_xml_tools.apple_xml_tools import (
    AppleXML,
    AppleXMLDict,
    AppleXMLInteger,
    AppleXMLKey,
    AppleXMLString,
    ParsedPrimitiveTypes,
)


class AppleXMLKeyedPart(BaseModel):
    """Configuration for locating and extracting a specific XML part by key.

    Attributes:
        XML_PATH (FilePath): Path to the XML file.
        TARGET_DICT_XPATH_RELATIVE_FROM_ROOT_TAG (str):
            XPath to the target dictionary relative to the root tag.
        TARGET_KEY (str): The key within the dictionary whose value will be retrieved.
        TARGET_VALUE_TYPES (Any): Mapping or list specifying expected value types for validation.
    """

    XML_PATH: FilePath  # Must be existing file
    TARGET_DICT_XPATH_RELATIVE_FROM_ROOT_TAG: StrictStr
    TARGET_KEY: StrictStr
    TARGET_VALUE_TYPES: Any

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @field_validator('XML_PATH', mode='before')
    @classmethod
    def __convert_str_to_file_path_and_validate(cls, arg: str) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return Path(arg.strip())

    @field_validator('TARGET_VALUE_TYPES')
    @classmethod
    def __validate_target_value_types(cls, arg: Any):

        def check_is_str_recursively(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    check_is_str_recursively(value)
            elif isinstance(obj, list):
                for value in obj:
                    check_is_str_recursively(value)
            elif not isinstance(obj, str):
                raise TypeError(
                    f'The argument must be a string or list of it or dict of it, got "{arg}" [{type(arg)}].'
                )

        check_is_str_recursively(arg)
        return arg

    def get_value(self) -> AppleXML:
        """Retrieve the XML value element for the configured key.

        Returns:
            AppleXML: The XML element associated with the specified key.

        Raises:
            KeyError: If the target key is not found in the dictionary.
            ET.ParseError: If the XML file cannot be parsed.
            FileNotFoundError: If the file does not exist.
        """

        apple_xml = AppleXML.read_file(self.XML_PATH)

        target_xmldict_raw = apple_xml.find(self.TARGET_DICT_XPATH_RELATIVE_FROM_ROOT_TAG)

        target_xmldict = AppleXMLDict(target_xmldict_raw)
        target_xmlkey = AppleXMLKey.fromstr(self.TARGET_KEY)

        try:
            return target_xmldict[target_xmlkey]
        except KeyError as err:
            raise KeyError(target_xmlkey.get_text()) from err


class MasterImageListTargetFieldsConfig(BaseModel):
    """Configuration for target field names in the Master Image List.

    Attributes:
        IMAGE_PATH (str): Name of the field containing the image path.
        ORIGINAL_PATH (str): Name of the field containing the original image path.
    """

    IMAGE_PATH: StrictStr
    ORIGINAL_PATH: StrictStr

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class ListOfAlbumsTargetFieldsConfig(BaseModel):
    """Configuration for target field names in the List of Albums.

    Attributes:
        ALBUM_ID (str): Name of the field containing the album ID.
        ALBUM_TYPE (str): Name of the field containing the album type.
        ALBUM_NAME (str): Name of the field containing the album name.
        MASTER_IMAGE_KEY_LIST (str): Name of the field containing the list of master image keys.
    """

    ALBUM_ID: StrictStr
    ALBUM_TYPE: StrictStr
    ALBUM_NAME: StrictStr
    MASTER_IMAGE_KEY_LIST: StrictStr

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class TargetFieldsConfig(BaseModel):
    """Container for field configurations for both Master Image List and List of Albums.

    Attributes:
        MASTER_IMAGE_LIST (MasterImageListTargetFieldsConfig): Config for Master Image List fields.
        LIST_OF_ALBUMS (ListOfAlbumsTargetFieldsConfig): Config for List of Albums fields.
    """

    MASTER_IMAGE_LIST: MasterImageListTargetFieldsConfig
    LIST_OF_ALBUMS: ListOfAlbumsTargetFieldsConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class FieldsFilter(BaseModel):
    """Represents filtering rules for DataFrame fields.

    Attributes:
        INCLUDE (dict[str, list[str | None]] | None): Values to include by field name.
        EXCLUDE (dict[str, list[str | None]] | None): Values to exclude by field name.
    """

    INCLUDE: dict[StrictStr, list[StrictStr | None]] | None = None
    EXCLUDE: dict[StrictStr, list[StrictStr | None]] | None = None

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    def apply_on_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the include and/or exclude filters to a DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to filter.

        Returns:
            pd.DataFrame: A filtered copy of the input DataFrame.
        """

        if not self.INCLUDE and not self.EXCLUDE:
            return df.copy()

        and_bool_series = pd.Series([True for _ in range(df.shape[0])], index=df.index)

        for is_INCLUDE, input_dict in ((True, self.INCLUDE), (False, self.EXCLUDE)):

            if input_dict is None:
                continue

            for key_str, values_list in input_dict.items():
                or_bool_series = pd.Series([False for _ in range(df.shape[0])], index=df.index)
                for value_str in values_list:
                    xmlkey = AppleXMLKey.fromstr(key_str)
                    if value_str is None:
                        if is_INCLUDE:
                            # True if the value is missing(np.nan).
                            or_bool_series |= df[xmlkey].apply(lambda x: x != x)
                        else:
                            # True if the value is not missing(np.nan).
                            or_bool_series |= df[xmlkey].apply(lambda x: x == x)
                    else:
                        if is_INCLUDE:
                            # True if the value matches and is not missing(np.nan).
                            or_bool_series |= df[xmlkey].apply(
                                lambda x: x.get_text() == value_str if x == x else False
                            )
                        else:
                            # True if the value does not match or is missing(np.nan).
                            or_bool_series |= df[xmlkey].apply(
                                lambda x: x.get_text() != value_str if x == x else True
                            )
                and_bool_series &= or_bool_series

        return df.loc[and_bool_series].copy()


class OutputCsvConfig(BaseModel):
    """Configuration for CSV output.

    Attributes:
        GENERATE (bool): Whether to generate the CSV.
        FILE_PATH (Path | None): Path to output file. Required if GENERATE is True.
        ENCODING (str | None): File encoding. Required if GENERATE is True.
        LIST_AND_DICT_DELIMITER (str | None):
            Delimiter for joining list/dict values. Required if GENERATE is True.
    """

    GENERATE: StrictBool
    FILE_PATH: NewPath | None = None  # None is set only when GENERATE is False.
    # NewPath: Must not exist & parent must exist
    ENCODING: StrictStr | None = None  # None is set only when GENERATE is False.
    LIST_AND_DICT_DELIMITER: StrictStr | None = Field(
        None, min_length=1, max_length=1
    )  # None is set only when GENERATE is False.

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @model_validator(mode='before')
    @classmethod
    def __skip_validations_if_generate_not_true(cls, values: dict) -> dict:
        if 'GENERATE' not in values:
            raise KeyError('"GENERATE" field is required.')

        if not isinstance(values['GENERATE'], bool) or not values['GENERATE']:
            return {'GENERATE': values['GENERATE']}  # the others: default None & skip validators

        for field in ('FILE_PATH', 'ENCODING'):
            if field not in values:
                raise KeyError(f'"{field}" field is required when "GENERATE" is true.')

        return values

    @field_validator('FILE_PATH', mode='before')
    @classmethod
    def __convert_str_to_file_path_and_validate(cls, arg: Any) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        path = Path(arg.strip())
        return path

    @field_validator('ENCODING')
    @classmethod
    def __validate_encoding_str(cls, arg: str | None) -> str:
        if arg is None:  # for when the field is blank
            raise ValueError('"None" is not supported as an encoding type.')
        try:
            codecs.lookup(arg)
        except LookupError as err:
            raise ValueError(f'"{arg}" is not supported as an encoding type.') from err
        return arg

    @field_validator('LIST_AND_DICT_DELIMITER')
    @classmethod
    def __validate_delimiter(cls, arg: str | None) -> str:
        if arg is None:  # for when the field is blank
            raise ValueError('"None" is not supported as a delimiter.')
        return arg


class IphotoMasterImage:
    """Represents a single master image entry from the Master Image List.

    Provides dictionary-like access to image information.
    """

    def __init__(self, image_info: dict):
        self.__image_info = image_info

    def __getitem__(self, key, /):
        return self.__image_info.__getitem__(key)


class IphotoMasterImageList:
    """Represents a list of master images.

    Wraps a DataFrame where each row corresponds to an image entry keyed by AppleXMLKey.
    """

    def __init__(self, df: pd.DataFrame):
        self.__iphoto_master_image_list_df = df

    def __getitem__(self, key: Any, /) -> IphotoMasterImage:
        row_dict = self.__iphoto_master_image_list_df.loc[key].to_dict()
        return IphotoMasterImage(row_dict)

    def __contains__(self, key: Any) -> bool:
        return key in self.__iphoto_master_image_list_df.index

    def filter(self, fields_filter: FieldsFilter | None) -> 'IphotoMasterImageList':
        """Filter the list using a FieldsFilter.

        Args:
            fields_filter (FieldsFilter | None): Filter rules to apply.

        Returns:
            IphotoMasterImageList: A filtered list. If fields_filter is None, returns self.
        """

        if fields_filter is None:
            return self

        filtered_df = fields_filter.apply_on_dataframe(self.__iphoto_master_image_list_df)
        return self.__class__(filtered_df)

    def to_csv(self, config: OutputCsvConfig):
        """Write the master image list to a CSV file based on configuration.

        Args:
            config (OutputCsvConfig): Output configuration.

        Notes:
            If GENERATE is False, no file is written.
        """

        if not config.GENERATE:
            return
        get_text = lambda x: ParsedPrimitiveTypes(x).get_text(config.LIST_AND_DICT_DELIMITER)
        iphoto_master_image_list_df = self.__iphoto_master_image_list_df.copy()
        iphoto_master_image_list_df.columns = iphoto_master_image_list_df.columns.map(get_text)
        iphoto_master_image_list_df.index = iphoto_master_image_list_df.index.map(get_text)
        iphoto_master_image_list_df = iphoto_master_image_list_df.map(get_text)
        getLogger(__name__).info(f'Writing CSV file "{config.FILE_PATH}"...')
        iphoto_master_image_list_df.to_csv(config.FILE_PATH, encoding=config.ENCODING)

    @classmethod
    def from_xml(cls, config: AppleXMLKeyedPart) -> 'IphotoMasterImageList':
        """Create an instance from an AppleXMLKeyedPart configuration.

        Args:
            config (AppleXMLKeyedPart): Config specifying the XML location and structure.

        Returns:
            IphotoMasterImageList: Loaded list of master images.

        Raises:
            ValueError: If the parsed XML is not a dict of dicts.
            TypeError: If validation fails against TARGET_VALUE_TYPES.
        """

        target_xml_part = config.get_value()
        iphoto_master_image_list = target_xml_part.parse_into_primitive_types()
        ParsedPrimitiveTypes(iphoto_master_image_list).validate(config.TARGET_VALUE_TYPES)

        if not isinstance(iphoto_master_image_list, dict):
            raise ValueError(
                '"MASTER_IMAGE_LIST" > "TARGET_VALUE_TYPES" should be a dict, '
                + f'but "{type(iphoto_master_image_list)}".'
            )
        elif not isinstance(list(iphoto_master_image_list.values())[0], dict):
            raise ValueError(
                '"MASTER_IMAGE_LIST" > "TARGET_VALUE_TYPES" should be a dict of a dict, '
                + f'but a dict of "{type(list(iphoto_master_image_list.values())[0])}".'
            )

        transposed_df = pd.DataFrame(iphoto_master_image_list).T
        return cls(transposed_df)


class IphotoAlbum:
    """Represents a single album entry from the List of Albums.

    Provides dictionary-like access to album information.
    """

    def __init__(self, album_info: dict):
        self.__album_info = album_info

    def __getitem__(self, key: Any, /) -> Any:
        return self.__album_info.__getitem__(key)


class IphotoListOfAlbums:
    """Represents a list of albums.

    Wraps a DataFrame where each row corresponds to an album.
    """

    def __init__(self, df: pd.DataFrame):
        self.__iphoto_list_of_albums_df = df

    def __iter__(self) -> Iterator[IphotoAlbum]:
        return (
            IphotoAlbum(row_dict)
            for row_dict in self.__iphoto_list_of_albums_df.to_dict(orient='records')
        )

    def filter(self, fields_filter: FieldsFilter | None) -> 'IphotoListOfAlbums':
        """Filter the list using a FieldsFilter.

        Args:
            fields_filter (FieldsFilter | None): Filter rules to apply.

        Returns:
            IphotoListOfAlbums: A filtered list. If fields_filter is None, returns self.
        """

        if fields_filter is None:
            return self

        filtered_df = fields_filter.apply_on_dataframe(self.__iphoto_list_of_albums_df)
        return self.__class__(filtered_df)

    def to_csv(self, config: OutputCsvConfig):
        """Write the list of albums to a CSV file based on configuration.

        Args:
            config (OutputCsvConfig): Output configuration.

        Notes:
            If GENERATE is False, no file is written.
        """

        if not config.GENERATE:
            return
        get_text = lambda x: ParsedPrimitiveTypes(x).get_text(config.LIST_AND_DICT_DELIMITER)
        iphoto_list_of_albums_df = self.__iphoto_list_of_albums_df.copy()
        iphoto_list_of_albums_df.columns = iphoto_list_of_albums_df.columns.map(get_text)
        iphoto_list_of_albums_df = iphoto_list_of_albums_df.map(get_text)
        getLogger(__name__).info(f'Writing CSV file "{config.FILE_PATH}"...')
        iphoto_list_of_albums_df.to_csv(config.FILE_PATH, encoding=config.ENCODING, index=False)

    @classmethod
    def from_xml(cls, config: AppleXMLKeyedPart) -> 'IphotoListOfAlbums':
        """Create an instance from an AppleXMLKeyedPart configuration.

        Args:
            config (AppleXMLKeyedPart): Config specifying the XML location and structure.

        Returns:
            IphotoListOfAlbums: Loaded list of albums.

        Raises:
            ValueError: If the parsed XML is not a list of dicts.
            TypeError: If validation fails against TARGET_VALUE_TYPES.
        """

        target_xml_part = config.get_value()
        iphoto_list_of_albums = target_xml_part.parse_into_primitive_types()
        ParsedPrimitiveTypes(iphoto_list_of_albums).validate(config.TARGET_VALUE_TYPES)

        if not isinstance(iphoto_list_of_albums, list):
            raise ValueError(
                '"LIST_OF_ALBUMS" > "TARGET_VALUE_TYPES" should be a list, '
                + f'but "{type(iphoto_list_of_albums)}".'
            )
        elif not isinstance(iphoto_list_of_albums[0], dict):
            raise ValueError(
                '"LIST_OF_ALBUMS" > "TARGET_VALUE_TYPES" should be a list of a dict, '
                + f'but a list of "{type(iphoto_list_of_albums[0])}".'
            )

        return cls(pd.DataFrame(iphoto_list_of_albums))


class CharsToEscapeInPath:
    """Utility for defining characters that must be escaped in file paths."""

    __CHARS = r'"<>:/\|?*'

    def __new__(cls, *args, **kwargs):
        raise AttributeError('An instance cannot be generate from this class.')

    def __init__(self, *args, **kwargs):
        raise AttributeError('An instance cannot be generate from this class.')

    @classmethod
    def get_match_char_regex(cls) -> str:
        """Return a regex pattern that matches characters to be escaped.

        Returns:
            str: Regex pattern string.
        """

        return fr'[{re.escape(cls.__CHARS)}]'

    @classmethod
    def get_unmatch_char_regex(cls) -> str:
        """Return a regex pattern that matches any character not in the escape list.

        Returns:
            str: Regex pattern string.
        """

        return fr'[^{re.escape(cls.__CHARS)}]'


class AlbumCompositionFileNameConfig(BaseModel):
    """Configuration for generating album composition TXT file names.

    Attributes:
        ALBUM_ID_ZERO_PADDING_LENGETH (int): Length to zero-pad album IDs.
        CHAR_TO_JOIN_VALUES (str): Character to join album ID, type, and name.
        ALBUM_NAME_ESCAPE_CHAR (str): Character to replace disallowed characters in album names.
    """

    ALBUM_ID_ZERO_PADDING_LENGETH: NonNegativeInt
    CHAR_TO_JOIN_VALUES: StrictStr = Field(
        min_length=1, max_length=1, pattern=CharsToEscapeInPath.get_unmatch_char_regex()
    )
    ALBUM_NAME_ESCAPE_CHAR: StrictStr = Field(
        min_length=1, max_length=1, pattern=CharsToEscapeInPath.get_unmatch_char_regex()
    )

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    def generate_txt_file_name(
        self,
        album_id_xmlinteger: AppleXMLInteger,
        album_type_xmlstring: AppleXMLString,
        album_name_xmlstring: AppleXMLString,
        re_char_to_escape_in_path: re.Pattern,
    ) -> str:
        """Generate a valid TXT file name for an album composition.

        Args:
            album_id_xmlinteger (AppleXMLInteger): Album ID.
            album_type_xmlstring (AppleXMLString): Album type.
            album_name_xmlstring (AppleXMLString): Album name.
            re_char_to_escape_in_path (Pattern): Regex to match invalid path characters.

        Returns:
            str: Generated TXT file name including extension.
        """

        album_id_str = album_id_xmlinteger.get_text()
        album_id_zfilled_str = album_id_str.zfill(self.ALBUM_ID_ZERO_PADDING_LENGETH)

        escaped_album_name_str = re_char_to_escape_in_path.sub(
            self.ALBUM_NAME_ESCAPE_CHAR,
            album_name_xmlstring.get_text(),
        )

        basename_without_ext = self.CHAR_TO_JOIN_VALUES.join(
            (album_id_zfilled_str, album_type_xmlstring.get_text(), escaped_album_name_str)
        )
        return f'{basename_without_ext}.txt'


class AlbumCompositionFileConfig(BaseModel):
    """Configuration for generating album composition TXT files.

    Attributes:
        GENERATE (bool): Whether to generate TXT files.
        DIR_PATH (Path | None): Directory where TXT files will be saved.
        ENCODING (str | None): Encoding for TXT files.
        NAME_CONFIG (AlbumCompositionFileNameConfig | None): Config for generating file names.
    """

    GENERATE: StrictBool
    DIR_PATH: Path | None = None  # None is set only when GENERATE is False.
    ENCODING: StrictStr | None = None  # None is set only when GENERATE is False.
    NAME_CONFIG: AlbumCompositionFileNameConfig | None = (
        None  # None is set only when GENERATE is False.
    )

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @model_validator(mode='before')
    @classmethod
    def __skip_validations_if_generate_not_true(cls, values: dict) -> dict:
        if 'GENERATE' not in values:
            raise KeyError('"GENERATE" field is required.')

        if not isinstance(values['GENERATE'], bool) or not values['GENERATE']:
            return {'GENERATE': values['GENERATE']}  # the others: default None & skip validators

        for field in ('DIR_PATH', 'ENCODING', 'NAME_CONFIG'):
            if field not in values:
                raise KeyError(f'"{field}" field is required when "GENERATE" is true.')

        return values

    @field_validator('DIR_PATH', mode='before')
    @classmethod
    def __convert_str_to_dir_path_and_validate(cls, arg: Any) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')

        path = Path(arg.strip())

        if not path.is_dir():
            raise FileNotFoundError(
                f'A directory of the argument path is not found on the server.: "{path}"'
            )
        if any(file_path.suffix == '.txt' for file_path in path.iterdir()):
            raise FileExistsError(f'Txt files already exist in the directory "{path}".')

        return path

    @field_validator('ENCODING')
    @classmethod
    def __validate_encoding_str(cls, arg: str | None) -> str:
        if arg is None:  # for when the field is blank
            raise ValueError('"None" is not supported as an encoding type.')
        try:
            codecs.lookup(arg)
        except LookupError as err:
            raise ValueError(f'"{arg}" is not supported as an encoding type.') from err
        return arg

    @field_validator('NAME_CONFIG')
    @classmethod
    def __validate_txt_file_name_generate_config(
        cls, arg: AlbumCompositionFileNameConfig | None
    ) -> AlbumCompositionFileNameConfig:
        if arg is None:  # for when the field is blank
            raise ValueError('"None" is not supported as a delimiter.')
        return arg


class IphotoListOfAlbumsWithMasterImageInfo:
    """Combines album and master image information to generate album composition files."""

    def __init__(
        self,
        iphoto_master_image_list: IphotoMasterImageList,
        iphoto_list_of_albums: IphotoListOfAlbums,
        target_fields_config: TargetFieldsConfig,
    ):
        self.__iphoto_master_image_list = iphoto_master_image_list
        self.__iphoto_list_of_albums = iphoto_list_of_albums
        self.__target_fields_config = target_fields_config
        self.__logger = getLogger(__name__)

    @staticmethod
    def __get_value_by_field_name(_object, field_name: str) -> Any:
        field_name_xmlkey = AppleXMLKey.fromstr(field_name)
        try:
            value = _object[field_name_xmlkey]
        except KeyError as err:
            raise KeyError(field_name) from err
        return value

    def create_album_composition_txts(self, config: AlbumCompositionFileConfig):
        """Generate TXT files listing image paths for each album.

        Args:
            config (AlbumCompositionFileConfig): Output configuration.

        Notes:
            If GENERATE is False, no files are created.
        """

        if not config.GENERATE:
            return

        RE_CHAR_TO_ESCAPE_IN_PATH = re.compile(CharsToEscapeInPath.get_match_char_regex())

        for album in self.__iphoto_list_of_albums:

            image_key_xmlstring_list: list[AppleXMLKey] = self.__get_value_by_field_name(
                album, self.__target_fields_config.LIST_OF_ALBUMS.MASTER_IMAGE_KEY_LIST
            )

            image_path_str_list = []
            for image_key_xmlstring in image_key_xmlstring_list:

                image_key_str = image_key_xmlstring.get_text()
                image_key_xmlkey = AppleXMLKey.fromstr(image_key_str)

                if image_key_xmlkey not in self.__iphoto_master_image_list:
                    dummy_image_path_str = (
                        f'Key "{image_key_str}" is not found in the Master Image List.'
                    )
                    self.__logger.warning(dummy_image_path_str)
                    image_path_str_list.append(dummy_image_path_str)
                    continue
                master_image = self.__iphoto_master_image_list[image_key_xmlkey]

                image_path_xmlstring: AppleXMLString = self.__get_value_by_field_name(
                    master_image, self.__target_fields_config.MASTER_IMAGE_LIST.IMAGE_PATH
                )
                original_path_xmlstring: AppleXMLString = self.__get_value_by_field_name(
                    master_image, self.__target_fields_config.MASTER_IMAGE_LIST.ORIGINAL_PATH
                )

                # Always write Masters path (not Previews path)
                if (
                    original_path_xmlstring == original_path_xmlstring
                    and original_path_xmlstring.get_text() != ''
                ):
                    image_path_str_list.append(original_path_xmlstring.get_text())
                else:
                    image_path_str_list.append(image_path_xmlstring.get_text())

            (
                album_id_xmlinteger,
                album_type_xmlstring,
                album_name_xmlstring,
            ) = [
                self.__get_value_by_field_name(album, target_field)
                for target_field in (
                    self.__target_fields_config.LIST_OF_ALBUMS.ALBUM_ID,
                    self.__target_fields_config.LIST_OF_ALBUMS.ALBUM_TYPE,
                    self.__target_fields_config.LIST_OF_ALBUMS.ALBUM_NAME,
                )
            ]

            txt_file_name = config.NAME_CONFIG.generate_txt_file_name(
                album_id_xmlinteger,
                album_type_xmlstring,
                album_name_xmlstring,
                RE_CHAR_TO_ESCAPE_IN_PATH,
            )
            txt_file_path = config.DIR_PATH / Path(txt_file_name)

            txt_file_content = '\n'.join(image_path_str_list)
            self.__logger.info(f'Writing TXT file "{txt_file_path}"...')
            with open(txt_file_path, 'w', encoding=config.ENCODING) as fw:
                fw.write(txt_file_content)
