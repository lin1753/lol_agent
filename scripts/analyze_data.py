"""Analyze all data files and print structure summary."""
import json
import csv
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(r"D:\Project\lol_yolo\data")


def analyze_hero_eval():
    path = DATA_DIR / "05_game_heroes_in_view_eval.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("=" * 60)
    print(f"05_game_heroes_in_view_eval.json")
    print(f"  Type: list, Length: {len(data)}")
    item = data[0]
    print(f"  Keys: {list(item.keys())}")
    img = item["image"]
    print(f"  Image field: ...{img[-80:]}")
    print(f"  Conversations:")
    for conv in item["conversations"]:
        print(f"    [{conv['from']}]: {conv['value'][:200]}")
    print()
    return data


def analyze_minimap_eval():
    path = DATA_DIR / "06_game_minimap_heros_understanding_eval.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("=" * 60)
    print(f"06_game_minimap_heros_understanding_eval.json")
    print(f"  Type: list, Length: {len(data)}")
    item = data[0]
    print(f"  Keys: {list(item.keys())}")
    img = item["image"]
    print(f"  Image field: ...{img[-80:]}")
    print(f"  Conversations:")
    for conv in item["conversations"]:
        print(f"    [{conv['from']}]: {conv['value'][:300]}")
    print()
    return data


def analyze_hero_name():
    path = DATA_DIR / "hero_name.csv"
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    print("=" * 60)
    print(f"hero_name.csv")
    print(f"  Rows: {len(rows)} (including header)")
    print(f"  Header: {rows[0]}")
    print(f"  Sample rows:")
    for r in rows[1:6]:
        print(f"    {r}")
    print(f"  ...")
    for r in rows[-3:]:
        print(f"    {r}")
    print()
    return rows


def analyze_class_map():
    path = DATA_DIR / "class_map.txt"
    with open(path, "r", encoding="utf-16") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    print("=" * 60)
    print(f"class_map.txt (UTF-16)")
    print(f"  Total classes: {len(lines)}")
    for i, line in enumerate(lines):
        print(f"    [{i}] {line}")
    print()
    return lines


def analyze_label_xml():
    label_dir = DATA_DIR / "label_xml"
    xml_files = list(label_dir.glob("*.xml"))
    print("=" * 60)
    print(f"label_xml/")
    print(f"  Total XML files: {len(xml_files)}")
    if xml_files:
        # Read first XML to understand format
        import xml.etree.ElementTree as ET

        tree = ET.parse(xml_files[0])
        root = tree.getroot()
        print(f"  First file: {xml_files[0].name}")
        print(f"  Root tag: {root.tag}")
        # Print structure
        filename = root.find("filename")
        if filename is not None:
            print(f"  Filename: {filename.text}")
        size = root.find("size")
        if size is not None:
            w = size.find("width")
            h = size.find("height")
            print(f"  Size: {w.text}x{h.text}")
        objects = root.findall("object")
        print(f"  Objects count: {len(objects)}")
        for obj in objects[:3]:
            name = obj.find("name").text
            bbox = obj.find("bndbox")
            xmin = bbox.find("xmin").text
            ymin = bbox.find("ymin").text
            xmax = bbox.find("xmax").text
            ymax = bbox.find("ymax").text
            print(f"    - {name}: ({xmin},{ymin})-({xmax},{ymax})")
    print()


def analyze_images():
    img_dir = DATA_DIR / "images"
    jpg_files = list(img_dir.glob("*.jpg"))
    print("=" * 60)
    print(f"images/")
    print(f"  Total images: {len(jpg_files)}")
    if jpg_files:
        print(f"  First: {jpg_files[0].name}")
        print(f"  Last:  {jpg_files[-1].name}")
    print()


if __name__ == "__main__":
    analyze_images()
    analyze_label_xml()
    analyze_class_map()
    analyze_hero_name()
    analyze_hero_eval()
    analyze_minimap_eval()
