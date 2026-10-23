# Same weights, different model

**Post-release changes to chat templates and generation defaults in the 200 most-downloaded text-generation models on
Hugging Face**

Emanuele Rizzan, independent researcher (Italy). Draft, October 2026.

## In short

I looked at the commit history of the 200 most-downloaded text-generation models on the Hugging Face Hub. I only
used public metadata. I counted how often, after release, a model changes the files that decide how it behaves (chat
template, end-of-sequence token, generation defaults) while its weights stay byte-identical.

- **58 of 189 models (30.7%) changed real behavior with the same weights.** For large organisations it is **43 of 89
  (48.3%)**. "Real" means the rendered chat prompt changed in ordinary use, or the end-of-sequence token or a sampling
  default was modified.
- **35 models** changed their chat template in a way that changes what the model receives in a normal chat. For 11 of
  them the change came more than a week after release. Eleven is a small number: read it as a hint, not a result.
- The first change usually comes fast: the median is 0.75 days after release. Some come months later (119 days for one
  Llama-3.2 copy).
- Effect on scores, same weights, old vs new files, GSM8K: for Qwen2.5-0.5B-Instruct the average does not move
  (46.9% vs 45.9%, p = 0.49), but 256 of 1,319 answers differ between old and new files, against 127 that differ in a
  control run that only changes the batch order (numerical noise).
  Qwen2.5-1.5B-Instruct: 71.1% vs 73.1% (p = 0.07, 0.21 after correcting for three tests), with 192 answers that
  differ, against 74 in the noise control. DeepSeek-R1-Distill-Qwen-1.5B with the forced `<think>`: 75.0% vs 73.9% (p = 0.55), with no more
  differing answers than the noise control; I had predicted an improvement, and I was wrong, because the model already opens its reasoning by
  itself. So in none of the three cases is there a demonstrated effect on the average score.

The point is simple: on the Hub, a model name is not a version. If you evaluate "the same model" twice, a month apart,
you may be evaluating two different prompts.

## Why I looked

A study from October 2026 ("Silent Updates", N. Sarvesh S R) showed that in-place updates change what Hub
*classifiers* predict, and found that config-only edits did not change their predictions. The author wrote that
generative models "deserve separate study". This note is a first, exploratory look at generative models, for the files that matter most in chat models. It
shows that config-only edits can change the prompt a chat model receives; whether they change scores is a separate
question, tested here on three models only.

## What I did

1. **Census.** The 200 most-downloaded `text-generation` models on 20/10/2026. Ten were gated and not readable without a
   token; one had no weights. 189 were analysed. For each model I read every commit of `main` and the file list with
   hashes, through the public API. I did not download any weights.
2. **What counts.** Behavior files: `tokenizer_config.json`, `chat_template.jinja`, `chat_template.json`,
   `generation_config.json`, `special_tokens_map.json`. Release: the first commit with weights. "Same weights": the
   weight files of the release are all still there with the same hash.
3. **What changed inside the files.** I downloaded only the before/after versions of the changed files (6.3 MB). I
   rendered old and new templates with the `transformers` function on five fixed conversations, and compared the text.
4. **Effect on scores.** Three case studies on GSM8K test, greedy decoding, same weights (verified byte-identical
   against both commits), old vs new files, plus a control run that only changes the batch order, to measure numerical
   noise.
5. **Checks.** Everything was pre-registered, with dated deviations. An independent reviewer (a separate AI session
   with its own code) recomputed every number, found real definition errors, and I adopted the corrected numbers. A
   second reviewer (Codex) checked the corrections by reading the files.

## Results

| | All (189) | Large organisations (89) |
|---|---|---|
| Any behavior-file change after release, release weights unchanged | 98 (51.9%) | 68 (76.4%) |
| … more than 7 days after release | 63 (33.3%) | – |
| **Real behavior change** (see above) | **58 (30.7%)** | **43 (48.3%)** |
| Upper bound (counting file creations I could not verify) | 68 (36.0%) | 44 (49.4%) |

Template changes, counted per commit (126): 44 change ordinary chat input, 32 change only tool use, 33 change nothing
visible, 9 have no effect because another template file takes precedence, 8 cannot be compared.

Some concrete cases:

- `Qwen/Qwen2.5-0.5B-Instruct`, 2 days after release: the default system prompt went from "You are a helpful
  assistant." to "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
- `deepseek-ai/DeepSeek-R1` and its distilled models, 20 days after release: the answer is now forced to start with
  `<think>`.
- `unsloth/Llama-3.2-1B-Instruct`, 119 days after release: every conversation renders differently.

**Who is in the sample.** 51 of the 189 models are `Qwen/*`, and most of them changed. Without Qwen, the share with any
change is 40.6%. Original models change much more often (70.4%) than quantized copies (28.4%).

## Effect on scores

| Case | Change | Before | After | Discordant answers (before right / after right) | Noise control |
|---|---|---|---|---|---|
| A, Qwen2.5-0.5B-Instruct | default system prompt | 46.85% | 45.94% | 134 / 122, p = 0.49 | 63 / 64 |
| B, Qwen2.5-1.5B-Instruct | same change | 71.11% | 73.09% | 83 / 109, p = 0.07 (0.21 after Holm) | 34 / 40 |
| C, DeepSeek-R1-Distill-Qwen-1.5B | forced `<think>` (660 problems) | 75.00% | 73.94% | 55 / 48, p = 0.55 | 60 / 46 |

Greedy decoding, 1,319 GSM8K test problems (660 for C), exact McNemar test with Holm correction over the three
models, written down before generating. The noise control reruns the old files with the problems in a different order,
so only the numerics change. No case shows a demonstrated effect. The change does alter the format: in A, answers
without `\boxed{}` go from 22 to 55, which matters for evaluators that parse the answer strictly.

## What I would suggest

- **Evaluators:** pin the revision hash of the model, not only the name, and save the rendered prompt.
- **Model makers:** say in the commit message when a change alters what the model receives.
- **The Hub:** a small marker on a model page when a behavior file changed after release would help.

## Limits

- Only the main folder of each repository and only `main`. Gated models are missing, and they are all from large
  organisations.
- The census says that a file changed, and the rendering says that the prompt changed. Only the case studies say what
  that does to a score, and they are three models.
- 11 models "more than a week after release" is a small number.
- **What the score test can see.** With these sample sizes, the test only detects differences of about 2.5 points or
  more (2.3 in B, 3.2 in C). Differences of 1-2 points would go unnoticed, so "no demonstrated effect" is not "no
  effect": in B the 95% interval of the change goes from -0.1 to +4.0 points.
- **Case C was almost empty by construction.** The model already starts every answer with `<think>` by itself, so the
  new template adds what it would write anyway; the before/after difference is numerical, like the noise control.
  About a quarter of C's answers hit the 2,048-token limit.
- **Scoring.** The frozen scorer takes the first number inside `\boxed{}`. An independent recount from the raw answers,
  with its own code, differs on 8 of 9,894 answers (fractions and one mixed box), and no verdict changes.

## Related work

N. Sarvesh S R, "Silent Updates" (2026, classifiers). Castaño et al., MSR 2024 and TOSEM (evolution of models on the
Hub). Ajibode et al., FSE 2026 (versioning of releases). "Benchmark Drift" (2026, evaluation datasets). "Same Name,
Different Server" (2026, MCP servers). ggufdoctor (2026, GGUF templates). arXiv 2608.04714 (inference backends). The
Hugging Face blog post "Evaluations with Chat Formats".

## Data and code

Everything needed to check the numbers is in this repository:
- `code/`: the census (`censimento.py`, `passo0b.py`, `passo0c.py`), the score test (`effetto.py`, `catena_B_1e.sh`)
  and their tests.
- `data/census/`: the census of the 200 models (model list, plan, classification, rendering, weight checks, summary).
  `riassunto.json` holds the first version of the numbers. The numbers in this note are the corrected ones, adopted
  after the independent recount: see `PREMESSA.md`, section "Correzioni dopo il ricalcolo indipendente".
- `census_independent_recount/`: the independent recount of the census (report and code, in Italian), written by a
  separate AI session with its own code, which found the definition errors.
  `PREMESSA.md` cites its report by the original path, `strumenti/esperimenti_ricalcolo/RICALCOLO_STESSI_PESI.md`;
  here it is `census_independent_recount/RICALCOLO_STESSI_PESI.md`.
- `data/census/third_party_files.csv`: the 506 behavior files downloaded from the Hub (chat templates, tokenizer
  and generation configs). They belong to the model authors and have different licences, so they are not copied here.
  Each row gives the model, the commit, the file, its size, its SHA-256 and the download URL.
- `results/effect/`: the answers of the three case studies on GSM8K (before, after, noise control), the analysis, and an
  independent recount with its own code (`independent_recount/`).
- `PREMESSA.md`: the plan, written before the data, with every dated deviation (in Italian).
- `reviews/`: the independent review of the numbers (in Italian).

The code and the plan are published exactly as they ran, local paths included.

## How this was made

I directed this work and checked the results. The code, the analysis and this text were written with AI assistants
(Claude and Codex), and the checks were done by separate AI sessions with their own code.
