from pathlib import Path
import json
from typing import List, Dict, Any

from src.stage2.aggregate.aggregate_by_header import aggregate_blocks_by_header
from src.stage2.structure.stage2A1_units import build_semantic_units
from src.utils.llm_client_realtime import LLMClientRealtime
from src.stage2.structure.stage2A2_units import assign_final_units
from src.stage2.structure.stage2B_pack import stage2B_pack_units
from src.stage2.engage.extract_engage import extract_engage_data
from src.stage2.engage2.extract_engage2 import extract_engage2
from src.stage2.bullets.extract_bullets import extract_bullets
from src.stage2.images.select_images import select_images
from src.stage2.labels.generate_labels import generate_labels
from src.stage2.quiz.generate_quiz import generate_quiz
from src.stage2.merge.merge_stage2 import merge_stage2


TARGET_HEADER = "Symptoms of Huntington's disease"

stage1_dir = Path("data/processed/stage1_blocks")
out_dir = Path("data/tmp/stage2_test")
out_dir.mkdir(parents=True, exist_ok=True)

# Stage 2A0
all_headers = aggregate_blocks_by_header(
    header=TARGET_HEADER,
    stage1_dir=stage1_dir,
)
header_doc = next(iter(all_headers.values()))
print("🔎 Using header:", header_doc["header"])

(out_dir / "A0_aggregated.json").write_text(
    json.dumps(header_doc, indent=2, ensure_ascii=False)
)

print("✅ Stage 2A0 OK")

# Stage 2A1
llm = LLMClientRealtime()

units_A1 = build_semantic_units(
    header=header_doc["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    llm=llm,
)

(out_dir / "A1_units.json").write_text(
    json.dumps(units_A1, indent=2, ensure_ascii=False)
)

print("✅ Stage 2A1 OK")

units_A2 = assign_final_units(
    header=header_doc["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    llm=llm,
)

(out_dir / "A2_units.json").write_text(
    json.dumps(units_A2, indent=2, ensure_ascii=False)
)

print("✅ Stage 2A2 OK")

# -------------------------
# Stage 2B — Page Packing
# -------------------------
packed = stage2B_pack_units(
    unit_plan=units_A2,
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
)

(out_dir / "B_packed.json").write_text(
    json.dumps(packed, indent=2, ensure_ascii=False)
)

print("✅ Stage 2B OK — STRUCTURE FROZEN")

# -------------------------
# extract_engage
# -------------------------
engage_data = extract_engage_data(
    header=packed["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    units=packed["units"],
)

(out_dir / "engage.json").write_text(
    json.dumps(engage_data, indent=2, ensure_ascii=False)
)

print("✅ extract_engage OK")

# -------------------------
# extract_engage2
# -------------------------
engage2_data = extract_engage2(
    header=packed["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    units=packed["units"],
    llm=llm,
)

(out_dir / "engage2.json").write_text(
    json.dumps(engage2_data, indent=2, ensure_ascii=False)
)

print("✅ extract_engage2 OK")

# -------------------------
# extract_bullets
# -------------------------
bullet_data = extract_bullets(
    header=packed["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    units=packed["units"],
    llm=llm,
)

(out_dir / "bullets.json").write_text(
    json.dumps(bullet_data, indent=2, ensure_ascii=False)
)

print("✅ extract_bullets OK")

# -------------------------
# select_images
# -------------------------

# TEMP: empty image catalog for test
image_catalog: List[Dict[str, Any]] = []

images_data = select_images(
    header=packed["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    units=packed["units"],
    image_catalog=image_catalog,
    llm=llm,
)

(out_dir / "images.json").write_text(
    json.dumps(images_data, indent=2, ensure_ascii=False)
)

print("✅ select_images OK")

# -------------------------
# generate_labels
# -------------------------

labels_data = generate_labels(
    header=packed["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    units=packed["units"],
    llm=llm,
)

(out_dir / "labels.json").write_text(
    json.dumps(labels_data, indent=2, ensure_ascii=False)
)

print("✅ generate_labels OK")

# -------------------------
# generate_quiz
# -------------------------

quiz_data = generate_quiz(
    header=packed["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    units=packed["units"],
    llm=llm,
)

(out_dir / "quiz.json").write_text(
    json.dumps(quiz_data, indent=2, ensure_ascii=False)
)

print("✅ generate_quiz OK")

# -------------------------
# merge_stage2 (FINAL)
# -------------------------

final_output = merge_stage2(
    header=packed["header"],
    paragraphs=[p["text"] for p in header_doc["paragraphs"]],
    units=packed["units"],
    engage_data=engage_data,
    engage2_data=engage2_data,
    labels_data=labels_data,
    images_data=images_data,
    bullet_data=bullet_data,
    quiz_data=quiz_data,
    notes=None,
)

(out_dir / "FINAL_module.json").write_text(
    json.dumps(final_output, indent=2, ensure_ascii=False)
)

print("🎉 Stage 2 COMPLETE — FINAL MODULE GENERATED")
