# Evidence Worker Baseline (non-generative ablation)

This configuration does NOT call the language model for source selection. It dispatches the Lead's admissible public-route action without a route critique or reranking call. The host still rejects requests to undiscovered custodians and duplicate exhausted routes. Its lack of a generative prompt is intentional; this file records the ablation contract rather than supplying a fake one-line agent instruction.
