# Assessor Baseline (non-generative ablation)

This configuration does NOT make a second reviewer language-model call. It passes model-proposed observations to exact-quote validation, scoped correction checks, and the unchanged v2 revision controller. It cannot independently determine that a quote entails an observation, that generic operating instructions applied to the incident, or that a later test implies incident onset. Its non-generative status is intentional and must be recorded in evaluations.
