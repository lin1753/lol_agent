"""Build center_yolo dataset with 29 classes.

Extracts detections from VOC XML across the full 1920x1080 frame,
converts to YOLO format with the selected classes. Keeps all detections
across the full frame (not just center ROI) so YOLO learns the full layout.

Usage:
    python scripts/build_center_dataset.py
"""

from __future__ import annotations

import argparse
import random
import xml.etree.ElementTree as ET
from pathlib import Path

# 31 selected classes — full frame detection
CENTER_CLASSES = {
    "小地图视野框": 0,
    "KDA": 1,
    "游戏时间": 2,
    "绿色血条英雄": 3,
    "蓝色血条英雄": 4,
    "红血血条英雄": 5,
    "红色小兵": 6,
    "红色炮车": 7,
    "蓝色小兵": 8,
    "蓝色炮车": 9,
    "蓝方防御塔": 10,
    "红方防御塔": 11,
    "绿色英雄血条": 12,
    "蓝色英雄血条": 13,
    "红色英雄血条": 14,
    "纳什男爵": 15,
    "峡谷先锋": 16,
    "虚空巢虫": 17,
    "元素龙": 18,
    "小地图": 19,
    "Q技能": 20,
    "W技能": 21,
    "E技能": 22,
    "R技能": 23,
    "D技能": 24,
    "F技能": 25,
    "金币": 26,
    "用户状态栏血条": 27,
    "用户英雄等级": 28,
    "队友英雄头像": 29,
    "敌方英雄头像": 30,
    "装备": 31,
}

CENTER_CLASS_NAMES = [
    "minimap_fov", "kda", "game_time",
    "green_hp_hero", "blue_hp_hero", "red_hp_hero",
    "red_minion", "red_cannon", "blue_minion", "blue_cannon",
    "blue_tower", "red_tower",
    "green_hp_bar", "blue_hp_bar", "red_hp_bar",
    "baron", "herald", "void_grub", "dragon",
    "minimap",
    "q_skill", "w_skill", "e_skill", "r_skill", "d_skill", "f_skill",
    "gold", "player_hp_bar", "player_level",
    "ally_hero_icon", "enemy_hero_icon", "equipment",
]


def convert_xml(xml_path: Path) -> list[str]:
    """Convert a single VOC XML to YOLO format."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    size = root.find("size")
    img_w = int(size.find("width").text)
    img_h = int(size.find("height").text)

    lines = []
    for obj in root.findall("object"):
        name_el = obj.find("name")
        if name_el is None:
            continue
        name = name_el.text.strip()

        class_id = CENTER_CLASSES.get(name)
        if class_id is None:
            continue

        bbox = obj.find("bndbox")
        if bbox is None:
            continue
        xmin = float(bbox.find("xmin").text)
        ymin = float(bbox.find("ymin").text)
        xmax = float(bbox.find("xmax").text)
        ymax = float(bbox.find("ymax").text)

        # Convert to YOLO normalized
        cx = ((xmin + xmax) / 2) / img_w
        cy = ((ymin + ymax) / 2) / img_h
        w = (xmax - xmin) / img_w
        h = (ymax - ymin) / img_h

        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        w = max(0.0, min(1.0, w))
        h = max(0.0, min(1.0, h))

        lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

    return lines


def build_dataset(data_dir: Path, output_dir: Path, train_ratio: float = 0.8) -> None:
    """Build dataset from VOC XML."""
    images_dir = data_dir / "images"
    labels_dir = data_dir / "label_xml"

    pairs = []
    for img_path in sorted(images_dir.glob("*.jpg")):
        xml_path = labels_dir / (img_path.stem + ".xml")
        if xml_path.exists():
            pairs.append((img_path, xml_path))

    print(f"Found {len(pairs)} image-XML pairs")

    # Filter: keep images that have at least one of our classes
    valid_pairs = []
    class_counts = {i: 0 for i in range(len(CENTER_CLASS_NAMES))}

    for img_path, xml_path in pairs:
        lines = convert_xml(xml_path)
        if lines:
            valid_pairs.append((img_path, xml_path))
            for line in lines:
                cls_id = int(line.split()[0])
                class_counts[cls_id] += 1

    print(f"Images with detections: {len(valid_pairs)}")
    print("Class distribution:")
    for cls_id, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  [{cls_id:2d}] {CENTER_CLASS_NAMES[cls_id]:20s}: {count}")

    # Shuffle and split
    random.seed(42)
    random.shuffle(valid_pairs)
    split_idx = int(len(valid_pairs) * train_ratio)
    train_pairs = valid_pairs[:split_idx]
    val_pairs = valid_pairs[split_idx:]

    # Create output
    import cv2
    import yaml

    for split_name, split_pairs in [("train", train_pairs), ("val", val_pairs)]:
        img_out = output_dir / "images" / split_name
        lbl_out = output_dir / "labels" / split_name
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_path, xml_path in split_pairs:
            # Copy full image (YOLO will handle full-frame detection)
            import shutil
            shutil.copy2(img_path, img_out / img_path.name)

            lines = convert_xml(xml_path)
            label_file = lbl_out / (img_path.stem + ".txt")
            with open(label_file, "w") as f:
                f.write("\n".join(lines))

        print(f"  {split_name}: {len(split_pairs)} samples")

    # Write YAML
    dataset_yaml = {
        "path": str(output_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": {i: name for i, name in enumerate(CENTER_CLASS_NAMES)},
        "nc": len(CENTER_CLASS_NAMES),
    }
    yaml_path = output_dir / "dataset.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(dataset_yaml, f, default_flow_style=False, allow_unicode=True)
    print(f"Wrote: {yaml_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 29-class center dataset")
    parser.add_argument("--data-dir", type=Path, default=Path(r"D:\Project\lol_yolo\data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/center_29_dataset"))
    parser.add_argument("--train-ratio", type=float, default=0.8)
    args = parser.parse_args()
    build_dataset(args.data_dir, args.output_dir, args.train_ratio)


if __name__ == "__main__":
    main()
