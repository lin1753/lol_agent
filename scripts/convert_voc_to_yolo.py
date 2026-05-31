"""Convert Pascal VOC XML annotations to YOLO format.

Usage:
    python scripts/convert_voc_to_yolo.py --data-dir D:/Project/lol_yolo/data --output-dir data/yolo_dataset
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml


# Full class map (48 classes from class_map.txt, UTF-16)
CLASS_NAMES = [
    "minimap_fov",       # 0  小地图视野框
    "chat_box",          # 1  聊天框
    "blue_kills",        # 2  蓝方击杀数
    "kda",               # 3  KDA
    "cs_count",          # 4  击杀小兵数量
    "game_time",         # 5  游戏时间
    "green_hp_hero",     # 6  绿色血条英雄
    "blue_hp_hero",      # 7  蓝色血条英雄
    "red_hp_hero",       # 8  红血血条英雄
    "red_minion",        # 9  红色小兵
    "red_cannon",        # 10 红色炮车
    "blue_minion",       # 11 蓝色小兵
    "blue_cannon",       # 12 蓝色炮车
    "blue_tower",        # 13 蓝方防御塔
    "red_tower",         # 14 红方防御塔
    "green_hp_bar",      # 15 绿色英雄血条
    "blue_hp_bar",       # 16 蓝色英雄血条
    "red_hp_bar",        # 17 红色英雄血条
    "jg_blue_buff",      # 18 野怪:蓝buff
    "jg_rock",           # 19 野怪:石头
    "jg_raptor",         # 20 野怪:六鸟
    "jg_red_buff",       # 21 野怪:红buff
    "jg_wolf",           # 22 野怪:三狼
    "jg_frog",           # 23 野怪:蛤蟆
    "jg_crab",           # 24 野怪:河蟹
    "baron",             # 25 纳什男爵
    "herald",            # 26 峡谷先锋
    "void_grub",         # 27 虚空巢虫
    "dragon",            # 28 元素龙
    "minimap",           # 29 小地图
    "ally_hero_icon",    # 30 队友英雄头像
    "enemy_hero_icon",   # 31 敌方英雄头像
    "passive_skill",     # 32 被动技能
    "q_skill",           # 33 Q技能
    "w_skill",           # 34 W技能
    "e_skill",           # 35 E技能
    "r_skill",           # 36 R技能
    "d_skill",           # 37 D技能
    "f_skill",           # 38 F技能
    "item",              # 39 装备
    "gold",              # 40 金币
    "player_hp_bar",     # 41 用户状态栏血条
    "player_level",      # 42 用户英雄等级
    "game_cursor",       # 43 游戏鼠标
    "blue_control_ward", # 44 蓝色真眼
    "blue_ward",         # 45 蓝色假眼
    "red_control_ward",  # 46 红色真眼
    "red_ward",          # 47 红色假眼
]

# Build name-to-index mapping for XML→YOLO conversion
_NAME_MAP: dict[str, int] = {}

# Load from class_map.txt at module level
def _load_class_map(data_dir: Path) -> dict[str, int]:
    """Build mapping from Chinese class names to indices."""
    class_map_path = data_dir / "class_map.txt"
    mapping = {}
    if class_map_path.exists():
        with open(class_map_path, "r", encoding="utf-16") as f:
            for idx, line in enumerate(f):
                name = line.strip()
                if name:
                    mapping[name] = idx
    return mapping


def convert_xml_to_yolo(
    xml_path: Path,
    img_width: int,
    img_height: int,
    name_to_idx: dict[str, int],
) -> list[str]:
    """Convert a single VOC XML to YOLO txt format lines.

    Returns list of YOLO format strings: "class_id cx cy w h" (normalized).
    """
    import xml.etree.ElementTree as ET

    tree = ET.parse(xml_path)
    root = tree.getroot()

    lines = []
    for obj in root.findall("object"):
        name_el = obj.find("name")
        if name_el is None or name_el.text is None:
            continue
        name = name_el.text.strip()

        class_id = name_to_idx.get(name)
        if class_id is None:
            # Try matching with spaces stripped
            for k, v in name_to_idx.items():
                if k.replace(" ", "") == name.replace(" ", ""):
                    class_id = v
                    break
            if class_id is None:
                continue  # Skip unknown classes

        bbox = obj.find("bndbox")
        if bbox is None:
            continue
        xmin = float(bbox.find("xmin").text)
        ymin = float(bbox.find("ymin").text)
        xmax = float(bbox.find("xmax").text)
        ymax = float(bbox.find("ymax").text)

        # Convert to YOLO format (normalized center x, center y, width, height)
        cx = ((xmin + xmax) / 2) / img_width
        cy = ((ymin + ymax) / 2) / img_height
        w = (xmax - xmin) / img_width
        h = (ymax - ymin) / img_height

        # Clamp to [0, 1]
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        w = max(0.0, min(1.0, w))
        h = max(0.0, min(1.0, h))

        lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

    return lines


def build_dataset(
    data_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.8,
) -> None:
    """Convert all VOC XMLs to YOLO format and organize into train/val split."""
    import xml.etree.ElementTree as ET

    name_to_idx = _load_class_map(data_dir)
    print(f"Loaded {len(name_to_idx)} class mappings")

    images_dir = data_dir / "images"
    labels_dir = data_dir / "label_xml"

    # Collect all image-xml pairs
    pairs = []
    for img_path in sorted(images_dir.glob("*.jpg")):
        xml_path = labels_dir / (img_path.stem + ".xml")
        if xml_path.exists():
            pairs.append((img_path, xml_path))

    print(f"Found {len(pairs)} image-XML pairs")

    # Shuffle and split
    import random
    random.seed(42)
    random.shuffle(pairs)
    split_idx = int(len(pairs) * train_ratio)
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]

    # Create output directories
    for split_name, split_pairs in [("train", train_pairs), ("val", val_pairs)]:
        img_out = output_dir / "images" / split_name
        lbl_out = output_dir / "labels" / split_name
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_path, xml_path in split_pairs:
            # Copy image
            shutil.copy2(img_path, img_out / img_path.name)

            # Get image dimensions from XML
            tree = ET.parse(xml_path)
            root = tree.getroot()
            size = root.find("size")
            w = int(size.find("width").text)
            h = int(size.find("height").text)

            # Convert and write label
            yolo_lines = convert_xml_to_yolo(xml_path, w, h, name_to_idx)
            label_file = lbl_out / (img_path.stem + ".txt")
            with open(label_file, "w", encoding="utf-8") as f:
                f.write("\n".join(yolo_lines))

        print(f"  {split_name}: {len(split_pairs)} samples")

    # Write dataset YAML for ultralytics
    dataset_yaml = {
        "path": str(output_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": {i: name for i, name in enumerate(CLASS_NAMES)},
        "nc": len(CLASS_NAMES),
    }
    yaml_path = output_dir / "dataset.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(dataset_yaml, f, default_flow_style=False, allow_unicode=True)
    print(f"Wrote dataset config: {yaml_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert VOC XML to YOLO format")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(r"D:\Project\lol_yolo\data"),
        help="Source data directory with images/ and label_xml/",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/yolo_dataset"),
        help="Output directory for YOLO dataset",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.8, help="Train split ratio"
    )
    args = parser.parse_args()
    build_dataset(args.data_dir, args.output_dir, args.train_ratio)


if __name__ == "__main__":
    main()
