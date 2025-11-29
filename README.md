# apple_xml_tools

* NOTE: 日本語版のREADMEは[`README-ja.md`](./README-ja.md)を参照。

## Overview

This repository provides tools for parsing and extracting data from Apple iPhoto's `AlbumData.xml` file.  
It is designed to process two sections below of `AlbumData.xml`, and to extract files list in each iPhoto album.

1. **`<key>Master Image List</key>`** – A dictionary of master data of photos & videos, including paths, metadata, etc.
2. **`<key>List of Albums</key>`** – A list of albums, each containing references to images in the master image list.

The main script, [`parse_iphoto_album_data_xml.py`](./parse_iphoto_album_data_xml.py), reads an `AlbumData.xml` and generates:

- A CSV file containing the master image list.
- A CSV file containing the list of albums.
- TXT files listing the composition of each album.

The repository includes two supporting modules:

- [`apple_xml_tools/apple_xml_tools.py`](./apple_xml_tools/apple_xml_tools.py)  
  Provides core parsing utilities for Apple-specific XML formats, including classes for XML primitive types (`<string>`, `<integer>`, `<dict>`, etc.) and methods for converting XML into Python structures.

- [`apple_xml_tools/iphoto_xml_tools.py`](./apple_xml_tools/iphoto_xml_tools.py)  
  Builds on `apple_xml_tools.py` to parse iPhoto-specific XML structures.  
  It defines models for the master image list, the list of albums, etc.

---

## License & Developer

- **License**: See [`LICENSE`](./LICENSE) in this repository.
- **Developer**: U-MAN Lab. ([https://u-man-lab.com/](https://u-man-lab.com/))

★The scripts in this repository were implemented for use in the following article.★  
[iPhotoの写真・動画＆アルバムをNASに移行しました。 | U-MAN Lab.](https://u-man-lab.com/photos-videos-albums-migration-from-iphoto-to-nas/?utm_source=github&utm_medium=social&utm_campaign=apple_xml_tools)

---

## 1. Installation & Usage

### (1) Install Python

Install Python from the [official Python website](https://www.python.org/downloads/).  
The scripts may not work properly if the version is lower than the verified one. Refer to the [`.python-version`](./.python-version).

### (2) Clone the Repository

```bash
git clone https://github.com/u-man-lab/parse_iphoto_album_data_xml.git
# If you don't have "git", copy the scripts and YAMLs manually to your environment.
cd ./parse_iphoto_album_data_xml
```

### (3) Install Python Dependencies

The scripts may not work properly if the versions are lower than the verified ones.
```bash
pip install --upgrade pip
pip install -r ./requirements.txt
```

### (4) Prepare the Input XML File

Copy your `AlbumData.xml` file into the `./data/` directory (or another location, adjusting the config accordingly).  
Normally, the file is located at the following path.  
```
/Users/<iMac User>/Pictures/iPhoto Library.photolibrary/AlbumData.xml
```

### (5) Edit the Configuration File

Open the configuration file [`configs/parse_iphoto_album_data_xml.yaml`](./configs/parse_iphoto_album_data_xml.yaml) and edit the values according to the comments in the file.

### (6) Run the Script

```bash
python ./parse_iphoto_album_data_xml.py ./configs/parse_iphoto_album_data_xml.yaml
```

---

## 2. Expected Output

If the script runs successfully, stderr will include logs like:

```
2025-08-15 13:21:36,850 [INFO] __main__: "parse_iphoto_album_data_xml.py" start!
2025-08-15 13:21:36,868 [INFO] __main__: Processing the "Master Image List" part in an XML...
2025-08-15 13:21:36,869 [INFO] apple_xml_tools.apple_xml_tools: Reading XML file "data\AlbumData.xml"...
2025-08-15 13:22:13,908 [INFO] apple_xml_tools.iphoto_xml_tools: Writing CSV file "results\iphoto_master_image_list.csv"...
2025-08-15 13:22:15,572 [INFO] __main__: Processing the "List of Albums" part in an XML...
2025-08-15 13:22:15,573 [INFO] apple_xml_tools.apple_xml_tools: Reading XML file "data\AlbumData.xml"...
2025-08-15 13:22:21,229 [INFO] apple_xml_tools.iphoto_xml_tools: Writing CSV file "results\iphoto_list_of_albums_only_regular.csv"...
2025-08-15 13:22:21,239 [INFO] __main__: Joining master images info to albums...
2025-08-15 13:22:21,353 [INFO] apple_xml_tools.iphoto_xml_tools: Writing TXT file "results\iphoto_album_composition\000008_Regular_最後の読み込み.txt"...
2025-08-15 13:22:21,371 [INFO] apple_xml_tools.iphoto_xml_tools: Writing TXT file "results\iphoto_album_composition\002521_Regular_名称未設定アルバム.txt"...
:
2025-08-15 13:22:28,858 [INFO] apple_xml_tools.iphoto_xml_tools: Writing TXT file "results\iphoto_album_composition\003672_Regular_未分類.txt"...
2025-08-15 13:22:28,859 [INFO] apple_xml_tools.iphoto_xml_tools: Writing TXT file "results\iphoto_album_composition\012281_Regular_プリント.txt"...
2025-08-15 13:22:28,863 [INFO] __main__: "parse_iphoto_album_data_xml.py" done!
```
(For reference, it took about 1min. to process on developers environment.)

The resulting CSV of master image list is like:

```
,Caption,Comment,GUID,Roll,Rating,ImagePath,MediaType,ModDateAsTimerInterval,DateAsTimerInterval,DateAsTimerIntervalGMT,MetaModDateAsTimerInterval,ThumbPath,OriginalPath,latitude,longitude
13977,0043BestPhoto, ,cgueNZzXRcSUQLe3t57PJA,890,0,/path1/0043BestPhoto.jpg,Image,249772358.000000,-662806770.000000,-662774370.000000,378490569.461026,/path2/0043BestPhoto.jpg,,,
13975,0042BestPhoto, ,NqKGzc2hQRGqiDMINQbFTw,890,0,/path1/0042BestPhoto.jpg,Image,273723116.000000,140410079.000000,140442479.000000,378490569.457300,/path2/0042BestPhoto.jpg,,,
:
```

* [Note] The "Master Image List" does not seem to include all files stored in iPhoto. If you want to obtain a list of all files, it is better to obtain it directly using a command like following.
  ```bash
  TARGET_DIR='/Users/<iMac User>/Pictures/iPhoto Library.photolibrary/Masters'
  find "$TARGET_DIR" -type f > ./file_paths_list.txt
  ```

The resulting CSV of list of albums is like:

```
AlbumId,AlbumName,Album Type,GUID,Master,TransitionSpeed,ShuffleSlides,KeyList,PhotoCount,Sort Order,SongPath,RepeatSlideShow,PlayMusic,SlideshowUseTitles,TransitionDirection,TransitionName,SecondsPerSlide,KeyPhotoKey,ProjectEarliestDateAsTimerInterval
8,最後の読み込み,Regular,lastImportAlbum,,1.000000,false,155101,1,1,/Applications/iPhoto.app/Contents/Frameworks/iLifeSlideshow.framework/Resources/Content/Audio/KenBurns.m4a,YES,YES,true,0,Default,1,,
2521,名称未設定アルバム,Regular,zaZVPaGqRUqWw9qHQGTFuA,,1.000000,false,14675|14677|14679|14681|14683|14685|14687|14689|14691|14693|14695|14697|14699|14701|14703|14705|14707|14709|14711|14717|14719|14721|14723|14725|14727|14729|14731|14733|14735|14737|14739|14741|14743|14745|14747|14749|14751|14753|14755|14757,40,1,/Applications/iPhoto.app/Contents/Resources/Music/Minuet in G.mp3,,,,,,,,
:
```

The resulting album composition TXT is like:

```
/path/2002_0428_110039AA.JPG
/path/2002_0428_110056AA.JPG
/path/2002_0428_122640AA.JPG
:
```

---

## 3. Common Errors

For full details, see the script source. Common errors include:

- Missing config path argument
  ```
  2025-08-13 09:46:05,471 [ERROR] __main__: This script needs a config file path as an arg.
  ```
- Invalid or missing config field
  ```
  2025-08-13 09:47:40,930 [ERROR] __main__: Failed to parse the config file.: "configs\group_file_paths_list_by_its_name.yaml"
  Traceback (most recent call last):
  :
  ```
