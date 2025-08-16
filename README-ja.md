# apple_xml_tools

* NOTE: See [`README.md`](./README.md) for English README.

## 概要

このリポジトリは、Apple iPhotoの`AlbumData.xml`ファイルからデータを解析し抽出するためのツールを提供します。  
このツールは、`AlbumData.xml`の以下の2つのセクションを処理し、各iPhotoアルバム内のファイル一覧を抽出するように設計されています。

1. **`<key>Master Image List</key>`** – 写真・動画のマスターデータを含む辞書で、ファイルパスやメタデータなどを含みます。
1. **`<key>List of Albums</key>`** – マスター画像一覧内の画像への参照を含むアルバムの一覧です。

メインスクリプト [`parse_iphoto_album_data_xml.py`](./parse_iphoto_album_data_xml.py) は、`AlbumData.xml` を読み込み、以下のファイルを生成します。:

- マスター画像一覧を含む CSV ファイル
- アルバム一覧を含むCSVファイル
- 各アルバムの構成を一覧表示するTXTファイル

リポジトリには2つのサポートモジュールが含まれています。:

- [`apple_xml_tools/apple_xml_tools.py`](./apple_xml_tools/apple_xml_tools.py)  
  Apple固有のXML形式用のコアパースユーティリティを提供し、XMLのプリミティブ型（`<string>`、`<integer>`、`<dict>`など）のクラスや、XMLをPython構造に変換するメソッドを含みます。

- [`apple_xml_tools/iphoto_xml_tools.py`](./apple_xml_tools/iphoto_xml_tools.py)  
  `apple_xml_tools.py`を基盤に、iPhoto固有のXML構造をパースします。  
  マスター画像リスト、アルバムリストなどのモデルを定義しています。

---

## ライセンス & 開発者

- **ライセンス**: このリポジトリ内の[`LICENSE`](./LICENSE)を参照してください。
- **開発者**: U-MAN Lab. ([https://u-man-lab.com/](https://u-man-lab.com/))

---

## 1. インストールと使用方法

#### (1) Pythonをインストールする

[公式サイト](https://www.python.org/downloads/)を参照してPythonをインストールしてください。  
開発者が検証したバージョンより古い場合、スクリプトが正常に動作しない可能性があります。[`.python-version`](./.python-version)を参照してください。

#### (2) リポジトリをクローンする

```bash
git clone https://github.com/u-man-lab/parse_iphoto_album_data_xml.git
# gitコマンドを利用できない場合は、別の方法でスクリプトファイルとYAML設定ファイルを環境に配置してください。
cd ./parse_iphoto_album_data_xml
```

#### (3) Pythonライブラリをインストールする

開発者が検証したバージョンより古い場合、スクリプトが正常に動作しない可能性があります。
```bash
pip install --upgrade pip
pip install -r ./requirements.txt
```

#### (4) 入力用のXMLファイルを用意する

`AlbumData.xml` ファイルを `./data/` ディレクトリ（または別の場所）にコピーし、設定を適切に調整してください。  
通常、このファイルは次のパスに格納されています。  
```
/Users/<iMac User>/Pictures/iPhoto Library.photolibrary/AlbumData.xml
```

#### (5) 設定ファイルを編集する

設定ファイル[`configs/parse_iphoto_album_data_xml.yaml`](./configs/parse_iphoto_album_data_xml.yaml)を開き、ファイル内のコメントに従って値を編集します。

#### (6) スクリプトを実行する

```bash
python ./parse_iphoto_album_data_xml.py ./configs/parse_iphoto_album_data_xml.yaml
```

---

### 1.3. 期待される出力

成功した場合、標準エラー出力(stderr)に次のようなログが出力されます。:

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
（参考までに、開発者の環境では約1分かかりました。）

生成される「Master Image List」のCSVは次のような形式になります。:

```
,Caption,Comment,GUID,Roll,Rating,ImagePath,MediaType,ModDateAsTimerInterval,DateAsTimerInterval,DateAsTimerIntervalGMT,MetaModDateAsTimerInterval,ThumbPath,OriginalPath,latitude,longitude
13977,0043BestPhoto, ,cgueNZzXRcSUQLe3t57PJA,890,0,/path1/0043BestPhoto.jpg,Image,249772358.000000,-662806770.000000,-662774370.000000,378490569.461026,/path2/0043BestPhoto.jpg,,,
13975,0042BestPhoto, ,NqKGzc2hQRGqiDMINQbFTw,890,0,/path1/0042BestPhoto.jpg,Image,273723116.000000,140410079.000000,140442479.000000,378490569.457300,/path2/0042BestPhoto.jpg,,,
:
```

* [注意] 「Master Image List」にはiPhotoに格納している全ファイルが含まれている訳ではないようです。全ファイルのリストを取得したい場合は、以下のようなコマンドで直接取得するほうがよいです。
  ```bash
  TARGET_DIR='/Users/<Macのユーザ名>/Pictures/iPhoto Library.photolibrary/Masters'
  find "$TARGET_DIR" -type f > ./file_paths_list.txt
  ```

生成される「List of Albums」のCSVは次のような形式になります。:

```
AlbumId,AlbumName,Album Type,GUID,Master,TransitionSpeed,ShuffleSlides,KeyList,PhotoCount,Sort Order,SongPath,RepeatSlideShow,PlayMusic,SlideshowUseTitles,TransitionDirection,TransitionName,SecondsPerSlide,KeyPhotoKey,ProjectEarliestDateAsTimerInterval
8,最後の読み込み,Regular,lastImportAlbum,,1.000000,false,155101,1,1,/Applications/iPhoto.app/Contents/Frameworks/iLifeSlideshow.framework/Resources/Content/Audio/KenBurns.m4a,YES,YES,true,0,Default,1,,
2521,名称未設定アルバム,Regular,zaZVPaGqRUqWw9qHQGTFuA,,1.000000,false,14675|14677|14679|14681|14683|14685|14687|14689|14691|14693|14695|14697|14699|14701|14703|14705|14707|14709|14711|14717|14719|14721|14723|14725|14727|14729|14731|14733|14735|14737|14739|14741|14743|14745|14747|14749|14751|14753|14755|14757,40,1,/Applications/iPhoto.app/Contents/Resources/Music/Minuet in G.mp3,,,,,,,,
:
```

生成されるアルバム構成ファイル一覧のTXTは次のような形式になります。:

```
/path/2002_0428_110039AA.JPG
/path/2002_0428_110056AA.JPG
/path/2002_0428_122640AA.JPG
:
```

---

### 3. よくあるエラー

詳細については、スクリプトのソースコードを参照してください。よくあるエラーには以下のものが含まれます。:

- スクリプトに引数を渡していない
  ```
  2025-08-13 09:46:05,471 [ERROR] __main__: This script needs a config file path as an arg.
  ```
- 設定ファイルの値がおかしい
  ```
  2025-08-13 09:47:40,930 [ERROR] __main__: Failed to parse the config file.: "configs\group_file_paths_list_by_its_name.yaml"
  Traceback (most recent call last):
  :
  ```
