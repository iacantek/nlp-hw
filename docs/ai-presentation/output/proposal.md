# Research Proposal Summary: Language Bias in Conflicting Multilingual RAG Evidence

**Author:** Alan Mattia Cantekin (Hanyang University)  
**Source Document:** [Language_Bias_in_Conflicting_Multilingual_RAG_Evidence.pdf](file:///Users/iacantek/Workspace/NLP/nlp-hw/docs/hw-1-presentation/Language_Bias_in_Conflicting_Multilingual_RAG_Evidence.pdf)

---

## 1. The Three Core Pillars for the Talk

### 1.1 Motivation
* **Why This Problem Matters:**
  > "Recent studies demonstrate that multilingual RAG (mRAG) systems preferentially cite English documents (Ki et al. 2025) and that English acts as a “semantic attractor” (Li, Xu, and Xie 2025) during multilingual generation and reasoning. Furthermore, language preference can lead models to cite irrelevant English documents over relevant non-English sources, which risks marginalizing non-English sources and reinforcing language hierarchies (Ki et al. 2025)." *(Section 2.2, p. 1)*
* **Gap in Prior Work:**
  > "However, it remains unclear whether models actually trust English facts more when sources directly contradict each other. While unexamined citation biases may degrade system performance across languages (Ki et al. 2025; Park and Lee 2025), the claim that English misinformation could override accurate Korean facts is not directly proven by the literature. Finally, by pairing contradictory claims across English and Korean and swapping their languages, this study tests whether citation bias extends into actual factual trust." *(Section 2.2, p. 1)*

### 1.2 Research Question
> "When a multilingual LLM is presented with directly conflicting factual claims in English and Korean, does it systematically favor the claim written in English regardless of the query language and its prior knowledge?" *(Section 1.2, p. 1)*

### 1.3 Hypothesis
> "Multilingual LLMs exhibit a systematic language preference bias favoring English and the query language during retrieval, reranking, and citation (Ki et al. 2025; Wang et al. 2026): when presented with directly conflicting factual claims in English and Korean, the model will systematically favor the claim written in English across both English and Korean queries, regardless of factual accuracy or prior knowledge." *(Section 2.1, p. 1)*

---

## 2. Mapping onto the Research Loop

| Stage | Proposal Details | Source / Status |
| :--- | :--- | :--- |
| **Prediction** | When evaluated on a counterbalanced pair `[English: Claim A, Korean: Claim B]` and its language-swapped counterpart `[Korean: Claim A, English: Claim B]`, the model will select **Claim A** in the first pair and switch to **Claim B** in the second pair under **both** English and Korean queries.<br><br>**Falsification Conditions:**<br>1. Model consistently selects Claim A in both pairs (decision driven by prior knowledge / factual accuracy).<br>2. Model favors the English claim on English queries but switches to the Korean claim on Korean queries (query-language alignment outweighs English authority). | Section 2.3 (p. 1) |
| **Design** | **Models:** `Qwen-2.5-7B-Instruct` and `Llama-3.1-8B-Instruct` (inference only, no training; run on single NVIDIA T4 GPU via free-tier Google Colab with Python 3.10+, PyTorch, Hugging Face).<br><br>**Dataset:** 150 culturally neutral QA pairs filtered from the MKQA benchmark (aligned English & Korean questions and ground-truth entity answers). Each true entity (Claim A) is paired with a plausible false entity of the same type (Claim B) inside uniform declarative English and Korean sentence templates.<br><br>**Five Experimental Controls:**<br>1. *Ordering bias:* Shuffle which language appears first in the prompt.<br>2. *Translation artifacts:* Use uniform declarative sentence templates.<br>3. *Prior knowledge bias:* Test closed-book (no context) in both languages first to separate known vs. unknown facts.<br>4. *Cultural entity bias:* Filter for culturally neutral facts.<br>5. *Query language alignment:* Test every claim pair under both English and Korean queries. | Sections 2.3–2.4 (pp. 1–2), Sections 4.1–4.4 (pp. 2–3) |
| **Planned Analysis** | **Qualitative logic specified in proposal:** Compare model claim selection across `[English: Claim A, Korean: Claim B]` vs. `[Korean: Claim A, English: Claim B]`, stratified by query language (EN vs. KO) and closed-book prior knowledge (known vs. unknown).<br><br>**Missing in original PDF (resolved below in Section 5):**<br>- **Missing in PDF:** Exact evaluation metric definitions (e.g., English preference rate, flip rate, exact entity match vs. token log-probability comparison).<br>- **Missing in PDF:** Statistical significance testing plan (e.g., McNemar's test, binomial test, or mixed-effects model) and numeric threshold to declare the hypothesis supported.<br>- **Missing in PDF:** Handling of abstentions, hedging, or conflict-detection outputs (e.g., when the model outputs *"The sources contradict each other"*). | Partially in Section 2.3–2.4; **statistical & scoring methodology missing in PDF (resolved in Section 5)** |
| **Expected Claim** | Language preference in multilingual LLMs is not merely a surface retrieval or citation artifact—it extends into **factual trust** during conflict resolution, such that English misinformation systematically overrides accurate Korean evidence across query languages and prior knowledge states. | Sections 1.1, 2.1, 2.2 (p. 1) |

---

## 3. Cited Papers

| Authors | Year | Venue (as cited in Proposal) | What You Claim It Shows |
| :--- | :--- | :--- | :--- |
| **Ki, Dayeon et al.** | 2025 | `DOI: 10.48550/arXiv.2509.13930` *(arXiv preprint; conference/journal venue not listed)* | LLMs show a systematic citation bias toward English documents in mRAG ("linguistic nepotism"); next-token citation predictions for English have higher accuracy, lower Shannon entropy, and lower perplexity; models trade off true document relevance for language preference (citing irrelevant English over relevant non-English sources), risking marginalizing non-English sources and degrading cross-lingual performance. |
| **Li, Bo, Zhenghua Xu, and Rui Xie** | 2025 | `DOI: 10.48550/arXiv.2511.09984` *(arXiv preprint; conference/journal venue not listed)* | Predominance of English in pre-training makes English a default "semantic attractor," causing decoder-level collapse and output "language drift" into unintended languages when processing cross-lingual evidence; proposed Soft Constrained Decoding (SCD) to softly penalize non-target tokens and preserve output language consistency. |
| **Park, Jeonghyun and Hwanhee Lee** | 2025 | `DOI: 10.48550/arXiv.2502.11175` *(arXiv preprint; conference/journal venue not listed)* | Proposed MultiLingualRankShift (MLRS) to measure rank improvements when non-query passages are translated into the query language; established that retrievers favor high-resource and query-matching languages while generators favor query languages and Latin scripts, causing cross-lingual answer inconsistencies. |
| **Qi, Jirui, Raquel Fernández, and Arianna Bisazza** | 2025 | `DOI: 10.18653/v1/2025.mrl-main.15` *(MRL 2025 Workshop at EMNLP; venue name omitted in bibliography)* | Evaluated multilingual context utilization to separate input comprehension from output generation; showed LLMs can extract relevant facts from cross-lingual passages but struggle to generate full answers in the target language, with query-language distracting passages strongly harming accuracy. |
| **Wang, Dan et al.** | 2026 | `DOI: 10.48550/arXiv.2604.20199` *(arXiv preprint; conference/journal venue not listed)* | Showed mRAG rerankers systematically favor English and the query's native language while suppressing key documents in other languages; proposed Language-Agnostic Utility-driven Reranker Alignment (LAURA) to align evidence selection with downstream generation quality rather than surface relevance signals. |

---

## 4. Discrepancies, Ambiguous Numbers, and Scope Audit

### 4.1 Internal Disagreements & Number Ambiguities
1. **Unresolved Combinatorics on Dataset Size (150 items vs. total prompt evaluations):**
   * Section 4.3 specifies **150** question-answer pairs, while Sections 2.3 and 2.4 layer multiple factors without stating whether they are fully crossed or randomly sampled:
     * **2** closed-book baseline prompts per item (EN query, KO query) = $300$ prompts.
     * **2** language-swapped pairs (`[EN: A, KO: B]` vs. `[KO: A, EN: B]`) $\times$ **2** query languages (EN vs. KO) $\times$ **2** prompt orderings (EN-first vs. KO-first, if fully crossed rather than randomly shuffled once).
   * Depending on whether prompt order is fully crossed ($2 \times 2 \times 2 = 8$ context prompts/item) or randomly assigned ($2 \times 2 = 4$ context prompts/item), 150 QA pairs equate to either **$900$** or **$1{,}500$** evaluations per model (**$1{,}800$** or **$3{,}000$** across both models).
2. **Tension Inside the Primary Hypothesis (Section 2.1 vs. Section 2.3):**
   * Section 2.1 begins by stating models exhibit a bias *"favoring English **and the query language**"* (two competing biases on Korean queries), yet immediately predicts that English will win across **both** English and Korean queries, and Section 2.3 classifies query-language preference as **falsification condition #2**. The talk should frame these clearly as **competing hypotheses** (English authority vs. Query-language alignment vs. Prior knowledge) rather than lumping query-language bias into the premise of the primary hypothesis.

### 4.2 Scope: Too Vague
1. **Response Extraction & Contradiction Handling:**
   * How is a model's choice of "Claim A" vs. "Claim B" extracted from `Qwen-2.5-7B-Instruct` and `Llama-3.1-8B-Instruct`? (e.g., forced multiple-choice prompt, exact string match on free-form generation, or next-token log-probabilities?)
   * Instruction-tuned models often notice explicit contradictions in a 2-sentence context and reply *"The provided documents conflict: one says A and the other says B."* The proposal does not specify how abstentions or "both" responses are prevented or scored.
2. **Template & Plausible False Entity Construction (Section 4.3):**
   * MKQA questions span diverse answer types (dates, numbers, people, locations). Converting a question + entity into a "uniform declarative sentence template" in both English and Korean requires either question-specific templates or restricted relation types, plus handling Korean morphosyntactic particle alternations (`은/는`, `이/가`, `을/를`) depending on final consonants (batchim).
3. **Decision Thresholds (Section 2.3):**
   * The falsifiability rule is stated deterministically (*"If the model selects Claim A in the first pair but switches to Claim B in the second pair..."*), without defining the aggregate metric or statistical test across the 150 examples.

### 4.3 Scope: Too Small
1. **Subgroup Sample Size After Prior-Knowledge Stratification:**
   * Once **150** QA pairs are partitioned by closed-book outcomes (e.g., *Unknown in both*, *Known in EN only*, *Known in KO only*, *Known in both*), some buckets may contain fewer than 15–25 items, leaving insufficient statistical power to claim behavior occurs *"regardless of prior knowledge."*
2. **Single Language Pair & Script Confound:**
   * Testing only English (Latin script) vs. Korean (Hangul) cannot separate **English-specific dominance** from **Latin-script preference** (which Park and Lee 2025 identify) or general high- vs. medium-resource competence gaps.
3. **Lack of a Korean-Strong Model Baseline:**
   * Both `Llama-3.1-8B-Instruct` (English-centric) and `Qwen-2.5-7B-Instruct` (Chinese/English-centric) have weaker Korean pretraining than English. Without a Korean-centric model (or a high-resource Latin-script control language), favoring English could partly reflect weaker Korean reading comprehension.

### 4.4 Scope: Potentially Too Big (If Unconstrained)
1. **Manual Authoring of 150 Parallel Declarative Templates:**
   * If 150 arbitrary MKQA questions are converted by hand into natural, parallel English and Korean declarative statements with hand-curated false entities, data preparation will take disproportionate effort relative to running the inference. Restricting the 150 items to 2–3 structured entity/relation categories (e.g., birth years, capital cities, numerical measurements) makes template generation fast and uniform.

---

## 5. Author-Clarified Decisions for the Presentation

1. **Response Measurement & Contradiction Handling:**
   * Force a single choice via prompt instruction and score using **both exact entity match and answer-token log-probabilities** (comparing `log P(Claim A)` vs. `log P(Claim B)` to avoid abstention/hedging ambiguity).
2. **Full Experimental Combinatorics:**
   * Fully cross all factors across the **150** MKQA items:
     * **Context runs:** $2 \text{ (language swaps)} \times 2 \text{ (query languages)} \times 2 \text{ (prompt orders)} = 8\text{ runs/item}$ ($1{,}200$ runs/model).
     * **Closed-book baseline runs:** $2 \text{ (query languages)} = 2\text{ runs/item}$ ($300$ runs/model).
     * **Total:** **$10$ runs per item** = **$1{,}500$ runs per model** (**$3{,}000$ total inference calls** across `Qwen-2.5-7B-Instruct` and `Llama-3.1-8B-Instruct`).
3. **Dataset & Template Construction Scope:**
   * Restrict MKQA filtering to **2–3 structured entity types** (e.g., years/dates, numbers, locations) and construct Claim B by swapping entities from the same category into fixed parallel English and Korean declarative templates.
4. **Planned Analysis Metric & Statistical Test:**
   * Define **English Preference Rate (EPR)** as the proportion of counterbalanced pairs where the model flips its selection (`Claim A` $\rightarrow$ `Claim B`) to follow the English-language claim, and test against the $50\%$ chance baseline using a **binomial / McNemar's test** across both English and Korean queries (stratified by closed-book prior knowledge).
