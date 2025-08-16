from __future__ import annotations

import unicodedata
import xml.etree.ElementTree as ET
from abc import ABCMeta, abstractmethod
from logging import getLogger
from pathlib import Path
from typing import Any, Iterator, Self


class AppleXML:
    """Represents an Apple XML document or element.

    This class wraps an ElementTree element from an Apple-specific XML format
    and provides methods for reading, parsing, and converting it into
    corresponding Python objects.

    Instances cannot be created directly; use `read_file()` or `fromstring()`.
    """

    __et_element: ET.Element

    def __new__(cls, *args, **kwargs):
        raise AttributeError('The constructor of this class is private.')

    def __init__(self, *args, **kwargs):
        raise AttributeError('The constructor of this class is private.')

    @classmethod
    def __private_constructor(cls, et_element: ET.Element) -> Self:
        self = super().__new__(cls)
        self.__et_element = et_element
        return self

    @classmethod
    def read_file(cls, apple_xml_path: str | Path) -> AppleXML:
        """Read an Apple XML file.

        Args:
            apple_xml_path (str | Path): Path to the XML file.

        Returns:
            AppleXML: A new AppleXML instance containing the root element.

        Raises:
            ET.ParseError: If the XML file cannot be parsed.
            FileNotFoundError: If the file does not exist.
        """

        getLogger(__name__).info(f'Reading XML file "{apple_xml_path}"...')
        tree = ET.parse(apple_xml_path)
        element_root = tree.getroot()
        return cls.__private_constructor(element_root)

    @classmethod
    def fromstring(cls, text: str, parser: ET.XMLParser | None = None) -> AppleXML:
        """Parse an Apple XML string into an AppleXML instance.

        Args:
            text (str): XML content as a string.
            parser (xml.etree.ElementTree.XMLParser, optional): Optional XML parser.

        Returns:
            AppleXML: Parsed AppleXML object.
        """

        return cls.__private_constructor(ET.fromstring(text, parser))

    def __getitem__(self, key, /):
        return self.__class__.__private_constructor(self.__et_element.__getitem__(key))

    def __iter__(self) -> Iterator[AppleXML]:
        return (self.__class__.__private_constructor(child) for child in iter(self.__et_element))

    def get_tag(self) -> str:
        """Get the tag name of the XML element.

        Returns:
            str: The tag name.
        """

        return self.__et_element.tag

    def get_text(self) -> str | None:
        """Get the text content of the XML element.

        Returns:
            str | None: Text value if present, otherwise None.
        """

        return self.__et_element.text

    def find(self, path: str, namespaces: dict[str, str] | None = None) -> AppleXML | None:
        """Find the first matching subelement.

        Args:
            path (str): XPath-like search path.
            namespaces (dict[str, str], optional): Namespace mapping.

        Returns:
            AppleXML | None: Matching element wrapped in AppleXML, or None if not found.
        """

        found = self.__et_element.find(path, namespaces)
        if found is None:
            return None
        return self.__class__.__private_constructor(found)

    def parse_into_primitive_types(
        self,
    ) -> dict | list | AppleXMLInteger | AppleXMLReal | AppleXMLString | AppleXMLBool:
        """Recursively parse XML into AppleXML primitive type objects or Python collections.

        Returns:
            dict | list | AppleXMLInteger | AppleXMLReal | AppleXMLString | AppleXMLBool:
                The parsed structure.

        Raises:
            ValueError: If the XML tag is not supported.
        """

        def __parse_into_primitive_types(
            apple_xml: AppleXML,
        ) -> dict | list | AppleXMLInteger | AppleXMLReal | AppleXMLString | AppleXMLBool:
            tag = apple_xml.get_tag()

            if tag == AppleXMLDict.get_tag():
                xmldict = AppleXMLDict(apple_xml)
                return {
                    xmlkey: __parse_into_primitive_types(value_xml)
                    for xmlkey, value_xml in xmldict.items()
                }

            if tag == AppleXMLArray.get_tag():
                xmlarray = AppleXMLArray(apple_xml)
                return [__parse_into_primitive_types(value_xml) for value_xml in xmlarray]

            if tag == AppleXMLInteger.get_tag():
                return AppleXMLInteger(apple_xml)
            if tag == AppleXMLReal.get_tag():
                return AppleXMLReal(apple_xml)
            if tag == AppleXMLString.get_tag():
                return AppleXMLString(apple_xml)
            if tag in AppleXMLBool.get_tags():
                return AppleXMLBool(apple_xml)

            raise ValueError(f'Apple XML tag "{tag}" is not supported.')

        return __parse_into_primitive_types(self)


class AppleXMLArray:
    """Represents an Apple XML array (<array> tag).

    Provides list-like access to its child AppleXML elements.
    """

    __TAG = 'array'

    DELIMITER_TO_TEXT = '|'

    def __init__(self, apple_xml: AppleXML):
        if not isinstance(apple_xml, AppleXML):
            raise TypeError(f'The argument is not AppleXML object, got {type(apple_xml)}.')
        tag = apple_xml.get_tag()
        if tag != self.__TAG:
            raise ValueError(
                f'The argument is not Apple original xml tag "{self.__TAG}", but "{tag}".'
            )
        self.__apple_xml_tuple = tuple(child_xml for child_xml in apple_xml)

    def __getitem__(self, key):
        return self.__apple_xml_tuple.__getitem__(key)

    def __len__(self) -> int:
        return self.__apple_xml_tuple.__len__()

    def __iter__(self) -> Iterator[AppleXML]:
        return iter(self.__apple_xml_tuple)

    @classmethod
    def get_tag(cls) -> str:
        return cls.__TAG


class AppleXMLPrimitiveType(metaclass=ABCMeta):
    """Abstract base class for Apple XML primitive types.

    All Apple XML primitive types must implement `get_text()`.
    """

    @abstractmethod
    def get_text(self):
        raise NotImplementedError


class AppleXMLKey(AppleXMLPrimitiveType):
    """Represents an Apple XML <key> element."""

    __TAG = 'key'

    def __init__(self, apple_xml: AppleXML):
        if not isinstance(apple_xml, AppleXML):
            raise TypeError(f'The argument is not AppleXML object, got {type(apple_xml)}.')
        self.__apple_xml = apple_xml
        tag = self.__apple_xml.get_tag()
        if tag != self.__TAG:
            raise ValueError(
                f'The argument is not Apple original xml tag "{self.__TAG}", but "{tag}".'
            )

    def __eq__(self, other) -> bool:
        if not isinstance(other, AppleXMLKey):
            return NotImplemented
        return self.__apple_xml.get_text() == other.__apple_xml.get_text()

    def __hash__(self) -> int:
        return hash(self.__apple_xml.get_text())

    @classmethod
    def fromstr(cls, text: str) -> AppleXMLKey:
        """Create an AppleXMLKey from a plain string.

        Args:
            text (str): Key text.

        Returns:
            AppleXMLKey: The created key object.
        """

        if not isinstance(text, str):
            raise TypeError(f'The argument is not str object, got "{text}" [{type(text)}].')
        tagged_text = f'<{cls.__TAG}>{text}</{cls.__TAG}>'
        apple_xml = AppleXML.fromstring(tagged_text)
        return cls(apple_xml)

    def get_text(self) -> str | None:
        return self.__apple_xml.get_text()

    @classmethod
    def get_tag(cls) -> str:
        return cls.__TAG


class AppleXMLDict:
    """Represents an Apple XML dictionary (<dict> tag).

    Provides dictionary-like access to AppleXML elements keyed by AppleXMLKey.
    """

    __TAG = 'dict'

    def __init__(self, apple_xml: AppleXML):
        if not isinstance(apple_xml, AppleXML):
            raise TypeError(f'The argument is not AppleXML object, got {type(apple_xml)}.')
        tag = apple_xml.get_tag()
        if tag != self.__TAG:
            raise ValueError(
                f'The argument is not Apple original xml tag "{self.__TAG}", but "{tag}".'
            )

        working_dict = {}
        key_xml = None
        for child_xml in apple_xml:
            # After a tag 'key' is found, the next element is it's value.
            if child_xml.get_tag() == 'key':
                key_xml = AppleXMLKey(child_xml)
                if key_xml in working_dict:
                    raise ValueError(
                        f'Apple original xml tag "dict" is broken.: A key "{key_xml.get_text()}" is duplicated.'
                    )
            elif key_xml is not None:
                working_dict[key_xml] = child_xml
                key_xml = None

        self.__value = working_dict.copy()

    def __getitem__(self, key: AppleXMLKey) -> AppleXML:
        if not isinstance(key, AppleXMLKey):
            raise TypeError(f'The type of key must be "AppleXMLKey", got "{key}" [{type(key)}].')

        return self.__value.__getitem__(key)

    def __iter__(self):
        return iter(self.__value)

    def keys(self):
        """Get the keys of the dictionary.

        Returns:
            tuple[AppleXMLKey]: Tuple of keys.
        """

        return tuple(self.__value.copy().keys())

    def items(self):
        """Get the dictionary items.

        Returns:
            tuple[tuple[AppleXMLKey, AppleXML]]: Tuple of key-value pairs.
        """

        return tuple(self.__value.copy().items())

    def get(self, key: AppleXMLKey, default: None = None, /):
        """Get the value associated with a key.

        Args:
            key (AppleXMLKey): The dictionary key.
            default (None, optional): Default if key not found.

        Returns:
            AppleXML | None: The corresponding value or default.
        """

        if not isinstance(key, AppleXMLKey):
            raise TypeError(f'The type of key must be "AppleXMLKey", got "{key}" [{type(key)}].')
        return self.__value.copy().get(key, default)

    @classmethod
    def get_tag(cls) -> str:
        return cls.__TAG


class AppleXMLInteger(AppleXMLPrimitiveType):
    """Represents an Apple XML <integer> element."""

    __TAG = 'integer'

    def __init__(self, apple_xml: AppleXML):
        if not isinstance(apple_xml, AppleXML):
            raise TypeError(
                f'The argument is not AppleXML object, got "{apple_xml}" [{type(apple_xml)}].'
            )
        tag = apple_xml.get_tag()
        if tag != self.__TAG:
            raise ValueError(
                f'The argument is not Apple original xml tag "{self.__TAG}", but "{tag}".'
            )
        self.__text = apple_xml.get_text()

    def get_text(self) -> str | None:
        return self.__text

    @classmethod
    def get_tag(cls) -> str:
        return cls.__TAG


class AppleXMLReal(AppleXMLPrimitiveType):
    """Represents an Apple XML <real> element."""

    __TAG = 'real'

    def __init__(self, apple_xml: AppleXML):
        if not isinstance(apple_xml, AppleXML):
            raise TypeError(
                f'The argument is not AppleXML object, got "{apple_xml}" [{type(apple_xml)}].'
            )
        tag = apple_xml.get_tag()
        if tag != self.__TAG:
            raise ValueError(
                f'The argument is not Apple original xml tag "{self.__TAG}", but "{tag}".'
            )
        self.__text = apple_xml.get_text()

    def get_text(self) -> str | None:
        return self.__text

    @classmethod
    def get_tag(cls) -> str:
        return cls.__TAG


class Diacritics:
    """Utility class for working with Unicode combining characters."""

    # Connect all Unicode combining characters (characters with non-zero canonical
    # concatenation class) as a string
    __ALL_COMBINING_CHARS = ''.join(
        chr(cp) for cp in range(0x110000) if unicodedata.combining(chr(cp)) != 0
    )

    @classmethod
    def replace_combining_chars_to_precomposed(cls, text: str) -> str:
        """Replace combining characters with precomposed Unicode characters.

        Args:
            text (str): Input text.

        Returns:
            str: Text with precomposed characters.
        """

        if not isinstance(text, str):
            raise TypeError(f'The argument is not str object, got "{text}" [{type(text)}].')

        new_text_as_chars: list[str] = []
        for char in text:
            if char in cls.__ALL_COMBINING_CHARS and new_text_as_chars:
                # Line up the base character with the combining character
                chars_to_compose = new_text_as_chars.pop() + char
                # Obtain the corresponding precomposed character
                new_char = unicodedata.normalize('NFC', chars_to_compose)
                new_text_as_chars.append(new_char)
            else:
                new_text_as_chars.append(char)

        return ''.join(new_text_as_chars)


class AppleXMLString(AppleXMLPrimitiveType):
    """Represents an Apple XML <string> element."""

    __TAG = 'string'

    def __init__(self, apple_xml: AppleXML):
        if not isinstance(apple_xml, AppleXML):
            raise TypeError(
                f'The argument is not AppleXML object, got "{apple_xml}" [{type(apple_xml)}].'
            )
        tag = apple_xml.get_tag()
        if tag != self.__TAG:
            raise ValueError(
                f'The argument is not Apple original xml tag "{self.__TAG}", but "{tag}".'
            )
        self.__text = apple_xml.get_text()

    def __eq__(self, other) -> bool:
        if not isinstance(other, AppleXMLString):
            return NotImplemented
        return self.__text == other.__text

    def __hash__(self) -> int:
        return hash(self.__text)

    def get_text(self) -> str | None:
        if self.__text is None:
            return None
        # Precomposed chars are splitted, so have to be combined.
        text_normalized = Diacritics.replace_combining_chars_to_precomposed(self.__text)
        return text_normalized

    @classmethod
    def get_tag(cls) -> str:
        return cls.__TAG


class AppleXMLBool(AppleXMLPrimitiveType):
    """Represents an Apple XML boolean element (<true> or <false>)."""

    __TAGS = ('true', 'false')

    def __init__(self, apple_xml: AppleXML):
        if not isinstance(apple_xml, AppleXML):
            raise TypeError(
                f'The argument is not AppleXML object, got "{apple_xml}" [{type(apple_xml)}].'
            )
        tag = apple_xml.get_tag()
        if tag not in self.__TAGS:
            raise ValueError(
                f'The argument is not Apple original xml tag "true" nor "false", but "{tag}".'
            )
        self.__text = tag

    def get_text(self) -> str | None:
        return self.__text

    @classmethod
    def get_tags(cls) -> tuple[str, ...]:
        """Get the tag names of the XML boolean element.

        Returns:
            tuple[str, ...]: The tag names of the XML boolean element.
        """
        return cls.__TAGS


class ParsedPrimitiveTypes:
    """Wrapper around parsed Apple XML primitive types.

    Provides methods to validate and extract text from parsed structures.
    """

    def __init__(self, parsed_primitive_types: Any):
        self.__parsed_primitive_types = parsed_primitive_types

    def validate(self, types_mapping: Any):
        """Validate the parsed data structure against a type mapping.

        Args:
            types_mapping (Any): Mapping specifying expected types.

        Raises:
            TypeError: If structure or type does not match expectations.
            ValueError: If mapping contains unsupported values.
        """

        def __validate(parsed_primitive_types: Any, types_mapping_part: Any):

            if isinstance(types_mapping_part, dict):
                if not isinstance(parsed_primitive_types, dict):
                    raise TypeError(f'It is "{type(parsed_primitive_types)}" type not a "dict".')

                for key, types_mapping_part_part in types_mapping_part.items():
                    xmlkey = AppleXMLKey.fromstr(key)
                    if xmlkey not in parsed_primitive_types:
                        continue
                    parsed_primitive_types_part = parsed_primitive_types[xmlkey]
                    __validate(parsed_primitive_types_part, types_mapping_part_part)

            elif isinstance(types_mapping_part, list):
                if len(types_mapping_part) != 1:
                    raise ValueError(
                        f'A list in the mapping arg must have only 1 object, but {len(types_mapping_part)}.'
                    )
                types_mapping_part_part = types_mapping_part[0]

                if isinstance(parsed_primitive_types, dict):
                    parsed_primitive_types_values = list(parsed_primitive_types.values())
                elif isinstance(parsed_primitive_types, list):
                    parsed_primitive_types_values = parsed_primitive_types
                else:
                    raise TypeError(
                        f'It is "{type(parsed_primitive_types)}" type not a "list", nor a "dict".'
                    )

                for parsed_primitive_types_part in parsed_primitive_types_values:
                    __validate(parsed_primitive_types_part, types_mapping_part_part)

            elif types_mapping_part == AppleXMLInteger.get_tag():
                if not isinstance(parsed_primitive_types, AppleXMLInteger):
                    raise TypeError(
                        f'It is "{type(parsed_primitive_types)}" type not an "integer".'
                    )
            elif types_mapping_part == AppleXMLReal.get_tag():
                if not isinstance(parsed_primitive_types, AppleXMLReal):
                    raise TypeError(f'It is "{type(parsed_primitive_types)}" type not a "real".')
            elif types_mapping_part == AppleXMLString.get_tag():
                if not isinstance(parsed_primitive_types, AppleXMLString):
                    raise TypeError(f'It is "{type(parsed_primitive_types)}" type not a "string".')
            elif types_mapping_part in AppleXMLBool.get_tags():
                if not isinstance(parsed_primitive_types, AppleXMLBool):
                    raise TypeError(f'It is "{type(parsed_primitive_types)}" type not a "bool".')

            elif isinstance(types_mapping_part, str):
                raise ValueError(f'Value "{types_mapping_part}" in the mapping is not supported.')

            else:
                raise TypeError(
                    f'A part of the types in the mapping is not supported: {type(types_mapping_part)}.'
                )

        __validate(self.__parsed_primitive_types, types_mapping)

    def get_text(self, list_and_dict_delimiter: str = '|') -> str | None:
        """Get string representation of the parsed data.

        Args:
            list_and_dict_delimiter (str, optional): Delimiter for joining list or dict values.

        Returns:
            str | None: String representation or None.
        """

        def __get_text(
            parsed_primitive_types: Any, list_and_dict_delimiter: str = '|'
        ) -> str | None:

            # np.nan for missing values
            if parsed_primitive_types != parsed_primitive_types:
                return ''

            if isinstance(parsed_primitive_types, dict):
                return list_and_dict_delimiter.join(
                    f'{key}: {__get_text(child)}' for key, child in parsed_primitive_types.items()
                )

            if isinstance(parsed_primitive_types, list):
                return list_and_dict_delimiter.join(
                    f'{__get_text(child)}' for child in parsed_primitive_types
                )

            return parsed_primitive_types.get_text()

        return __get_text(self.__parsed_primitive_types, list_and_dict_delimiter)
