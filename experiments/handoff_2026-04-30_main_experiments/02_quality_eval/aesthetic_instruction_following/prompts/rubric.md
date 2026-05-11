Instruction-following rubric:
- theme_alignment: Does the image visibly match the benchmark theme and genre?
- text_image_alignment: Does the image correspond to the specific scene text or current turn?
- style_following: Does it follow the requested image_style.type and visual prompt style?
- constraint_coverage: Does it cover the benchmark must-have constraints that are visually checkable?
- forbidden_violation: 5 means no forbidden issue; 1 means severe forbidden issue.
- instruction_following_score: holistic score from the above dimensions.

Aesthetic-consistency rubric:
- style_lighting_consistency: Across the group's images, are color, lighting, texture, and visual style stable?
- subject_attribute_consistency: Are protagonist/key subject visual attributes stable across turns?
- scene_world_consistency: Does the visual world stay in the same setting/genre without abrupt drift?
- composition_quality: Are the images clear, readable, and well composed?
- artifact_rate: 5 means no meaningful artifacts; 1 means severe or frequent artifacts.
- aesthetic_consistency_score: holistic cross-image consistency score.
